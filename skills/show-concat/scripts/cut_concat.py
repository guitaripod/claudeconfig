#!/usr/bin/env python3
"""
Phase 6: cut intro/outro from each episode (using PAL→NTSC conversions where
applicable) and concatenate into one master mkv.

Inputs:
  cuts.csv   - intro/outro plan from detect_all.py
  pal/       - PAL→NTSC converted versions of the late-season files (if any)

Process per episode (or multi-part group):
  - Replace late-season paths with the converted file in pal/ when present
  - For each part, slice (intro_end, outro_start) with ffmpeg -c copy
  - Append all slices to a single concat list, then ffmpeg concat -c copy

Output:
  out/show_complete.mkv

Notes:
  • Cuts are keyframe-aligned (±1 s) because we use -c copy for losslessness.
  • Codec uniformity is required for concat to succeed.  If the test concat
    in Phase 7 fails, do a pre-pass that re-encodes the minority encoder
    group to match the majority.
"""
import csv
import re
import subprocess
import sys
from pathlib import Path

# ────────── CONFIGURE ──────────
ROOT = Path(__file__).parent
CSV_PATH = ROOT / "cuts.csv"
WORK = Path("/path/to/output")
PAL_DIR = WORK / "pal"
SEG_DIR = WORK / "segments"
OUT_DIR = WORK / "out"
FINAL = OUT_DIR / "show_complete.mkv"

def needs_pal_substitution(season: int) -> bool:
    """Return True if this season's source files were re-encoded into PAL_DIR."""
    return season >= 7
# ───────────────────────────────

CD_RE = re.compile(r"-\s*cd(\d+)\.mkv$", re.IGNORECASE)


def converted_path(orig: Path) -> Path:
    """Map a re-encoded source to its converted counterpart in pal/."""
    return PAL_DIR / orig.name


def cut_segment(src: Path, start: float, end: float, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-ss", f"{start:.3f}",
        "-to", f"{end:.3f}",
        "-i", str(src),
        "-c", "copy",
        "-map", "0:v:0", "-map", "0:a:0",
        "-avoid_negative_ts", "make_zero",
        str(out),
    ]
    subprocess.run(cmd, check=True)


def main():
    SEG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(CSV_PATH)))

    grouped = {}
    for r in rows:
        key = (int(r["season"]), int(r["episode"]))
        grouped.setdefault(key, []).append(r)
    for k in grouped:
        grouped[k].sort(key=lambda r: int(r["part"]))

    concat_lines = []
    for (s, e), parts in sorted(grouped.items()):
        for i, r in enumerate(parts):
            n = len(parts)
            src = Path(r["file"])
            if needs_pal_substitution(s):
                src = converted_path(src)
                if not src.exists():
                    sys.exit(f"missing converted file: {src}")
            dur = float(r["duration"])
            if n == 1:
                start = float(r["intro_end"]) if r["intro_end"] else 0.0
                stop = float(r["outro_start"]) if r["outro_start"] else dur
            elif i == 0:
                start = float(r["intro_end"]) if r["intro_end"] else 0.0
                stop = dur
            elif i == n - 1:
                start = 0.0
                stop = float(r["outro_start"]) if r["outro_start"] else dur
            else:
                start = 0.0
                stop = dur
            tag = f"s{s:02d}e{e:02d}"
            if n > 1:
                tag += f"_cd{r['part']}"
            seg = SEG_DIR / f"{tag}.mkv"
            if not seg.exists() or seg.stat().st_size == 0:
                print(f"cut {tag}: {start:.1f} → {stop:.1f}", flush=True)
                cut_segment(src, start, stop, seg)
            else:
                print(f"skip {tag} (exists)", flush=True)
            concat_lines.append(f"file '{seg.resolve()}'")

    list_path = ROOT / "concat.txt"
    list_path.write_text("\n".join(concat_lines) + "\n")
    print(f"concat list: {list_path} ({len(concat_lines)} entries)")
    cmd = [
        "ffmpeg", "-hide_banner", "-nostdin", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_path),
        "-c", "copy",
        str(FINAL),
    ]
    print("running concat …", flush=True)
    subprocess.run(cmd, check=True)
    print(f"DONE: {FINAL}")


if __name__ == "__main__":
    main()
