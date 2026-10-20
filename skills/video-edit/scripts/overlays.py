#!/usr/bin/env python3
"""overlays.py — drawtext chain for project.json "overlays".

Each overlay is {"text", "start", "end", "style"}; styles are title,
lower_third, caption and score. The chain is applied once to the concatenated
video, so a title or caption can span cuts. Positions and sizes are relative to
the output canvas, which makes the same overlay work at draft and full res.
"""

import os

STYLES = {
    "title":       {"size": 10, "y": 0.50, "box": "black@0.55", "x": "center", "border": 18},
    "lower_third": {"size": 32, "y": 0.78, "box": "black@0.55", "x": 0.06, "border": 12},
    "caption":     {"size": 34, "y": 0.86, "box": "black@0.60", "x": "center", "border": 10},
    "score":       {"size": 38, "y": 0.04, "box": "black@0.45", "x": 0.70, "border": 8},
}



def chain(cfg, w, h, textdir):
    items = cfg.get("overlays") or []
    if not items:
        return ""
    os.makedirs(textdir, exist_ok=True)
    parts = []
    for k, o in enumerate(items):
        style = STYLES.get(o.get("style", "caption"), STYLES["caption"])
        size = max(12, int(h / style["size"]))
        x = "(w-text_w)/2" if style["x"] == "center" else f"w*{style['x']}"
        y = f"h*{style['y']}"
        if o.get("style") == "title":
            y = "(h-text_h)/2"
        start, end = float(o.get("start", 0)), float(o.get("end", 1e9))
        path = os.path.join(textdir, f"overlay_{k:02d}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(o["text"]).replace("\n", " "))
        parts.append(
            f"drawtext=textfile='{path}':expansion=none:fontsize={size}:fontcolor=white:"
            f"x={x}:y={y}:box=1:boxcolor={style['box']}:boxborderw={style['border']}:"
            f"enable='between(t,{start:.3f},{end:.3f})'")
    return ",".join(parts)
