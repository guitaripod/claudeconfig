#!/usr/bin/env python3
"""Measure how much prose Claude Code actually makes you read.

Walks ~/.claude/projects/**/*.jsonl, groups assistant text into turns, strips
fenced code, and reports length distributions plus preamble/closer rates so the
brevity hooks can be verified instead of trusted.
"""
import argparse
import json
import os
import re
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DESCRIPTION = "Measure how much prose Claude Code actually makes you read."

FENCE_RE = re.compile(r"```.*?```", re.S)
OPENER_RE = re.compile(
    r"^\s*(i'?ll\b|i am going to\b|i'?m going to\b|let me\b|let'?s\b|sure[,.!]|great[,.!]|"
    r"perfect[,.!]|got it\b|i'?ve\b|i have\b|now i\b|first,|here'?s what\b|"
    r"to (answer|do|start)\b|looking at\b|i see\b)",
    re.I,
)
CLOSER_RE = re.compile(
    r"(let me know\b|would you like\b|feel free\b|happy to\b|if you'?d like\b|"
    r"anything else\b|want me to\b|hope (this|that) helps\b|just say the word\b|"
    r"i can also\b|shall i\b)[^.!?]*[.!?]?\s*$",
    re.I,
)


def strip_code(text):
    return FENCE_RE.sub(" ", text).strip()


def is_real_user_turn(obj):
    if obj.get("type") != "user" or obj.get("isMeta"):
        return False
    content = obj.get("message", {}).get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        return not any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content
        )
    return False


def iter_turns(path):
    """Yield (timestamp, [assistant text blocks]) per user-initiated turn."""
    current, ts = [], None
    try:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                if '"toolUseResult"' in line:
                    continue
                if '"type":"assistant"' not in line and '"type":"user"' not in line:
                    continue
                try:
                    obj = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if obj.get("isSidechain"):
                    continue
                if is_real_user_turn(obj):
                    if current:
                        yield ts, current
                    current, ts = [], obj.get("timestamp")
                elif obj.get("type") == "assistant":
                    blocks = obj.get("message", {}).get("content") or []
                    if not isinstance(blocks, list):
                        continue
                    for b in blocks:
                        if isinstance(b, dict) and b.get("type") == "text":
                            body = (b.get("text") or "").strip()
                            if body:
                                current.append(body)
                                ts = ts or obj.get("timestamp")
    except OSError:
        return
    if current:
        yield ts, current


def collect(root, since, project_filter):
    rows = []
    for path in Path(root).glob("*/*.jsonl"):
        if project_filter and project_filter not in path.parent.name:
            continue
        try:
            if datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < since:
                continue
        except OSError:
            continue
        for ts, blocks in iter_turns(path):
            if not ts:
                continue
            try:
                when = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
            if when < since:
                continue
            prose = strip_code("\n\n".join(blocks))
            final = strip_code(blocks[-1])
            rows.append(
                {
                    "when": when,
                    "project": path.parent.name,
                    "prose_chars": len(prose),
                    "final_chars": len(final),
                    "blocks": len(blocks),
                    "opener": bool(OPENER_RE.search(blocks[0])),
                    "closer": bool(CLOSER_RE.search(final)) if final else False,
                    "head": " ".join(blocks[0].split())[:70],
                }
            )
    return rows


def summarize(rows):
    if not rows:
        return None
    prose = sorted(r["prose_chars"] for r in rows)
    final = sorted(r["final_chars"] for r in rows)

    def pct(vals, q):
        return vals[min(len(vals) - 1, int(len(vals) * q))]

    return {
        "turns": len(rows),
        "prose_median": int(statistics.median(prose)),
        "prose_p90": pct(prose, 0.9),
        "final_median": int(statistics.median(final)),
        "final_p90": pct(final, 0.9),
        "opener_pct": round(100 * sum(r["opener"] for r in rows) / len(rows), 1),
        "closer_pct": round(100 * sum(r["closer"] for r in rows) / len(rows), 1),
    }


def bucket_key(when, daily):
    return when.strftime("%Y-%m-%d") if daily else "%d-W%02d" % when.isocalendar()[:2]


def print_table(buckets):
    header = f"{'period':<12}{'turns':>7}{'prose~':>8}{'p90':>7}{'final~':>8}{'p90':>7}{'open%':>7}{'close%':>8}"
    print(header)
    print("-" * len(header))
    for key in sorted(buckets):
        s = summarize(buckets[key])
        if not s:
            continue
        print(
            f"{key:<12}{s['turns']:>7}{s['prose_median']:>8}{s['prose_p90']:>7}"
            f"{s['final_median']:>8}{s['final_p90']:>7}{s['opener_pct']:>7}{s['closer_pct']:>8}"
        )


def print_before_after(rows, split):
    before = [r for r in rows if r["when"] < split]
    after = [r for r in rows if r["when"] >= split]
    b, a = summarize(before), summarize(after)
    if not b or not a:
        print("not enough data on both sides of the split", file=sys.stderr)
        return
    print(f"split at {split.date()}\n")
    print(f"{'metric':<16}{'before':>10}{'after':>10}{'change':>10}")
    print("-" * 46)
    for label, key in [
        ("turns", "turns"),
        ("prose median", "prose_median"),
        ("prose p90", "prose_p90"),
        ("final median", "final_median"),
        ("final p90", "final_p90"),
        ("preamble %", "opener_pct"),
        ("closer %", "closer_pct"),
    ]:
        delta = "" if key == "turns" else f"{(a[key] - b[key]) / b[key] * 100:+.0f}%" if b[key] else "n/a"
        print(f"{label:<16}{b[key]:>10}{a[key]:>10}{delta:>10}")


def main():
    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument("--days", type=int, default=90, help="lookback window (default 90)")
    ap.add_argument("--project", help="only projects whose dir name contains this")
    ap.add_argument("--daily", action="store_true", help="bucket by day instead of ISO week")
    ap.add_argument("--before-after", metavar="YYYY-MM-DD", help="compare two periods around a date")
    ap.add_argument("--worst", type=int, metavar="N", help="show the N longest turns")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument(
        "--root",
        default=os.path.expanduser("~/.claude/projects"),
        help="transcript root",
    )
    args = ap.parse_args()

    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    split = None
    if args.before_after:
        split = datetime.fromisoformat(args.before_after).replace(tzinfo=timezone.utc)
        since = min(since, split - timedelta(days=args.days))

    rows = collect(args.root, since, args.project)
    if not rows:
        print("no turns found", file=sys.stderr)
        return 1

    if args.json:
        buckets = {}
        for r in rows:
            buckets.setdefault(bucket_key(r["when"], args.daily), []).append(r)
        print(json.dumps(
            {
                "overall": summarize(rows),
                "buckets": {k: summarize(v) for k, v in sorted(buckets.items())},
            },
            indent=2,
        ))
        return 0

    if split:
        print_before_after(rows, split)
        return 0

    if args.worst:
        print(f"{'when':<12}{'chars':>7}  opening line")
        for r in sorted(rows, key=lambda r: -r["prose_chars"])[: args.worst]:
            print(f"{r['when'].date()!s:<12}{r['prose_chars']:>7}  {r['head']}")
        return 0

    buckets = {}
    for r in rows:
        buckets.setdefault(bucket_key(r["when"], args.daily), []).append(r)
    print_table(buckets)
    s = summarize(rows)
    if s:
        print(f"\noverall: {s['turns']} turns, prose median {s['prose_median']} chars, "
              f"p90 {s['prose_p90']}, preamble {s['opener_pct']}%, closer {s['closer_pct']}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
