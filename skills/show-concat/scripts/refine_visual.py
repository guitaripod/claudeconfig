#!/usr/bin/env python3
"""
Override low-confidence audio detections with frame-template visual matches.

Reads cuts.csv, runs find_visual on rows whose intro_score is below
THRESHOLD (or whose offset disagrees substantially with a separate
candidate), and writes results back to cuts.csv.

Configure SCOPE_FILTER, THRESHOLD, and REF_IMAGE for the show at hand.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from find_visual import find_best, load_thumb  # type: ignore

# ────────── CONFIGURE ──────────
ROOT = Path(__file__).parent
CSV_PATH = ROOT / "cuts.csv"
REF_IMAGE = ROOT / "refs" / "title_frame.jpg"
THEME_DUR = 32.0          # add to match offset to get intro_end
AUDIO_THRESHOLD = 0.55    # below this, prefer the visual match
DISAGREE_SECONDS = 5.0    # if visual disagrees with audio by ≥ this, prefer visual

def in_scope(row) -> bool:
    """Limit visual refinement to specific seasons / files. Default: every row."""
    _ = row
    # Example: only late seasons (where audio mastering differs):
    # return int(row["season"]) >= 7
    return True
# ───────────────────────────────


def main():
    ref = load_thumb(REF_IMAGE)
    rows = list(csv.DictReader(open(CSV_PATH)))
    refined = 0
    for r in rows:
        if not in_scope(r):
            continue
        if r["notes"] in ("multi-part:middle", "multi-part:last"):
            continue
        path = Path(r["file"])
        prev_ie = float(r["intro_end"]) if r["intro_end"] else None
        prev_score = float(r["intro_score"]) if r["intro_score"] else 0.0
        t, mae = find_best(path, ref, dur=600.0, fps=2.0)
        if t is None:
            continue
        sim = max(0.0, 1.0 - mae / 255.0)
        new_ie = t + THEME_DUR
        marker = ""
        if sim < 0.80:
            marker = "vis:weak"
        elif (prev_ie is None
              or abs(new_ie - prev_ie) >= DISAGREE_SECONDS
              or prev_score < AUDIO_THRESHOLD):
            r["intro_end"] = f"{new_ie:.3f}"
            r["intro_score"] = f"{sim:.4f}"
            marker = "vis:override"
            refined += 1
            try:
                dur = float(r["duration"])
            except Exception:
                dur = 0.0
            os_ = float(r["outro_start"]) if r["outro_start"] else dur
            r["content_dur"] = f"{max(0.0, os_ - new_ie):.3f}"
        else:
            marker = "vis:ok"
        if marker:
            r["notes"] = f"{r['notes']} {marker}".strip()
        print(f"S{int(r['season']):02d}E{int(r['episode']):02d} cd{r['part']}: "
              f"prev={prev_ie} → vis@{t:.2f} sim={sim:.3f} {marker}",
              file=sys.stderr, flush=True)

    with CSV_PATH.open("w", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"refined {refined} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
