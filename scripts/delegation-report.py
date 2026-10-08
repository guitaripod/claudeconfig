#!/usr/bin/env python3
"""Measure how Claude Code spends money across the main session and subagents.

Walks the local transcript tree (main sessions plus subagent and workflow agent
transcripts), prices every deduplicated API call at list rates, and reports spend
by model, main versus delegated spend, effort mix, delegation behavior and the
read-only share of main-session tool calls.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict, namedtuple
from datetime import datetime, timedelta, timezone
from pathlib import Path

DESCRIPTION = "Measure how Claude Code spends money across main and delegated sessions."
MAIN_ROLE = "main"
UNKNOWN_SUBAGENT_ROLE = "subagent:unknown"
SPAWN_TOOLS = ("Agent", "Task")
ESCALATION_MODELS = ("sonnet", "opus", "fable")
MILLION = 1_000_000
HAIKU_55_KEY = "haiku-5-5"
HAIKU_55_PROMPT_LIMIT = 100_000
EXAMPLE_LIMIT = 10
READ_ONLY_TOOLS = ("Read", "Grep", "Glob", "WebFetch", "WebSearch", "LS", "NotebookRead")
READ_ONLY_TOOL_PREFIXES = ("mcp__lightpanda__",)
READ_ONLY_BASH = (
    "cd", "cat", "head", "tail", "rg", "grep", "ls", "find", "wc", "jq", "stat", "file", "tree", "du", "readlink",
    "realpath", "which", "sort", "uniq", "cut", "tr", "column", "diff", "basename", "dirname", "echo", "printf",
    "pwd", "date", "nl", "tac",
)
READ_ONLY_GIT = ("log", "show", "diff", "status", "blame", "grep", "ls-files", "rev-parse", "branch")
DISCARDED_REDIRECT = re.compile(r"[0-9]?>&[0-9]|[0-9]?>\s*/dev/null")
SEGMENT_SPLIT = re.compile(r"\s*(?:;|&&|\|\||\||\n)\s*")
GIT_OPTIONS = re.compile(r"^git\s+(?:(?:-C|-c)\s+\S+\s+|--no-pager\s+)*")
WORKFLOW_ROLE = "workflow-subagent"
TRANSCRIPT_PATTERNS = ("*/*/subagents/agent-*.jsonl", "*/*/subagents/workflows/*/agent-*.jsonl")
COMPARISON_ROWS = (
    ("spend", lambda s: s["spend_usd"], "money"),
    ("spend per day", lambda s: s["spend_per_day_usd"], "money"),
    ("calls", lambda s: s["calls"], "count"),
    ("delegated spend %", lambda s: s["scopes"]["delegated"]["spend_share_pct"], "pct"),
    ("delegated output %", lambda s: s["scopes"]["delegated"]["output_share_pct"], "pct"),
    ("escalation %", lambda s: s["delegation"]["escalation_pct"], "pct"),
    ("zero-tool %", lambda s: s["zero_tool"]["rate_pct"], "pct"),
    ("read-only %", lambda s: s["main_tools"]["read_only_pct"], "pct"),
)

Rate = namedtuple("Rate", "input write_5m write_1h read output")
OPUS_4_RATE = Rate(5, 6.25, 10, 0.50, 25)
SONNET_4_RATE = Rate(3, 3.75, 6, 0.30, 15)
PRICES = {
    "fable-5-1": Rate(10, 12.5, 20, 0.25, 50),
    "fable-5": Rate(10, 12.5, 20, 1, 50),
    "opus-5-5": Rate(4, 5, 8, 0.20, 20),
    "opus-5": Rate(5, 6.25, 10, 0.50, 25),
    "opus-4-8": OPUS_4_RATE,
    "opus-4-7": OPUS_4_RATE,
    "opus-4-6": OPUS_4_RATE,
    "opus-4-5": OPUS_4_RATE,
    "sonnet-5-5": Rate(2, 2.5, 4, 0.10, 10),
    "sonnet-5": Rate(2, 2.5, 4, 0.20, 10),
    "sonnet-4-6": SONNET_4_RATE,
    "sonnet-4-5": SONNET_4_RATE,
    "haiku-5-5": Rate(0.10, 0.125, 0.20, 0.01, 0.50),
    "haiku-4-5": Rate(1, 1.25, 2, 0.10, 5),
}
HAIKU_55_LARGE_PROMPT = Rate(0.50, 0.625, 1, 0.05, 2.50)


class Window:
    """A half-open UTC time range that spend and tool calls are attributed to."""

    def __init__(self, label, start, end):
        self.label = label
        self.start = start
        self.end = end

    def contains(self, when):
        """Return True when a timestamp falls inside [start, end)."""
        return self.start <= when < self.end

    def days(self):
        """Length of the window in days, used for spend per day."""
        return (self.end - self.start).total_seconds() / 86400


def day_arg(value):
    """Parse a YYYY-MM-DD argument as midnight UTC."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {value!r}")


def parse_timestamp(value):
    """Parse an ISO-8601 transcript timestamp into an aware UTC datetime, or None."""
    if not isinstance(value, str):
        return None
    try:
        when = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def parse_line(line):
    """Parse one JSONL line into a dict, or None when it is not a JSON object."""
    try:
        obj = json.loads(line)
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def as_int(value):
    """Return a token count as an int, treating anything missing or non-numeric as zero."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


def token_counts(usage):
    """Split a usage object into input, output, cache read and 5m/1h cache write counts."""
    total_write = as_int(usage.get("cache_creation_input_tokens"))
    breakdown = usage.get("cache_creation")
    if isinstance(breakdown, dict):
        write_5m = as_int(breakdown.get("ephemeral_5m_input_tokens"))
        write_1h = as_int(breakdown.get("ephemeral_1h_input_tokens"))
    else:
        write_5m, write_1h = total_write, 0
    return {
        "input": as_int(usage.get("input_tokens")),
        "output": as_int(usage.get("output_tokens")),
        "read": as_int(usage.get("cache_read_input_tokens")),
        "write": total_write,
        "write_5m": write_5m,
        "write_1h": write_1h,
    }


def prompt_tokens(counts):
    """Prompt size that selects the tier for tiered models: input plus both cache sides."""
    return counts["input"] + counts["write"] + counts["read"]


def price_key(model):
    """Return the longest price key contained in a model id, or None when nothing matches."""
    matches = [key for key in PRICES if key in model]
    return max(matches, key=len) if matches else None


def rate_for(model, counts):
    """Return the list rate for a call, switching haiku-5-5 to its large-prompt tier."""
    key = price_key(model)
    if key is None:
        return None
    if key == HAIKU_55_KEY and prompt_tokens(counts) > HAIKU_55_PROMPT_LIMIT:
        return HAIKU_55_LARGE_PROMPT
    return PRICES[key]


def call_cost(model, usage):
    """Return (total USD, cache USD) for one call, or None when the model has no price."""
    counts = token_counts(usage)
    rate = rate_for(model, counts)
    if rate is None:
        return None
    multiplier = 2 if usage.get("speed") == "fast" and "opus" in model else 1
    cache = (
        counts["write_5m"] * rate.write_5m
        + counts["write_1h"] * rate.write_1h
        + counts["read"] * rate.read
    ) / MILLION
    base = (counts["input"] * rate.input + counts["output"] * rate.output) / MILLION
    return (base + cache) * multiplier, cache * multiplier


def segment_read_only(segment):
    """Return True when one shell segment only reads: a listed command, `sed -n`, or a read-only git subcommand."""
    words = segment.split()
    head = words[0] if words else ""
    if head in READ_ONLY_BASH:
        return True
    if head == "sed":
        return words[1:2] == ["-n"]
    if head != "git":
        return False
    rest = GIT_OPTIONS.sub("git ", segment).split()
    return len(rest) > 1 and rest[1] in READ_ONLY_GIT


def is_read_only(name, tool_input):
    """Classify a main-session tool call as read-only with the same rules as hooks/delegate-midrun.sh."""
    if name in READ_ONLY_TOOLS or name.startswith(READ_ONLY_TOOL_PREFIXES):
        return True
    if name != "Bash":
        return False
    command = DISCARDED_REDIRECT.sub("", str(tool_input.get("command") or ""))
    if ">" in command:
        return False
    segments = [part.strip() for part in SEGMENT_SPLIT.split(command) if part.strip()]
    return bool(segments) and all(segment_read_only(part) for part in segments)


def absorb_assistant(scan, obj):
    """Record one assistant line: the call (last line per message id wins) and its tool_use blocks."""
    message = obj.get("message") if isinstance(obj.get("message"), dict) else {}
    model = message.get("model")
    when = parse_timestamp(obj.get("timestamp"))
    if model == "<synthetic>" or when is None:
        return
    content = message.get("content")
    blocks = content if isinstance(content, list) else []
    uses = [block for block in blocks if isinstance(block, dict) and block.get("type") == "tool_use"]
    for block in uses:
        key = block.get("id") or ("anon", len(scan["tool_uses"]))
        tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
        scan["tool_uses"][key] = {
            "id": block.get("id"),
            "name": block.get("name") or "",
            "input": tool_input,
            "when": when,
        }
    if uses:
        scan["tool_use_times"].append(when)
    call_key = message.get("id") or ("anon", len(scan["calls"]))
    previous = scan["calls"].get(call_key, {})
    scan["calls"][call_key] = {
        "when": when,
        "model": model,
        "usage": message.get("usage") if isinstance(message.get("usage"), dict) else {},
        "effort": obj.get("effort") or previous.get("effort"),
    }


def absorb_result(scan, obj):
    """Record the resolved model and agent id that a tool result reports, keyed by tool_use_id."""
    result = obj.get("toolUseResult")
    message = obj.get("message") if isinstance(obj.get("message"), dict) else {}
    content = message.get("content")
    if not isinstance(result, dict) or not isinstance(content, list):
        return
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_result" and block.get("tool_use_id"):
            scan["results"][block["tool_use_id"]] = {
                "resolvedModel": result.get("resolvedModel"),
                "agentId": result.get("agentId"),
            }


def scan_transcript(path):
    """Collect deduplicated calls, tool uses and agent results from one transcript, or None on read error."""
    scan = {"calls": {}, "tool_uses": {}, "tool_use_times": [], "results": {}}
    try:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                if '"assistant"' not in line and '"toolUseResult"' not in line:
                    continue
                obj = parse_line(line)
                if obj is None:
                    continue
                if obj.get("type") == "assistant":
                    absorb_assistant(scan, obj)
                elif obj.get("type") == "user" and obj.get("toolUseResult") is not None:
                    absorb_result(scan, obj)
    except OSError:
        return None
    return scan


def read_meta(path):
    """Load the sibling .meta.json of a subagent transcript, or an empty dict when it is absent."""
    try:
        with open(path.with_name(path.stem + ".meta.json"), "r", errors="replace") as fh:
            meta = json.load(fh)
    except (OSError, ValueError):
        return {}
    return meta if isinstance(meta, dict) else {}


def role_of(meta):
    """Role name for a subagent: its agentType, or a placeholder when there is no meta."""
    return meta.get("agentType") or UNKNOWN_SUBAGENT_ROLE


def transcript_paths(root):
    """Yield (path, is_subagent) for every main and subagent transcript under the root."""
    for path in sorted(root.glob("*/*.jsonl")):
        yield path, False
    for pattern in TRANSCRIPT_PATTERNS:
        for path in sorted(root.glob(pattern)):
            yield path, True


def modified_since(path, lower):
    """Return True when the file was modified at or after the lower bound, so it can hold window data."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) >= lower
    except OSError:
        return False


def new_role():
    """Empty totals for one role within a window."""
    return {
        "transcripts": 0,
        "calls": 0,
        "spend": 0.0,
        "output": 0,
        "models": defaultdict(float),
        "effort": Counter(),
    }


def new_accumulator():
    """Empty totals for one window, filled by fold_transcript."""
    return {
        "calls": 0,
        "spend": 0.0,
        "cache": 0.0,
        "models": defaultdict(float),
        "unpriced": defaultdict(Counter),
        "roles": defaultdict(new_role),
        "spawns": 0,
        "escalations": 0,
        "spawn_types": Counter(),
        "spawn_explicit": Counter(),
        "spawn_resolved": Counter(),
        "subagent_transcripts": 0,
        "zero_tool": [],
        "tool_calls": 0,
        "read_only": 0,
    }


def record_unpriced(acc, model, usage):
    """Keep token totals for a model with no price so it is listed instead of silently costing zero."""
    counts = token_counts(usage)
    row = acc["unpriced"][model]
    row["calls"] += 1
    row["input"] += counts["input"]
    row["cache_write"] += counts["write"]
    row["cache_read"] += counts["read"]
    row["output"] += counts["output"]


def add_call(acc, stats, call):
    """Add one in-window call to the window totals and to its role."""
    model = call["model"] or "unknown"
    usage = call["usage"]
    acc["calls"] += 1
    stats["calls"] += 1
    stats["output"] += as_int(usage.get("output_tokens"))
    stats["effort"][str(call["effort"] or "none")] += 1
    priced = call_cost(model, usage)
    if priced is None:
        record_unpriced(acc, model, usage)
        return
    total, cache = priced
    acc["spend"] += total
    acc["cache"] += cache
    acc["models"][model] += total
    stats["spend"] += total
    stats["models"][model] += total


def record_spawn(acc, tool_input, result):
    """Count one Agent or Task spawn by subagent type, explicit model and resolved model."""
    explicit = tool_input.get("model") or "default"
    resolved = (result or {}).get("resolvedModel") or "unmatched"
    acc["spawns"] += 1
    if explicit in ESCALATION_MODELS:
        acc["escalations"] += 1
    acc["spawn_types"][tool_input.get("subagent_type") or "unspecified"] += 1
    acc["spawn_explicit"][explicit] += 1
    acc["spawn_resolved"][resolved] += 1


def fold_main_tools(acc, window, scan):
    """Count main-session tool calls in the window, their read-only share and agent spawns."""
    for tool in scan["tool_uses"].values():
        if not window.contains(tool["when"]):
            continue
        acc["tool_calls"] += 1
        if is_read_only(tool["name"], tool["input"]):
            acc["read_only"] += 1
        if tool["name"] in SPAWN_TOOLS:
            record_spawn(acc, tool["input"], scan["results"].get(tool["id"]))


def fold_zero_tool(acc, window, scan, path, meta, role):
    """Count an Agent-spawned subagent as zero-tool when none of its in-window messages call a tool.

    Workflow agents are left out: many of their phases reason over inputs by design and need no tools.
    """
    if role == WORKFLOW_ROLE:
        return
    acc["subagent_transcripts"] += 1
    if any(window.contains(when) for when in scan["tool_use_times"]):
        return
    acc["zero_tool"].append({"agentType": role, "description": meta.get("description") or "", "path": str(path)})


def fold_transcript(acc, window, scan, path, meta, role, is_subagent):
    """Fold one transcript into a window's totals."""
    if not is_subagent:
        fold_main_tools(acc, window, scan)
    calls = [call for call in scan["calls"].values() if window.contains(call["when"])]
    if not calls:
        return
    stats = acc["roles"][role]
    stats["transcripts"] += 1
    for call in calls:
        add_call(acc, stats, call)
    if is_subagent:
        fold_zero_tool(acc, window, scan, path, meta, role)


def collect(root, windows):
    """Scan every transcript that can hold window data and return one accumulator per window label."""
    lower = min(window.start for window in windows)
    accs = {window.label: new_accumulator() for window in windows}
    for path, is_subagent in transcript_paths(root):
        if not modified_since(path, lower):
            continue
        scan = scan_transcript(path)
        if scan is None:
            continue
        meta = read_meta(path) if is_subagent else {}
        role = role_of(meta) if is_subagent else MAIN_ROLE
        for window in windows:
            fold_transcript(accs[window.label], window, scan, path, meta, role, is_subagent)
    return accs


def pct(part, whole):
    """Percentage rounded to two places, or 0.0 when the whole is zero."""
    return round(100 * part / whole, 2) if whole else 0.0


def ranked(totals, whole):
    """Rows of {model, spend_usd, share_pct} sorted by spend, largest first."""
    return [
        {"model": model, "spend_usd": round(value, 4), "share_pct": pct(value, whole)}
        for model, value in sorted(totals.items(), key=lambda item: -item[1])
    ]


def role_summary(name, stats, spend_total, output_total):
    """Summary dict for one role: transcripts, calls, spend, output share, model mix and effort mix."""
    return {
        "role": name,
        "transcripts": stats["transcripts"],
        "calls": stats["calls"],
        "spend_usd": round(stats["spend"], 4),
        "spend_share_pct": pct(stats["spend"], spend_total),
        "output_tokens": stats["output"],
        "output_share_pct": pct(stats["output"], output_total),
        "models": ranked(stats["models"], stats["spend"]),
        "effort": dict(stats["effort"].most_common()),
    }


def unpriced_summary(unpriced):
    """Rows for models with no price, with their token totals."""
    return [
        {
            "model": model,
            "calls": row["calls"],
            "input_tokens": row["input"],
            "cache_write_tokens": row["cache_write"],
            "cache_read_tokens": row["cache_read"],
            "output_tokens": row["output"],
        }
        for model, row in sorted(unpriced.items())
    ]


def scope_summary(stats, spend_total, output_total):
    """Spend and output-token totals and shares for one scope (main or delegated)."""
    return {
        "spend_usd": round(stats["spend"], 4),
        "spend_share_pct": pct(stats["spend"], spend_total),
        "output_tokens": stats["output"],
        "output_share_pct": pct(stats["output"], output_total),
    }


def summarize(window, acc):
    """Turn one window's accumulator into the plain dict that both the text and JSON output use."""
    days = window.days()
    spend = acc["spend"]
    roles = acc["roles"]
    main = roles.get(MAIN_ROLE) or new_role()
    output_total = sum(stats["output"] for stats in roles.values())
    delegated = {"spend": spend - main["spend"], "output": output_total - main["output"]}
    spawns = acc["spawns"]
    subagents = acc["subagent_transcripts"]
    zero = acc["zero_tool"]
    return {
        "label": window.label,
        "start": window.start.isoformat(),
        "end": window.end.isoformat(),
        "days": round(days, 2),
        "spend_usd": round(spend, 4),
        "spend_per_day_usd": round(spend / days, 4) if days else 0.0,
        "calls": acc["calls"],
        "cache_share_pct": pct(acc["cache"], spend),
        "models": ranked(acc["models"], spend),
        "unpriced": unpriced_summary(acc["unpriced"]),
        "scopes": {
            "main": scope_summary(main, spend, output_total),
            "delegated": scope_summary(delegated, spend, output_total),
        },
        "roles": [
            role_summary(name, stats, spend, output_total)
            for name, stats in sorted(roles.items(), key=lambda item: -item[1]["spend"])
        ],
        "delegation": {
            "spawns": spawns,
            "escalations": acc["escalations"],
            "escalation_pct": pct(acc["escalations"], spawns),
            "by_subagent_type": dict(acc["spawn_types"].most_common()),
            "by_explicit_model": dict(acc["spawn_explicit"].most_common()),
            "by_resolved_model": dict(acc["spawn_resolved"].most_common()),
        },
        "zero_tool": {
            "transcripts": subagents,
            "zero_tool": len(zero),
            "rate_pct": pct(len(zero), subagents),
            "examples": sorted(zero, key=lambda row: row["path"])[:EXAMPLE_LIMIT],
        },
        "main_tools": {
            "calls": acc["tool_calls"],
            "read_only": acc["read_only"],
            "read_only_pct": pct(acc["read_only"], acc["tool_calls"]),
        },
    }


def money(value):
    """Format a USD amount with thousands separators."""
    return f"${value:,.2f}"


def format_value(value, kind):
    """Format a comparison cell by its metric kind."""
    if kind == "money":
        return money(value)
    if kind == "count":
        return f"{value:,}"
    return f"{value:.1f}%"


def format_change(before, after, kind):
    """Relative change for money and counts, percentage-point change for shares."""
    if kind == "pct":
        return f"{after - before:+.1f}pp"
    return f"{(after - before) / before * 100:+.0f}%" if before else "n/a"


def print_comparison(before, after):
    """Print the before/after headline table for the two --before-after windows."""
    print(f"{'metric':<20}{before['label']:>12}{after['label']:>12}{'change':>12}")
    print("-" * 56)
    for label, get, kind in COMPARISON_ROWS:
        b, a = get(before), get(after)
        print(f"{label:<20}{format_value(b, kind):>12}{format_value(a, kind):>12}{format_change(b, a, kind):>12}")


def print_models(summary):
    """Print spend by model and any unpriced models with their token totals."""
    print("\nspend by model")
    print(f"{'model':<30}{'spend':>12}{'share':>8}")
    for row in summary["models"]:
        print(f"{row['model']:<30}{money(row['spend_usd']):>12}{row['share_pct']:>7.1f}%")
    for row in summary["unpriced"]:
        print(
            f"unpriced: {row['model']} calls={row['calls']} input={row['input_tokens']} "
            f"cache_write={row['cache_write_tokens']} cache_read={row['cache_read_tokens']} "
            f"output={row['output_tokens']}"
        )


def print_scopes(summary):
    """Print the main versus delegated split, then delegated spend per role with its model mix."""
    print("\nmain vs delegated")
    print(f"{'scope':<12}{'spend':>12}{'spend%':>8}{'out tokens':>13}{'out%':>8}")
    for name in ("main", "delegated"):
        row = summary["scopes"][name]
        print(
            f"{name:<12}{money(row['spend_usd']):>12}{row['spend_share_pct']:>7.1f}%"
            f"{row['output_tokens']:>13,}{row['output_share_pct']:>7.1f}%"
        )
    print("\ndelegated by role")
    print(f"{'role':<30}{'transcripts':>12}{'calls':>9}{'spend':>12}{'spend%':>8}")
    for role in summary["roles"]:
        if role["role"] == MAIN_ROLE:
            continue
        print(
            f"{role['role']:<30}{role['transcripts']:>12}{role['calls']:>9}"
            f"{money(role['spend_usd']):>12}{role['spend_share_pct']:>7.1f}%"
        )
        for row in role["models"]:
            print(f"    {row['model']:<26}{money(row['spend_usd']):>12}")


def print_effort(summary):
    """Print the effort mix per role as counts of each effort value."""
    print("\neffort mix per role (calls)")
    for role in summary["roles"]:
        mix = " ".join(f"{key}={count}" for key, count in role["effort"].items())
        print(f"{role['role']:<30}{mix}")


def print_counter(title, mapping, total):
    """Print one spawn breakdown as a count and share per key."""
    print(f"{title}:")
    for key, count in mapping.items():
        print(f"  {key:<28}{count:>7}{pct(count, total):>8.1f}%")


def print_delegation(summary):
    """Print spawn counts, escalation rate and the three spawn breakdowns."""
    d = summary["delegation"]
    print("\ndelegation from main transcripts")
    print(
        f"spawns {d['spawns']}  escalations {d['escalations']} ({d['escalation_pct']:.1f}%) "
        f"[explicit model in {', '.join(ESCALATION_MODELS)}]"
    )
    print_counter("by subagent_type", d["by_subagent_type"], d["spawns"])
    print_counter("by explicit input.model", d["by_explicit_model"], d["spawns"])
    print_counter("by resolvedModel", d["by_resolved_model"], d["spawns"])


def print_zero_tool(summary):
    """Print the zero-tool delegate rate and up to ten example transcripts."""
    z = summary["zero_tool"]
    print("\nzero-tool delegates")
    print(f"{z['zero_tool']} of {z['transcripts']} Agent-spawned subagent transcripts ({z['rate_pct']:.1f}%)")
    for row in z["examples"]:
        description = " ".join(row["description"].split())[:60]
        print(f"  {row['agentType']}  {description}  {row['path']}")


def print_main_tools(summary):
    """Print the main-session tool calls and their read-only share."""
    t = summary["main_tools"]
    print("\nmain-session tools")
    print(f"tool calls {t['calls']}  read-only {t['read_only']} ({t['read_only_pct']:.1f}%)")


def print_window(summary):
    """Print one window's full report."""
    print(f"{summary['label']}: {summary['start'][:10]} .. {summary['end'][:10]} ({summary['days']:.1f} days)")
    print(
        f"total {money(summary['spend_usd'])}  calls {summary['calls']}  "
        f"per day {money(summary['spend_per_day_usd'])}  cache share {summary['cache_share_pct']:.1f}%"
    )
    print_models(summary)
    print_scopes(summary)
    print_effort(summary)
    print_delegation(summary)
    print_zero_tool(summary)
    print_main_tools(summary)


def build_windows(args, now):
    """Return the windows to report: a before/after pair around a date, or one since/until span."""
    if args.before_after:
        span = timedelta(days=args.days)
        split = args.before_after
        return [
            Window("before", split - span, split),
            Window("after", split, max(split, min(split + span, now))),
        ]
    end = args.until or now
    start = args.since or end - timedelta(days=args.days)
    return [Window("window", start, end)]


def build_parser():
    """Command-line parser for the report."""
    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument("--since", type=day_arg, metavar="YYYY-MM-DD", help="window start, inclusive (UTC)")
    ap.add_argument("--until", type=day_arg, metavar="YYYY-MM-DD", help="window end, exclusive (UTC, default now)")
    ap.add_argument("--before-after", type=day_arg, metavar="YYYY-MM-DD", help="compare [DATE-N, DATE) with [DATE, DATE+N)")
    ap.add_argument("--days", type=int, default=14, help="window length for --before-after, or lookback without dates (default 14)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument(
        "--root",
        default=os.path.expanduser("~/.claude/projects"),
        help="transcript root",
    )
    return ap


def main():
    """Parse arguments, scan the transcripts, and print the report or its JSON form."""
    ap = build_parser()
    args = ap.parse_args()
    if args.days < 1:
        ap.error("--days must be at least 1")
    if args.before_after and (args.since or args.until):
        ap.error("--before-after cannot be combined with --since or --until")
    windows = build_windows(args, datetime.now(timezone.utc))
    for window in windows:
        if not args.before_after and window.start >= window.end:
            ap.error(f"the {window.label} window is empty (check the dates)")
    accs = collect(Path(os.path.expanduser(args.root)), windows)
    summaries = [summarize(window, accs[window.label]) for window in windows]
    if not any(summary["calls"] for summary in summaries):
        print("no API calls found", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"windows": summaries}, indent=2))
        return 0
    if args.before_after:
        print_comparison(summaries[0], summaries[1])
    for index, summary in enumerate(summaries):
        if index or args.before_after:
            print()
        print_window(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
