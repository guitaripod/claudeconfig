#!/usr/bin/env python3
"""look.py <workdir> <list|preview|set|shuffle|show> [...] — the colour direction.

The look is the one part of a hype edit with no house style: pacing is fixed,
coloring is yours. This module holds a library of genuinely different grades and
resolves which one a given segment renders through, so a single edit can change
its coloring by section, by source, or shot to shot.

  list                      names + one-line character of every look
  preview [--from N]        render ONE real frame through every look into
                            frames/looks.png — look at it, then choose
  show                      print the resolved look block
  set base=ember drop=neon seg:10=mono_steel src:abc123=ice drift=0.35
  shuffle [--seed N]        roll a random base + per-section assignment

Resolution order for a segment: explicit seg["grade"] > look.segments[i] >
look.sources[src] > look.sections[tag] > look.base. look.tech, when set, is a
non-colour technical prefix (denoise/sharpen) that always runs first. `drift` (0..1) adds a small
deterministic per-segment jitter on top, so even a single-look edit breathes
instead of sitting under one flat filter.

A look value is either a library name or a raw ffmpeg filter chain — anything
ffmpeg accepts is fair game, the library is a starting vocabulary, not a menu.
"""
import sys, os, json, subprocess, random, glob

# Each entry is a comma-joined ffmpeg filter chain, no leading/trailing comma.
# They are deliberately far apart in character — this is a palette, not presets.
LOOKS = {
    "neutral":
        "eq=contrast=1.06:saturation=1.05",
    # the legacy stadium-night montage look
    "teal_orange":
        "eq=contrast=1.12:saturation=1.14:brightness=-0.02:gamma=0.96,"
        "colorbalance=rs=-0.06:gs=-0.02:bs=0.08:rm=0.02:bm=-0.02:rh=0.10:gh=0.03:bh=-0.08,"
        "curves=master='0/0 0.10/0.03 0.5/0.5 0.9/0.97 1/1',vignette=angle=PI/6",
    "ember":
        "eq=contrast=1.20:saturation=1.10:gamma=0.92,"
        "colorbalance=rs=0.06:gs=-0.02:bs=-0.08:rm=0.05:bm=-0.05:rh=0.12:gh=0.02:bh=-0.10,"
        "curves=master='0/0 0.10/0.02 0.5/0.50 0.9/0.98 1/1',vignette=angle=PI/4.5",
    "ice":
        "eq=contrast=1.10:saturation=0.88:brightness=0.02,"
        "colorbalance=rs=-0.10:bs=0.14:rm=-0.04:bm=0.08:rh=-0.06:bh=0.10,"
        "curves=master='0/0.04 0.5/0.52 1/1'",
    "bleach":
        "eq=contrast=1.45:saturation=0.55:gamma=0.95,"
        "curves=master='0/0 0.15/0.06 0.5/0.55 0.85/0.96 1/1',unsharp=5:5:0.8:5:5:0",
    "neon":
        "eq=contrast=1.18:saturation=1.55:gamma=0.94,"
        "colorbalance=rs=0.10:bs=0.12:gm=-0.06:rh=0.08:bh=0.14,"
        "curves=master='0/0.02 0.5/0.52 1/0.98',vignette=angle=PI/4",
    "mono_steel":
        "hue=s=0.12,eq=contrast=1.32:gamma=0.94,"
        "colorbalance=bs=0.10:bm=0.05:bh=0.06,"
        "curves=master='0/0 0.12/0.04 0.5/0.52 1/1'",
    "sunbleach":
        "eq=contrast=0.95:saturation=0.82:brightness=0.04:gamma=1.06,"
        "colorbalance=rs=0.05:gs=0.04:bs=-0.06:rh=0.06:gh=0.05:bh=-0.04,"
        "curves=master='0/0.10 0.5/0.52 1/0.94'",
    "emerald":
        "eq=contrast=1.22:saturation=1.18:gamma=0.93,"
        "colorbalance=gs=0.08:bs=0.05:gm=0.04:gh=0.06:rh=-0.06,"
        "curves=master='0/0 0.5/0.51 1/1',vignette=angle=PI/5",
    "crimson":
        "eq=contrast=1.28:saturation=1.20:gamma=0.90,"
        "colorbalance=rs=0.12:gs=-0.05:bs=-0.05:rh=0.10:gh=-0.04:bh=-0.06,"
        "curves=master='0/0 0.14/0.04 0.5/0.50 1/0.99',vignette=angle=PI/4",
    "kodak":
        "eq=contrast=1.12:saturation=1.12:gamma=0.98,"
        "colorbalance=rs=0.03:bs=-0.03:rh=0.06:bh=-0.05,"
        "curves=r='0/0.02 0.5/0.52 1/1':b='0/0 0.5/0.48 1/0.97'",
    "nightdrive":
        "eq=contrast=1.35:saturation=1.05:brightness=-0.05:gamma=0.88,"
        "colorbalance=rs=-0.08:bs=0.16:bm=0.06:rh=0.08:bh=-0.04,"
        "curves=master='0/0 0.2/0.05 0.7/0.82 1/1',vignette=angle=PI/3.5",
    "vhs":
        "eq=contrast=1.05:saturation=1.25:gamma=1.02,gblur=sigma=0.6,noise=alls=8:allf=t,"
        "colorbalance=rs=0.04:bs=0.06:rh=-0.04:bh=0.05,"
        "curves=master='0/0.05 0.5/0.52 1/0.96'",
    "arctic":
        "eq=contrast=1.14:saturation=0.78:brightness=0.06,"
        "colorbalance=bs=0.12:bm=0.06:bh=0.08:rh=-0.05,"
        "curves=master='0/0.06 0.5/0.56 1/1'",
    "gold":
        "eq=contrast=1.16:saturation=1.22:gamma=0.95,"
        "colorbalance=rs=0.04:gs=0.02:bs=-0.10:rm=0.06:gm=0.03:bm=-0.07:rh=0.14:gh=0.07:bh=-0.12,"
        "curves=master='0/0 0.5/0.53 1/1',vignette=angle=PI/5",
    "inkwash":
        "eq=contrast=1.30:saturation=0.70:gamma=0.90,"
        "colorbalance=rs=-0.06:bs=0.10,"
        "curves=master='0/0 0.18/0.04 0.5/0.50 1/0.97'",
    "solar":
        "eq=contrast=1.40:saturation=1.35:brightness=0.03:gamma=0.90,"
        "curves=master='0/0 0.4/0.45 0.8/0.95 1/1',unsharp=5:5:0.6:5:5:0,vignette=angle=PI/4",
}

CHARACTER = {
    "neutral": "barely-there lift; a base to build on",
    "teal_orange": "stadium-night blockbuster; the old default",
    "ember": "amber highlights over red-black shadow",
    "ice": "cold blue-white, lifted blacks, low sat",
    "bleach": "bleach bypass — crushed, desaturated, harsh",
    "neon": "magenta/cyan overdrive, night-city",
    "mono_steel": "near-monochrome with a steel-blue cast",
    "sunbleach": "faded print, washed and yellowed",
    "emerald": "deep green-cyan, forest-heavy material",
    "crimson": "red-dominant and dark, violent",
    "kodak": "warm neutral film, gentle S-curve",
    "nightdrive": "very dark, blue shadow, hot speculars",
    "vhs": "soft chroma smear + grain, analogue",
    "arctic": "high-key white-blue, snow and sky",
    "gold": "golden hour, warm and rich",
    "inkwash": "desaturated cool, crushed blacks, cinema",
    "solar": "blown highlights, maximum punch",
}


def chain_for(name):
    """A look value is a library name or a raw ffmpeg chain — pass both through."""
    if not name:
        return None
    return LOOKS.get(name, name)


def _drift(i, amt):
    """Deterministic per-segment jitter so one look still breathes shot to shot."""
    r = random.Random((int(i) * 2654435761) % (2 ** 32))
    c = 1 + (r.random() - 0.5) * 0.18 * amt
    s = 1 + (r.random() - 0.5) * 0.34 * amt
    g = 1 + (r.random() - 0.5) * 0.12 * amt
    h = (r.random() - 0.5) * 12 * amt
    return f"eq=contrast={c:.3f}:saturation={s:.3f}:gamma={g:.3f},hue=h={h:.2f}"


def color_chain(cfg, seg=None):
    """Resolve the colour chain for one segment (or the edit's base if seg is None)."""
    look = cfg.get("look") or {}
    if seg is not None and seg.get("grade"):
        return seg["grade"]
    name = None
    if seg is not None:
        name = ((look.get("segments") or {}).get(str(seg.get("i")))
                or (look.get("sources") or {}).get(seg.get("src"))
                or (look.get("sections") or {}).get(seg.get("tag")))
    name = name or look.get("base")
    chain = chain_for(name) or cfg.get("grade") or LOOKS["neutral"]
    amt = float(look.get("drift") or 0)
    if amt > 0 and seg is not None:
        chain += "," + _drift(seg.get("i", 0), amt)
    # A style's technical base (denoise/sharpen/HDR pop) is not colour and always
    # runs first — swapping looks must never drop it.
    tech = look.get("tech")
    return f"{tech},{chain}" if tech else chain


def _cfg(root):
    return json.load(open(f"{root}/project.json"))


def _save(root, cfg):
    json.dump(cfg, open(f"{root}/project.json", "w"), indent=1)


def cmd_list():
    for k in LOOKS:
        print(f"  {k:14s} {CHARACTER.get(k, '')}")
    print("\nAny raw ffmpeg filter chain is also a valid look value.")


def cmd_show(root):
    cfg = _cfg(root)
    print(json.dumps(cfg.get("look") or {"base": None}, indent=1))
    if cfg.get("grade"):
        print("\n(legacy 'grade' present — used only where no look resolves)")


def _source_frame(root, want):
    """One real frame from this edit, preferring an assigned segment's in-point."""
    out = f"{root}/frames/_look_src.png"
    os.makedirs(f"{root}/frames", exist_ok=True)
    ap = f"{root}/assign.json"
    if os.path.exists(ap):
        segs = json.load(open(ap))["segments"]
        s = segs[want % len(segs)] if want is not None else next(
            (x for x in segs if x.get("hero")), segs[0])
        src, t = f"{root}/src/{s['src']}.mp4", s["in_tc"] + s["dur"] / 2
    else:
        vids = sorted(glob.glob(f"{root}/src/*.mp4"))
        if not vids:
            sys.exit("no assign.json and no src/*.mp4 — nothing to preview")
        src, t = vids[len(vids) // 2], 30.0
    subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", src,
                    "-frames:v", "1", "-vf", "scale=640:-2", "-y", out], check=True)
    return out


def cmd_preview(root, want, names):
    frame = _source_frame(root, want)
    tmp = f"{root}/frames/_looks"
    subprocess.run(["rm", "-rf", tmp]); os.makedirs(tmp, exist_ok=True)
    names = names or list(LOOKS)
    for i, n in enumerate(names):
        vf = f"{chain_for(n)},drawtext=text='{n}':fontsize=26:fontcolor=yellow:box=1:boxcolor=black:x=8:y=8"
        subprocess.run(["ffmpeg", "-v", "error", "-i", frame, "-vf", vf,
                        "-frames:v", "1", "-y", f"{tmp}/l_{i:02d}.png"], check=True)
    cols = 4 if len(names) > 6 else 3
    rows = (len(names) + cols - 1) // cols
    out = f"{root}/frames/looks.png"
    subprocess.run(["ffmpeg", "-v", "error", "-i", f"{tmp}/l_%02d.png",
                    "-vf", f"tile={cols}x{rows}", "-frames:v", "1", "-y", out], check=True)
    print(f"{len(names)} looks on one real frame → {out}\nRead it as an image, then: "
          f"look.py {root} set base=<name> [peak=<name> drop=<name> drift=0.3]")


def cmd_set(root, args):
    cfg = _cfg(root)
    look = cfg.get("look") or {}
    for a in args:
        if "=" not in a:
            sys.exit(f"bad arg {a!r} — expected key=value")
        k, v = a.split("=", 1)
        if k == "base":
            look["base"] = v
        elif k == "drift":
            look["drift"] = float(v)
        elif k.startswith("seg:"):
            look.setdefault("segments", {})[k[4:]] = v
        elif k.startswith("src:"):
            look.setdefault("sources", {})[k[4:]] = v
        elif k in ("drop", "peak", "build", "low"):
            look.setdefault("sections", {})[k] = v
        else:
            sys.exit(f"unknown key {k!r}")
    cfg["look"] = look
    _save(root, cfg)
    print(json.dumps(look, indent=1))


def cmd_shuffle(root, seed):
    r = random.Random(seed)
    pool = [k for k in LOOKS if k != "neutral"]
    base = r.choice(pool)
    rest = [k for k in pool if k != base]
    look = {"base": base,
            "sections": {"drop": r.choice(rest), "peak": base, "build": r.choice(rest)},
            "drift": round(r.uniform(0.15, 0.45), 2)}
    cfg = _cfg(root)
    cfg["look"] = look
    _save(root, cfg)
    print(json.dumps(look, indent=1))
    print("\nA roll is a starting point, not a decision — preview it and adjust.")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    root, cmd, rest = os.path.abspath(sys.argv[1]), sys.argv[2], sys.argv[3:]
    if cmd == "list":
        cmd_list()
    elif cmd == "show":
        cmd_show(root)
    elif cmd == "preview":
        want = int(rest[rest.index("--from") + 1]) if "--from" in rest else None
        names = (rest[rest.index("--looks") + 1].split(",")) if "--looks" in rest else None
        cmd_preview(root, want, names)
    elif cmd == "set":
        cmd_set(root, rest)
    elif cmd == "shuffle":
        cmd_shuffle(root, int(rest[rest.index("--seed") + 1]) if "--seed" in rest else None)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
