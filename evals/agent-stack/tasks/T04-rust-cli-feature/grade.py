"""Grade a logstat workspace with the hidden CLI tests; prints one JSON line {"score", "checks"}."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
HIDDEN = HERE / "hidden" / "cli.rs"
RESULT = re.compile(r"test result: \w+\. (\d+) passed; (\d+) failed")
CASE = re.compile(r"^test (\S+) \.\.\. (ok|FAILED)$", re.MULTILINE)


def score(workdir):
    """Run the hidden tests against a temp copy of workdir and return the result dict."""
    root = Path(tempfile.mkdtemp(prefix="grade-T04-"))
    try:
        work = root / "work"
        shutil.copytree(workdir, work, ignore=shutil.ignore_patterns("target", ".git"))
        (work / "tests").mkdir(exist_ok=True)
        shutil.copyfile(HIDDEN, work / "tests" / "hidden_cli.rs")
        env = dict(os.environ, CARGO_TARGET_DIR=str(root / "target"))
        proc = subprocess.run(
            ["cargo", "test", "--offline", "--test", "hidden_cli"],
            cwd=work,
            env=env,
            text=True,
            capture_output=True,
            timeout=900,
        )
        output = proc.stdout + proc.stderr
        match = RESULT.search(output)
        if match is None:
            return {"score": 0, "checks": {}, "error": "build or test run failed: " + output[-2000:]}
        passed, failed = int(match.group(1)), int(match.group(2))
        total = passed + failed
        if total == 0:
            return {"score": 0, "checks": {}, "error": "no tests ran"}
        cases = {name: status for name, status in CASE.findall(output)}
        return {
            "score": round(passed / total, 4),
            "checks": {"passed": passed, "failed": failed, "tests": cases},
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    """Print the grade for WORKDIR (argv[1]); ANSWER_FILE (argv[2]) is accepted by the contract and unused."""
    try:
        result = score(Path(sys.argv[1]))
    except Exception as exc:
        result = {"score": 0, "checks": {}, "error": repr(exc)}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
