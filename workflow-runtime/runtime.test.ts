import { afterAll, beforeAll, describe, expect, test } from "bun:test"
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs"
import { homedir, tmpdir } from "node:os"
import path from "node:path"
import { toolDescription, ultracodeNotice } from "./instructions"
import {
  type AgentRequest,
  type AgentResult,
  type Runner,
  type WorkflowEvent,
  findWorkflow,
  formatResult,
  hasUltracodeKeyword,
  RepeatGuard,
  invocationKey,
  listWorkflows,
  loadScript,
  runWorkflow,
} from "./runtime"

const WORKFLOWS_DIR = path.join(homedir(), "claudeconfig", "workflows")
const GLOBALS_MESSAGE =
  "agent, parallel, pipeline, phase, log, args, budget and workflow are already defined globals: do not require, import or redeclare them."
const SAVED = ["flyr", "hinta-best", "kaytetty-best", "verdict", "wwdc"]

let root: string
let savedEnv: Record<string, string | undefined>

beforeAll(() => {
  root = mkdtempSync(path.join(tmpdir(), "workflow-runtime-"))
  savedEnv = { WORKFLOW_PATH: process.env.WORKFLOW_PATH, WORKFLOW_CONCURRENCY: process.env.WORKFLOW_CONCURRENCY }
  delete process.env.WORKFLOW_PATH
  delete process.env.WORKFLOW_CONCURRENCY
})

afterAll(() => {
  for (const [key, value] of Object.entries(savedEnv)) {
    if (value === undefined) delete process.env[key]
    else process.env[key] = value
  }
  rmSync(root, { recursive: true, force: true })
})

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function runnerOf(fn: (req: AgentRequest) => Promise<AgentResult | string> | AgentResult | string, nativeSchema = false): Runner {
  return {
    nativeSchema,
    async run(req) {
      const out = await fn(req)
      return typeof out === "string" ? { text: out } : out
    },
  }
}

function run(source: string, runner: Runner, extra: Partial<Parameters<typeof runWorkflow>[0]> = {}) {
  return runWorkflow({ source, runner, cwd: root, ...extra })
}

/// A valid value for a schema, used to stub structured replies.
function sampleFor(schema: any): unknown {
  if (!schema || typeof schema !== "object") return null
  if (Array.isArray(schema.enum)) return schema.enum[0]
  const type = Array.isArray(schema.type) ? (schema.type.find((t: string) => t !== "null") ?? "null") : schema.type
  if (type === "object") {
    const out: Record<string, unknown> = {}
    for (const [key, sub] of Object.entries(schema.properties ?? {})) out[key] = sampleFor(sub)
    return out
  }
  if (type === "array") return []
  if (type === "string") return ""
  if (type === "number" || type === "integer") return 0
  if (type === "boolean") return false
  return null
}

describe("loadScript", () => {
  test("parses a multi-line meta with nested braces, strings and comments", () => {
    const source = `export const meta = {
  name: 'demo',
  description: "has } and { and 'quotes' inside",
  phases: [{ title: 'A', detail: 'x' }, { title: 'B' }], // trailing }
  /* block } comment */
  whenToUse: 'when {needed}',
};
return 1 + 1`
    const { meta, body } = loadScript(source)
    expect(meta.name).toBe("demo")
    expect(meta.description).toBe("has } and { and 'quotes' inside")
    expect(meta.phases?.length).toBe(2)
    expect(meta.whenToUse).toBe("when {needed}")
    expect(body.trim()).toBe("return 1 + 1")
  })

  test("accepts meta without a semicolon and with a template literal", () => {
    const { meta, body } = loadScript("export const meta = { name: `t${'}'}x` }\nreturn 2")
    expect(meta.name).toBe("t}x")
    expect(body.trim()).toBe("return 2")
  })

  test("meta is optional and defaults to inline", () => {
    const { meta, body } = loadScript("return 5")
    expect(meta.name).toBe("inline")
    expect(body).toBe("return 5")
  })

  test("meta without a name defaults to inline", () => {
    expect(loadScript("export const meta = { description: 'd' }\nreturn 1").meta.name).toBe("inline")
  })

  test("strips a byte order mark", () => {
    expect(loadScript("﻿export const meta = { name: 'bom' }\nreturn 1").meta.name).toBe("bom")
  })

  test("rejects a meta that is not an object literal", () => {
    expect(() => loadScript("export const meta = 5\nreturn 1")).toThrow("object literal")
  })

  test("rejects unbalanced and unterminated meta", () => {
    expect(() => loadScript("export const meta = { name: 'a'\nreturn 1")).toThrow()
    expect(() => loadScript("export const meta = { name: 'a }\nreturn 1")).toThrow("unterminated")
  })

  test("rejects a meta whose literal does not evaluate", () => {
    expect(() => loadScript("export const meta = { name: nope.x }\nreturn 1")).toThrow("meta is not a valid object literal")
  })
})

describe("saved workflows", () => {
  test("all five saved workflows are listed from WORKFLOW_PATH", () => {
    process.env.WORKFLOW_PATH = WORKFLOWS_DIR
    try {
      const names = listWorkflows(root).map((w) => w.name)
      for (const name of SAVED) expect(names).toContain(name)
      expect(findWorkflow("wwdc", root)).toBe(path.join(WORKFLOWS_DIR, "wwdc.js"))
      expect(findWorkflow("wwdc.js", root)).toBe(path.join(WORKFLOWS_DIR, "wwdc.js"))
    } finally {
      delete process.env.WORKFLOW_PATH
    }
  })

  for (const name of SAVED) {
    test(`${name} runs end to end with a stub runner`, async () => {
      process.env.WORKFLOW_PATH = WORKFLOWS_DIR
      try {
        for (const args of ["", "sample request words", { q: "object" }]) {
          const r = await runWorkflow({
            name,
            args,
            cwd: root,
            runner: runnerOf((req) => ({ text: "stub", data: req.schema ? sampleFor(req.schema) : undefined }), true),
          })
          expect(r.error).toBeUndefined()
          expect(r.ok).toBe(true)
          expect(r.name).toBe(name)
        }
      } finally {
        delete process.env.WORKFLOW_PATH
      }
    })
  }

  test("lookup order is WORKFLOW_PATH, then cwd, then home, and listing dedupes by name", () => {
    const first = path.join(root, "first")
    const project = path.join(root, "project")
    mkdirSync(first, { recursive: true })
    mkdirSync(path.join(project, ".claude", "workflows"), { recursive: true })
    writeFileSync(path.join(first, "shared.js"), "export const meta = { name: 'shared', description: 'from env' }\nreturn 'env'")
    writeFileSync(path.join(project, ".claude", "workflows", "shared.js"), "export const meta = { name: 'shared', description: 'from cwd' }\nreturn 'cwd'")
    writeFileSync(path.join(project, ".claude", "workflows", "only-cwd.js"), "export const meta = { name: 'only-cwd' }\nreturn 'x'")
    writeFileSync(path.join(project, ".claude", "workflows", "broken.js"), "export const meta = { name: \nreturn")
    process.env.WORKFLOW_PATH = `${first}:`
    try {
      expect(findWorkflow("shared", project)).toBe(path.join(first, "shared.js"))
      const listed = listWorkflows(project)
      expect(listed.filter((w) => w.name === "shared").map((w) => w.description)).toEqual(["from env"])
      expect(listed.map((w) => w.name)).toContain("only-cwd")
      expect(listed.map((w) => w.name)).not.toContain("broken")
    } finally {
      delete process.env.WORKFLOW_PATH
    }
    expect(findWorkflow("shared", project)).toBe(path.join(project, ".claude", "workflows", "shared.js"))
  })

  test("rejects names that escape the workflow directories", () => {
    expect(findWorkflow("../x", root)).toBeUndefined()
    expect(findWorkflow("a/b", root)).toBeUndefined()
    expect(findWorkflow(".hidden", root)).toBeUndefined()
    expect(findWorkflow("", root)).toBeUndefined()
  })

  test("running an unknown name lists what is saved", async () => {
    const r = await runWorkflow({ name: "nope", cwd: root, runner: runnerOf(() => "x") })
    expect(r.ok).toBe(false)
    expect(r.error).toContain('workflow "nope" not found')
  })

  test("running by scriptPath works and takes the file name when meta has none", async () => {
    const file = path.join(root, "by-path.js")
    writeFileSync(file, "return args")
    const r = await runWorkflow({ scriptPath: file, args: 7, cwd: root, runner: runnerOf(() => "x") })
    expect(r.result).toBe(7)
    expect(r.name).toBe("by-path")
  })
})

describe("agent", () => {
  test("returns text, defaults the label and carries the request fields", async () => {
    const seen: AgentRequest[] = []
    const r = await run(
      `export const meta = { name: 'fields' }
phase("P1")
const a = await agent("hello")
const b = await agent("again", { label: "mine", phase: "P2", model: "prov/m", agentType: "explore" })
return [a, b]`,
      runnerOf((req) => {
        seen.push(req)
        return `reply:${req.prompt}`
      }),
    )
    expect(r.result).toEqual(["reply:hello", "reply:again"])
    expect(seen[0]).toMatchObject({ label: "agent-1", phase: "P1", workflow: "fields", index: 1, prompt: "hello" })
    expect(seen[1]).toMatchObject({ label: "mine", phase: "P2", model: "prov/m", agentType: "explore", index: 2 })
    expect(r.agents).toBe(2)
    expect(r.failed).toBe(0)
  })

  test("a non-string prompt throws into the script", async () => {
    const r = await run(`return await agent(5)`, runnerOf(() => "x"))
    expect(r.ok).toBe(false)
    expect(r.error).toContain("prompt must be a string")
  })

  test("a runner throw gives null, counts as failed and logs the reason", async () => {
    const r = await run(`return await agent("x", { label: "boom" })`, {
      async run() {
        throw new Error("exploded")
      },
    })
    expect(r.ok).toBe(true)
    expect(r.result).toBeNull()
    expect(r.failed).toBe(1)
    expect(r.logs).toContain("agent boom failed: exploded")
  })

  test("never exceeds the concurrency cap and reaches it with 20 agents", async () => {
    let running = 0
    let peak = 0
    const r = await run(
      `const out = await parallel(Array.from({ length: 20 }, (_, i) => () => agent("n" + i)))
return out.length`,
      runnerOf(async () => {
        running += 1
        peak = Math.max(peak, running)
        await sleep(15)
        running -= 1
        return "ok"
      }),
      { concurrency: 5 },
    )
    expect(r.result).toBe(20)
    expect(peak).toBe(5)
  })

  test("defaults to 8 concurrent agents and honours WORKFLOW_CONCURRENCY", async () => {
    const measure = async () => {
      let running = 0
      let peak = 0
      await run(
        `await parallel(Array.from({ length: 30 }, (_, i) => () => agent("n" + i)))`,
        runnerOf(async () => {
          running += 1
          peak = Math.max(peak, running)
          await sleep(10)
          running -= 1
          return "ok"
        }),
      )
      return peak
    }
    expect(await measure()).toBe(8)
    process.env.WORKFLOW_CONCURRENCY = "3"
    try {
      expect(await measure()).toBe(3)
    } finally {
      delete process.env.WORKFLOW_CONCURRENCY
    }
  })

  test("events report start, end and running counts", async () => {
    const events: WorkflowEvent[] = []
    await run(
      `phase("One")
log("note")
await agent("a", { label: "x" })`,
      runnerOf(() => "ok"),
      { onEvent: (e) => events.push(e) },
    )
    expect(events.map((e) => e.type)).toEqual(["phase", "log", "agent_start", "agent_end"])
    expect(events[2]).toMatchObject({ type: "agent_start", label: "x", phase: "One", running: 1 })
    expect(events[3]).toMatchObject({ type: "agent_end", ok: true, running: 0, done: 1, failed: 0 })
  })

  test("a throwing onEvent does not break the run", async () => {
    const r = await run(`return await agent("a")`, runnerOf(() => "fine"), {
      onEvent: () => {
        throw new Error("listener")
      },
    })
    expect(r.result).toBe("fine")
  })

  test("maxAgents throws inside the script and retries do not count", async () => {
    const r = await run(
      `const a = await agent("1")
const b = await agent("2")
try {
  await agent("3")
} catch (e) {
  return [a, b, e.message]
}`,
      runnerOf(() => "ok"),
      { maxAgents: 2 },
    )
    expect(r.result).toEqual(["ok", "ok", "agent limit of 2 exceeded"])
    expect(r.agents).toBe(2)

    let calls = 0
    const retried = await run(
      `return [await agent("1", { schema: { type: "object", required: ["a"] } }), await agent("2")]`,
      runnerOf(() => {
        calls += 1
        return calls === 1 ? "{}" : calls === 2 ? '{"a":1}' : "fine"
      }),
      { maxAgents: 2 },
    )
    expect(retried.result).toEqual([{ a: 1 }, "fine"])
    expect(retried.agents).toBe(2)
  })
})

describe("schema", () => {
  const schema = `{ type: "object", properties: { n: { type: "integer" } }, required: ["n"], additionalProperties: false }`

  test("appends the schema instruction to the prompt", async () => {
    let seen = ""
    await run(`await agent("do it", { schema: ${schema} })`, runnerOf((req) => {
      seen = req.prompt
      return '{"n":1}'
    }))
    expect(seen).toStartWith("do it\n\nWhen you are done, reply with ONLY a JSON object matching this JSON Schema, with no other text:\n")
    expect(seen).toContain('"required":["n"]')
  })

  test("retries with the errors then succeeds", async () => {
    const prompts: string[] = []
    const r = await run(`return await agent("do it", { schema: ${schema} })`, runnerOf((req) => {
      prompts.push(req.prompt)
      return prompts.length === 1 ? '{"n":"x"}' : '{"n":2}'
    }))
    expect(r.result).toEqual({ n: 2 })
    expect(r.failed).toBe(0)
    expect(prompts).toHaveLength(2)
    expect(prompts[1]).toStartWith(prompts[0])
    expect(prompts[1]).toContain("Your previous reply did not match the schema: $.n should be integer, got string. Reply again with only the JSON object.")
  })

  test("gives up after three attempts with null and a failed count", async () => {
    let calls = 0
    const r = await run(`return await agent("do it", { schema: ${schema}, label: "s" })`, runnerOf(() => {
      calls += 1
      return "not json at all"
    }))
    expect(calls).toBe(3)
    expect(r.result).toBeNull()
    expect(r.failed).toBe(1)
    expect(r.logs[0]).toStartWith("agent s failed: invalid structured output")
  })

  test("parses the last fenced json block and the last balanced object", async () => {
    const fenced = await run(`return await agent("x", { schema: ${schema} })`, runnerOf(() => 'sure\n```json\n{"n":1}\n```\nand\n```json\n{"n":2}\n```\nbye'))
    expect(fenced.result).toEqual({ n: 2 })
    const loose = await run(`return await agent("x", { schema: ${schema} })`, runnerOf(() => 'I used {curly} words and a { stray. Final: {"n": 3} thanks'))
    expect(loose.result).toEqual({ n: 3 })
    const braceInString = await run(
      `return await agent("x", { schema: { type: "object", required: ["t"] } })`,
      runnerOf(() => 'result {"t": "a } b"}'),
    )
    expect(braceInString.result).toEqual({ t: "a } b" })
  })

  test("array schemas read the last array", async () => {
    const r = await run(`return await agent("x", { schema: { type: "array", items: { type: "string" } } })`, runnerOf(() => 'list: ["a","b"]'))
    expect(r.result).toEqual(["a", "b"])
  })

  test("native schema validates data and skips the instruction", async () => {
    let seen = ""
    const ok = await run(`return await agent("p", { schema: ${schema} })`, runnerOf((req) => {
      seen = req.prompt
      return { text: "ignored", data: { n: 4 } }
    }, true))
    expect(seen).toBe("p")
    expect(ok.result).toEqual({ n: 4 })

    let calls = 0
    const bad = await run(`return await agent("p", { schema: ${schema} })`, runnerOf(() => {
      calls += 1
      return { text: "", data: { n: 1, extra: true } }
    }, true))
    expect(bad.result).toBeNull()
    expect(calls).toBe(3)
  })

  test("native schema falls back to parsing text when no data came back", async () => {
    const r = await run(`return await agent("p", { schema: ${schema} })`, runnerOf(() => ({ text: '{"n":9}' }), true))
    expect(r.result).toEqual({ n: 9 })
  })

  test("validator covers type arrays, enum, items, required and additionalProperties", async () => {
    const check = async (schemaSource: string, reply: string) =>
      (await run(`return await agent("x", { schema: ${schemaSource} })`, runnerOf(() => reply))).result
    const nullable = `{ type: "object", properties: { v: { type: ["string", "null"] } }, required: ["v"] }`
    expect(await check(nullable, '{"v":null}')).toEqual({ v: null })
    expect(await check(nullable, '{"v":"s"}')).toEqual({ v: "s" })
    expect(await check(nullable, '{"v":1}')).toBeNull()
    expect(await check(nullable, "{}")).toBeNull()
    const en = `{ type: "object", properties: { k: { enum: ["a", "b"] } } }`
    expect(await check(en, '{"k":"b"}')).toEqual({ k: "b" })
    expect(await check(en, '{"k":"c"}')).toBeNull()
    const items = `{ type: "object", properties: { l: { type: "array", items: { type: "number" } } } }`
    expect(await check(items, '{"l":[1,2.5]}')).toEqual({ l: [1, 2.5] })
    expect(await check(items, '{"l":[1,"x"]}')).toBeNull()
    expect(await check(schema, '{"n":1.5}')).toBeNull()
    expect(await check(schema, '{"n":1,"z":2}')).toBeNull()
  })
})

describe("parallel and pipeline", () => {
  test("parallel is a barrier and turns thunk errors into null", async () => {
    const r = await run(
      `const out = await parallel([
  () => agent("a"),
  () => { throw new Error("bad thunk") },
  async () => { await agent("b"); throw new Error("late") },
])
return out`,
      runnerOf((req) => req.prompt),
    )
    expect(r.result).toEqual(["a", null, null])
    expect(r.logs.some((l) => l.includes("bad thunk"))).toBe(true)
  })

  test("pipeline has no barrier between stages", async () => {
    const order: string[] = []
    const r = await run(
      `return await pipeline(["slow", "fast"],
  async (item) => { const t = await agent("s1:" + item); return t },
  async (prev, item, i) => { const t = await agent("s2:" + item + ":" + i + ":" + prev); return t },
)`,
      runnerOf(async (req) => {
        await sleep(req.prompt === "s1:slow" ? 120 : 5)
        order.push(req.prompt.split(":").slice(0, 2).join(":"))
        return req.prompt
      }),
    )
    expect(order.indexOf("s2:fast")).toBeLessThan(order.indexOf("s1:slow"))
    expect(r.result).toEqual(["s2:slow:0:s1:slow", "s2:fast:1:s1:fast"])
  })

  test("a throwing stage nulls that item and skips later stages", async () => {
    const r = await run(
      `const seen = []
const out = await pipeline([1, 2, 3],
  (x) => { if (x === 2) throw new Error("stage1 boom"); return x * 10 },
  (prev, item) => { seen.push(item); return prev + 1 },
)
return { out, seen }`,
      runnerOf(() => "x"),
    )
    expect(r.result).toEqual({ out: [11, null, 31], seen: [1, 3] })
    expect(r.logs.some((l) => l.includes("stage1 boom"))).toBe(true)
  })
})

describe("script errors", () => {
  test("TypeScript syntax tells the author to use plain JavaScript", async () => {
    const r = await run(`const x: number = 1\nreturn x`, runnerOf(() => "x"))
    expect(r.ok).toBe(false)
    expect(r.error).toContain("not valid JavaScript")
    expect(r.error).toContain("Write plain JavaScript only")
  })

  test("import and export in the body give the same hint", async () => {
    const r = await run(`import fs from "node:fs"\nreturn 1`, runnerOf(() => "x"))
    expect(r.ok).toBe(false)
    expect(r.error).toContain("Write plain JavaScript only")
  })

  test("a runtime error becomes ok false with the message", async () => {
    const r = await run(`return missing.value`, runnerOf(() => "x"))
    expect(r.ok).toBe(false)
    expect(r.error).toContain("missing")
  })

  test("redeclaring an injected name explains that the globals already exist", async () => {
    const r = await run(`const { agent } = require("opencode")\nreturn 1`, runnerOf(() => "x"))
    expect(r.ok).toBe(false)
    expect(r.error).toContain("not valid JavaScript")
    expect(r.error).toContain(GLOBALS_MESSAGE)
    expect(r.error).toContain("Write plain JavaScript only")
    const second = await run(`let log = 2\nreturn log`, runnerOf(() => "x"))
    expect(second.error).toContain(GLOBALS_MESSAGE)
  })

  test("import in the body also gets the globals message", async () => {
    const r = await run(`import fs from "node:fs"\nreturn 1`, runnerOf(() => "x"))
    expect(r.error).toContain(GLOBALS_MESSAGE)
  })

  test("calling require at run time explains that the globals already exist", async () => {
    const r = await run(`const fs = require("node:fs")\nreturn typeof fs`, runnerOf(() => "x"))
    expect(r.ok).toBe(false)
    expect(r.error).toContain("require")
    expect(r.error).toContain(GLOBALS_MESSAGE)
  })

  test("an unrelated runtime error does not get the globals message", async () => {
    const r = await run(`return missing.value`, runnerOf(() => "x"))
    expect(r.error).not.toContain(GLOBALS_MESSAGE)
    const syntax = await run(`const x: number = 1\nreturn x`, runnerOf(() => "x"))
    expect(syntax.error).not.toContain(GLOBALS_MESSAGE)
  })

  test("budget, args, phase and log are available", async () => {
    const r = await run(
      `log({ a: 1 })
phase("p")
return [args, budget.total, budget.spent(), budget.remaining()]`,
      runnerOf(() => "x"),
      { args: { k: 1 } },
    )
    expect(r.result).toEqual([{ k: 1 }, null, 0, Infinity])
    expect(r.logs).toEqual(['{"a":1}'])
  })

  test("a bad meta in an inline script is a failed result, not a throw", async () => {
    const r = await run(`export const meta = 5\nreturn 1`, runnerOf(() => "x"))
    expect(r.ok).toBe(false)
    expect(r.error).toContain("object literal")
  })
})

describe("abort", () => {
  test("aborting mid-run resolves ok false with aborted and signals the runner", async () => {
    const controller = new AbortController()
    let aborted = 0
    const started = Date.now()
    const promise = run(
      `await parallel(Array.from({ length: 6 }, (_, i) => () => agent("n" + i)))
return "done"`,
      {
        async run(req) {
          await new Promise<void>((resolve) => req.signal.addEventListener("abort", () => resolve(), { once: true }))
          aborted += 1
          return { text: "late" }
        },
      },
      { signal: controller.signal, concurrency: 2 },
    )
    await sleep(30)
    controller.abort()
    const r = await promise
    expect(r.ok).toBe(false)
    expect(r.error).toBe("aborted")
    expect(Date.now() - started).toBeLessThan(2000)
    expect(aborted).toBe(2)
  })

  test("a runner that ignores the signal still lets the run end", async () => {
    const controller = new AbortController()
    const promise = run(`return await agent("x")`, { run: () => new Promise<AgentResult>(() => {}) }, { signal: controller.signal })
    await sleep(10)
    controller.abort()
    const r = await promise
    expect(r).toMatchObject({ ok: false, error: "aborted" })
  })

  test("an already aborted signal never starts agents", async () => {
    const controller = new AbortController()
    controller.abort()
    let calls = 0
    const r = await run(`return await agent("x")`, runnerOf(() => {
      calls += 1
      return "x"
    }), { signal: controller.signal })
    expect(r).toMatchObject({ ok: false, error: "aborted" })
    expect(calls).toBe(0)
  })
})

describe("run-scoped abort", () => {
  test("an agent the script never awaited is aborted once the run resolves", async () => {
    const seen: AbortSignal[] = []
    const r = await run(
      `agent("floating")
return "done"`,
      {
        run(req) {
          seen.push(req.signal)
          return new Promise<AgentResult>(() => {})
        },
      },
    )
    expect(r).toMatchObject({ ok: true, result: "done" })
    expect(seen).toHaveLength(1)
    expect(seen[0].aborted).toBe(true)
  })

  test("Promise.race losers and agents left behind by a script error are aborted", async () => {
    const signals: AbortSignal[] = []
    const stuck: Runner = {
      run(req) {
        signals.push(req.signal)
        if (req.label === "fast") return Promise.resolve({ text: "fast" })
        return new Promise<AgentResult>(() => {})
      },
    }
    const raced = await run(`return await Promise.race([agent("a", { label: "slow" }), agent("b", { label: "fast" })])`, stuck)
    expect(raced).toMatchObject({ ok: true, result: "fast" })
    const threw = await run(`agent("c", { label: "slow" })\nthrow new Error("boom")`, stuck)
    expect(threw).toMatchObject({ ok: false, error: "boom" })
    expect(signals).toHaveLength(3)
    expect(signals.every((s) => s.aborted)).toBe(true)
  })

  test("the caller signal still aborts the run through the internal one", async () => {
    const controller = new AbortController()
    let seen: AbortSignal | undefined
    const promise = run(
      `return await agent("x")`,
      {
        run(req) {
          seen = req.signal
          return new Promise<AgentResult>(() => {})
        },
      },
      { signal: controller.signal },
    )
    await sleep(10)
    expect(seen?.aborted).toBe(false)
    controller.abort()
    expect(await promise).toMatchObject({ ok: false, error: "aborted" })
    expect(seen?.aborted).toBe(true)
  })

  test("a settled run leaves no listener behind on the caller signal", async () => {
    const controller = new AbortController()
    let removed = 0
    const original = controller.signal.removeEventListener.bind(controller.signal)
    controller.signal.removeEventListener = ((...a: Parameters<typeof original>) => {
      removed += 1
      return original(...a)
    }) as typeof original
    await run(`return "x"`, runnerOf(() => "x"), { signal: controller.signal })
    expect(removed).toBeGreaterThan(0)
  })

  test("a floating agent that rejects never raises an unhandled rejection", async () => {
    let unhandled = 0
    const count = () => {
      unhandled += 1
    }
    process.on("unhandledRejection", count)
    try {
      const r = await run(
        `agent("floating")
agent("also floating")
await agent("quick")
return "done"`,
        {
          async run(req) {
            if (req.prompt === "quick") return { text: "q" }
            await new Promise<void>((resolve) => req.signal.addEventListener("abort", () => resolve(), { once: true }))
            return { text: "late" }
          },
        },
      )
      expect(r.ok).toBe(true)
      await sleep(50)
    } finally {
      process.off("unhandledRejection", count)
    }
    expect(unhandled).toBe(0)
  })

  test("a floating agent aborted with the run is silent after the run settled", async () => {
    const events: WorkflowEvent[] = []
    const r = await run(
      `agent("floating")
return "done"`,
      { run: () => new Promise<AgentResult>(() => {}) },
      { onEvent: (e) => events.push(e) },
    )
    await sleep(20)
    expect(events.some((e) => e.type === "agent_end")).toBe(false)
    expect(r.logs).toEqual([])
  })
})

describe("abort bookkeeping", () => {
  test("aborted agents count as failed and each gets a log line", async () => {
    const controller = new AbortController()
    const events: WorkflowEvent[] = []
    const promise = run(
      `await parallel(Array.from({ length: 5 }, (_, i) => () => agent("n" + i, { label: "a" + i })))
return "done"`,
      { run: (req) => new Promise<AgentResult>(() => req.signal) },
      { signal: controller.signal, concurrency: 2, onEvent: (e) => events.push(e) },
    )
    await sleep(30)
    controller.abort()
    const r = await promise
    expect(r).toMatchObject({ ok: false, error: "aborted", agents: 5, failed: 5 })
    expect(r.logs.filter((l) => /^agent a\d failed: aborted$/.test(l))).toHaveLength(5)
    const text = formatResult(r)
    expect(text).toContain("workflow inline failed: aborted")
    expect(text).toContain("5 agents, 5 failed")
    expect(text).toContain("agent a0 failed: aborted")
    expect(events.filter((e) => e.type === "agent_end" && !e.ok)).toHaveLength(5)
  })

  test("agents that finished before the abort are not counted as failed", async () => {
    const controller = new AbortController()
    const promise = run(
      `const a = await agent("ok", { label: "good" })
await agent("hang", { label: "bad" })
return a`,
      {
        run(req) {
          if (req.prompt === "ok") return Promise.resolve({ text: "fine" })
          return new Promise<AgentResult>(() => {})
        },
      },
      { signal: controller.signal },
    )
    await sleep(30)
    controller.abort()
    const r = await promise
    expect(r).toMatchObject({ ok: false, agents: 2, failed: 1 })
    expect(r.logs).toEqual(["agent bad failed: aborted"])
  })
})

describe("nested workflow", () => {
  function saveNested(): string {
    const dir = path.join(root, "nested")
    mkdirSync(dir, { recursive: true })
    writeFileSync(
      path.join(dir, "child.js"),
      `export const meta = { name: 'child' }
const out = await parallel(Array.from({ length: 6 }, (_, i) => () => agent("c" + i, { label: "child:" + i })))
return { args, count: out.length }`,
    )
    writeFileSync(path.join(dir, "grand.js"), `return await workflow("child")`)
    writeFileSync(path.join(dir, "mid.js"), `return await workflow("grand")`)
    return dir
  }

  test("runs inline with args, shares the semaphore and the counters", async () => {
    const dir = saveNested()
    process.env.WORKFLOW_PATH = dir
    try {
      let running = 0
      let peak = 0
      const names = new Set<string>()
      const r = await run(
        `const outer = await parallel(Array.from({ length: 6 }, (_, i) => () => agent("o" + i)))
const inner = await workflow("child", { from: "parent" })
return { outer: outer.length, inner }`,
        runnerOf(async (req) => {
          running += 1
          peak = Math.max(peak, running)
          names.add(req.workflow)
          await sleep(15)
          running -= 1
          return "ok"
        }),
        { concurrency: 3 },
      )
      expect(r.result).toEqual({ outer: 6, inner: { args: { from: "parent" }, count: 6 } })
      expect(r.agents).toBe(12)
      expect(peak).toBe(3)
      expect([...names].sort()).toEqual(["child", "inline"])
    } finally {
      delete process.env.WORKFLOW_PATH
    }
  })

  test("two levels deep throws and one level of scriptPath works", async () => {
    const dir = saveNested()
    process.env.WORKFLOW_PATH = dir
    try {
      const deep = await run(`return await workflow("mid")`, runnerOf(() => "x"))
      expect(deep.ok).toBe(false)
      expect(deep.error).toContain("one level")
      const byPath = await run(`return await workflow({ scriptPath: ${JSON.stringify(path.join(dir, "child.js"))} }, 1)`, runnerOf(() => "x"))
      expect(byPath.result).toEqual({ args: 1, count: 6 })
      const missing = await run(`return await workflow("ghost")`, runnerOf(() => "x"))
      expect(missing.error).toContain('workflow "ghost" not found')
    } finally {
      delete process.env.WORKFLOW_PATH
    }
  })

  test("maxAgents covers nested agents too", async () => {
    const dir = saveNested()
    process.env.WORKFLOW_PATH = dir
    try {
      const r = await run(`return await workflow("child")`, runnerOf(() => "x"), { maxAgents: 4 })
      expect(r.agents).toBe(4)
      expect(r.result).toMatchObject({ count: 6 })
      expect(r.logs.some((l) => l.includes("agent limit of 4 exceeded"))).toBe(true)
    } finally {
      delete process.env.WORKFLOW_PATH
    }
  })
})

describe("formatResult", () => {
  const base = { name: "w", ok: true, agents: 3, failed: 1, logs: [], durationMs: 1234 }

  test("strings go out verbatim with a footer", () => {
    expect(formatResult({ ...base, result: "hello" })).toBe("hello\n\nworkflow w: 3 agents, 1 failed, 1.2s")
  })

  test("other values are pretty JSON and failure logs follow the footer", () => {
    const text = formatResult({ ...base, result: { a: 1 }, logs: ["fine", "agent x failed: nope", "an Error happened"] })
    expect(text).toBe('{\n  "a": 1\n}\n\nworkflow w: 3 agents, 1 failed, 1.2s\nagent x failed: nope\nan Error happened')
  })

  test("a failed run leads with the reason", () => {
    expect(formatResult({ ...base, ok: false, error: "kaput" })).toStartWith("workflow w failed: kaput\n")
  })

  test("a cyclic result falls back to its string form with a note", () => {
    const cyclic: Record<string, unknown> = {}
    cyclic.self = cyclic
    const text = formatResult({ ...base, result: cyclic })
    expect(text).toStartWith("[object Object]\n(the value was not JSON serializable")
    expect(text).toContain("workflow w: 3 agents")
  })

  test("a BigInt result and a prototype-less object never throw", () => {
    expect(formatResult({ ...base, result: 10n })).toContain("10\n(the value was not JSON serializable")
    const bare = Object.create(null)
    bare.self = bare
    expect(() => formatResult({ ...base, result: bare })).not.toThrow()
  })

  test("an undefined result still prints something", () => {
    expect(formatResult({ ...base })).toContain("returned no value")
  })
})

describe("hasUltracodeKeyword", () => {
  test("matches a standalone word in any case", () => {
    expect(hasUltracodeKeyword("ultracode: count the lines")).toBe(true)
    expect(hasUltracodeKeyword("please ULTRACODE this")).toBe(true)
    expect(hasUltracodeKeyword("do it. Ultracode.")).toBe(true)
    expect(hasUltracodeKeyword("ultracode")).toBe(true)
    expect(hasUltracodeKeyword("(ultracode)")).toBe(true)
  })

  test("ignores longer words and path-like uses", () => {
    expect(hasUltracodeKeyword("ultracoder")).toBe(false)
    expect(hasUltracodeKeyword("myultracode")).toBe(false)
    expect(hasUltracodeKeyword("ultracode-lite")).toBe(false)
    expect(hasUltracodeKeyword("ultra-code")).toBe(false)
    expect(hasUltracodeKeyword("open src/ultracode.ts")).toBe(false)
    expect(hasUltracodeKeyword("ultracode_x")).toBe(false)
  })

  test("ignores inline code and fenced blocks", () => {
    expect(hasUltracodeKeyword("what does `ultracode` do")).toBe(false)
    expect(hasUltracodeKeyword("see ``ultracode`` here")).toBe(false)
    expect(hasUltracodeKeyword("look:\n```\nultracode\n```\nthanks")).toBe(false)
    expect(hasUltracodeKeyword("look:\n```js\nultracode\n")).toBe(false)
    expect(hasUltracodeKeyword("~~~\nultracode\n~~~")).toBe(false)
    expect(hasUltracodeKeyword("`x` then ultracode please")).toBe(true)
    expect(hasUltracodeKeyword("```\ncode\n``` ultracode")).toBe(true)
  })
})

describe("instructions", () => {
  const saved = [
    { name: "wwdc", description: "Search the WWDC knowledge base" },
    { name: "long", description: "x".repeat(500) },
    { name: "bare" },
  ]

  test("the tool description documents the whole API and lists saved workflows", () => {
    const text = toolDescription(saved)
    for (const word of ["agent(prompt", "parallel(thunks)", "pipeline(items", "phase(title)", "log(message)", "workflow(nameOrRef", "budget", "args", "schema", "label", "Plain JavaScript only", "fresh", "16 agents", "script", "name"]) {
      expect(text).toContain(word)
    }
    expect(text).toContain("- wwdc: Search the WWDC knowledge base")
    expect(text).toMatch(/^- bare$/m)
    expect(text).not.toContain("x".repeat(250))
  })

  test("the tool description copes with no saved workflows", () => {
    expect(toolDescription([])).toContain("No saved workflows.")
  })

  test("the notice names the tool and the saved workflows", () => {
    const text = ultracodeNotice(saved)
    expect(text).toContain('"workflow" tool')
    expect(text).toContain("wwdc, long, bare")
    expect(ultracodeNotice([])).not.toContain("Saved workflows")
  })

  test("both texts say the functions are globals and a failing script must change", () => {
    for (const text of [toolDescription([]), ultracodeNotice([])]) {
      expect(text).toContain("already defined globals")
      expect(text).toMatch(/do not require or import|Never require\(\) or import/)
      expect(text).toMatch(/redeclare|declare a variable/)
      expect(text).toMatch(/resending the same failing script|never resend/)
    }
  })

  test("the worked example in the description runs", async () => {
    const text = toolDescription([])
    const example = text.slice(text.indexOf("const files = args.files"), text.indexOf("No saved workflows."))
    const r = await run(example.trim(), runnerOf((req) => (req.schema ? { text: "", data: { summary: "s", bugs: [] } } : "done"), true), {
      args: { files: ["a.ts", "b.ts"] },
    })
    expect(r.error).toBeUndefined()
    expect(r.result).toBe("done")
    expect(r.agents).toBe(3)
  })
})

describe("RepeatGuard", () => {
  const REFUSAL = "The workflow tool failed 3 times in a row; stop calling it and do the task directly."

  test("a first failure passes through unchanged and a repeat is marked", () => {
    const guard = new RepeatGuard()
    const key = invocationKey({ script: "return 1" })
    expect(guard.record("s", key, false, "boom")).toBe("boom")
    const second = guard.record("s", key, false, "boom")
    expect(second).toStartWith("This exact script already failed 1 time(s). Change it, or do the task without the workflow tool.")
    expect(second).toEndWith("boom")
    expect(guard.record("s", key, false, "boom")).toContain("already failed 2 time(s)")
  })

  test("the key ignores surrounding whitespace and separates scripts, names and args", () => {
    expect(invocationKey({ script: " return 1\n" })).toBe(invocationKey({ script: "return 1" }))
    expect(invocationKey({ script: "return 1" })).not.toBe(invocationKey({ script: "return 2" }))
    expect(invocationKey({ name: "a", args: 1 })).not.toBe(invocationKey({ name: "a", args: 2 }))
    expect(invocationKey({ name: "a", args: { x: 1 } })).toBe(invocationKey({ name: "a", args: { x: 1 } }))
  })

  test("a different failing script is not marked as a repeat", () => {
    const guard = new RepeatGuard()
    guard.record("s", invocationKey({ script: "a" }), false, "x")
    expect(guard.record("s", invocationKey({ script: "b" }), false, "y")).toBe("y")
  })

  test("three failures in a row refuse every further call until a reset", () => {
    const guard = new RepeatGuard()
    expect(guard.refusal("s")).toBeUndefined()
    for (const script of ["a", "b", "c"]) guard.record("s", invocationKey({ script }), false, "x")
    expect(guard.refusal("s")).toBe(REFUSAL)
    expect(guard.refusal("other")).toBeUndefined()
    guard.reset("s")
    expect(guard.refusal("s")).toBeUndefined()
    guard.record("s", invocationKey({ script: "a" }), false, "x")
    expect(guard.refusal("s")).toBeUndefined()
  })

  test("a success resets the streak and forgets that script's failures", () => {
    const guard = new RepeatGuard()
    const key = invocationKey({ script: "a" })
    guard.record("s", key, false, "x")
    guard.record("s", invocationKey({ script: "b" }), false, "x")
    expect(guard.record("s", key, true, "fine")).toBe("fine")
    guard.record("s", invocationKey({ script: "c" }), false, "x")
    guard.record("s", invocationKey({ script: "d" }), false, "x")
    expect(guard.refusal("s")).toBeUndefined()
    expect(guard.record("s", key, false, "x")).toBe("x")
  })

  test("a reset keeps remembering which scripts failed", () => {
    const guard = new RepeatGuard()
    const key = invocationKey({ script: "a" })
    guard.record("s", key, false, "x")
    guard.reset("s")
    expect(guard.record("s", key, false, "x")).toContain("already failed 1 time(s)")
    guard.reset("never-seen")
    expect(guard.refusal("never-seen")).toBeUndefined()
  })

  test("the oldest sessions are forgotten past the limit", () => {
    const guard = new RepeatGuard(3)
    const key = invocationKey({ script: "a" })
    for (const id of ["s1", "s2", "s3"]) for (let i = 0; i < 3; i++) guard.record(id, key, false, "x")
    expect(guard.refusal("s1")).toBe(REFUSAL)
    guard.record("s4", key, false, "x")
    expect(guard.refusal("s1")).toBeUndefined()
    expect(guard.record("s1", key, false, "x")).toBe("x")
    expect(guard.refusal("s3")).toBe(REFUSAL)
  })

  test("one session remembers a bounded number of failed scripts", () => {
    const guard = new RepeatGuard()
    for (let i = 0; i < 80; i++) guard.record("s", invocationKey({ script: `s${i}` }), false, "x")
    expect(guard.record("s", invocationKey({ script: "s0" }), false, "x")).toBe("x")
    expect(guard.record("s", invocationKey({ script: "s79" }), false, "x")).toContain("already failed 1 time(s)")
  })
})
