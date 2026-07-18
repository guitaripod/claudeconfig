#!/usr/bin/env python3
"""restore.py <workdir> --segs 0,5,12 | --heroes — opt-in SeedVR2 restoration of
chosen segments' source windows before the full render. Extracts each segment's
exact render input window (same fast-seek -ss, so pinned in_tcs stay valid),
runs SeedVR2 3B fp8 on it at native resolution (~2.7s/frame on the RTX 5080;
needs ~10GB free VRAM), writes src/<id>__srNNN.mp4 and repoints the segment at
it (in_tc rebased to 0). assign.json is backed up to assign.json.presr; re-run
render.py afterwards. Re-running assign_clips.py discards the repointing, like
any hand-patch. HYPE_SEEDVR2 overrides the tool root."""
import sys, json, os, shutil, subprocess

ROOT = os.path.abspath(sys.argv[1])
CFG = json.load(open(f"{ROOT}/project.json"))
SVR = os.environ.get("HYPE_SEEDVR2", "/mnt/games-nvme-gen4/tools/seedvr2")
PY = f"{SVR}/.venv/bin/python"
if not os.path.exists(PY):
    sys.exit(f"SeedVR2 not found at {SVR} (set HYPE_SEEDVR2)")

ASSIGN = json.load(open(f"{ROOT}/assign.json"))
segs = ASSIGN["segments"]
if "--heroes" in sys.argv:
    targets = [s["i"] for s in segs if s.get("hero") or s.get("clip_id", 0) < 0]
elif "--segs" in sys.argv:
    targets = [int(x) for x in sys.argv[sys.argv.index("--segs") + 1].split(",")]
else:
    sys.exit("pass --segs i,j,k or --heroes")


def probe(path, entries):
    return subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", f"stream={entries}", "-of", "csv=p=0", path],
        capture_output=True, text=True).stdout.strip()


def restore_one(s):
    src = f"{ROOT}/src/{s['src']}.mp4"
    if "__sr" in s["src"]:
        return "already restored"
    inp = round(s["dur"] * s.get("speed", 1.0) + 1.2, 3)
    win = f"{ROOT}/work/sr_in_{s['i']:03d}.mp4"
    name = f"{s['src']}__sr{s['i']:03d}"
    out = f"{ROOT}/src/{name}.mp4"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", str(s["in_tc"]), "-t", str(inp), "-i", src,
        "-c:v", "libx264", "-crf", "10", "-preset", "fast", "-an", win],
        capture_output=True, text=True)
    if r.returncode != 0:
        return f"window extract failed: {r.stderr.strip()[-120:]}"
    w, h = probe(win, "width,height").split(",")
    r = subprocess.run([PY, f"{SVR}/inference_cli.py", win, "--output", out,
        "--resolution", str(min(int(w), int(h))), "--batch_size", "5",
        "--vae_encode_tiled", "--vae_decode_tiled"],
        capture_output=True, text=True, cwd=SVR)
    if r.returncode != 0 or not os.path.exists(out):
        return f"seedvr2 failed: {(r.stderr or r.stdout).strip()[-160:]}"
    n_in, n_out = (int(probe(p, "nb_frames") or 0) for p in (win, out))
    if n_out < n_in * 0.9:
        os.remove(out); return f"frame loss {n_out}/{n_in}, kept original"
    s["src"], s["in_tc"] = name, 0.0
    os.remove(win)
    return f"ok → src/{name}.mp4 ({n_out}f)"


shutil.copy(f"{ROOT}/assign.json", f"{ROOT}/assign.json.presr")
changed = 0
for s in segs:
    if s["i"] not in targets:
        continue
    msg = restore_one(s)
    changed += msg.startswith("ok")
    print(f"seg {s['i']:3d}  {msg}")
json.dump(ASSIGN, open(f"{ROOT}/assign.json", "w"), indent=1)
print(f"\n{changed} segment(s) restored — re-run render.py (both orientations)")
