#!/usr/bin/env python3
"""Count the asks Marcus keeps repeating to agents, so the rules that should end them can be checked.

Reads every human prompt on this machine from Claude Code (~/.claude/projects), opencode
(~/.local/share/opencode/opencode.db) and omp (~/.omp/agent/sessions), skipping sub-agents,
hook output and machine-injected prompts, and reports how often each family of repeated ask
shows up per 100 prompts, by ISO week or before and after a date.
"""
import argparse
import glob
import json
import os
import re
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone

DESCRIPTION = "Count the asks Marcus keeps repeating to agents."
HOME = os.path.expanduser("~")

FAMILIES = {
    "status": r"^\W*(status|eta|are you done|done\s*\?|are we done|finished\?|still working|any progress)",
    "resume": r"^\W*(continue|resume|go on|keep going|carry on|why did you stop)\b",
    "approve": r"^\W*(yes|yeah|yep|sure|ok|okay|do it|go ahead|your call|you decide|you can do (it|that|all|everything|the rest))\W*(\.|!)?\s*$",
    "finish": r"\b(push|sync (up|it|them|my)|sync$|clean ?up|clean (git )?trees|install it|get it installed|did you (install|push|commit))\b",
    "handoff": r"^\W*(i )?(ran it|ran those|ran all|quit steam|closed (it|the game)|restarted)|gimme the (commands|sudos|oneliners)",
    "research": r"web research|research (it|the web)|search the web|did you (actually )?look it up",
    "visual": r"\b(\d|three|five) iterations?\b|iteration cycles?|bigger|big (fonts?|text)|easy to (see|read)",
}
SKIP_PREFIX = (
    "<task-notification", "<local-command", "Caveat:", "[Request interrupted", "Base directory for this skill",
    "This session is being continued", "<system-reminder>", "<bash-", "<user-prompt-submit-hook>",
    "Stop hook feedback", "<command-", "You were interrupted. The machine running you",
    "You ended the turn offering work", "You announced a next step",
)
SKIP_PROJECT = re.compile(r"agent-stack-eval|rounds-watch|hooktest|claude-test|tmp-tmp-|scratchpad|pokedex-llm-benchmark")


def parse_time(value):
    """A timezone-aware datetime from an ISO string or epoch milliseconds, or None."""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def texts_of(content):
    """The text parts of a message body that is either a string or a list of parts."""
    if isinstance(content, str):
        return [content]
    return [p.get("text", "") for p in content or [] if isinstance(p, dict) and p.get("type") == "text"]


def claude_prompts():
    """Human prompts typed into Claude Code sessions."""
    for path in glob.glob(f"{HOME}/.claude/projects/*/*.jsonl"):
        if SKIP_PROJECT.search(path):
            continue
        for line in open(path, errors="replace"):
            if '"type":"user"' not in line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("isSidechain") or record.get("isMeta") or record.get("origin") or record.get("toolUseResult") is not None:
                continue
            for text in texts_of(record.get("message", {}).get("content")):
                yield record.get("uuid"), record.get("timestamp"), text


def opencode_prompts():
    """Human prompts sent to top-level opencode sessions, both storage generations."""
    db = f"{HOME}/.local/share/opencode/opencode.db"
    if not os.path.exists(db):
        return
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    queries = [
        """select p.id, m.time_created, p.data from part p join message m on m.id = p.message_id
           join session s on s.id = m.session_id where s.parent_id is null and json_extract(m.data, '$.role') = 'user'""",
        """select m.id, m.time_created, m.data from session_message m join session_v2 s on s.id = m.session_id
           where s.parent_id is null and m.type = 'user'""",
    ]
    for query in queries:
        try:
            for key, created, data in con.execute(query):
                part = json.loads(data)
                if part.get("synthetic") or part.get("type", "text") != "text":
                    continue
                yield key, created, part.get("text", "")
        except sqlite3.OperationalError:
            continue


def omp_prompts():
    """Human prompts sent to top-level omp sessions."""
    for path in glob.glob(f"{HOME}/.omp/agent/sessions/*/*.jsonl"):
        for line in open(path, errors="replace"):
            if '"role":"user"' not in line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            message = record.get("message") or {}
            if record.get("type") == "message" and message.get("role") == "user":
                for text in texts_of(message.get("content")):
                    yield record.get("id"), record.get("timestamp"), text


def collect(since):
    """Every human prompt since `since` as (time, text), each counted once."""
    seen, rows = set(), []
    for source in (claude_prompts, opencode_prompts, omp_prompts):
        for key, when, text in source():
            text = text.strip()
            when = parse_time(when)
            if not text or text.startswith(SKIP_PREFIX) or when is None or when < since or (key and key in seen):
                continue
            seen.add(key)
            rows.append((when, text))
    return rows


def rates(rows):
    """Prompt count plus each family's share per 100 prompts."""
    counts = Counter()
    for _, text in rows:
        for name, pattern in FAMILIES.items():
            if re.search(pattern, text, re.I):
                counts[name] += 1
    total = len(rows)
    return total, {name: (100 * counts[name] / total if total else 0.0) for name in FAMILIES}


def print_rows(label_rows):
    """One table line per (label, rows) pair."""
    print(f"{'period':<12}{'prompts':>8}" + "".join(f"{name:>10}" for name in FAMILIES))
    for label, rows in label_rows:
        total, share = rates(rows)
        print(f"{label:<12}{total:>8}" + "".join(f"{share[name]:>10.1f}" for name in FAMILIES))


def main():
    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument("--days", type=int, default=90, help="lookback window (default 90)")
    ap.add_argument("--before-after", metavar="YYYY-MM-DD", help="compare the periods before and after a date")
    args = ap.parse_args()
    rows = collect(datetime.now(timezone.utc) - timedelta(days=args.days))
    print("asks per 100 prompts\n")
    if args.before_after:
        split = datetime.fromisoformat(args.before_after).replace(tzinfo=timezone.utc)
        print_rows([("before", [r for r in rows if r[0] < split]), ("after", [r for r in rows if r[0] >= split])])
        return
    weeks = {}
    for row in rows:
        year, week, _ = row[0].isocalendar()
        weeks.setdefault(f"{year}-W{week:02d}", []).append(row)
    print_rows(sorted(weeks.items()))


if __name__ == "__main__":
    main()
