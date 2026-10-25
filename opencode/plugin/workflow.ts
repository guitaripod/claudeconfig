import { toolDescription, ultracodeNotice } from "../../workflow-runtime/instructions.ts"
import { formatResult, hasUltracodeKeyword, invocationKey, listWorkflows, RepeatGuard, runWorkflow } from "../../workflow-runtime/runtime.ts"
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

const FALLBACK_AGENT = "general"
const LIST_ARGUMENT = "list"
const STOP_ARGUMENT = "stop"
const INTERRUPTED_EVENT = "session.execution.interrupted"

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

/// The message that hands a finished workflow result to the model for relaying.
function deliveryText(body: string): string {
  return `The workflow finished. Relay the result below to the user as is, without calling any tools.\n\n${body}`
}

export default {
  id: "workflow",
  setup: async (ctx: any) => {
    const children = new Set<string>()
    const flagged = new Set<string>()
    const models = new Map<string, ModelRef>()
    const runs = new Map<string, Set<AbortController>>()
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

    /// Aborts a session's workflows whenever the harness reports that the session was interrupted.
    async function watchInterrupts(): Promise<void> {
      try {
        for await (const event of ctx.event.subscribe()) {
          if (event?.type === INTERRUPTED_EVENT && event.data?.sessionID) abortRuns(event.data.sessionID)
        }
      } catch {
        return
      }
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

    void watchInterrupts()

    await ctx.tool.transform((tools: any) => {
      tools.add({
        name: "workflow",
        description: toolDescription(listWorkflows(ctx.location.directory)),
        input: INPUT,
        options: { codemode: false },
        execute: async (input: WorkflowInput, context: ToolContext) => {
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

    /// Runs a saved workflow in the background and delivers its result to the session unless the run was stopped.
    async function runDetached(sessionID: string, name: string, args: string | undefined): Promise<void> {
      const run = trackRun(sessionID)
      let body: string
      try {
        body = formatResult(await execute(sessionID, { name }, args, run.controller.signal, undefined))
      } catch (error) {
        body = `workflow failed: ${error instanceof Error ? error.message : String(error)}`
      } finally {
        run.release()
      }
      if (run.controller.signal.aborted) return
      await deliver(sessionID, body)
    }

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
        description: "Run a saved workflow in the background: /workflow <name> [args...], /workflow list, /workflow stop",
        execute: async ({ sessionID, prompt }: { sessionID: string; prompt: { text?: string } }) => {
          flagged.delete(sessionID)
          guard.reset(sessionID)
          const { name, args } = parseCommand(prompt?.text ?? "")
          if (name === "" || name === LIST_ARGUMENT) {
            await deliver(sessionID, listText(listWorkflows(await sessionDirectory(sessionID))))
          } else if (name === STOP_ARGUMENT) {
            await deliver(sessionID, `Stopped ${abortRuns(sessionID)} running workflow(s).`)
          } else {
            void runDetached(sessionID, name, args)
          }
        },
      })
    })

    await ctx.session.hook("prompt", async (event: any) => {
      const sessionID: string = event.sessionID
      if (await isChild(sessionID)) return
      guard.reset(sessionID)
      if (hasUltracodeKeyword(event.prompt?.text ?? "")) flagged.add(sessionID)
      else flagged.delete(sessionID)
    })

    await ctx.session.hook("context", (event: any) => {
      if (event.model && !children.has(event.sessionID)) models.set(event.sessionID, toModelRef(event.model))
      if (flagged.has(event.sessionID)) {
        event.system.push({ type: "text", text: ultracodeNotice(listWorkflows(ctx.location.directory)) })
      }
    })
  },
}
