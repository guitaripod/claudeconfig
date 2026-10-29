import json
import re
import sys

PATTERN = re.compile('sandbox|storekit|test store|test account', re.I)


def main():
    """Score 1 when the answer is non-empty and on topic; routing itself is read from the transcript by run.py."""
    try:
        text = open(sys.argv[2], errors="replace").read()
        hit = bool(text.strip()) and bool(PATTERN.search(text))
        print(json.dumps({"score": 1.0 if hit else 0.0, "checks": {"on_topic": hit}}))
    except Exception as exc:
        print(json.dumps({"score": 0, "checks": {}, "error": repr(exc)}))


if __name__ == "__main__":
    main()
