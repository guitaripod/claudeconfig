#!/usr/bin/env python3
"""Lint Claude Code auto-memory folders.

memory-lint [DIR ...]   lint these memory folders
memory-lint             lint every folder under ~/.claude/projects/*/memory
                        plus the stores in ~/claudememory, each real folder once
memory-lint -v          also list dangling [[links]] (allowed, informational)

Exits 1 when any folder has an error.
"""

import argparse
import re
import sys
from pathlib import Path

INDEX = "MEMORY.md"
MAX_INDEX_LINES = 200
MAX_INDEX_BYTES = 16_000
MAX_INDEX_LINE = 220
DANGLING_ENDINGS = {
    "a", "an", "and", "as", "at", "because", "but", "by", "for", "from", "if",
    "in", "into", "of", "on", "or", "so", "than", "that", "the", "then", "to",
    "via", "when", "which", "while", "with", "without",
}
INDEX_LINK = re.compile(r"\]\(([^)]+?\.md)\)")
WIKI_LINK = re.compile(r"\[\[([^\]]+)\]\]")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.S)


def slug(text):
    """Normalise a memory name or [[link]] so hyphen/underscore/case variants match."""
    return re.sub(r"\.md$", "", text.strip()).lower().replace("_", "-")


class Report:
    def __init__(self, folder):
        self.folder = folder
        self.errors = []
        self.warnings = []
        self.info = []

    def error(self, message):
        self.errors.append(message)

    def warn(self, message):
        self.warnings.append(message)

    def note(self, message):
        self.info.append(message)


def default_folders():
    """Every memory folder Claude Code can load, deduplicated by real path."""
    home = Path.home()
    candidates = sorted((home / ".claude/projects").glob("*/memory"))
    store_root = home / "claudememory"
    if store_root.is_dir():
        candidates += sorted(p for p in store_root.iterdir() if p.is_dir() and not p.name.startswith("."))
    seen = {}
    for path in candidates:
        if path.is_symlink() and not path.exists():
            seen.setdefault(str(path), path)
            continue
        real = path.resolve()
        if (real / INDEX).exists() or any(real.glob("*.md")):
            seen.setdefault(str(real), path)
    return list(seen.values())


def parse_frontmatter(text):
    match = FRONTMATTER.match(text)
    if not match:
        return None, text
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.strip().partition(":")
        if sep:
            fields.setdefault(key.strip(), value.strip().strip("\"'"))
    return fields, match.group(2)


def looks_cut_off(body):
    """True when the last line of prose ends mid-sentence on a connective word."""
    lines = [line.rstrip() for line in body.strip().splitlines() if line.strip()]
    if not lines:
        return False
    last = lines[-1]
    if last.endswith(("```", "|")):
        return False
    words = re.findall(r"[A-Za-z']+$", last)
    return bool(words) and words[0].lower() in DANGLING_ENDINGS


def lint_index(folder, report, files):
    index = folder / INDEX
    if not index.exists():
        if files:
            report.error(f"{INDEX} missing while {len(files)} memory files exist")
        return set()
    text = index.read_text(errors="replace")
    lines = text.splitlines()
    if len(lines) > MAX_INDEX_LINES:
        report.error(f"{INDEX} has {len(lines)} lines (limit {MAX_INDEX_LINES}); it loads into every session")
    if len(text.encode()) > MAX_INDEX_BYTES:
        report.warn(f"{INDEX} is {len(text.encode())} bytes (budget {MAX_INDEX_BYTES}); shorten hooks")
    for number, line in enumerate(lines, 1):
        if len(line) > MAX_INDEX_LINE:
            report.warn(f"{INDEX}:{number} is {len(line)} chars; keep index lines short")
    linked = set()
    for target in INDEX_LINK.findall(text):
        name = target.split("#")[0]
        if "/" in name:
            report.error(f"{INDEX} links {target}; links must be bare file names in this folder")
            name = name.rsplit("/", 1)[-1]
        linked.add(name)
        if not (folder / name).exists():
            report.error(f"{INDEX} links {name}, which does not exist")
    return linked


def lint_folder(folder):
    report = Report(folder)
    if folder.is_symlink() and not folder.exists():
        report.error(f"dangling symlink to {folder.readlink()}")
        return report
    files = sorted(p for p in folder.glob("*.md") if p.name != INDEX)
    linked = lint_index(folder, report, files)
    names = {}
    stems = {p.stem for p in files}
    bodies = {}
    for path in files:
        text = path.read_text(errors="replace")
        fields, body = parse_frontmatter(text)
        bodies[path.name] = body
        if path.name not in linked:
            report.warn(f"{path.name} is not linked from {INDEX}")
        if fields is None:
            report.error(f"{path.name} has no frontmatter")
            continue
        for key in ("name", "description"):
            if not fields.get(key):
                report.error(f"{path.name} frontmatter lacks {key}")
        if not fields.get("type"):
            report.error(f"{path.name} frontmatter lacks type")
        name = fields.get("name")
        if name:
            if name in names:
                report.error(f"{path.name} and {names[name]} share the name {name}")
            names[name] = path.name
        if not body.strip():
            report.error(f"{path.name} has an empty body")
        elif looks_cut_off(body):
            report.error(f"{path.name} ends mid-sentence: {body.strip().splitlines()[-1][-60:]!r}")
    known = {slug(name) for name in names} | {slug(stem) for stem in stems}
    for file_name, body in bodies.items():
        for target in sorted(set(WIKI_LINK.findall(body))):
            if slug(target) not in known:
                report.note(f"{file_name} links [[{target}]], which no memory here defines")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folders", nargs="*", type=Path)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    folders = args.folders or default_folders()
    failed = False
    for folder in folders:
        report = lint_folder(folder)
        shown = report.errors or report.warnings or (args.verbose and report.info)
        if not shown:
            continue
        print(f"== {folder}")
        for message in report.errors:
            print(f"  ERROR {message}")
        for message in report.warnings:
            print(f"  warn  {message}")
        if args.verbose:
            for message in report.info:
                print(f"  info  {message}")
        failed = failed or bool(report.errors)
    print(f"{len(folders)} memory folders checked" + (", errors found" if failed else ", no errors"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
