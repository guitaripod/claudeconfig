import { afterAll, beforeAll, describe, expect, mock, test } from "bun:test"
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import path from "node:path"

const PARENT = "ses_parent"
const SYSTEM_TOOLS = ["read", "bash", "workflow", "task", "ask", "irc"]

let root: string
let manager: unknown

mock.module("@oh-my-pi/pi-coding-agent/mcp", () => ({ MCPManager: { instance: () => manager } }))

const { default: extension } = await import("../omp/extensions/workflow.ts")

beforeAll(() => {
  root = mkdtempSync(path.join(tmpdir(), "workflow-omp-adapter-"))
  const dir = path.join(root, ".claude", "workflows")
  mkdirSync(dir, { recursive: true })
  writeFileSync(path.join(dir, "answer.js"), "export const meta = { name: 'answer', description: 'Returns args' }\nreturn 'answer:' + args")
  writeFileSync(path.join(dir, "kids.js"), "export const meta = { name: 'kids' }\nreturn await agent('do the work')")
})

afterAll(() => {
  rmSync(root, { recursive: true, force: true })
})

/// A zod stand-in whose every call and property access returns itself, enough for the schema the extension declares.
function chain(): any {
  const proxy: any = new Proxy(() => proxy, { get: () => proxy, apply: () => proxy })
  return proxy
}

/// A child session stand-in that records aborts and, when held, never finishes its prompt until aborted.
function fakeSession(hold: boolean, record: { aborts: number; trims: string[][]; disposed: number }) {
  let release: (() => void) | undefined
  return {
    messages: [],
    getLastAssistantText: () => "child done",
    getActiveToolNames: () => [...SYSTEM_TOOLS],
    getToolByName: (name: string) => (name.startsWith("mcp__") ? {} : undefined),
    setActiveToolsByName: async (names: string[]) => void record.trims.push(names),
    prompt: () => (hold ? new Promise<void>((resolve) => (release = resolve)) : Promise.resolve()),
    abort: async () => {
      record.aborts += 1
      release?.()
    },
    dispose: async () => void (record.disposed += 1),
  }
}

/// A stand-in for the omp extension API that records what the extension registers, hooks and sends.
function loadExtension(holdChildren = false) {
  const handlers = new Map<string, (event: any, ctx: any) => any>()
  const sent: { message: any; options: any }[] = []
  const created: any[] = []
  const record = { aborts: 0, trims: [] as string[][], disposed: 0 }
  const registered: { tool?: any; command?: any } = {}
  const pi: any = {
    zod: chain(),
    typebox: { Type: { Unsafe: (schema: unknown) => schema } },
    registerTool: (tool: any) => (registered.tool = tool),
    registerCommand: (_name: string, command: any) => (registered.command = command),
    on: (name: string, handler: any) => void handlers.set(name, handler),
    sendMessage: (message: any, options: any) => void sent.push({ message, options }),
    getThinkingLevel: () => "off",
    pi: {
      MAIN_AGENT_ID: "Main",
      Settings: { instance: {}, isolated: () => ({}) },
      createSubagentSettings: () => undefined,
      SessionManager: { inMemory: () => ({}) },
      createMCPProxyTools: (source: any) => source.tools.map((name: string) => ({ name })),
      createAgentSession: async (options: any) => {
        created.push(options)
        return { session: fakeSession(holdChildren, record) }
      },
    },
  }
  extension(pi)
  const ctx: any = {
    cwd: root,
    model: { provider: "p", id: "m" },
    modelRegistry: { find: () => undefined, authStorage: {} },
    sessionManager: { getSessionId: () => PARENT },
  }
  return { handlers, sent, created, record, registered, ctx }
}

type Loaded = ReturnType<typeof loadExtension>

/// Runs the `/workflow` command the way omp does for the session.
async function runCommand(loaded: Loaded, text: string) {
  await loaded.registered.command.handler(text, loaded.ctx)
}

/// What the before_provider_request hook makes of a request body, or undefined when it leaves the body alone.
async function rewritten(loaded: Loaded, payload: object, ctx: any = loaded.ctx) {
  return loaded.handlers.get("before_provider_request")?.({ type: "before_provider_request", payload }, ctx)
}

/// Runs the registered workflow tool as omp does, with an abort signal.
async function callTool(loaded: Loaded, input: object, signal = new AbortController().signal) {
  return loaded.registered.tool.execute("call_1", input, signal, undefined, loaded.ctx)
}

const chatBody = () => ({
  messages: [],
  tools: ["read", "workflow"].map((name) => ({ type: "function", function: { name, description: name, parameters: { type: "object" } } })),
})

async function endAgent(loaded: Loaded, stopReason: string) {
  await loaded.handlers.get("agent_end")?.({ type: "agent_end", messages: [{ role: "assistant", stopReason }] }, loaded.ctx)
}

describe("/workflow command", () => {
  test("starts a hidden model turn that names the workflow and its arguments", async () => {
    const loaded = loadExtension()
    await runCommand(loaded, "answer 42")
    expect(loaded.sent).toHaveLength(1)
    const { message, options } = loaded.sent[0]
    expect(options).toEqual({ triggerTurn: true })
    expect(message.display).toBe(false)
    expect(message.content).toContain('Call the workflow tool now, exactly once, with name "answer" and args "42"')
  })

  test("forces the call: only the workflow tool, a fixed input and a required tool choice", async () => {
    const loaded = loadExtension()
    await runCommand(loaded, "answer 42")
    const body: any = await rewritten(loaded, chatBody())
    expect(body.tools.map((tool: any) => tool.function.name)).toEqual(["workflow"])
    expect(body.tools[0].function.parameters.properties).toEqual({ name: { const: "answer" }, args: { const: "42" } })
    expect(body.tool_choice).toBe("required")
  })

  test("forces the call on the messages and responses wire formats too", async () => {
    const loaded = loadExtension()
    await runCommand(loaded, "answer")
    const messages: any = await rewritten(loaded, { tools: [{ name: "read" }, { name: "workflow", input_schema: {} }] })
    expect(messages.tool_choice).toEqual({ type: "any" })
    expect(messages.tools[0].input_schema.properties).toEqual({ name: { const: "answer" } })
    const responses: any = await rewritten(loaded, { tools: [{ type: "function", name: "workflow", parameters: {} }] })
    expect(responses.tool_choice).toBe("required")
    expect(responses.tools[0].parameters.properties).toEqual({ name: { const: "answer" } })
  })

  test("leaves requests alone without a command, without the tool, and for sub-agents", async () => {
    const loaded = loadExtension()
    expect(await rewritten(loaded, chatBody())).toBeUndefined()
    await runCommand(loaded, "answer")
    expect(await rewritten(loaded, { messages: [], tools: [{ type: "function", function: { name: "read" } }] })).toBeUndefined()
    expect(await rewritten(loaded, { messages: [] })).toBeUndefined()
    expect(await rewritten(loaded, chatBody(), { ...loaded.ctx, agent: { kind: "task" } })).toBeUndefined()
  })

  test("the tool runs the typed workflow whatever the model sent, then the next request switches tools off", async () => {
    const loaded = loadExtension()
    await runCommand(loaded, "answer 42")
    const result = await callTool(loaded, { script: "return 1" })
    expect(result.content[0].text).toContain("answer:42")
    const relay: any = await rewritten(loaded, chatBody())
    expect(relay.tool_choice).toBe("none")
    expect(relay.tools).toHaveLength(1)
  })

  test("list, stop and an unknown name are relayed by a tool-less model turn", async () => {
    const loaded = loadExtension()
    await runCommand(loaded, "list")
    await runCommand(loaded, "stop")
    await runCommand(loaded, "missing")
    const bodies = loaded.sent.map((entry) => entry.message.content as string)
    expect(bodies[0]).toContain("- answer: Returns args")
    expect(bodies[1]).toContain("No workflow is running.")
    expect(bodies[2]).toContain('No saved workflow named "missing"')
    expect(loaded.sent.every((entry) => entry.options.triggerTurn && entry.message.display === false)).toBe(true)
    const body: any = await rewritten(loaded, chatBody())
    expect(body.tool_choice).toBe("none")
  })

  test("a turn that ends without the tool call says so plainly through a tool-less model turn", async () => {
    const loaded = loadExtension()
    await runCommand(loaded, "answer")
    await endAgent(loaded, "stop")
    expect(loaded.sent).toHaveLength(2)
    expect(loaded.sent[1].options).toEqual({ triggerTurn: true })
    expect(loaded.sent[1].message.content).toContain('The workflow "answer" did not run')
    const body: any = await rewritten(loaded, chatBody())
    expect(body.tool_choice).toBe("none")
  })

  test("a stopped or failed turn says nothing and releases the session", async () => {
    const loaded = loadExtension()
    await runCommand(loaded, "answer")
    await endAgent(loaded, "aborted")
    await runCommand(loaded, "answer")
    await endAgent(loaded, "error")
    expect(loaded.sent).toHaveLength(2)
    expect(await rewritten(loaded, chatBody())).toBeUndefined()
  })

  test("a finished command turn releases the session", async () => {
    const loaded = loadExtension()
    await runCommand(loaded, "answer")
    await callTool(loaded, {})
    await endAgent(loaded, "stop")
    expect(loaded.sent).toHaveLength(1)
    expect(await rewritten(loaded, chatBody())).toBeUndefined()
  })

  test("a different user prompt drops a pending command", async () => {
    const loaded = loadExtension()
    await runCommand(loaded, "answer")
    await loaded.handlers.get("before_agent_start")?.({ type: "before_agent_start", prompt: "something else", systemPrompt: [] }, loaded.ctx)
    expect(await rewritten(loaded, chatBody())).toBeUndefined()
  })
})

describe("stop", () => {
  test("aborting the tool signal aborts every child and ends the run at once", async () => {
    const loaded = loadExtension(true)
    const controller = new AbortController()
    const script = "return await parallel([1, 2, 3].map((i) => () => agent('work ' + i)))"
    const pending = callTool(loaded, { script }, controller.signal)
    await Bun.sleep(30)
    controller.abort()
    const result = await pending
    expect(result.content[0].text).toContain("aborted")
    expect(loaded.record.aborts).toBe(3)
    expect(loaded.record.disposed).toBe(3)
  })

  test("/workflow stop aborts a running workflow", async () => {
    const loaded = loadExtension(true)
    const slow = callTool(loaded, { script: "await agent('block')\nreturn 1" })
    await Bun.sleep(30)
    await runCommand(loaded, "stop")
    const result = await slow
    expect(result.content[0].text).toContain("aborted")
    expect(loaded.sent.at(-1)?.message.content).toContain("Stopped 1 running workflow.")
  })
})

describe("sub-agents", () => {
  test("lose the tools that start agents or wait for a person and run without MCP when the parent has none", async () => {
    manager = undefined
    const loaded = loadExtension()
    const result = await callTool(loaded, { name: "kids" })
    expect(result.content[0].text).toContain("child done")
    expect(loaded.created[0].enableMCP).toBe(false)
    expect(loaded.created[0].mcpManager).toBeUndefined()
    expect(loaded.record.trims).toEqual([["read", "bash"]])
  })

  test("share the parent's MCP connections instead of starting servers of their own", async () => {
    manager = { tools: ["mcp__stub_ping"] }
    const loaded = loadExtension()
    await callTool(loaded, { name: "kids" })
    const options = loaded.created[0]
    expect(options.enableMCP).toBe(true)
    expect(options.mcpManager).toBe(manager)
    expect(options.customTools.map((tool: any) => tool.name)).toEqual(["mcp__stub_ping"])
    expect(options.disableExtensionDiscovery).toBe(true)
    expect(loaded.record.trims).toEqual([["read", "bash", "mcp__stub_ping"]])
    manager = undefined
  })
})
