import { afterAll, beforeAll, describe, expect, test } from "bun:test"
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import path from "node:path"
import plugin from "../opencode/plugin/workflow.ts"

const PARENT = "ses_parent"
const CODE_MODE_BLOCK = { type: "text", text: "# Code Mode\n\nUse the `execute` tool to call the tools listed below." }

let root: string

beforeAll(() => {
  root = mkdtempSync(path.join(tmpdir(), "workflow-adapter-"))
  const dir = path.join(root, ".claude", "workflows")
  mkdirSync(dir, { recursive: true })
  writeFileSync(path.join(dir, "answer.js"), "export const meta = { name: 'answer', description: 'Returns args' }\nreturn 'answer:' + args")
  writeFileSync(path.join(dir, "kids.js"), "export const meta = { name: 'kids' }\nreturn await agent('do the work')")
})

afterAll(() => {
  rmSync(root, { recursive: true, force: true })
})

/// An async iterable the test pushes harness events into.
function eventFeed() {
  const queue: any[] = []
  let wake: (() => void) | undefined
  return {
    push(event: any) {
      queue.push(event)
      wake?.()
    },
    async *subscribe() {
      while (true) {
        while (queue.length > 0) yield queue.shift()
        await new Promise<void>((resolve) => (wake = resolve))
      }
    },
  }
}

/// A stand-in for the opencode plugin context that records what the plugin registers and sends.
async function loadPlugin(holdChildren = false) {
  const waiting = new Map<string, () => void>()
  const hooks = new Map<string, (event: any) => any>()
  const sent = { prompts: [] as any[], synthetics: [] as string[], interrupts: [] as string[], created: [] as string[] }
  const registered: { tool?: any; command?: any } = {}
  const feed = eventFeed()
  const childContexts: any[] = []
  const ctx = {
    location: { directory: root },
    event: { subscribe: () => feed.subscribe() },
    agent: { list: async () => [] },
    model: { default: async () => ({ data: { providerID: "p", id: "m" } }) },
    tool: { transform: async (fn: any) => fn({ add: (tool: any) => (registered.tool = tool) }) },
    command: { transform: async (fn: any) => fn({ add: (command: any) => (registered.command = command) }) },
    session: {
      hook: async (name: string, fn: (event: any) => any) => void hooks.set(name, fn),
      get: async ({ sessionID }: any) => ({ id: sessionID, location: { directory: root } }),
      prompt: async ({ sessionID, text }: any) => {
        sent.prompts.push({ sessionID, text })
        if (sessionID === PARENT) await hooks.get("prompt")?.({ sessionID, messageID: "msg_1", prompt: { text } })
        else {
          const event = childEvent(sessionID)
          await hooks.get("context")?.(event)
          childContexts.push(event)
        }
      },
      synthetic: async ({ text }: any) => void sent.synthetics.push(text),
      create: async () => {
        const id = `ses_child_${sent.created.length}`
        sent.created.push(id)
        return { id }
      },
      wait: ({ sessionID }: any) => (holdChildren ? new Promise<void>((resolve) => waiting.set(sessionID, resolve)) : Promise.resolve()),
      context: async () => [{ type: "assistant", content: [{ type: "text", text: "child done" }] }, { type: "idle", outcome: "succeeded" }],
      interrupt: async ({ sessionID }: any) => {
        sent.interrupts.push(sessionID)
        waiting.get(sessionID)?.()
      },
    },
  }
  await plugin.setup(ctx)
  return { hooks, sent, registered, feed, childContexts }
}

/// A context-hook event shaped like the harness sends it, with the code-mode listing and a full tool set.
function childEvent(sessionID: string) {
  return {
    sessionID,
    system: [{ type: "text", text: "base prompt" }, { ...CODE_MODE_BLOCK }],
    tools: Object.fromEntries(["read", "shell", "execute", "workflow", "subagent", "question"].map((name) => [name, { description: name, input: {} }])),
  }
}

/// Runs the `/workflow` command the way the harness does for a session.
async function runCommand(loaded: Awaited<ReturnType<typeof loadPlugin>>, text: string) {
  await loaded.registered.command.execute({ sessionID: PARENT, prompt: { text } })
}

/// The tool-choice rewrite the http.request hook applies to a request body, or undefined when it leaves the request alone.
async function rewrittenBody(loaded: Awaited<ReturnType<typeof loadPlugin>>, kind: string, body: object) {
  const event: any = {
    sessionID: PARENT,
    kind,
    request: new Request("http://llm.test/v1/chat/completions", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }),
  }
  const original = event.request
  await loaded.hooks.get("http.request")?.(event)
  return event.request === original ? undefined : JSON.parse(await event.request.text())
}

function parentContext(loaded: Awaited<ReturnType<typeof loadPlugin>>) {
  const event = childEvent(PARENT)
  loaded.hooks.get("context")?.(event)
  return event
}

describe("/workflow command", () => {
  test("starts a model turn with the workflow named in the user message", async () => {
    const loaded = await loadPlugin()
    await runCommand(loaded, "answer 42")
    expect(loaded.sent.prompts).toEqual([{ sessionID: PARENT, text: 'Run the saved workflow "answer" with the arguments: 42' }])
    expect(loaded.sent.synthetics).toEqual([])
  })

  test("an unknown workflow is answered at once and starts no turn", async () => {
    const loaded = await loadPlugin()
    await runCommand(loaded, "missing")
    expect(loaded.sent.prompts).toEqual([])
    expect(loaded.sent.synthetics[0]).toContain('No saved workflow named "missing"')
    expect(loaded.sent.synthetics[0]).toContain("- answer: Returns args")
  })

  test("list and stop are answered at once and start no turn", async () => {
    const loaded = await loadPlugin()
    await runCommand(loaded, "list")
    await runCommand(loaded, "stop")
    expect(loaded.sent.prompts).toEqual([])
    expect(loaded.sent.synthetics[0]).toContain("Saved workflows:")
    expect(loaded.sent.synthetics[1]).toContain("Stopped 0 running workflow(s)")
  })

  test("narrows the first request to the workflow tool with a fixed input and forces the call", async () => {
    const loaded = await loadPlugin()
    await runCommand(loaded, "answer 42")
    const event = parentContext(loaded)
    expect(Object.keys(event.tools)).toEqual(["workflow"])
    expect(event.tools.workflow.input.properties).toEqual({ name: { const: "answer" }, args: { const: "42" } })
    expect(event.system.some((block: any) => String(block.text).startsWith("# Code Mode"))).toBe(false)
    expect(event.system.at(-1).text).toContain("Call the workflow tool now")
    const body = await rewrittenBody(loaded, "primary", { tools: [{ type: "function" }], messages: [] })
    expect(body.tool_choice).toBe("required")
  })

  test("does not touch title requests, tool-less requests or sessions without a command", async () => {
    const loaded = await loadPlugin()
    expect(await rewrittenBody(loaded, "primary", { tools: [{}], messages: [] })).toBeUndefined()
    await runCommand(loaded, "answer")
    expect(await rewrittenBody(loaded, "title", { tools: [{}], messages: [] })).toBeUndefined()
    expect(await rewrittenBody(loaded, "primary", { messages: [] })).toBeUndefined()
  })

  test("the tool runs the typed workflow whatever the model sent, then the next request has no tools", async () => {
    const loaded = await loadPlugin()
    await runCommand(loaded, "answer 42")
    const result = await loaded.registered.tool.execute({ script: "return 1" }, { sessionID: PARENT, signal: new AbortController().signal, progress: () => undefined })
    expect(result.content).toContain("answer:42")
    const relay = parentContext(loaded)
    expect(Object.keys(relay.tools)).toEqual([])
    expect(relay.system.at(-1).text).toContain("Relay its result")
    expect(await rewrittenBody(loaded, "primary", { tools: [], messages: [] })).toBeUndefined()
  })

  test("a turn that ends without the tool call says so plainly", async () => {
    const loaded = await loadPlugin()
    await runCommand(loaded, "answer")
    loaded.feed.push({ type: "session.execution.succeeded", data: { sessionID: PARENT } })
    await Bun.sleep(20)
    expect(loaded.sent.synthetics).toHaveLength(1)
    expect(loaded.sent.synthetics[0]).toContain('The workflow "answer" did not run')
    expect(Object.keys(parentContext(loaded).tools)).toContain("read")
  })

  test("a finished or interrupted turn releases the session without a message", async () => {
    const loaded = await loadPlugin()
    await runCommand(loaded, "answer")
    await loaded.registered.tool.execute({}, { sessionID: PARENT, signal: new AbortController().signal, progress: () => undefined })
    loaded.feed.push({ type: "session.execution.succeeded", data: { sessionID: PARENT } })
    await Bun.sleep(20)
    expect(loaded.sent.synthetics).toEqual([])
    await runCommand(loaded, "answer")
    loaded.feed.push({ type: "session.execution.interrupted", data: { sessionID: PARENT } })
    await Bun.sleep(20)
    expect(loaded.sent.synthetics).toEqual([])
    expect(Object.keys(parentContext(loaded).tools)).toContain("read")
  })

  test("stop before the tool call interrupts the turn instead of reporting nothing", async () => {
    const loaded = await loadPlugin()
    await runCommand(loaded, "answer")
    await runCommand(loaded, "stop")
    expect(loaded.sent.interrupts).toEqual([PARENT])
    expect(loaded.sent.synthetics.at(-1)).toContain("Stopped 1 running workflow(s)")
    expect(Object.keys(parentContext(loaded).tools)).toContain("read")
  })

  test("a different prompt in the session drops the pending command", async () => {
    const loaded = await loadPlugin()
    await runCommand(loaded, "answer")
    await loaded.hooks.get("prompt")?.({ sessionID: PARENT, messageID: "msg_2", prompt: { text: "something else" } })
    expect(Object.keys(parentContext(loaded).tools)).toContain("read")
  })
})

describe("stop", () => {
  test("aborting the tool signal interrupts every child and ends the run at once", async () => {
    const loaded = await loadPlugin(true)
    const controller = new AbortController()
    const context = { sessionID: PARENT, signal: controller.signal, progress: () => undefined }
    const script = "return await parallel([1, 2, 3].map((i) => () => agent('work ' + i)))"
    const pending = loaded.registered.tool.execute({ script }, context)
    await Bun.sleep(30)
    controller.abort()
    const result = await pending
    expect(result.content).toContain("aborted")
    expect(new Set(loaded.sent.interrupts)).toEqual(new Set(loaded.sent.created))
  })

  test("an interrupt event for the session aborts a running workflow", async () => {
    const loaded = await loadPlugin(true)
    const context = { sessionID: PARENT, signal: new AbortController().signal, progress: () => undefined }
    const never = "await agent('block')\nreturn 1"
    const slow = loaded.registered.tool.execute({ script: never }, context)
    await Bun.sleep(30)
    loaded.feed.push({ type: "session.execution.interrupted", data: { sessionID: PARENT } })
    const result = await slow
    expect(result.content).toContain("aborted")
    expect(new Set(loaded.sent.interrupts).size).toBe(1)
  })
})

describe("sub-agent requests", () => {
  test("sub-agents lose the tools that start agents or wait for a person and keep code mode", async () => {
    const loaded = await loadPlugin()
    const result = await loaded.registered.tool.execute({ name: "kids" }, { sessionID: PARENT, signal: new AbortController().signal, progress: () => undefined })
    expect(result.content).toContain("child done")
    const child = loaded.childContexts[0]
    expect(Object.keys(child.tools).sort()).toEqual(["execute", "read", "shell"])
    expect(child.system).toEqual([{ type: "text", text: "base prompt" }, CODE_MODE_BLOCK])
  })
})
