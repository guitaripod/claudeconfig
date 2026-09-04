import { describe, expect, test } from "bun:test"
import { renderRunSummary } from "./delegate.ts"

const SYNTHETIC_LINES = [
  JSON.stringify({
    run_id: "r1",
    seq: 1,
    ts: "2026-09-04T00:00:00Z",
    kind: "attempt_finished",
    tier: "t1",
    attempt: 1,
    status: "passed",
    verify_exit: 0,
    duration_ms: 1200,
    tokens_in: 100,
    tokens_out: 50,
    changed_files: ["NOTES.md"],
    scope_violations: [],
    verify_tail: "ok",
    worker_summary: "Created NOTES.md with hello.",
  }),
  JSON.stringify({
    run_id: "r1",
    seq: 2,
    ts: "2026-09-04T00:00:01Z",
    kind: "applied",
    files: ["NOTES.md"],
    patch_bytes: 42,
  }),
  JSON.stringify({
    run_id: "r1",
    seq: 3,
    ts: "2026-09-04T00:00:02Z",
    kind: "run_finished",
    status: "passed",
    passed_tier: "t1",
    escalations: 0,
    duration_ms: 1500,
    summary: "Packet completed on first tier.",
  }),
]

describe("renderRunSummary", () => {
  test("summarizes a passing run from three synthetic event lines", () => {
    const output = renderRunSummary(SYNTHETIC_LINES)

    expect(output).toContain("run r1: passed (tier t1)")
    expect(output).toContain("escalations: 0")
    expect(output).toContain("duration: 1500ms")
    expect(output).toContain("changed files: NOTES.md")
    expect(output).toContain("worker: Packet completed on first tier.")
    expect(output).toContain("hint: delegate show r1")
  })

  test("ignores blank and non-JSON lines", () => {
    const output = renderRunSummary(["", "not json", ...SYNTHETIC_LINES, "   "])
    expect(output).toContain("run r1: passed")
  })

  test("handles an empty stream", () => {
    expect(renderRunSummary([])).toBe("delegate run produced no parseable events")
  })
})
