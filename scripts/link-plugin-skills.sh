#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$REPO_DIR/skills/plugins"

python3 - "$DEST" <<'PY'
import json
import os
import shutil
import sys
from pathlib import Path

dest = Path(sys.argv[1])
home = Path.home()


def load(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}


enabled = {
    name
    for name, on in load(home / ".claude/settings.json").get("enabledPlugins", {}).items()
    if on
}
installed = load(home / ".claude/plugins/installed_plugins.json").get("plugins", {})


def install_paths(name):
    entries = installed.get(name, [])
    if isinstance(entries, dict):
        entries = [entries]
    entries.sort(key=lambda e: 0 if e.get("scope") == "user" else 1)
    seen = set()
    paths = []
    for entry in entries:
        raw = entry.get("installPath")
        if raw and raw not in seen:
            seen.add(raw)
            paths.append(Path(raw))
    return paths


claimed = {"plugins"}
for root in (home / ".claude/skills", home / ".agents/skills"):
    if root.is_dir():
        claimed.update(p.parent.name for p in root.glob("*/SKILL.md"))

wanted = {}
for name in sorted(enabled):
    for base in install_paths(name):
        if not base.is_dir():
            continue
        for md in base.rglob("SKILL.md"):
            if "node_modules" in md.parts or md.parent.parent.name != "skills":
                continue
            skill_id = md.parent.name
            if skill_id in claimed or skill_id in wanted:
                continue
            wanted[skill_id] = md.parent.resolve()

dest.mkdir(parents=True, exist_ok=True)
for entry in sorted(dest.iterdir()):
    if entry.name in wanted:
        continue
    if entry.is_symlink() or not entry.is_dir():
        entry.unlink()
    else:
        shutil.rmtree(entry)

added = []
for skill_id, source in sorted(wanted.items()):
    link = dest / skill_id
    if link.is_symlink() and os.readlink(link) == str(source):
        continue
    if link.is_symlink() or link.exists():
        if link.is_dir() and not link.is_symlink():
            shutil.rmtree(link)
        else:
            link.unlink()
    link.symlink_to(source)
    added.append(skill_id)

print(f"  {len(wanted)} plugin skills linked into {dest} ({len(added)} new)")
if added:
    print("    " + ", ".join(added))
PY
