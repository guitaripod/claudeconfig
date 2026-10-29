import json
import re
import sys

EXPECTED = {
    "q1": ("crates/ignore/src/walk.rs", "skip_filesize"),
    "q2": ("crates/printer/src/standard.rs", "write_exceeded_line"),
    "q3": ("crates/core/search.rs", "should_decompress"),
}
NUMBERED = re.compile(r"^\W*([123])\.")


def path_pattern(path):
    """Match the repo-relative path, optionally prefixed with ./, as a whole path token."""
    return re.compile(r"(?<![\w/.-])(?:\./)?" + re.escape(path) + r"(?![\w/-]|\.\w)")


def ident_pattern(ident):
    """Match the identifier as a whole word."""
    return re.compile(r"\b" + re.escape(ident) + r"\b")


def line_answers(line, path, ident):
    """Return True when a numbered answer line names both the expected path and identifier."""
    return bool(path_pattern(path).search(line)) and bool(ident_pattern(ident).search(line))


def last_numbered_lines(text):
    """Return the last numbered line seen for each answer number."""
    found = {}
    for line in text.splitlines():
        match = NUMBERED.match(line)
        if match:
            found[match.group(1)] = line
    return found


def grade(answer_path):
    """Score the answer file against the expected (path, identifier) pairs."""
    with open(answer_path, encoding="utf-8", errors="replace") as fh:
        lines = last_numbered_lines(fh.read())
    checks = {}
    for index, (key, (path, ident)) in enumerate(EXPECTED.items(), start=1):
        line = lines.get(str(index), "")
        checks[key] = line_answers(line, path, ident)
    score = sum(checks.values()) / len(checks)
    return {"score": score, "checks": checks}


def main():
    """Print the single JSON result line; any failure scores 0 with an error key."""
    try:
        result = grade(sys.argv[2])
    except Exception as exc:
        result = {
            "score": 0,
            "checks": {key: False for key in EXPECTED},
            "error": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
