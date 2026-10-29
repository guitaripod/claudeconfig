import ast
import json
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parent
VISIBLE_NAME = Path("tests") / "test_invoice.py"
FIXTURE_VISIBLE = TASK_DIR / "fixture" / VISIBLE_NAME
HIDDEN = TASK_DIR / "hidden" / "test_hidden.py"
IGNORED = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache")


def emit(payload):
    """Print the single JSON result line."""
    print(json.dumps(payload, sort_keys=True))


def count_hidden_tests(path):
    """Return how many module-level test functions the hidden file defines."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return sum(1 for node in tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))


def visible_untouched(workdir):
    """Return True when the visible test file in workdir matches the fixture byte for byte."""
    candidate = workdir / VISIBLE_NAME
    return candidate.is_file() and candidate.read_bytes() == FIXTURE_VISIBLE.read_bytes()


def run_hidden(workdir, scratch):
    """Run the hidden tests against a copy of workdir and return how many passed."""
    graded = Path(scratch) / "work"
    shutil.copytree(workdir, graded, ignore=IGNORED)
    (graded / "tests").mkdir(exist_ok=True)
    shutil.copy(HIDDEN, graded / "tests" / "test_hidden.py")
    report = Path(scratch) / "junit.xml"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "--junitxml",
            str(report),
            "tests/test_hidden.py",
        ],
        cwd=graded,
        capture_output=True,
        text=True,
        timeout=300,
    )
    cases = ET.parse(report).getroot().iter("testcase")
    return sum(1 for case in cases if not any(child.tag in ("failure", "error", "skipped") for child in case))


def main():
    """Grade WORKDIR and print one JSON line with the score and its checks."""
    try:
        if len(sys.argv) < 3:
            raise ValueError("usage: grade.py WORKDIR ANSWER_FILE")
        workdir = Path(sys.argv[1])
        untouched = visible_untouched(workdir)
        total = count_hidden_tests(HIDDEN)
        with tempfile.TemporaryDirectory(prefix="t02-grade-") as scratch:
            passed = run_hidden(workdir, scratch)
        score = passed / total if untouched and total else 0
        emit(
            {
                "score": score,
                "checks": {
                    "hidden_passed": passed,
                    "hidden_total": total,
                    "visible_tests_untouched": untouched,
                },
            }
        )
    except Exception as exc:
        emit({"score": 0, "error": f"{type(exc).__name__}: {exc}"})


if __name__ == "__main__":
    main()
