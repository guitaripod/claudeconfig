import importlib.util
import json
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARKER = "db.pool.max_size=0"
CAUSE = re.compile(r"max_size\W{0,3}(=|to|of|is|was|became)?\W{0,3}0\b|pool size\W{0,3}(=|to|of|is|was)?\W{0,3}0\b|\bzero\b|\bto 0\b")
POOL = re.compile(r"pool")


def load_generator():
    """Import the task's log generator from hidden/gen_log.py."""
    spec = importlib.util.spec_from_file_location("gen_log", HERE / "hidden" / "gen_log.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def marker_lines(path):
    """Return the 1-based numbers of the lines in path that carry the root-cause marker."""
    with open(path, encoding="utf-8") as fh:
        return [number for number, text in enumerate(fh, 1) if MARKER in text]


def canonical_line(gen):
    """Regenerate the log in a temp dir and return the one root-cause line number it contains."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "app.log")
        with open(path, "w", encoding="utf-8", newline="\n") as out:
            gen.write_log(out)
        found = marker_lines(path)
    if len(found) != 1:
        raise RuntimeError("generator produced %d root-cause lines" % len(found))
    return found[0]


def check_workdir(workdir, line):
    """Confirm the workdir log carries the root-cause marker on the same line."""
    if marker_lines(os.path.join(workdir, "logs", "app.log")) != [line]:
        raise RuntimeError("workdir log does not carry the root-cause line at %d" % line)


def cause_named(text):
    """Return True when the lowercase answer text names a zero pool size."""
    return bool(CAUSE.search(text)) and bool(POOL.search(text))


def grade(workdir, answer_path):
    """Score the answer file against the canonical root-cause line and its explanation."""
    line = canonical_line(load_generator())
    check_workdir(workdir, line)
    with open(answer_path, encoding="utf-8", errors="replace") as fh:
        answer = fh.read()
    numbers = {int(number) for number in re.findall(r"\d+", answer)}
    line_exact = line in numbers
    named = cause_named(answer.lower())
    score = 1.0 if line_exact and named else 0.5 if named else 0.0
    return {"score": score, "checks": {"line_exact": line_exact, "cause_named": named}}


def main(argv):
    """Print the single JSON result line; any failure scores 0 with an error key."""
    try:
        result = grade(argv[1], argv[2])
    except Exception as exc:
        result = {"score": 0.0, "checks": {}, "error": "%s: %s" % (type(exc).__name__, exc)}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv)
