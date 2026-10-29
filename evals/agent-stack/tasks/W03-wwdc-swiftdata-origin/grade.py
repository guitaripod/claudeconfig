import json
import re
import sys


def grade(text):
    """Score the answer against the session facts verified in the knowledge base on 2026-10-29."""
    checks = {"session": bool(re.search(r"\b10187\b", text)), "title": "meet swiftdata" in text.lower()}
    return {"score": 0.5 * checks["session"] + 0.5 * checks["title"], "checks": checks}


def main():
    """Print one JSON line; any failure scores 0 with an error key."""
    try:
        print(json.dumps(grade(open(sys.argv[2], errors="replace").read())))
    except Exception as exc:
        print(json.dumps({"score": 0, "checks": {}, "error": repr(exc)}))


if __name__ == "__main__":
    main()
