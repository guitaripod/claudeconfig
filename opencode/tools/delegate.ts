import { tool } from "@opencode-ai/plugin"
import { existsSync } from "node:fs"
import { homedir } from "node:os"
import path from "node:path"

type Mode = "normal" | "conserve" | "rush"

interface DelegateArgs {
  op: "run" | "new" | "log" | "stats" | "show" | "tiers"
  packet?: string
  class?: string
  goal?: string
  paths?: string[]
  verify?: string
  read?: string[]
  notes?: string
  tier?: string
  ceiling?: string
  mode?: Mode
}

interface DelegateEvent {
  run_id?: string
  seq?: number
  ts?: string
  kind: string
  [key: string]: unknown
}

const WORKER_SUMMARY_LIMIT = 400

function whichSync(name: string, searchPath: string): string | undefined {
  for (const dir of searchPath.split(path.delimiter)) {
    if (!dir) continue
    const candidate = path.join(dir, name)
    if (existsSync(candidate)) return candidate
  }
  return undefined
}

function resolveDelegateBin(): string {
  const home = homedir()

  const envBin = process.env.DELEGATE_BIN
  if (envBin && existsSync(envBin)) return envBin

  const onPath = whichSync("delegate", process.env.PATH ?? "")
  if (onPath) return onPath

  const cargoBin = path.join(home, ".cargo/bin/delegate")
  if (existsSync(cargoBin)) return cargoBin

  const devBin = path.join(home, "Dev/rust/delegate/target/debug/delegate")
  if (existsSync(devBin)) return devBin

  return "delegate"
}

function buildChildEnv(): Record<string, string | undefined> {
  const home = homedir()
  const extraPath = [
    path.join(home, ".bun/bin"),
    path.join(home, ".cargo/bin"),
    path.join(home, ".local/bin"),
    "/opt/homebrew/bin",
  ].join(path.delimiter)
  const inherited = process.env.PATH ?? ""

  return {
    ...process.env,
    PATH: inherited ? `${extraPath}${path.delimiter}${inherited}` : extraPath,
  }
}

async function runCli(
  bin: string,
  cwd: string,
  cliArgs: string[],
): Promise<{ stdout: string; stderr: string; exitCode: number }> {
  const proc = Bun.spawn([bin, ...cliArgs], {
    cwd,
    env: buildChildEnv(),
    stdout: "pipe",
    stderr: "pipe",
  })
  const [stdout, stderr, exitCode] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
    proc.exited,
  ])
  return { stdout, stderr, exitCode }
}

function newPacketArgs(args: DelegateArgs): string[] {
  if (!args.class || !args.goal) {
    throw new Error("class and goal are both required to create a packet")
  }
  const cliArgs = ["new", "--class", args.class, "--goal", args.goal]
  for (const p of args.paths ?? []) cliArgs.push("--path", p)
  if (args.verify) cliArgs.push("--verify", args.verify)
  for (const r of args.read ?? []) cliArgs.push("--read", r)
  if (args.notes) cliArgs.push("--notes", args.notes)
  if (args.tier) cliArgs.push("--tier", args.tier)
  if (args.ceiling) cliArgs.push("--ceiling", args.ceiling)
  if (args.mode) cliArgs.push("--mode", args.mode)
  return cliArgs
}

async function createPacket(bin: string, cwd: string, args: DelegateArgs): Promise<{ path: string; yaml: string }> {
  const { stdout, stderr, exitCode } = await runCli(bin, cwd, newPacketArgs(args))
  const packetPath = stdout.trim().split("\n").pop()?.trim()
  if (exitCode !== 0 || !packetPath) {
    throw new Error(`delegate new failed (exit ${exitCode}): ${stderr.trim() || stdout.trim()}`)
  }
  const yaml = await Bun.file(packetPath).text()
  return { path: packetPath, yaml }
}

function parseEvents(lines: string[]): DelegateEvent[] {
  const events: DelegateEvent[] = []
  for (const raw of lines) {
    const line = raw.trim()
    if (!line) continue
    try {
      const parsed = JSON.parse(line)
      if (parsed && typeof parsed === "object" && typeof parsed.kind === "string") {
        events.push(parsed as DelegateEvent)
      }
    } catch {
      // Non-JSON line (human-mode fallback, stray log noise) — skip it.
    }
  }
  return events
}

function trimOneLine(text: string, limit: number): string {
  const oneLine = text.replace(/\s+/g, " ").trim()
  return oneLine.length > limit ? `${oneLine.slice(0, limit - 1)}…` : oneLine
}

function findLast(events: DelegateEvent[], kind: string): DelegateEvent | undefined {
  for (let i = events.length - 1; i >= 0; i--) {
    if (events[i].kind === kind) return events[i]
  }
  return undefined
}

/**
 * Renders the compact text summary of a `delegate run --json` event stream.
 * Takes raw JSON event lines (as printed, one per line) rather than
 * pre-parsed events so it can be exercised directly with synthetic output.
 */
export function renderRunSummary(lines: string[]): string {
  const events = parseEvents(lines)
  if (events.length === 0) {
    return "delegate run produced no parseable events"
  }

  const runId = events.find((e) => typeof e.run_id === "string")?.run_id as string | undefined
  const finished = findLast(events, "run_finished")
  const applied = findLast(events, "applied")
  const lastAttempt = findLast(events, "attempt_finished")

  const status = (finished?.status as string | undefined) ?? "unknown"
  const passedTier = (finished?.passed_tier as string | undefined) ?? (lastAttempt?.tier as string | undefined)
  const escalations = (finished?.escalations as number | undefined) ?? 0
  const durationMs = (finished?.duration_ms as number | undefined) ?? (lastAttempt?.duration_ms as number | undefined)
  const changedFiles =
    (applied?.files as string[] | undefined) ?? (lastAttempt?.changed_files as string[] | undefined) ?? []
  const workerSummaryRaw =
    (finished?.summary as string | undefined) ?? (lastAttempt?.worker_summary as string | undefined) ?? ""
  const workerSummary = trimOneLine(workerSummaryRaw, WORKER_SUMMARY_LIMIT)

  const parts = [
    `run ${runId ?? "unknown"}: ${status}${passedTier ? ` (tier ${passedTier})` : ""}`,
    `escalations: ${escalations}${durationMs !== undefined ? `, duration: ${durationMs}ms` : ""}`,
    `changed files: ${changedFiles.length ? changedFiles.join(", ") : "none"}`,
  ]
  if (workerSummary) parts.push(`worker: ${workerSummary}`)
  if (runId) parts.push(`hint: delegate show ${runId}`)

  return parts.join("\n")
}

export default tool({
  description:
    "Dispatch a bounded task packet through the delegate tier ladder (t1 local, t2 cheap cloud, t3 frontier) or inspect delegate runs. Only use when the user explicitly asks to delegate a task, write or run a packet, or check delegate log/stats/show/tiers — never to offload work opportunistically, and never choosing tier/ceiling unless the user says to.",
  args: {
    op: tool.schema.enum(["run", "new", "log", "stats", "show", "tiers"]).describe("Delegate subcommand to perform."),
    packet: tool.schema.string().optional().describe("Packet YAML path for op=run; run id for op=show."),
    class: tool.schema.string().optional().describe("Packet class (op=new, or op=run with no packet)."),
    goal: tool.schema.string().optional().describe("Packet goal, self-contained (op=new, or op=run with no packet)."),
    paths: tool.schema.array(tool.schema.string()).optional().describe("Allowed paths/globs for a new packet."),
    verify: tool.schema.string().optional().describe("Verify command for a new packet."),
    read: tool.schema.array(tool.schema.string()).optional().describe("Files the worker should read first."),
    notes: tool.schema.string().optional().describe("Free-form notes appended to the worker prompt."),
    tier: tool.schema.string().optional().describe("Start tier override."),
    ceiling: tool.schema.string().optional().describe("Ceiling tier override."),
    mode: tool.schema.enum(["normal", "conserve", "rush"]).optional().describe("Dispatch mode override."),
  },
  async execute(args, context) {
    const bin = resolveDelegateBin()
    const cwd = context.directory

    if (args.op === "new") {
      const { path: packetPath, yaml } = await createPacket(bin, cwd, args as DelegateArgs)
      return { title: `delegate new: ${args.class ?? "?"}`, output: `${packetPath}\n\n${yaml}` }
    }

    if (args.op === "run") {
      let packetPath = args.packet
      if (!packetPath) {
        const created = await createPacket(bin, cwd, args as DelegateArgs)
        packetPath = created.path
      }
      const runArgs = ["run", packetPath, "--json", "-y"]
      if (args.tier) runArgs.push("--tier", args.tier)
      if (args.ceiling) runArgs.push("--ceiling", args.ceiling)
      if (args.mode) runArgs.push("--mode", args.mode)

      const { stdout, stderr } = await runCli(bin, cwd, runArgs)
      const summary = renderRunSummary(stdout.split("\n"))
      const output = stderr.trim() ? `${summary}\n\nstderr:\n${stderr.trim()}` : summary
      return { title: `delegate run: ${packetPath}`, output }
    }

    if (args.op === "show") {
      if (!args.packet) throw new Error("op=show needs `packet` set to a run id")
      const { stdout, stderr, exitCode } = await runCli(bin, cwd, ["show", args.packet])
      if (exitCode !== 0) throw new Error(`delegate show failed (exit ${exitCode}): ${stderr.trim() || stdout.trim()}`)
      return { title: `delegate show: ${args.packet}`, output: stdout.trim() || stderr.trim() }
    }

    if (args.op === "log" || args.op === "tiers") {
      const { stdout, stderr, exitCode } = await runCli(bin, cwd, [args.op])
      if (exitCode !== 0) throw new Error(`delegate ${args.op} failed (exit ${exitCode}): ${stderr.trim() || stdout.trim()}`)
      return { title: `delegate ${args.op}`, output: stdout.trim() || stderr.trim() }
    }

    // op === "stats"
    const statsArgs = ["stats"]
    if (args.class) statsArgs.push("--class", args.class)
    const { stdout, stderr, exitCode } = await runCli(bin, cwd, statsArgs)
    if (exitCode !== 0) throw new Error(`delegate stats failed (exit ${exitCode}): ${stderr.trim() || stdout.trim()}`)
    return { title: "delegate stats", output: stdout.trim() || stderr.trim() }
  },
})
