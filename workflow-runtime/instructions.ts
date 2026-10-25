import type { Meta } from "./runtime"

const DESCRIPTION_LIMIT = 200

const WORKED_EXAMPLE = `const files = args.files
phase("Inspect")
const reports = await pipeline(
  files,
  (file) =>
    agent("Read " + file + " and report what it does and any bugs. Reply with the JSON object only.", {
      label: "inspect:" + file,
      schema: {
        type: "object",
        properties: { summary: { type: "string" }, bugs: { type: "array", items: { type: "string" } } },
        required: ["summary", "bugs"],
      },
    })
)
phase("Synthesize")
const ok = reports.filter((r) => r !== null)
return await agent("Combine these file reports into one short review:\\n" + JSON.stringify(ok), { label: "synthesize" })`

/// One line per saved workflow, with long descriptions cut short.
function savedList(saved: Meta[]): string {
  if (saved.length === 0) return "No saved workflows."
  const lines = saved.map((w) => {
    const text = (w.description ?? "").replace(/\s+/g, " ").trim()
    const short = text.length > DESCRIPTION_LIMIT ? `${text.slice(0, DESCRIPTION_LIMIT)}...` : text
    return short ? `- ${w.name}: ${short}` : `- ${w.name}`
  })
  return ["Saved workflows (run one with { name, args }):", ...lines].join("\n")
}

export function toolDescription(saved: Meta[]): string {
  return `Run a multi-agent workflow: a JavaScript script that fans work out to many sub-agents in parallel and returns one result. Every agent() call starts a real sub-agent with the normal coding tools (read, bash, edit, search) on your model.

Input: give EITHER "script" (JavaScript you wrote, see below) OR "name" (a saved workflow) plus optional "args". Never both, never neither.

Script rules:
- agent, parallel, pipeline, phase, log, args, budget and workflow are already defined globals. Never require() or import them and never declare a variable with one of those names (const agent = ... or const { agent } = require(...) fails). Just call them.
- Plain JavaScript only. No TypeScript, no import, no export, no require. The body is an async function: use await and top-level return. The value you return is the tool result: return a string or a JSON value.
- An optional first line "export const meta = { name: 'x', description: '...' }" names the script.
- Each sub-agent starts with a fresh, empty context. It sees only its prompt, so make every prompt self-contained: include the file paths, the data, the goal and the answer format.

Functions available in the script:
- agent(prompt, opts?) -> Promise<string | object | null>. Runs one sub-agent and resolves with its final reply. opts: label (short name shown in progress), phase, schema, model, agentType. With opts.schema (a JSON Schema object) the reply is parsed and validated and you get the parsed object back; a mismatch is retried twice, then you get null. Supported schema keywords: type (a string or array of types, "null" allowed), properties, required, items, enum, additionalProperties: false. It resolves to null (it never throws) when the agent fails, so check for null before using a result.
- parallel(thunks) -> Promise<array>. Takes an array of functions that each return a promise, for example items.map((x) => () => agent(...)). Waits for all of them. A thunk that throws gives null in its slot.
- pipeline(items, ...stages) -> Promise<array>. Runs every item through the stages in order, each item independently: stage(prev, item, index) where prev is the previous stage result (the item itself for the first stage). A stage that throws makes that item null and skips its remaining stages. Prefer pipeline over parallel followed by a second parallel, because slow items do not hold back fast ones.
- phase(title) sets the current phase name shown in progress.
- log(message) records a note that appears in the progress output.
- args is the "args" input, passed through as given (a string or any JSON).
- budget has total, spent() and remaining(); there is no token limit here.
- workflow(nameOrRef, args) runs a saved workflow inline (name string or { scriptPath }) and returns its result. It may be nested one level only.

Limits: at most 8 agents run at the same time and the rest wait their turn (WORKFLOW_CONCURRENCY changes this), and a run may start at most 200 agents. Prefer 16 agents or fewer in total unless the task truly needs more. Give each agent one bounded job and keep the final synthesis in a separate agent or in your own answer.

Errors come back as text: a syntax or runtime error in your script returns "workflow <name> failed: <reason>". Change the script to fix the error and call the tool again; resending the same failing script fails the same way, and the tool refuses calls after three failures in a row. The result ends with a line "workflow <name>: N agents, F failed, Ts" and any failure notes.

Example, fan out over a list with a schema and then synthesize (called with args { files: ["a.ts", "b.ts"] }):

${WORKED_EXAMPLE}

${savedList(saved)}`
}

export function ultracodeNotice(saved: Meta[]): string {
  const fit =
    saved.length > 0
      ? `\nIf a saved workflow fits the task, call the tool with its name instead of writing a script. Saved workflows: ${saved.map((w) => w.name).join(", ")}.`
      : ""
  return `The user asked for multi-agent orchestration (the word "ultracode"). Do this task by calling the "workflow" tool with a script that splits the work into independent parts and fans them out to parallel sub-agents with agent(), parallel() or pipeline(). Make every sub-agent prompt self-contained, because sub-agents start with no context. In the script, agent, parallel, pipeline, phase, log, args, budget and workflow are already defined globals: do not require or import them and do not redeclare them. If the script fails, change it before calling again, never resend it unchanged; after repeated failures do the task directly. Verify with a further agent or your own check where a mistake would matter, then answer the user from the workflow result. Do not do the independent parts yourself.${fit}`
}
