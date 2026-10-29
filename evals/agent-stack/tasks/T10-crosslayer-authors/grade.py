"""Grade a T10 workdir: run the hidden tests on a temp copy and print one JSON score line."""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TASK = Path(__file__).resolve().parent
SUMMARY_LINE = re.compile(r"\bin \d+(?:\.\d+)?s\b")
COUNT = re.compile(r"(\d+) (passed|failed|errors?|skipped)\b")
PYTEST_TIMEOUT = 600


def load_generator():
    """Import legacy_db.py from the task directory without changing sys.path or writing bytecode there."""
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("legacy_db", TASK / "legacy_db.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_summary(output):
    """Return (passed, total) from pytest's final summary line, or None when there is none."""
    for line in reversed(output.splitlines()):
        if SUMMARY_LINE.search(line):
            counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
            for number, kind in COUNT.findall(line):
                counts["error" if kind.startswith("error") else kind] += int(number)
            return counts["passed"], sum(counts.values())
    return None


def run_hidden(workdir, scratch):
    """Copy workdir and the hidden tests into scratch, run the hidden tests and return (passed, total)."""
    copy = Path(scratch) / "work"
    shutil.copytree(workdir, copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    tests = copy / "tests"
    tests.mkdir(exist_ok=True)
    for source in sorted((TASK / "hidden").glob("*.py")):
        shutil.copy(source, tests / source.name)
    fresh = Path(scratch) / "legacy_fresh.db"
    load_generator().build(str(fresh))
    env = dict(os.environ, SHELF_LEGACY_DB=str(fresh), PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider", "tests/test_hidden.py"],
        cwd=str(copy),
        env=env,
        capture_output=True,
        text=True,
        timeout=PYTEST_TIMEOUT,
    )
    output = proc.stdout + proc.stderr
    summary = parse_summary(output)
    if summary is None:
        raise RuntimeError("no pytest summary: " + output[-500:])
    return summary


def main():
    """Print the single JSON score line; any failure scores 0 with an error key."""
    try:
        with tempfile.TemporaryDirectory(prefix="t10-grade-") as scratch:
            passed, total = run_hidden(sys.argv[1], scratch)
        result = {"score": passed / total if total else 0, "checks": {"passed": passed, "total": total}}
    except Exception as exc:
        result = {"score": 0, "checks": {"passed": 0, "total": 0}, "error": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
