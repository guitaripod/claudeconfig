"""Re-run the graders over a finished run's kept workdirs and answers after a grader fix, rewriting its results."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def regrade(home, row):
    """Grade one stored run again and return the updated row."""
    run_dir = Path(home) / "runs" / row["label"] / row["task"] / f"t{row['trial']}"
    grader = HERE / "tasks" / row["task"] / "grade.py"
    if not (run_dir / "work").is_dir() or not grader.exists():
        return row
    env = dict(os.environ, EVAL_CACHE=str(Path(home) / "cache"), TMPDIR=str(Path(home) / "tmp"))
    proc = subprocess.run([sys.executable, str(grader), str(run_dir / "work"), str(run_dir / "answer.txt")],
                          env=env, capture_output=True, text=True, timeout=1800)
    lines = [line for line in proc.stdout.splitlines() if line.strip().startswith("{")]
    grade = json.loads(lines[-1]) if lines else {"score": 0.0, "error": proc.stderr[-1000:]}
    if grade.get("score") != row.get("score"):
        print(f"{row['task']} t{row['trial']}: {row.get('score')} -> {grade.get('score')}")
    row.update(score=grade.get("score", 0.0) or 0.0, checks=grade.get("checks", {}), grade_error=grade.get("error"))
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    parser.add_argument("--tasks", default="", help="comma list of task id prefixes (default: all)")
    parser.add_argument("--home", default=os.environ.get("EVAL_HOME", str(Path.home() / ".cache" / "agent-stack-eval")))
    args = parser.parse_args()
    wanted = [w for w in args.tasks.split(",") if w]
    path = Path(args.home) / "results" / f"{args.label}.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    rows = [regrade(args.home, r) if not wanted or any(r["task"].startswith(w) for w in wanted) else r for r in rows]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


if __name__ == "__main__":
    main()
