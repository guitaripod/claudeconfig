import ast
import json
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
HIDDEN = HERE / "hidden"
HIDDEN_FILE = "test_hidden.py"
MODULES = ("cronexpr", "semrange", "inifile", "csvdiff")
IGNORED = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache")


def hidden_test_names():
    """Return the hidden test function names in file order."""
    tree = ast.parse((HIDDEN / HIDDEN_FILE).read_text(encoding="utf-8"))
    return [node.name for node in tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]


def module_of(test_name):
    """Return the module a hidden test targets, read from its test_<module>_ prefix."""
    return test_name[len("test_"):].split("_", 1)[0]


def passing_tests(report):
    """Return the names of JUnit testcases that neither failed, errored nor skipped."""
    if not report.exists():
        return set()
    passed = set()
    for case in ET.parse(report).getroot().iter("testcase"):
        if all(case.find(tag) is None for tag in ("failure", "error", "skipped")):
            passed.add(case.get("name"))
    return passed


def run_hidden(workdir):
    """Run the hidden tests against a temporary copy of workdir and return the passing test names."""
    with tempfile.TemporaryDirectory(prefix="t06-build-grade-") as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(workdir, work, ignore=IGNORED)
        tests = work / "tests"
        tests.mkdir(exist_ok=True)
        for source in HIDDEN.glob("*.py"):
            shutil.copy(source, tests / source.name)
        report = Path(tmp) / "report.xml"
        subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={report}", f"tests/{HIDDEN_FILE}"],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return passing_tests(report)


def grade(workdir):
    """Return the score and per-module pass counts for the code in workdir."""
    names = hidden_test_names()
    passing = run_hidden(workdir) & set(names)
    checks = {"passed": len(passing), "total": len(names)}
    for module in MODULES:
        checks[module] = sum(1 for name in names if module_of(name) == module and name in passing)
    return {"score": len(passing) / len(names), "checks": checks}


def failure(exc):
    """Return the zero-score result for an error, with the hidden total when it can be read."""
    try:
        total = len(hidden_test_names())
    except Exception:
        total = 0
    checks = {"passed": 0, "total": total}
    checks.update({module: 0 for module in MODULES})
    return {"score": 0.0, "checks": checks, "error": f"{type(exc).__name__}: {exc}"[:500]}


def main(argv):
    """Grade WORKDIR and print exactly one JSON result line. ANSWER_FILE is unused: the code in WORKDIR is the answer."""
    try:
        if len(argv) != 3:
            raise ValueError("usage: grade.py WORKDIR ANSWER_FILE")
        result = grade(Path(argv[1]))
    except Exception as exc:
        result = failure(exc)
    print(json.dumps(result))


if __name__ == "__main__":
    main(sys.argv)
