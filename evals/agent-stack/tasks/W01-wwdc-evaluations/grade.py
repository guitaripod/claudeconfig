import json
import re
import sys


def grade(text):
    """Score the answer against the session facts verified in the knowledge base on 2026-10-29."""
    found = {n for n in ("298", "299", "335") if re.search(r"\b%s\b" % n, text)}
    return {"score": round(len(found) / 3, 3), "checks": {"found": sorted(found)}}


def main():
    """Print one JSON line; any failure scores 0 with an error key."""
    try:
        print(json.dumps(grade(open(sys.argv[2], errors="replace").read())))
    except Exception as exc:
        print(json.dumps({"score": 0, "checks": {}, "error": repr(exc)}))


if __name__ == "__main__":
    main()
