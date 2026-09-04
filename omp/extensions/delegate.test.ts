import { describe, expect, test } from "bun:test";
import { buildResultMarkdown, parseDelegateEventLine, renderEventLine } from "./delegate.ts";

const REAL_RUN_LINES = [
	'{"run_id":"01M1PYKJ7R5EZY792W983WV8RJ","seq":1,"ts":"2026-09-04T19:33:53.018822255Z","kind":"run_started","packet_id":"01M1PYKDN1WPTMH00WHPSSY7V5","class":"docs","start_tier":"t1","ceiling":"t2","mode":"normal","host":"arch","repo":"/tmp/omp-ext-test"}',
	'{"run_id":"01M1PYKJ7R5EZY792W983WV8RJ","seq":2,"ts":"2026-09-04T19:33:53.019922257Z","kind":"tier_selected","tier":"t1","label":"local","runner":"omp","model":"llama-swap/qwen38-nvfp4","chain_index":0}',
	'{"run_id":"01M1PYKJ7R5EZY792W983WV8RJ","seq":3,"ts":"2026-09-04T19:33:53.020611096Z","kind":"attempt_started","tier":"t1","attempt":1,"model":"llama-swap/qwen38-nvfp4"}',
	'{"run_id":"01M1PYKJ7R5EZY792W983WV8RJ","seq":4,"ts":"2026-09-04T19:33:55.893118069Z","kind":"progress","tier":"t1","attempt":1,"text":"write NOTES.md"}',
	'{"run_id":"01M1PYKJ7R5EZY792W983WV8RJ","seq":5,"ts":"2026-09-04T19:33:56.610856169Z","kind":"progress","tier":"t1","attempt":1,"text":"read NOTES.md"}',
	'{"run_id":"01M1PYKJ7R5EZY792W983WV8RJ","seq":6,"ts":"2026-09-04T19:33:57.517357805Z","kind":"attempt_finished","tier":"t1","attempt":1,"status":"pass","verify_exit":null,"duration_ms":4496,"tokens_in":57018,"tokens_out":190,"changed_files":["NOTES.md"],"scope_violations":[],"verify_tail":"","worker_summary":"Created NOTES.md containing the word hello."}',
	'{"run_id":"01M1PYKJ7R5EZY792W983WV8RJ","seq":7,"ts":"2026-09-04T19:33:57.522747529Z","kind":"applied","files":["NOTES.md"],"patch_bytes":127}',
	'{"run_id":"01M1PYKJ7R5EZY792W983WV8RJ","seq":8,"ts":"2026-09-04T19:33:57.525810096Z","kind":"run_finished","status":"passed","passed_tier":"t1","escalations":0,"duration_ms":4506,"summary":"1 file(s): Created NOTES.md containing the word hello."}',
] as const;

describe("parseDelegateEventLine", () => {
	test("parses every line from a real delegate run --json capture", () => {
		const kinds = REAL_RUN_LINES.map(line => parseDelegateEventLine(line)?.kind);
		expect(kinds).toEqual([
			"run_started",
			"tier_selected",
			"attempt_started",
			"progress",
			"progress",
			"attempt_finished",
			"applied",
			"run_finished",
		]);
	});

	test("returns undefined for malformed JSON instead of throwing", () => {
		expect(parseDelegateEventLine("not json")).toBeUndefined();
		expect(parseDelegateEventLine("")).toBeUndefined();
	});

	test("returns undefined when required fields are missing", () => {
		expect(parseDelegateEventLine('{"seq":1}')).toBeUndefined();
		expect(parseDelegateEventLine('{"kind":"run_started"}')).toBeUndefined();
	});
});

describe("renderEventLine", () => {
	test("renders a passing attempt without a duration suffix", () => {
		const event = parseDelegateEventLine(REAL_RUN_LINES[5]);
		expect(event).toBeDefined();
		expect(renderEventLine(event!)).toBe("t1 ✓ attempt 1 1 file(s)");
	});

	test("renders applied with a file count", () => {
		const event = parseDelegateEventLine(REAL_RUN_LINES[6]);
		expect(event).toBeDefined();
		expect(renderEventLine(event!)).toBe("applied 1 file(s)");
	});

	test("renders run_finished with its passed tier", () => {
		const event = parseDelegateEventLine(REAL_RUN_LINES[7]);
		expect(event).toBeDefined();
		expect(renderEventLine(event!)).toBe("■ passed (tier t1)");
	});

	test("renders a failing attempt with verify exit and duration, matching the spec example", () => {
		const line = JSON.stringify({
			run_id: "r1",
			seq: 6,
			ts: "2026-09-04T00:00:00Z",
			kind: "attempt_finished",
			tier: "t1",
			attempt: 1,
			status: "fail",
			verify_exit: 101,
			duration_ms: 12300,
			tokens_in: 1,
			tokens_out: 1,
			changed_files: [],
			scope_violations: [],
			verify_tail: "",
			worker_summary: "",
		});
		const event = parseDelegateEventLine(line);
		expect(event).toBeDefined();
		expect(renderEventLine(event!)).toBe("t1 ✗ attempt 1 verify exit 101 (12.3s)");
	});

	test("renders a timeout attempt without a verify exit code", () => {
		const line = JSON.stringify({
			run_id: "r1",
			seq: 6,
			ts: "2026-09-04T00:00:00Z",
			kind: "attempt_finished",
			tier: "t2",
			attempt: 2,
			status: "timeout",
			verify_exit: null,
			duration_ms: 5000,
			tokens_in: 1,
			tokens_out: 1,
			changed_files: [],
			scope_violations: [],
			verify_tail: "",
			worker_summary: "",
		});
		const event = parseDelegateEventLine(line);
		expect(renderEventLine(event!)).toBe("t2 ✗ attempt 2 timeout (5.0s)");
	});

	test("renders escalation exactly as the spec example", () => {
		const line = JSON.stringify({ run_id: "r1", seq: 9, ts: "2026-09-04T00:00:00Z", kind: "escalated", from: "t1", to: "t2", reason: "fail" });
		const event = parseDelegateEventLine(line);
		expect(renderEventLine(event!)).toBe("t1 → t2");
	});

	test("renders a second-tier passing attempt exactly as the spec example", () => {
		const line = JSON.stringify({
			run_id: "r1",
			seq: 10,
			ts: "2026-09-04T00:00:00Z",
			kind: "attempt_finished",
			tier: "t2",
			attempt: 1,
			status: "pass",
			verify_exit: 0,
			duration_ms: 2000,
			tokens_in: 1,
			tokens_out: 1,
			changed_files: ["a", "b", "c"],
			scope_violations: [],
			verify_tail: "",
			worker_summary: "",
		});
		const event = parseDelegateEventLine(line);
		expect(renderEventLine(event!)).toBe("t2 ✓ attempt 1 3 file(s)");
	});

	test("renders tier_skipped, approval_required, and approval_resolved", () => {
		expect(
			renderEventLine(
				parseDelegateEventLine(
					JSON.stringify({ run_id: "r1", seq: 1, ts: "t", kind: "tier_skipped", tier: "t2", reason: "unhealthy" }),
				)!,
			),
		).toBe("t2 skipped (unhealthy)");
		expect(
			renderEventLine(
				parseDelegateEventLine(
					JSON.stringify({ run_id: "r1", seq: 1, ts: "t", kind: "approval_required", tier: "t3", reason: "ceiling" }),
				)!,
			),
		).toBe("⚠ approval required at t3: ceiling");
		expect(
			renderEventLine(
				parseDelegateEventLine(
					JSON.stringify({ run_id: "r1", seq: 1, ts: "t", kind: "approval_resolved", tier: "t3", approved: true }),
				)!,
			),
		).toBe("✓ approval granted at t3");
	});
});

describe("buildResultMarkdown", () => {
	test("includes run id, status, tier, escalations, duration, files, and a show hint", () => {
		const event = parseDelegateEventLine(REAL_RUN_LINES[7]);
		expect(event).toBeDefined();
		if (event?.kind !== "run_finished") throw new Error("expected run_finished");
		const markdown = buildResultMarkdown("01M1PYKJ7R5EZY792W983WV8RJ", event, ["NOTES.md"]);
		expect(markdown).toContain("01M1PYKJ7R5EZY792W983WV8RJ");
		expect(markdown).toContain("passed");
		expect(markdown).toContain("passed tier: t1");
		expect(markdown).toContain("escalations: 0");
		expect(markdown).toContain("duration: 4.5s");
		expect(markdown).toContain("changed files: NOTES.md");
		expect(markdown).toContain("delegate show 01M1PYKJ7R5EZY792W983WV8RJ");
	});

	test("truncates a long summary to roughly 600 characters", () => {
		const event = parseDelegateEventLine(REAL_RUN_LINES[7]);
		if (event?.kind !== "run_finished") throw new Error("expected run_finished");
		const longSummary = { ...event, summary: "x".repeat(1000) };
		const markdown = buildResultMarkdown("r1", longSummary, []);
		expect(markdown).toContain("x".repeat(600));
		expect(markdown).not.toContain("x".repeat(601));
	});

	test("reports no changed files as none", () => {
		const event = parseDelegateEventLine(REAL_RUN_LINES[7]);
		if (event?.kind !== "run_finished") throw new Error("expected run_finished");
		const markdown = buildResultMarkdown("r1", event, []);
		expect(markdown).toContain("changed files: none");
	});
});
