"""Build an isolated CLAUDE_CONFIG_DIR for one stack variant.

A variant directory under variants/ may hold:
  base               name of the variant it builds on (default: the live config)
  CLAUDE.md          replaces the user instructions
  hooks/*.sh         replace or add hook scripts
  agents/*.md        replace or add subagent definitions
  delete.txt         relative paths to drop from the built config (e.g. agents/bulk.md)
  settings.patch.json  deep-merged into settings.json; lists are concatenated
"""

import json
import os
import shutil
from pathlib import Path

HOME = Path.home()
LIVE = HOME / "claudeconfig"
LIVE_DOT = HOME / ".claude"
HERE = Path(__file__).resolve().parent.parent
VARIANTS = HERE / "variants"


def deep_merge(base, patch):
    """Merge patch into base: dicts recurse, lists concatenate without duplicates, scalars replace."""
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        elif isinstance(value, list) and isinstance(base.get(key), list):
            base[key] = base[key] + [item for item in value if item not in base[key]]
        else:
            base[key] = value
    return base


def chain(name):
    """Return the variant names from the root down to name, following base files."""
    names = []
    while name and name != "live":
        names.insert(0, name)
        base_file = VARIANTS / name / "base"
        name = base_file.read_text().strip() if base_file.exists() else None
    return names


def seed_live(cfg):
    """Copy the live tracked config into cfg; share skills, workflows, plugins and rules by link."""
    shutil.copy2(LIVE / "CLAUDE.md", cfg / "CLAUDE.md")
    shutil.copytree(LIVE / "hooks", cfg / "hooks")
    shutil.copytree(LIVE / "agents", cfg / "agents")
    for name in ("skills", "workflows"):
        (cfg / name).symlink_to(LIVE / name)
    (cfg / "plugins").symlink_to(LIVE_DOT / "plugins")
    (cfg / "rules").mkdir()
    for rule in sorted((LIVE_DOT / "rules").glob("*.md")):
        (cfg / "rules" / rule.name).symlink_to(rule.resolve())
    (cfg / ".credentials.json").symlink_to(LIVE_DOT / ".credentials.json")
    live_state = json.loads((HOME / ".claude.json").read_text())
    (cfg / ".claude.json").write_text(json.dumps({
        "hasCompletedOnboarding": True,
        "mcpServers": live_state.get("mcpServers", {}),
    }))
    return json.loads((LIVE / "settings.json").read_text())


def apply_variant(cfg, settings, name):
    """Overlay one variant directory onto cfg and fold its settings patch into settings."""
    src = VARIANTS / name
    if (src / "CLAUDE.md").exists():
        shutil.copy2(src / "CLAUDE.md", cfg / "CLAUDE.md")
    for sub in ("hooks", "agents"):
        for path in sorted((src / sub).glob("*")) if (src / sub).is_dir() else []:
            shutil.copy2(path, cfg / sub / path.name)
    if (src / "delete.txt").exists():
        for rel in (src / "delete.txt").read_text().split():
            target = cfg / rel
            if target.is_file() or target.is_symlink():
                target.unlink()
    if (src / "settings.patch.json").exists():
        deep_merge(settings, json.loads((src / "settings.patch.json").read_text()))


def finalize_settings(cfg, settings, memory_seed):
    """Point hooks at the variant's copies, sandbox auto-memory, and drop the pinned model."""
    text = json.dumps(settings)
    text = text.replace("$HOME/claudeconfig/hooks/", f"{cfg}/hooks/")
    settings = json.loads(text)
    settings.pop("model", None)
    memory = cfg / "memory"
    if memory_seed and Path(memory_seed).is_dir():
        shutil.copytree(memory_seed, memory, ignore=shutil.ignore_patterns(".git"))
    else:
        memory.mkdir()
    settings["autoMemoryDirectory"] = str(memory)
    settings["outputStyle"] = "Concise"
    (cfg / "settings.json").write_text(json.dumps(settings, indent=2))


def build(name, root, dirname=None, memory_seed=str(HOME / "claudememory" / "global")):
    """Build variant name under root/cfg/<dirname or name> from scratch and return its path."""
    cfg = Path(root) / "cfg" / (dirname or name)
    if cfg.exists():
        shutil.rmtree(cfg)
    cfg.mkdir(parents=True)
    settings = seed_live(cfg)
    for step in chain(name):
        apply_variant(cfg, settings, step)
    finalize_settings(cfg, settings, memory_seed)
    return cfg


if __name__ == "__main__":
    import sys
    print(build(sys.argv[1], os.environ.get("EVAL_HOME", str(HOME / ".cache" / "agent-stack-eval"))))
