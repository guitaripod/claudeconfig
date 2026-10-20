#!/usr/bin/env python3
"""preset.py — resolve a workdir's preset. Every stage reads its direction here.

A workdir must name a preset in project.json. There is deliberately no default:
the preset is what decides pacing, effects, geometry, gates and delivery, so a
missing preset is an error, not a fallback to whatever the last edit used.

Workdirs from before presets carry "style": "classic" | "remaster"; those map to
the hype and hype-quality presets so an in-flight edit keeps working.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PRESETS = os.path.join(os.path.dirname(HERE), "presets")

LEGACY_STYLE = {"classic": "hype", "remaster": "hype-quality"}


class PresetError(SystemExit):
    pass


def read(path):
    with open(path) as f:
        return json.load(f)


def available():
    return {f[:-5]: read(os.path.join(PRESETS, f))["summary"]
            for f in sorted(os.listdir(PRESETS)) if f.endswith(".json")}


def list_text():
    return "\n".join(f"  {n:14s} {s}" for n, s in available().items())


def name_for(cfg):
    """The preset a workdir declares, mapping the pre-preset style key."""
    name = cfg.get("preset")
    if name:
        return name
    legacy = cfg.get("style")
    if legacy in LEGACY_STYLE:
        return LEGACY_STYLE[legacy]
    raise PresetError(
        'project.json has no "preset". Pass --preset to init.py or extract_audio.py.\n'
        + list_text())


def load(root):
    """Return (project, preset). The project's canvas and effect intensities
    override the preset's, because they are what actually rendered."""
    cfg = read(os.path.join(root, "project.json"))
    name = name_for(cfg)
    path = os.path.join(PRESETS, f"{name}.json")
    if not os.path.exists(path):
        raise PresetError(f'unknown preset "{name}".\n' + list_text())
    p = read(path)
    p["canvas"] = {
        "w": int(cfg.get("out_w", p["canvas"]["w"])),
        "h": int(cfg.get("out_h", p["canvas"]["h"])),
        "fps": int(cfg.get("fps", p["canvas"]["fps"])),
    }
    p["effects"]["flash_gain"] = float(cfg.get("flash_gain", p["effects"].get("flash_gain", 1.0)))
    p["effects"]["rgb_shift"] = int(cfg.get("rgb_shift", p["effects"].get("rgb_shift", 0)))
    if cfg.get("pacing"):
        p["pacing"] = {**p.get("pacing", {}), **cfg["pacing"]}
    if cfg.get("domain"):
        p["scan"]["profile"] = cfg["domain"]
    return cfg, p


def require(p, *path):
    """Fetch a nested preset value, failing loudly on a malformed preset."""
    node = p
    for key in path:
        if not isinstance(node, dict) or key not in node:
            raise PresetError(f'preset "{p.get("name")}" is missing {"/".join(path)}')
        node = node[key]
    return node


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(list_text())
        raise SystemExit(0)
    cfg, p = load(os.path.abspath(sys.argv[1]))
    print(json.dumps({"preset": p["name"], "project": {k: cfg[k] for k in ("fps", "out_w", "out_h") if k in cfg},
                      "resolved": p}, indent=1))
