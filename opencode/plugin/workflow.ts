import { toolDescription, ultracodeNotice } from "../../workflow-runtime/instructions.ts"
import { findWorkflow, formatResult, hasUltracodeKeyword, invocationKey, listWorkflows, RepeatGuard, runWorkflow } from "../../workflow-runtime/runtime.ts"
import type { AgentRequest, AgentResult, Meta, RunResult, Runner, WorkflowEvent } from "../../workflow-runtime/runtime.ts"

interface ModelRef {
  providerID: string
  id: string
  variant?: string
}

interface WorkflowInput {
  script?: string
  name?: string
  args?: unknown
}

interface ToolContext {
  sessionID: string
  signal: AbortSignal
  progress: (state: object) => Promise<void> | void
}

interface Progress {
  phase?: string
  running: number
  done: number
  failed: number
  agents: number
}

interface Pin {
  name: string
  args: string | undefined
  text: string
  stage: "call" | "relay"
}

const FALLBACK_AGENT = "general"
const LIST_ARGUMENT = "list"
const STOP_ARGUMENT = "stop"
const TOOL_NAME = "workflow"
const CODE_MODE_HEADING = "# Code Mode"
const CODE_MODE_TOOL = "execute"
const ORCHESTRATION_TOOLS = [TOOL_NAME, "subagent", "question"]
const TURN_END_EVENTS = new Set(["session.execution.interrupted", "session.execution.succeeded", "session.execution.failed"])
const INTERRUPTED_EVENT = "session.execution.interrupted"
const SUCCEEDED_EVENT = "session.execution.succeeded"

const INPUT = {
  type: "object",
  properties: {
    script: {
      type: "string",
      description: "JavaScript workflow script to run. Give either script or name, never both.",
    },
    name: { type: "string", description: "Name of a saved workflow to run. Give either name or script, never both." },
    args: { description: "Value passed to the script as `args` (a string or any JSON). Optional." },
  },
  additionalProperties: false,
}

/// Splits a model id of the form `provider/id` into its parts, or returns undefined for plain aliases such as `haiku`.
function parseModel(value: string | undefined): ModelRef | undefined {
  if (!value) return undefined
  const slash = value.indexOf("/")
  if (slash <= 0 || slash === value.length - 1) return undefined
  return { providerID: value.slice(0, slash), id: value.slice(slash + 1) }
}

/// Reduces a model description to the three fields `session.create` accepts.
function toModelRef(model: { providerID: string; id: string; variant?: string }): ModelRef {
  return model.variant
    ? { providerID: model.providerID, id: model.id, variant: model.variant }
    : { providerID: model.providerID, id: model.id }
}

/// Concatenates the text parts of the last assistant message and fails when the session did not finish cleanly.
function finalText(messages: any[]): string {
  const idle = messages.findLast((m) => m.type === "idle")
  const last = messages.findLast((m) => m.type === "assistant")
  if (last?.error) throw new Error(describeError(last.error))
  if (idle && idle.outcome !== "succeeded") throw new Error(`sub-agent ended with outcome ${idle.outcome}`)
  if (!last) throw new Error("sub-agent produced no reply")
  return (last.content ?? [])
    .filter((part: any) => part.type === "text")
    .map((part: any) => part.text)
    .join("")
}

/// Turns an assistant error payload of unknown shape into one readable line.
function describeError(error: unknown): string {
  if (typeof error === "string") return error
  const message = (error as { message?: unknown } | null)?.message
  return typeof message === "string" ? message : JSON.stringify(error)
}

/// One line per saved workflow plus the reserved command words, for the `/workflow list` reply.
function listText(saved: Meta[]): string {
  const lines = saved.map((w) => (w.description ? `- ${w.name}: ${w.description}` : `- ${w.name}`))
  const reserved = `Reserved: /workflow ${STOP_ARGUMENT} stops running workflows; saved workflows named ${LIST_ARGUMENT} or ${STOP_ARGUMENT} cannot be run by command.`
  return [saved.length === 0 ? "No saved workflows." : "Saved workflows:", ...lines, reserved].join("\n")
}

/// Splits `/workflow` command text into the workflow name and the remaining argument string.
function parseCommand(text: string): { name: string; args: string | undefined } {
  const trimmed = text.trim()
  const space = trimmed.search(/\s/)
  if (space === -1) return { name: trimmed, args: undefined }
  const rest = trimmed.slice(space).trim()
  return { name: trimmed.slice(0, space), args: rest || undefined }
}

/// The user message of the turn that runs a saved workflow for `/workflow <name> [args]`.
function commandPrompt(name: string, args: string | undefined): string {
  return args === undefined ? `Run the saved workflow "${name}".` : `Run the saved workflow "${name}" with the arguments: ${args}`
}

/// The tool input schema for a pinned call: the model can only emit the exact name and args the user typed.
function pinnedSchema(pin: Pin): object {
  const properties: Record<string, object> = { name: { const: pin.name } }
  if (pin.args !== undefined) properties.args = { const: pin.args }
  return { type: "object", properties, required: Object.keys(properties), additionalProperties: false }
}

/// The hidden instruction for a pinned turn: call the tool first, then relay what it returned.
function pinNotice(pin: Pin): string {
  if (pin.stage === "relay") {
    return "The workflow tool has finished. Relay its result to the user as is. Do not call any tools."
  }
  return `The user ran the command /workflow ${pin.name}. Call the ${TOOL_NAME} tool now, exactly once, with the name and args already fixed in its schema. Do not answer before calling it.`
}

/// The text that tells the user a pinned turn ended without the tool being called.
function notRunText(pin: Pin): string {
  return `The workflow "${pin.name}" did not run: the model answered without calling the ${TOOL_NAME} tool. Tell the user plainly that nothing ran and that /workflow ${pin.name} can be tried again.`
}

/// The message that hands a reply of the `/workflow` command to the model for relaying.
function deliveryText(body: string): string {
  return `Relay the message below to the user as is, without calling any tools.\n\n${body}`
}

export default {
  id: "workflow",
  setup: async (ctx: any) => {
    const children = new Set<string>()
    const flagged = new Set<string>()
    const models = new Map<string, ModelRef>()
    const runs = new Map<string, Set<AbortController>>()
    const pins = new Map<string, Pin>()
    const guard = new RepeatGuard()

    /// Registers a running workflow for a session; its controller aborts with `external` and is dropped by `release`.
    function trackRun(sessionID: string, external?: AbortSignal): { controller: AbortController; release: () => void } {
      const controller = new AbortController()
      const abort = () => controller.abort()
      if (external?.aborted) abort()
      else external?.addEventListener("abort", abort, { once: true })
      const set = runs.get(sessionID) ?? new Set<AbortController>()
      set.add(controller)
      runs.set(sessionID, set)
      return {
        controller,
        release: () => {
          external?.removeEventListener("abort", abort)
          set.delete(controller)
          if (set.size === 0 && runs.get(sessionID) === set) runs.delete(sessionID)
        },
      }
    }

    /// Aborts every workflow still running for a session and returns how many were stopped.
    function abortRuns(sessionID: string): number {
      let stopped = 0
      for (const controller of runs.get(sessionID) ?? []) {
        if (controller.signal.aborted) continue
        controller.abort()
        stopped += 1
      }
      return stopped
    }

    /// Stops every workflow of a session, also a command whose tool call has not started yet, and returns how many were stopped.
    async function stopAll(sessionID: string): Promise<number> {
      const stopped = abortRuns(sessionID)
      if (pins.get(sessionID)?.stage !== "call") return stopped
      pins.delete(sessionID)
      await ctx.session.interrupt({ sessionID, resume: false }).catch(() => undefined)
      return stopped + 1
    }

    /// Reacts to turn events: an interrupt aborts the session's workflows, and any turn end settles a pinned command.
    async function watchTurns(): Promise<void> {
      try {
        for await (const event of ctx.event.subscribe()) {
          const sessionID: string | undefined = event?.data?.sessionID
          if (!sessionID || !TURN_END_EVENTS.has(event.type)) continue
          if (event.type === INTERRUPTED_EVENT) abortRuns(sessionID)
          void settlePin(sessionID, event.type === SUCCEEDED_EVENT)
        }
      } catch {
        return
      }
    }

    /// Drops the pinned command of a session once its turn ended, and says so plainly if the tool was never called.
    async function settlePin(sessionID: string, succeeded: boolean): Promise<void> {
      const pin = pins.get(sessionID)
      if (!pin) return
      pins.delete(sessionID)
      if (succeeded && pin.stage === "call") await deliver(sessionID, notRunText(pin))
    }

    /// True for sessions this plugin created and for any other session that has a parent.
    async function isChild(sessionID: string): Promise<boolean> {
      if (children.has(sessionID)) return true
      try {
        const session = await ctx.session.get({ sessionID })
        if (session?.parentID) children.add(sessionID)
        return Boolean(session?.parentID)
      } catch {
        return false
      }
    }

    /// The directory the calling session works in, which becomes the working directory of every sub-agent.
    async function sessionDirectory(sessionID: string): Promise<string> {
      try {
        const session = await ctx.session.get({ sessionID })
        return session?.location?.directory ?? ctx.location.directory
      } catch {
        return ctx.location.directory
      }
    }

    /// The model the calling session runs on: the one seen by the context hook, else its own, else the default.
    async function parentModel(sessionID: string): Promise<ModelRef> {
      const seen = models.get(sessionID)
      if (seen) return seen
      const session = await ctx.session.get({ sessionID }).catch(() => undefined)
      if (session?.model) return toModelRef(session.model)
      return toModelRef((await ctx.model.default()).data)
    }

    /// Names of the agents that can run as sub-agents, read once per workflow run.
    async function subagentNames(): Promise<Set<string>> {
      try {
        const listed = await ctx.agent.list()
        const agents: any[] = Array.isArray(listed) ? listed : (listed?.data ?? [])
        return new Set(agents.filter((a) => a.mode === "subagent").map((a) => a.name))
      } catch {
        return new Set()
      }
    }

    /// Builds the runner that executes each agent() call as a child session of `parentID`.
    async function createRunner(parentID: string, title: string): Promise<Runner> {
      const [directory, fallbackModel, subagents] = await Promise.all([
        sessionDirectory(parentID),
        parentModel(parentID),
        subagentNames(),
      ])

      /// Stops one child session without resuming any queued work.
      async function interrupt(sessionID: string): Promise<void> {
        try {
          await ctx.session.interrupt({ sessionID, resume: false })
        } catch {
          return
        }
      }

      return {
        async run(req: AgentRequest): Promise<AgentResult> {
          const session = await ctx.session.create({
            parentID,
            title: `${title}: ${req.label}`,
            agent: req.agentType && subagents.has(req.agentType) ? req.agentType : FALLBACK_AGENT,
            model: parseModel(req.model) ?? fallbackModel,
            location: { directory },
          })
          children.add(session.id)
          const stop = () => void interrupt(session.id)
          req.signal.addEventListener("abort", stop, { once: true })
          let completed = false
          try {
            if (req.signal.aborted) throw new Error("aborted")
            await ctx.session.prompt({ sessionID: session.id, text: req.prompt })
            if (req.signal.aborted) throw new Error("aborted")
            await ctx.session.wait({ sessionID: session.id })
            if (req.signal.aborted) throw new Error("aborted")
            const text = finalText(await ctx.session.context({ sessionID: session.id }))
            completed = true
            return { text }
          } finally {
            req.signal.removeEventListener("abort", stop)
            if (!completed) await interrupt(session.id)
          }
        },
      }
    }

    /// Runs a script or saved workflow for a session and returns the run result.
    async function execute(
      sessionID: string,
      source: { script?: string; name?: string },
      args: unknown,
      signal: AbortSignal | undefined,
      progress: ((state: Progress) => Promise<void> | void) | undefined,
    ): Promise<RunResult> {
      const cwd = await sessionDirectory(sessionID)
      const state: Progress = { running: 0, done: 0, failed: 0, agents: 0 }
      const onEvent = (e: WorkflowEvent) => {
        if (e.type === "phase") state.phase = e.title
        if (e.type === "agent_start") {
          state.agents = Math.max(state.agents, e.index)
          state.running = e.running
          state.phase = e.phase ?? state.phase
        }
        if (e.type === "agent_end") {
          state.running = e.running
          state.done = e.done
          state.failed = e.failed
        }
        void Promise.resolve(progress?.({ ...state })).catch(() => undefined)
      }
      const runner = await createRunner(sessionID, source.name ?? "workflow")
      return runWorkflow({
        source: source.script,
        name: source.name,
        args,
        runner,
        cwd,
        signal,
        onEvent,
      })
    }

    void watchTurns()

    await ctx.tool.transform((tools: any) => {
      tools.add({
        name: TOOL_NAME,
        description: toolDescription(listWorkflows(ctx.location.directory)),
        input: INPUT,
        options: { codemode: false },
        execute: async (modelInput: WorkflowInput, context: ToolContext) => {
          const pin = pins.get(context.sessionID)
          const input: WorkflowInput = pin?.stage === "call" ? { name: pin.name, args: pin.args } : modelInput
          if (pin?.stage === "call") pin.stage = "relay"
          const hasScript = typeof input.script === "string" && input.script.trim() !== ""
          const hasName = typeof input.name === "string" && input.name.trim() !== ""
          if (hasScript === hasName) {
            return { content: "workflow: give exactly one of script or name (with optional args), not both and not neither." }
          }
          if (await isChild(context.sessionID)) {
            return { content: "workflow: sub-agents cannot start workflows. Do the work yourself and reply." }
          }
          const refusal = guard.refusal(context.sessionID)
          if (refusal) return { content: refusal }
          const key = invocationKey(input)
          const run = trackRun(context.sessionID, context.signal)
          try {
            const result = await execute(
              context.sessionID,
              hasScript ? { script: input.script } : { name: input.name?.trim() },
              input.args,
              run.controller.signal,
              (state) => context.progress(state),
            )
            return { content: guard.record(context.sessionID, key, result.ok, formatResult(result)) }
          } catch (error) {
            const text = `workflow failed: ${error instanceof Error ? error.message : String(error)}`
            return { content: guard.record(context.sessionID, key, false, text) }
          } finally {
            run.release()
            flagged.delete(context.sessionID)
          }
        },
      })
    })

    /// Hands text to the model of a session so it relays it to the user.
    async function deliver(sessionID: string, body: string): Promise<void> {
      try {
        await ctx.session.synthetic({ sessionID, text: deliveryText(body) })
      } catch {
        return
      }
    }

    await ctx.command.transform((commands: any) => {
      commands.add({
        name: "workflow",
        description: "Run a saved workflow in a model turn that can be stopped: /workflow <name> [args...], /workflow list, /workflow stop",
        execute: async ({ sessionID, prompt }: { sessionID: string; prompt: { text?: string } }) => {
          flagged.delete(sessionID)
          guard.reset(sessionID)
          const { name, args } = parseCommand(prompt?.text ?? "")
          const directory = await sessionDirectory(sessionID)
          if (name === "" || name === LIST_ARGUMENT) {
            await deliver(sessionID, listText(listWorkflows(directory)))
          } else if (name === STOP_ARGUMENT) {
            await deliver(sessionID, `Stopped ${await stopAll(sessionID)} running workflow(s).`)
          } else if (findWorkflow(name, directory) === undefined) {
            await deliver(sessionID, `No saved workflow named "${name}".\n\n${listText(listWorkflows(directory))}`)
          } else {
            const pin: Pin = { name, args, text: commandPrompt(name, args), stage: "call" }
            pins.set(sessionID, pin)
            await ctx.session.prompt({ sessionID, text: pin.text })
          }
        },
      })
    })

    await ctx.session.hook("prompt", async (event: any) => {
      const sessionID: string = event.sessionID
      if (await isChild(sessionID)) return
      if (pins.get(sessionID)?.text === event.prompt?.text) return
      pins.delete(sessionID)
      guard.reset(sessionID)
      if (hasUltracodeKeyword(event.prompt?.text ?? "")) flagged.add(sessionID)
      else flagged.delete(sessionID)
    })

    /// Removes the code-mode instructions, which list every tool and weigh about fourteen thousand tokens, together with the `execute` tool they describe.
    function dropCodeMode(event: any): void {
      const kept = event.system.filter((block: any) => !String(block?.text ?? "").startsWith(CODE_MODE_HEADING))
      if (kept.length === event.system.length) return
      event.system.splice(0, event.system.length, ...kept)
      delete event.tools?.[CODE_MODE_TOOL]
    }

    /// Takes the tools that start more agents or wait for a person away from a sub-agent; code mode stays, because MCP tools are reachable only through it.
    function trimChild(event: any): void {
      for (const name of ORCHESTRATION_TOOLS) delete event.tools?.[name]
    }

    /// Narrows a pinned turn: before the call only the workflow tool with a fixed input, afterwards no tools at all.
    function applyPin(event: any, pin: Pin): void {
      dropCodeMode(event)
      const tools = event.tools ?? {}
      const tool = tools[TOOL_NAME]
      for (const key of Object.keys(tools)) delete tools[key]
      if (pin.stage === "call" && tool) tools[TOOL_NAME] = { ...tool, input: pinnedSchema(pin) }
      event.system.push({ type: "text", text: pinNotice(pin) })
    }

    await ctx.session.hook("http.request", async (event: any) => {
      if (event.kind !== "primary" || pins.get(event.sessionID)?.stage !== "call") return
      try {
        const body = JSON.parse(await event.request.clone().text())
        if (!Array.isArray(body.tools) || body.tools.length === 0) return
        body.tool_choice = "required"
        const headers = new Headers(event.request.headers)
        headers.delete("content-length")
        event.request = new Request(event.request.url, { method: event.request.method, headers, body: JSON.stringify(body) })
      } catch {
        return
      }
    })

    await ctx.session.hook("context", (event: any) => {
      if (event.model && !children.has(event.sessionID)) models.set(event.sessionID, toModelRef(event.model))
      if (children.has(event.sessionID)) {
        trimChild(event)
        return
      }
      const pin = pins.get(event.sessionID)
      if (pin) {
        applyPin(event, pin)
        return
      }
      if (flagged.has(event.sessionID)) {
        event.system.push({ type: "text", text: ultracodeNotice(listWorkflows(ctx.location.directory)) })
      }
    })
  },
}
