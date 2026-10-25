import { createHash } from "node:crypto"
import { existsSync, readdirSync, readFileSync } from "node:fs"
import { homedir } from "node:os"
import path from "node:path"

export interface Meta {
  name: string
  description?: string
  whenToUse?: string
  phases?: { title: string; detail?: string }[]
}

export interface AgentRequest {
  prompt: string
  label: string
  phase?: string
  schema?: object
  model?: string
  agentType?: string
  workflow: string
  index: number
  signal: AbortSignal
}

export interface AgentResult {
  text: string
  data?: unknown
}

export interface Runner {
  run(req: AgentRequest): Promise<AgentResult>
  nativeSchema?: boolean
}

export type WorkflowEvent =
  | { type: "phase"; title: string }
  | { type: "log"; message: string }
  | { type: "agent_start"; index: number; label: string; phase?: string; running: number }
  | {
      type: "agent_end"
      index: number
      label: string
      ok: boolean
      running: number
      done: number
      failed: number
      error?: string
    }

export interface RunOptions {
  source?: string
  name?: string
  scriptPath?: string
  args?: unknown
  runner: Runner
  cwd: string
  concurrency?: number
  maxAgents?: number
  signal?: AbortSignal
  onEvent?: (e: WorkflowEvent) => void
}

export interface RunResult {
  name: string
  ok: boolean
  result?: unknown
  error?: string
  agents: number
  failed: number
  logs: string[]
  durationMs: number
}

interface AgentOptions {
  label?: string
  phase?: string
  schema?: object
  model?: string
  agentType?: string
}

interface LoadedScript {
  meta: Meta
  body: string
}

type Schema = Record<string, unknown>
type Outcome = { ok: true; value: unknown } | { ok: false; error: string }
type ScriptFunction = (...helpers: unknown[]) => Promise<unknown>

const DEFAULT_CONCURRENCY = 8
const DEFAULT_MAX_AGENTS = 200
const MAX_ATTEMPTS = 3
const MAX_NESTING = 1
const ABORTED = "aborted"
const INLINE_NAME = "inline"
const HELPER_NAMES = ["agent", "parallel", "pipeline", "phase", "log", "args", "budget", "workflow"]
const GLOBALS_HINT = `${HELPER_NAMES.slice(0, -1).join(", ")} and ${HELPER_NAMES[HELPER_NAMES.length - 1]} are already defined globals: do not require, import or redeclare them.`
const SYNTAX_HINT =
  "Write plain JavaScript only: no TypeScript syntax (type annotations, interfaces, generics), no import or export, and put the optional `export const meta = {...}` first."

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor as new (
  ...parts: string[]
) => ScriptFunction

class Semaphore {
  private free: number
  private waiters: (() => void)[] = []

  constructor(private readonly limit: number) {
    this.free = limit
  }

  get inUse(): number {
    return this.limit - this.free
  }

  acquire(signal: AbortSignal): Promise<void> {
    if (signal.aborted) return Promise.reject(new Error(ABORTED))
    if (this.free > 0) {
      this.free -= 1
      return Promise.resolve()
    }
    return new Promise<void>((resolve, reject) => {
      const grant = () => {
        signal.removeEventListener("abort", onAbort)
        resolve()
      }
      const onAbort = () => {
        const at = this.waiters.indexOf(grant)
        if (at >= 0) this.waiters.splice(at, 1)
        reject(new Error(ABORTED))
      }
      this.waiters.push(grant)
      signal.addEventListener("abort", onAbort, { once: true })
    })
  }

  release(): void {
    const next = this.waiters.shift()
    if (next) next()
    else this.free += 1
  }
}

interface RunState {
  runner: Runner
  cwd: string
  semaphore: Semaphore
  signal: AbortSignal
  maxAgents: number
  agents: number
  done: number
  failed: number
  logs: string[]
  pending: Set<Promise<unknown>>
  closed: boolean
  emit: (e: WorkflowEvent) => void
}

function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

/// Resolves with `work`, or rejects as soon as `signal` aborts, whichever happens first.
function raceAbort<T>(work: Promise<T>, signal: AbortSignal): Promise<T> {
  if (signal.aborted) {
    work.catch(() => undefined)
    return Promise.reject(new Error(ABORTED))
  }
  return new Promise<T>((resolve, reject) => {
    const onAbort = () => reject(new Error(ABORTED))
    signal.addEventListener("abort", onAbort, { once: true })
    work.then(resolve, reject).finally(() => signal.removeEventListener("abort", onAbort))
  })
}

/// Index just past a quoted string that opens at `from`.
function skipString(src: string, from: number): number {
  const quote = src[from]
  let i = from + 1
  while (i < src.length) {
    if (src[i] === "\\") i += 2
    else if (src[i] === quote) return i + 1
    else i += 1
  }
  throw new Error("unterminated string in meta")
}

/// Index just past a template literal that opens at `from`, including nested `${...}` expressions.
function skipTemplate(src: string, from: number): number {
  let i = from + 1
  while (i < src.length) {
    if (src[i] === "\\") i += 2
    else if (src[i] === "`") return i + 1
    else if (src[i] === "$" && src[i + 1] === "{") i = skipBraces(src, i + 1)
    else i += 1
  }
  throw new Error("unterminated template literal in meta")
}

/// Index just past the brace block that opens at `from`, skipping strings, templates and comments.
function skipBraces(src: string, from: number): number {
  let depth = 0
  let i = from
  while (i < src.length) {
    const c = src[i]
    if (c === "'" || c === '"') i = skipString(src, i)
    else if (c === "`") i = skipTemplate(src, i)
    else if (c === "/" && src[i + 1] === "/") {
      const end = src.indexOf("\n", i)
      i = end < 0 ? src.length : end
    } else if (c === "/" && src[i + 1] === "*") {
      const end = src.indexOf("*/", i + 2)
      if (end < 0) throw new Error("unterminated comment in meta")
      i = end + 2
    } else {
      if (c === "{") depth += 1
      else if (c === "}") {
        depth -= 1
        if (depth === 0) return i + 1
      }
      i += 1
    }
  }
  throw new Error("unbalanced braces in meta")
}

/// Evaluates the meta object literal and fills in the default name.
function evaluateMeta(literal: string): Meta {
  let value: unknown
  try {
    value = new Function(`return (${literal})`)()
  } catch (e) {
    throw new Error(`meta is not a valid object literal: ${errorMessage(e)}`)
  }
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("meta must be an object literal")
  }
  const meta = value as Partial<Meta>
  return { ...meta, name: typeof meta.name === "string" && meta.name ? meta.name : INLINE_NAME }
}

export function loadScript(source: string): LoadedScript {
  const text = source.replace(/^﻿/, "")
  const head = /^\s*export\s+const\s+meta\s*=\s*/.exec(text)
  if (!head) return { meta: { name: INLINE_NAME }, body: text }
  const open = head[0].length
  if (text[open] !== "{") throw new Error("meta must be an object literal")
  const end = skipBraces(text, open)
  return {
    meta: evaluateMeta(text.slice(open, end)),
    body: text.slice(end).replace(/^\s*;?/, ""),
  }
}

/// The directories searched for saved workflows, highest priority first.
function workflowDirs(cwd: string): string[] {
  const fromEnv = (process.env.WORKFLOW_PATH ?? "")
    .split(path.delimiter)
    .filter(Boolean)
    .map((dir) => path.resolve(cwd, dir))
  const all = [...fromEnv, path.join(cwd, ".claude", "workflows"), path.join(homedir(), ".claude", "workflows")]
  return [...new Set(all)]
}

function workflowFiles(dir: string): string[] {
  if (!existsSync(dir)) return []
  return readdirSync(dir)
    .filter((file) => file.endsWith(".js"))
    .sort()
}

export function findWorkflow(name: string, cwd: string): string | undefined {
  const base = name.replace(/\.js$/, "")
  if (!base || base.includes("/") || base.includes("\\") || base.startsWith(".")) return undefined
  for (const dir of workflowDirs(cwd)) {
    const file = path.join(dir, `${base}.js`)
    if (existsSync(file)) return file
  }
  return undefined
}

export function listWorkflows(cwd: string): (Meta & { path: string })[] {
  const seen = new Set<string>()
  const found: (Meta & { path: string })[] = []
  for (const dir of workflowDirs(cwd)) {
    for (const file of workflowFiles(dir)) {
      const name = file.replace(/\.js$/, "")
      if (seen.has(name)) continue
      try {
        const full = path.join(dir, file)
        const { meta } = loadScript(readFileSync(full, "utf8"))
        seen.add(name)
        found.push({ ...meta, name, path: full })
      } catch {
        continue
      }
    }
  }
  return found
}

function matchesType(value: unknown, type: unknown): boolean {
  switch (type) {
    case "string":
      return typeof value === "string"
    case "number":
      return typeof value === "number" && Number.isFinite(value)
    case "integer":
      return Number.isInteger(value)
    case "boolean":
      return typeof value === "boolean"
    case "null":
      return value === null
    case "array":
      return Array.isArray(value)
    case "object":
      return typeof value === "object" && value !== null && !Array.isArray(value)
    default:
      return true
  }
}

function describeValue(value: unknown): string {
  if (value === null) return "null"
  if (Array.isArray(value)) return "array"
  return typeof value
}

function isSchema(value: unknown): value is Schema {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

/// Checks `value` against the supported JSON Schema subset and lists every mismatch with its path.
function validate(value: unknown, schema: Schema, at = "$"): string[] {
  const types = schema.type === undefined ? undefined : ([] as unknown[]).concat(schema.type)
  if (types && !types.some((type) => matchesType(value, type))) {
    return [`${at} should be ${types.join(" or ")}, got ${describeValue(value)}`]
  }
  if (Array.isArray(schema.enum) && !schema.enum.some((option) => JSON.stringify(option) === JSON.stringify(value))) {
    return [`${at} should be one of ${JSON.stringify(schema.enum)}`]
  }
  const errors: string[] = []
  if (matchesType(value, "object")) errors.push(...validateObject(value as Record<string, unknown>, schema, at))
  if (Array.isArray(value) && isSchema(schema.items)) {
    const items = schema.items
    value.forEach((item, i) => errors.push(...validate(item, items, `${at}[${i}]`)))
  }
  return errors
}

function validateObject(value: Record<string, unknown>, schema: Schema, at: string): string[] {
  const errors: string[] = []
  const properties = isSchema(schema.properties) ? schema.properties : {}
  if (Array.isArray(schema.required)) {
    for (const key of schema.required) {
      if (value[String(key)] === undefined) errors.push(`${at}.${key} is required`)
    }
  }
  for (const [key, sub] of Object.entries(properties)) {
    if (value[key] !== undefined && isSchema(sub)) errors.push(...validate(value[key], sub, `${at}.${key}`))
  }
  if (schema.additionalProperties === false) {
    for (const key of Object.keys(value)) {
      if (!(key in properties)) errors.push(`${at}.${key} is not allowed`)
    }
  }
  return errors
}

/// End index of the bracket block starting at `from`, or -1 when it never closes.
function matchBlockEnd(text: string, from: number, open: string, close: string): number {
  let depth = 0
  let inString = false
  for (let i = from; i < text.length; i++) {
    const c = text[i]
    if (inString) {
      if (c === "\\") i += 1
      else if (c === '"') inString = false
    } else if (c === '"') inString = true
    else if (c === open) depth += 1
    else if (c === close) {
      depth -= 1
      if (depth === 0) return i + 1
    }
  }
  return -1
}

/// Balanced top-level `{...}` (or `[...]`) blocks of `text` in order, ignoring stray unclosed brackets.
function topLevelBlocks(text: string, open: string): string[] {
  const close = open === "{" ? "}" : "]"
  const blocks: string[] = []
  let i = 0
  while (i < text.length) {
    if (text[i] !== open) {
      i += 1
      continue
    }
    const end = matchBlockEnd(text, i, open, close)
    if (end < 0) {
      i += 1
      continue
    }
    blocks.push(text.slice(i, end))
    i = end
  }
  return blocks
}

function fencedBlocks(text: string): string[] {
  return [...text.matchAll(/```[\w-]*[ \t]*\r?\n([\s\S]*?)```/g)].map((m) => m[1])
}

/// Finds the JSON value a reply ends with: the last fenced block, else the last balanced top-level block.
function extractJson(text: string, wantsArray: boolean): { found: true; value: unknown } | { found: false } {
  const candidates = [...fencedBlocks(text).reverse(), ...topLevelBlocks(text, wantsArray ? "[" : "{").reverse()]
  for (const candidate of candidates) {
    try {
      return { found: true, value: JSON.parse(candidate) }
    } catch {
      continue
    }
  }
  return { found: false }
}

function schemaWantsArray(schema: Schema): boolean {
  return ([] as unknown[]).concat(schema.type).includes("array")
}

/// Reads and validates the structured value of one runner reply.
function readStructured(
  result: AgentResult,
  schema: Schema,
  nativeSchema: boolean,
): { value?: unknown; errors: string[] } {
  if (nativeSchema && result.data !== undefined) {
    return { value: result.data, errors: validate(result.data, schema) }
  }
  const parsed = extractJson(result.text, schemaWantsArray(schema))
  if (!parsed.found) return { errors: ["the reply contained no parseable JSON"] }
  return { value: parsed.value, errors: validate(parsed.value, schema) }
}

function schemaInstruction(schema: object): string {
  return `When you are done, reply with ONLY a JSON object matching this JSON Schema, with no other text:\n${JSON.stringify(schema)}`
}

/// Calls the runner, retrying a structured agent with the validation errors up to MAX_ATTEMPTS times in total.
async function executeAgent(state: RunState, request: AgentRequest): Promise<Outcome> {
  const schema = request.schema as Schema | undefined
  const nativeSchema = state.runner.nativeSchema === true
  let lastErrors = ""
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    const prompt =
      attempt === 1
        ? request.prompt
        : `${request.prompt}\n\nYour previous reply did not match the schema: ${lastErrors}. Reply again with only the JSON object.`
    let result: AgentResult
    try {
      result = await raceAbort(state.runner.run({ ...request, prompt }), state.signal)
    } catch (e) {
      if (state.signal.aborted) throw new Error(ABORTED)
      return { ok: false, error: errorMessage(e) }
    }
    const text = String(result?.text ?? "")
    if (!schema) return { ok: true, value: text }
    const read = readStructured({ ...result, text }, schema, nativeSchema)
    if (read.errors.length === 0) return { ok: true, value: read.value }
    lastErrors = read.errors.join("; ")
  }
  return { ok: false, error: `invalid structured output: ${lastErrors}` }
}

function recordFinish(state: RunState, index: number, label: string, error?: string): void {
  state.done += 1
  if (error !== undefined) state.failed += 1
  state.emit({
    type: "agent_end",
    index,
    label,
    ok: error === undefined,
    running: state.semaphore.inUse,
    done: state.done,
    failed: state.failed,
    error,
  })
}

/// Counts an agent that was cut short by an abort as failed and logs it.
function recordAbortedAgent(state: RunState, index: number, label: string, error: unknown): void {
  recordFinish(state, index, label, errorMessage(error))
  recordLog(state, `agent ${label} failed: ${errorMessage(error)}`)
}

/// Starts an agent and tracks it so a run can wait for its bookkeeping; a rejection nobody awaits stays silent.
function startAgent(state: RunState, start: () => Promise<unknown>): Promise<unknown> {
  const promise = start()
  promise.catch(() => undefined)
  state.pending.add(promise)
  const forget = () => state.pending.delete(promise)
  promise.then(forget, forget)
  return promise
}

async function runAgent(
  state: RunState,
  workflowName: string,
  currentPhase: () => string | undefined,
  prompt: unknown,
  opts: AgentOptions | undefined,
): Promise<unknown> {
  if (typeof prompt !== "string") throw new TypeError("agent(prompt, opts): prompt must be a string")
  const options = opts ?? {}
  if (state.signal.aborted) throw new Error(ABORTED)
  if (state.agents >= state.maxAgents) throw new Error(`agent limit of ${state.maxAgents} exceeded`)
  state.agents += 1
  const index = state.agents
  const label = options.label ?? `agent-${index}`
  const phase = options.phase ?? currentPhase()
  const needsInstruction = options.schema !== undefined && state.runner.nativeSchema !== true
  const request: AgentRequest = {
    prompt: needsInstruction ? `${prompt}\n\n${schemaInstruction(options.schema as object)}` : prompt,
    label,
    phase,
    schema: options.schema,
    model: options.model,
    agentType: options.agentType,
    workflow: workflowName,
    index,
    signal: state.signal,
  }
  try {
    await state.semaphore.acquire(state.signal)
  } catch (e) {
    recordAbortedAgent(state, index, label, e)
    throw e
  }
  state.emit({ type: "agent_start", index, label, phase, running: state.semaphore.inUse })
  let outcome: Outcome
  try {
    outcome = await executeAgent(state, request)
  } catch (e) {
    state.semaphore.release()
    recordAbortedAgent(state, index, label, e)
    throw e
  }
  state.semaphore.release()
  if (outcome.ok) {
    recordFinish(state, index, label)
    return outcome.value
  }
  recordFinish(state, index, label, outcome.error)
  recordLog(state, `agent ${label} failed: ${outcome.error}`)
  return null
}

function recordLog(state: RunState, message: string): void {
  if (state.closed) return
  state.logs.push(message)
  state.emit({ type: "log", message })
}

async function runParallel(state: RunState, thunks: unknown): Promise<unknown[]> {
  if (!Array.isArray(thunks)) throw new TypeError("parallel(thunks): thunks must be an array of functions")
  return Promise.all(
    thunks.map(async (thunk, i) => {
      try {
        return typeof thunk === "function" ? await thunk() : await thunk
      } catch (e) {
        if (!state.signal.aborted) recordLog(state, `parallel item ${i} failed: ${errorMessage(e)}`)
        return null
      }
    }),
  )
}

async function runPipeline(state: RunState, items: unknown, stages: unknown[]): Promise<unknown[]> {
  if (!Array.isArray(items)) throw new TypeError("pipeline(items, ...stages): items must be an array")
  if (stages.some((stage) => typeof stage !== "function")) throw new TypeError("pipeline stages must be functions")
  return Promise.all(
    items.map(async (item, i) => {
      let value: unknown = item
      for (const [s, stage] of (stages as ((...a: unknown[]) => unknown)[]).entries()) {
        try {
          value = await stage(value, item, i)
        } catch (e) {
          if (!state.signal.aborted) recordLog(state, `pipeline item ${i} failed at stage ${s}: ${errorMessage(e)}`)
          return null
        }
      }
      return value
    }),
  )
}

function stringifyLog(message: unknown): string {
  if (typeof message === "string") return message
  try {
    return JSON.stringify(message) ?? String(message)
  } catch {
    return String(message)
  }
}

/// True when a compile error message says the script redeclared one of the injected names or used import, export or require.
function misusesGlobals(message: string): boolean {
  const redeclared = /(?:variable twice: '(\w+)'|Identifier '(\w+)' has already been declared)/.exec(message)
  const name = redeclared?.[1] ?? redeclared?.[2]
  if (name !== undefined && HELPER_NAMES.includes(name)) return true
  return /\b(?:import|export|require)\b/.test(message)
}

/// Compiles a script body, turning syntax errors into an authoring hint.
function compileBody(body: string): ScriptFunction {
  try {
    return new AsyncFunction(...HELPER_NAMES, body)
  } catch (e) {
    const message = errorMessage(e)
    const globals = misusesGlobals(message) ? ` ${GLOBALS_HINT}` : ""
    throw new Error(`the script is not valid JavaScript (${message}).${globals} ${SYNTAX_HINT}`)
  }
}

/// The failure text for an error thrown while a script ran, with the globals hint added when the script tried to require or import.
function describeScriptError(e: unknown): string {
  const message = errorMessage(e)
  const kind = e instanceof Error ? e.name : ""
  const lookup = (kind === "ReferenceError" || kind === "TypeError") && /\b(?:require|import)\b/.test(message)
  return lookup ? `${message}. ${GLOBALS_HINT}` : message
}

/// Resolves a `workflow()` argument to a script file path.
function resolveReference(ref: unknown, cwd: string): { file?: string; label: string } {
  if (typeof ref === "string") return { file: findWorkflow(ref, cwd), label: ref }
  if (isSchema(ref) && typeof ref.scriptPath === "string") {
    const file = path.resolve(cwd, ref.scriptPath)
    return { file: existsSync(file) ? file : undefined, label: ref.scriptPath }
  }
  if (isSchema(ref) && typeof ref.name === "string") return { file: findWorkflow(ref.name, cwd), label: ref.name }
  throw new TypeError("workflow(nameOrRef, args): pass a saved workflow name or { scriptPath }")
}

async function executeScript(
  state: RunState,
  loaded: LoadedScript,
  args: unknown,
  depth: number,
  inheritedPhase: string | undefined,
): Promise<unknown> {
  const run = compileBody(loaded.body)
  let currentPhase = inheritedPhase
  const helpers = [
    (prompt: unknown, opts?: AgentOptions) =>
      startAgent(state, () => runAgent(state, loaded.meta.name, () => currentPhase, prompt, opts)),
    (thunks: unknown) => runParallel(state, thunks),
    (items: unknown, ...stages: unknown[]) => runPipeline(state, items, stages),
    (title: unknown) => {
      currentPhase = String(title)
      state.emit({ type: "phase", title: currentPhase })
    },
    (message: unknown) => recordLog(state, stringifyLog(message)),
    args,
    { total: null, spent: () => 0, remaining: () => Infinity },
    async (ref: unknown, nestedArgs?: unknown) => {
      if (depth >= MAX_NESTING) throw new Error("workflow() can be nested only one level deep")
      const { file, label } = resolveReference(ref, state.cwd)
      if (!file) throw new Error(`workflow "${label}" not found`)
      const nested = loadScript(readFileSync(file, "utf8"))
      if (nested.meta.name === INLINE_NAME) nested.meta.name = path.basename(file).replace(/\.js$/, "")
      return executeScript(state, nested, nestedArgs, depth + 1, currentPhase)
    },
  ]
  return run(...helpers)
}

/// Reads the script a run was asked for: inline source, an explicit path, or a saved workflow by name.
function readScript(opts: RunOptions): LoadedScript {
  if (opts.source !== undefined) {
    const loaded = loadScript(opts.source)
    if (opts.name && loaded.meta.name === INLINE_NAME) loaded.meta.name = opts.name
    return loaded
  }
  const file = opts.scriptPath ?? (opts.name ? findWorkflow(opts.name, opts.cwd) : undefined)
  if (!file) {
    if (!opts.name) throw new Error("runWorkflow needs source, scriptPath or name")
    const saved = listWorkflows(opts.cwd).map((w) => w.name)
    throw new Error(`workflow "${opts.name}" not found. Saved workflows: ${saved.join(", ") || "none"}`)
  }
  const loaded = loadScript(readFileSync(file, "utf8"))
  if (loaded.meta.name === INLINE_NAME) loaded.meta.name = opts.name ?? path.basename(file).replace(/\.js$/, "")
  return loaded
}

function positiveInt(value: number | undefined, fallback: number): number {
  return value !== undefined && Number.isFinite(value) && value >= 1 ? Math.floor(value) : fallback
}

/// An abort controller that follows `parent` and can also be aborted on its own; `detach` stops following.
function linkedController(parent: AbortSignal | undefined): { controller: AbortController; detach: () => void } {
  const controller = new AbortController()
  if (!parent) return { controller, detach: () => undefined }
  if (parent.aborted) {
    controller.abort()
    return { controller, detach: () => undefined }
  }
  const onAbort = () => controller.abort()
  parent.addEventListener("abort", onAbort, { once: true })
  return { controller, detach: () => parent.removeEventListener("abort", onAbort) }
}

function createState(opts: RunOptions, signal: AbortSignal): RunState {
  const concurrency = positiveInt(opts.concurrency ?? (Number(process.env.WORKFLOW_CONCURRENCY) || undefined), DEFAULT_CONCURRENCY)
  const onEvent = opts.onEvent
  const state: RunState = {
    runner: opts.runner,
    cwd: opts.cwd,
    semaphore: new Semaphore(concurrency),
    signal,
    maxAgents: positiveInt(opts.maxAgents, DEFAULT_MAX_AGENTS),
    agents: 0,
    done: 0,
    failed: 0,
    logs: [],
    pending: new Set(),
    closed: false,
    emit: (e) => {
      if (state.closed) return
      try {
        onEvent?.(e)
      } catch {
        return
      }
    },
  }
  return state
}

/// Waits until every agent that was started has recorded its outcome.
async function settleAgents(state: RunState): Promise<void> {
  while (state.pending.size > 0) await Promise.allSettled([...state.pending])
}

export async function runWorkflow(opts: RunOptions): Promise<RunResult> {
  const started = Date.now()
  const { controller, detach } = linkedController(opts.signal)
  const state = createState(opts, controller.signal)
  let name = opts.name ?? INLINE_NAME
  const finish = (fields: { ok: boolean; result?: unknown; error?: string }): RunResult => ({
    name,
    ...fields,
    agents: state.agents,
    failed: state.failed,
    logs: state.logs,
    durationMs: Date.now() - started,
  })
  try {
    const loaded = readScript(opts)
    name = loaded.meta.name
    const result = await raceAbort(executeScript(state, loaded, opts.args, 0, undefined), state.signal)
    if (state.signal.aborted) {
      await settleAgents(state)
      return finish({ ok: false, error: ABORTED })
    }
    return finish({ ok: true, result })
  } catch (e) {
    if (state.signal.aborted) await settleAgents(state)
    return finish({ ok: false, error: state.signal.aborted ? ABORTED : describeScriptError(e) })
  } finally {
    detach()
    state.closed = true
    controller.abort()
  }
}

/// Pretty JSON for a result, or its string form when it cannot be serialized (cycles, BigInt).
function stringifyResult(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2) ?? "(the workflow returned no value)"
  } catch {
    return `${plainString(value)}\n(the value was not JSON serializable, showing its string form)`
  }
}

function plainString(value: unknown): string {
  try {
    return String(value)
  } catch {
    return Object.prototype.toString.call(value)
  }
}

export function formatResult(r: RunResult): string {
  const body = !r.ok
    ? `workflow ${r.name} failed: ${r.error}`
    : typeof r.result === "string"
      ? r.result
      : stringifyResult(r.result)
  const footer = `workflow ${r.name}: ${r.agents} agents, ${r.failed} failed, ${(r.durationMs / 1000).toFixed(1)}s`
  const problems = r.logs.filter((line) => /fail|error/i.test(line))
  return [body, "", footer, ...problems].join("\n")
}

export function hasUltracodeKeyword(text: string): boolean {
  const prose = text.replace(/(```|~~~)[\s\S]*?(?:\1|$)/g, " ").replace(/(`+)[\s\S]*?\1/g, " ")
  return /(?<![\w\-./@#$])ultracode(?![\w-]|\.\w|\/)/i.test(prose)
}

const MAX_FAILURE_STREAK = 3
const MAX_GUARDED_SESSIONS = 200
const MAX_FAILED_SCRIPTS_PER_SESSION = 50
const STREAK_REFUSAL = "The workflow tool failed 3 times in a row; stop calling it and do the task directly."

interface SessionFailures {
  streak: number
  failed: Map<string, number>
}

/// A short stable key for one workflow tool call: its script source, or its saved name plus args.
export function invocationKey(input: { script?: string; name?: string; args?: unknown }): string {
  const text =
    typeof input.script === "string" && input.script.trim() !== ""
      ? `script:${input.script.trim()}`
      : `name:${(input.name ?? "").trim()}:${stringifyKey(input.args)}`
  return createHash("sha1").update(text).digest("hex")
}

function stringifyKey(value: unknown): string {
  try {
    return JSON.stringify(value) ?? ""
  } catch {
    return plainString(value)
  }
}

/// Stops a model from resending a failing workflow call: marks repeats of a failed script and refuses calls after three failures in a row. State is per session id and bounded.
export class RepeatGuard {
  private readonly sessions = new Map<string, SessionFailures>()

  constructor(private readonly maxSessions = MAX_GUARDED_SESSIONS) {}

  /// The refusal text when the session already failed three times in a row, else undefined.
  refusal(sessionId: string): string | undefined {
    const record = this.sessions.get(sessionId)
    return record !== undefined && record.streak >= MAX_FAILURE_STREAK ? STREAK_REFUSAL : undefined
  }

  /// Records the outcome of a call and returns its text, prefixed when this exact call had failed before.
  record(sessionId: string, key: string, ok: boolean, text: string): string {
    const record = this.touch(sessionId)
    if (ok) {
      record.streak = 0
      record.failed.delete(key)
      return text
    }
    const before = record.failed.get(key) ?? 0
    record.streak += 1
    record.failed.delete(key)
    record.failed.set(key, before + 1)
    while (record.failed.size > MAX_FAILED_SCRIPTS_PER_SESSION) {
      record.failed.delete(record.failed.keys().next().value as string)
    }
    if (before === 0) return text
    return `This exact script already failed ${before} time(s). Change it, or do the task without the workflow tool.\n\n${text}`
  }

  /// Clears the failure streak of a session, which a new user prompt does; scripts that failed stay remembered.
  reset(sessionId: string): void {
    const record = this.sessions.get(sessionId)
    if (record !== undefined) record.streak = 0
  }

  /// The session's record, created on first use, moved to the newest slot, with the oldest sessions forgotten beyond the limit.
  private touch(sessionId: string): SessionFailures {
    const record = this.sessions.get(sessionId) ?? { streak: 0, failed: new Map<string, number>() }
    this.sessions.delete(sessionId)
    this.sessions.set(sessionId, record)
    while (this.sessions.size > this.maxSessions) {
      this.sessions.delete(this.sessions.keys().next().value as string)
    }
    return record
  }
}
