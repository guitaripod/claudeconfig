import { describe, expect, test } from "bun:test"
import { spawnSync } from "node:child_process"
import { mkdtempSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { verdict as ompVerdict } from "../../omp/extensions/follow-through.ts"
import { verdict as opencodeVerdict } from "../plugin/follow-through.js"

const HOOK = join(import.meta.dir, "../../hooks/follow-through.sh")

const OFFERS = [
  "Fixed and tested. The two local commits still need your go-ahead to push.",
  "Built, 43 tests pass, clippy clean. Want me to push?",
  'Nothing is watching the run right now, so say "resume" and I\'ll re-arm the wait.',
  "Phase 0 is done. Should I start Phase 1 now?",
  "The release body is drafted. Say the word and I'll publish it.",
  "A one-line `chmod 644` before the `mv` would fix it. Want me to add it?",
  "43 tests passing, clippy clean, 2,620 lines changed across 8 files. Continue?",
]

const STALLS = [
  "Smoke failure is pre-existing on master. Tests all pass. Now rebuild release and install:",
  "Let me check how Tailscode fetches the model list and what the server actually returns.",
  "Found the bug. Now let me fix the search function.",
  "Launching the game briefly to verify ReShade hooks:",
]

const FINISHED = [
  "Installed 1.2.0 to ~/.cargo/bin/rounds and pushed `4f2a1c9`.",
  "On lcb 46/101, ETA 22:10. bolt-watch publishes the board when it lands.",
  "Pushed.\n\n```\ngit log --oneline -1\n```",
  "https://midgarcorp.cc/tailscode/",
  "Now it opens instantly, and the next release picks this up automatically.",
  "Next release picks this up automatically.",
]

/// The hook's decision for a final message, or "pass" when it lets the turn end.
function hookVerdict(message: string, retry = false): string {
  const input = JSON.stringify({ session_id: "t", cwd: "/t", stop_hook_active: retry, last_assistant_message: message })
  const env = { ...process.env, XDG_DATA_HOME: mkdtempSync(join(tmpdir(), "ft-")) }
  const out = spawnSync("bash", [HOOK], { input, env, encoding: "utf8" }).stdout.trim()
  if (!out) return "pass"
  return JSON.parse(out).reason.startsWith("You announced") ? "stall" : "offer"
}

describe("follow-through", () => {
  for (const [name, verdict] of [
    ["opencode", opencodeVerdict],
    ["omp", ompVerdict],
    ["hook", (text: string) => (hookVerdict(text) === "pass" ? undefined : hookVerdict(text))],
  ] as const) {
    test(`${name} flags offers`, () => {
      for (const text of OFFERS) expect([text, verdict(text)]).toEqual([text, "offer"])
    })
    test(`${name} flags announced steps`, () => {
      for (const text of STALLS) expect([text, verdict(text)]).toEqual([text, "stall"])
    })
    test(`${name} lets finished turns end`, () => {
      for (const text of FINISHED) expect([text, verdict(text)]).toEqual([text, undefined])
    })
  }

  test("hook lets the second stop through", () => {
    expect(hookVerdict(OFFERS[1], true)).toBe("pass")
  })
})

/// An opencode plugin context whose one session ends a turn with `reply` after the prompt `prompt`.
function opencodeHost(reply: string, prompt = "fix the bug", parentID?: string) {
  const prompts: string[] = []
  let promptHook: (event: any) => void = () => {}
  let release: () => void = () => {}
  const done = new Promise<void>((resolve) => (release = resolve))
  const ctx = {
    session: {
      hook: async (name: string, fn: any) => {
        if (name === "prompt") promptHook = fn
      },
      get: async () => ({ id: "s", parentID }),
      context: async () => [
        { type: "user", text: prompt },
        { type: "assistant", content: [{ type: "text", text: reply }] },
      ],
      prompt: async ({ text }: { text: string }) => {
        prompts.push(text)
        promptHook({ sessionID: "s", prompt: { text } })
      },
    },
    event: {
      subscribe: async function* () {
        yield { type: "session.execution.succeeded", data: { sessionID: "s" } }
        yield { type: "session.execution.succeeded", data: { sessionID: "s" } }
        release()
      },
    },
  }
  return { ctx, prompts, done }
}

describe("opencode plugin", () => {
  test("nudges once per prompt after an offer", async () => {
    const { default: plugin } = await import("../plugin/follow-through.js")
    const host = opencodeHost(OFFERS[1])
    await plugin.setup(host.ctx)
    await host.done
    await Bun.sleep(10)
    expect(host.prompts.length).toBe(1)
    expect(host.prompts[0]).toStartWith("You ended the turn offering work")
  })

  test("leaves finished turns, child sessions and relays alone", async () => {
    const { default: plugin } = await import("../plugin/follow-through.js")
    for (const host of [
      opencodeHost(FINISHED[0]),
      opencodeHost(OFFERS[1], "fix the bug", "parent"),
      opencodeHost(OFFERS[1], "Relay the message below to the user as is"),
    ]) {
      await plugin.setup(host.ctx)
      await host.done
      await Bun.sleep(10)
      expect(host.prompts).toEqual([])
    }
  })
})

describe("omp extension", () => {
  /// Runs the extension's agent_end handler over one run's messages and returns what it sent.
  async function ompRun(messages: unknown[], willContinue = false) {
    const { default: extension } = await import("../../omp/extensions/follow-through.ts")
    const handlers: Record<string, (event: any, ctx: any) => Promise<void>> = {}
    const sent: any[] = []
    extension({ on: (name: string, fn: any) => (handlers[name] = fn), sendMessage: (m: any) => sent.push(m) } as any)
    const ctx = { sessionManager: { getSessionId: () => "s" } }
    await handlers.before_agent_start({ prompt: "fix the bug" }, ctx)
    await handlers.agent_end({ messages, willContinue }, ctx)
    await handlers.agent_end({ messages, willContinue }, ctx)
    return sent
  }

  const reply = (text: string, stopReason = "stop") => ({ role: "assistant", stopReason, content: [{ type: "text", text }] })

  test("nudges once after an announced step", async () => {
    const sent = await ompRun([reply(STALLS[0])])
    expect(sent.length).toBe(1)
    expect(sent[0].customType).toBe("follow-through")
  })

  test("leaves finished, continuing, aborted and injected runs alone", async () => {
    expect(await ompRun([reply(FINISHED[0])])).toEqual([])
    expect(await ompRun([reply(OFFERS[1])], true)).toEqual([])
    expect(await ompRun([reply(OFFERS[1], "aborted")])).toEqual([])
    expect(await ompRun([{ role: "custom", customType: "workflow-command", content: "x" }, reply(OFFERS[1])])).toEqual([])
  })
})
