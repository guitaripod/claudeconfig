"""Prove each task's grader: the untouched fixture must score below 0.5 and the reference solution 1.0."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TASKS = HERE / "tasks"
CACHE = Path(os.environ.get("EVAL_CACHE", Path(os.environ.get("EVAL_HOME", Path.home() / ".cache" / "agent-stack-eval")) / "cache"))


def sh(args, cwd=None, capture=True, timeout=1800):
    """Run a command with the eval cache exported and return the completed process."""
    env = dict(os.environ, EVAL_CACHE=str(CACHE))
    return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=capture, timeout=timeout)


def grade(task_dir, workdir, answer_text):
    """Run the task's grader on workdir with answer_text and return its parsed JSON line."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(answer_text)
        answer = fh.name
    proc = sh([sys.executable, str(task_dir / "grade.py"), str(workdir), answer])
    lines = [line for line in proc.stdout.splitlines() if line.strip().startswith("{")]
    if proc.returncode != 0 or not lines:
        return {"score": None, "error": (proc.stderr or proc.stdout)[-2000:]}
    return json.loads(lines[-1])


def fresh_workdir(task_dir, root, label):
    """Create an empty workdir under root and populate it with the task's setup.sh."""
    workdir = Path(root) / label / "work"
    workdir.mkdir(parents=True)
    proc = sh(["bash", str(task_dir / "setup.sh"), str(workdir)])
    if proc.returncode != 0:
        raise RuntimeError(f"setup failed: {proc.stderr[-2000:]}")
    return workdir


def validate(task_id):
    """Return (ok, report) for one task id."""
    task_dir = TASKS / task_id
    CACHE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"validate-{task_id}-") as root:
        untouched = fresh_workdir(task_dir, root, "untouched")
        empty = grade(task_dir, untouched, "")
        solved = fresh_workdir(task_dir, root, "reference")
        ref = sh(["bash", str(task_dir / "reference.sh"), str(solved)])
        if ref.returncode != 0:
            return False, {"task": task_id, "error": f"reference.sh failed: {ref.stderr[-2000:]}"}
        reference = grade(task_dir, solved, ref.stdout)
    ok = (
        empty.get("score") is not None
        and reference.get("score") is not None
        and empty["score"] < 0.5
        and reference["score"] == 1.0
    )
    return ok, {"task": task_id, "untouched": empty, "reference": reference}


def main():
    ids = sys.argv[1:] or sorted(p.name for p in TASKS.iterdir() if (p / "task.json").exists())
    failed = 0
    for task_id in ids:
        ok, report = validate(task_id)
        failed += not ok
        print(("PASS " if ok else "FAIL ") + json.dumps(report))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
