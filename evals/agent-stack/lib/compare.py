"""Compare two eval runs task by task: score, flips, cost, latency, delegation and skill routing."""

import argparse
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load(home, label):
    """Load result rows for a label, grouped by task."""
    rows = defaultdict(list)
    for line in (Path(home) / "results" / f"{label}.jsonl").read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            if not row.get("infra_error"):
                rows[row["task"]].append(row)
    return rows


def summarize(rows):
    """Aggregate one task's trials."""
    scores = [r.get("score") or 0.0 for r in rows]
    spawns = Counter()
    for r in rows:
        spawns.update(r.get("spawns") or {})
    hits = [r.get("skill_hit") for r in rows if r.get("skill_hit") is not None]
    return {
        "n": len(rows),
        "mean": statistics.mean(scores) if scores else 0.0,
        "scores": scores,
        "cost": statistics.mean([r.get("cost") or 0.0 for r in rows]) if rows else 0.0,
        "wall": statistics.median([r.get("wall_s") or 0.0 for r in rows]) if rows else 0.0,
        "spawns": sum(spawns.values()) / len(rows) if rows else 0.0,
        "skill_hit": (sum(hits) / len(hits)) if hits else None,
        "errors": sum(1 for r in rows if r.get("harness_error") or r.get("timed_out") or r.get("is_error")),
    }


def fmt_hit(value):
    """Render a skill-hit rate or a dash."""
    return "-" if value is None else f"{value:.0%}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base")
    parser.add_argument("cand", nargs="?")
    parser.add_argument("--home", default=os.environ.get("EVAL_HOME", str(Path.home() / ".cache" / "agent-stack-eval")))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    base = load(args.home, args.base)
    cand = load(args.home, args.cand) if args.cand else None
    tasks = sorted(set(base) | set(cand or {}))
    report = {"base": args.base, "cand": args.cand, "tasks": {}, "degraded": []}
    totals = defaultdict(float)

    header = f"{'task':26} {'base':>6} {'cand':>6} {'Δ':>6}  {'$base':>6} {'$cand':>6}  {'s base':>6} {'s cand':>6}  {'spawn b/c':>9}  {'skill b/c':>9}"
    lines = [header if cand else f"{'task':26} {'score':>6}  {'$':>6}  {'s':>6}  {'spawns':>6}  {'skill':>5}  scores"]
    for task in tasks:
        b = summarize(base.get(task, []))
        totals["b_score"] += b["mean"]
        totals["b_cost"] += b["cost"]
        totals["b_wall"] += b["wall"]
        entry = {"base": b}
        if cand is not None:
            c = summarize(cand.get(task, []))
            totals["c_score"] += c["mean"]
            totals["c_cost"] += c["cost"]
            totals["c_wall"] += c["wall"]
            entry["cand"] = c
            trials = max(b["n"], c["n"], 1)
            delta = c["mean"] - b["mean"]
            degraded = delta <= -(1.0 / trials) + 1e-9
            entry["delta"] = delta
            entry["degraded"] = degraded
            if degraded:
                report["degraded"].append(task)
            mark = "  << DEGRADED" if degraded else ""
            lines.append(
                f"{task:26} {b['mean']:6.2f} {c['mean']:6.2f} {delta:+6.2f}  {b['cost']:6.2f} {c['cost']:6.2f}  "
                f"{b['wall']:6.0f} {c['wall']:6.0f}  {b['spawns']:4.1f}/{c['spawns']:<4.1f}  "
                f"{fmt_hit(b['skill_hit']):>4}/{fmt_hit(c['skill_hit']):<4}{mark}"
            )
        else:
            lines.append(
                f"{task:26} {b['mean']:6.2f}  {b['cost']:6.2f}  {b['wall']:6.0f}  {b['spawns']:6.1f}  "
                f"{fmt_hit(b['skill_hit']):>5}  {' '.join(f'{s:.2f}' for s in b['scores'])}"
            )
        report["tasks"][task] = entry

    n = max(len(tasks), 1)
    if cand is not None:
        lines.append(
            f"{'TOTAL (score sum/10)':26} {totals['b_score']:6.2f} {totals['c_score']:6.2f} "
            f"{totals['c_score'] - totals['b_score']:+6.2f}  {totals['b_cost']:6.2f} {totals['c_cost']:6.2f}  "
            f"{totals['b_wall']:6.0f} {totals['c_wall']:6.0f}"
        )
        lines.append("degraded: " + (", ".join(report["degraded"]) or "none"))
    else:
        lines.append(f"{'TOTAL (score sum/10)':26} {totals['b_score']:6.2f}  {totals['b_cost']:6.2f}  {totals['b_wall']:6.0f}")
    report["totals"] = dict(totals)
    report["n_tasks"] = n
    print(json.dumps(report, indent=2) if args.json else "\n".join(lines))
    sys.exit(2 if report["degraded"] else 0)


if __name__ == "__main__":
    main()
