import json
import os
import re
import sys

EXPECTED = {
    "pickerless": {"brisk-7b", "hollow-22b", "marl-8b", "nettle-3b"},
    "drift": {"coral-12b", "corvid-27b", "sable-32b"},
}
LABEL = re.compile(r"^[\s*_`>-]*(pickerless|drift)[*_`]*\s*:", re.IGNORECASE)


def parse_ids(value):
    """Split a labelled value on commas and whitespace, dropping empty tokens and the word none."""
    tokens = {token.strip("*_`.").lower() for token in re.split(r"[,\s]+", value)}
    return {token for token in tokens if token and token != "none"}


def last_values(text):
    """Return the id set from the last line naming each label, keyed by lowercase label."""
    found = {}
    for line in text.splitlines():
        match = LABEL.match(line)
        if match:
            found[match.group(1).lower()] = parse_ids(line[match.end():])
    return found


def f1(predicted, truth):
    """Return the F1 of a predicted id set against the truth set, where two empty sets score 1.0."""
    if not predicted and not truth:
        return 1.0
    hits = len(predicted & truth)
    if not hits:
        return 0.0
    precision = hits / len(predicted)
    recall = hits / len(truth)
    return 2 * precision * recall / (precision + recall)


def grade(workdir, answer_path):
    """Check the fixture is present, then score both labelled answer lines against the expected sets."""
    if not os.path.isfile(os.path.join(workdir, "config", "llama-swap.yaml")):
        raise FileNotFoundError("config/llama-swap.yaml missing from WORKDIR")
    with open(answer_path, encoding="utf-8", errors="replace") as fh:
        values = last_values(fh.read())
    checks = {}
    scores = []
    for label, truth in EXPECTED.items():
        predicted = values.get(label)
        score = f1(predicted or set(), truth)
        scores.append(score)
        checks[f"{label}_f1"] = round(score, 3)
        checks[f"{label}_exact"] = predicted == truth
    return {"score": round(sum(scores) / len(scores), 3), "checks": checks}


def main():
    """Print the single JSON result line; any failure scores 0 with an error key."""
    try:
        result = grade(sys.argv[1], sys.argv[2])
    except Exception as exc:
        result = {
            "score": 0,
            "checks": {"pickerless_f1": 0, "drift_f1": 0, "pickerless_exact": False, "drift_exact": False},
            "error": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
