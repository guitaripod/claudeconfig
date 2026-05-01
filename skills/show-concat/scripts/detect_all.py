#!/usr/bin/env python3
"""
Detect intro/outro for every episode of a show and write a CSV.

Configure SHOW_ROOT and the references at the top.  REF_BY_SEASON maps
season number to a theme reference WAV — use one entry covering all seasons
if mastering is uniform, or per-season-group entries when audio drifts.

Multi-part episodes (filename ending in `- cd1.mkv`, `- cd2.mkv`, etc.):
  - cd1: cut intro, do NOT cut outro (continues into next part)
  - middle parts: do not cut intro or outro
  - last part: do not cut intro, cut outro

Output columns:
  season, episode, part, file, duration, intro_end, intro_score,
  outro_start, outro_black, content_dur, notes
"""
import csv
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from find_theme import find_theme  # type: ignore
from find_outro import find_outro_start  # type: ignore

# ────────── CONFIGURE ──────────
SHOW_ROOT = Path("/path/to/show")              # contains "Season N/" subdirs
THEME_DUR = 32.0                                 # seconds; tune to actual theme length
REFS_DIR = Path(__file__).parent / "refs"

def ref_for_season(season: int) -> Path:
    """Return the theme reference WAV appropriate for this season.
    Override when masterings differ across eras (e.g. NTSC vs PAL re-encodes)."""
    # Single-reference example (most shows):
    _ = season
    return REFS_DIR / "theme.wav"
    # Per-season-group example:
    # return REFS_DIR / ("theme_late.wav" if season >= 7 else "theme_early.wav")

OUT_CSV = Path(__file__).parent / "cuts.csv"
# ───────────────────────────────

EP_RE = re.compile(r"S(\d{2})E(\d{2})", re.IGNORECASE)
CD_RE = re.compile(r"-\s*cd(\d+)\.mkv$", re.IGNORECASE)


def list_episodes():
    rows = []
    for season_dir in sorted(SHOW_ROOT.glob("Season *")):
        for f in sorted(season_dir.glob("*.mkv")):
            m = EP_RE.search(f.name)
            if not m:
                continue
            s = int(m.group(1))
            e = int(m.group(2))
            cdm = CD_RE.search(f.name)
            cd = int(cdm.group(1)) if cdm else 0
            rows.append((s, e, cd, f))
    return rows


def group_by_episode(rows):
    g = {}
    for s, e, cd, f in rows:
        g.setdefault((s, e), []).append((cd, f))
    for k in g:
        g[k].sort(key=lambda x: x[0])
    return g


def detect_one(path, do_intro, do_outro, season):
    intro_end = ""
    intro_score = ""
    outro_start = ""
    outro_black = ""
    dur = 0.0
    if do_intro:
        offset, score = find_theme(str(path), str(ref_for_season(season)), 0.0, 600.0)
        if offset is not None:
            intro_end = f"{offset + THEME_DUR:.3f}"
            intro_score = f"{score:.4f}"
    if do_outro:
        cut, dur, bdur = find_outro_start(str(path), 120.0, 0.5)
        if cut is not None:
            outro_start = f"{cut:.3f}"
            outro_black = f"{bdur:.2f}"
    if not dur:
        try:
            dur = float(subprocess.check_output(
                ["ffprobe", "-v", "error",
                 "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", str(path)]).strip())
        except Exception:
            dur = 0.0
    return intro_end, intro_score, outro_start, outro_black, dur


def main():
    eps = list_episodes()
    grouped = group_by_episode(eps)
    print(f"found {len(eps)} files across {len(grouped)} episodes", file=sys.stderr)
    rows = []
    for (s, e), parts in sorted(grouped.items()):
        n_parts = len(parts)
        for i, (cd, path) in enumerate(parts):
            if n_parts == 1:
                do_intro, do_outro, notes = True, True, ""
            elif i == 0:
                do_intro, do_outro, notes = True, False, "multi-part:first"
            elif i == n_parts - 1:
                do_intro, do_outro, notes = False, True, "multi-part:last"
            else:
                do_intro, do_outro, notes = False, False, "multi-part:middle"

            print(f"S{s:02d}E{e:02d}{f' cd{cd}' if cd else ''} ({path.name})",
                  file=sys.stderr, flush=True)
            try:
                ie, isc, os_, ob, dur = detect_one(path, do_intro, do_outro, s)
            except Exception as exc:
                print(f"  ERROR: {exc}", file=sys.stderr)
                ie = isc = os_ = ob = ""
                dur = 0.0
                notes = (notes + " ERROR").strip()

            content_dur = ""
            if ie or os_:
                start = float(ie) if ie else 0.0
                end = float(os_) if os_ else dur
                content_dur = f"{max(0.0, end - start):.3f}"

            rows.append({
                "season": s, "episode": e, "part": cd,
                "file": str(path), "duration": f"{dur:.3f}",
                "intro_end": ie, "intro_score": isc,
                "outro_start": os_, "outro_black": ob,
                "content_dur": content_dur, "notes": notes,
            })

    with OUT_CSV.open("w", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT_CSV} with {len(rows)} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
