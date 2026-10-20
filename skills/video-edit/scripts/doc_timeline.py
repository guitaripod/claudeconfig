#!/usr/bin/env python3
"""doc_timeline.py <workdir> --aroll <srcid> [--srt cues.srt] [--every 6]
                   [--chunk 8] [--broll-every 2] [--lower-third "Name, role"]

The documentary/talking-head producer. The A-roll's audio is the master track, so
A-roll cuts are pinned to their absolute timeline position (in_tc = cut start) and
the video stays in sync while B-roll covers selected chunks. Cues come from an SRT
(no ASR dependency) or fixed --every-second chunks. Captions and the optional
lower third are written to project.json overlays for the render pass.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preset
import timeline

STAMP = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")


def stamp(g):
    h, m, s, ms = (int(x) for x in g)
    return h * 3600 + m * 60 + s + ms / 1000.0


def parse_srt(path):
    cues = []
    for block in re.split(r"\n\s*\n", open(path, encoding="utf-8").read().strip()):
        lines = [x.strip() for x in block.splitlines() if x.strip()]
        for i, line in enumerate(lines):
            m = STAMP.search(line)
            if m:
                text = " ".join(lines[i + 1:])
                text = re.sub(r"<[^>]+>", "", text).strip()
                cues.append({"start": stamp(m.groups()[:4]),
                             "end": stamp(m.groups()[4:]), "text": text})
                break
    if not cues:
        sys.exit("no cues found in the SRT")
    return sorted(cues, key=lambda c: c["start"])


def chunk_cues(cues, span):
    chunks = []
    for c in cues:
        if chunks and c["start"] - chunks[-1]["start"] < span:
            chunks[-1]["end"] = max(chunks[-1]["end"], c["end"])
            chunks[-1]["text"] = (chunks[-1]["text"] + " " + c["text"]).strip()
        else:
            chunks.append(dict(c))
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--aroll", required=True)
    ap.add_argument("--srt")
    ap.add_argument("--every", type=float, default=6.0)
    ap.add_argument("--chunk", type=float, default=None)
    ap.add_argument("--broll-every", type=int, default=None,
                    help="every Nth chunk is B-roll; 0 = none")
    ap.add_argument("--lower-third")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    cfg, p = preset.load(root)
    pacing = p.get("pacing") or {}
    if a.chunk is None:
        a.chunk = float(pacing.get("chunk_s", 8.0))
    if a.broll_every is None:
        a.broll_every = int(pacing.get("broll_every", 0))
    if p.get("timeline") != "doc":
        sys.exit(f'preset "{p["name"]}" declares timeline "{p.get("timeline")}" — '
                 "use a doc preset (documentary / talking-head)")
    dur, fps = cfg["dur"], cfg["fps"]
    if a.srt:
        chunks = chunk_cues(parse_srt(a.srt), a.chunk)
    else:
        chunks = [{"start": t, "end": min(t + a.every, dur), "text": ""}
                  for t in [i * a.every for i in range(int(dur / a.every) + 1)]
                  if t < dur]
    chunks = [c for c in chunks if c["end"] - c["start"] >= 0.5]

    scenes = json.load(open(f"{root}/scenes.json"))["clips"]
    bpool = []
    if a.broll_every:
        bpool = [c for c in scenes if c["src"] != a.aroll and not c.get("dark")
                 and c["dur"] >= 1.5]
        if bpool:
            bpool = sorted({c["src"]: c for c in bpool}.values(), key=lambda c: c["src"])
        else:
            print("no B-roll pool — staying on A-roll")

    cuts, t, bi = [], 0.0, 0

    def add(start, end, src, pin=None):
        if end - start < 0.12:
            return
        cuts.append({"i": len(cuts), "start": round(start, 4), "end": round(end, 4),
                     "dur": round(end - start, 4), "tag": "body", "hero": False,
                     "src": src, **({"in_tc": round(pin, 4)} if pin is not None else {})})

    for c in chunks:
        if c["start"] > t + 0.05:
            add(t, c["start"], a.aroll, t)
        start, end = max(c["start"], t), min(c["end"], dur)
        use_b = bpool and a.broll_every and (bi % a.broll_every == 1)
        if use_b:
            add(start, end, bpool[bi % len(bpool)]["src"])
        else:
            add(start, end, a.aroll, start)
        t = end
        bi += 1
        if t >= dur - 1e-6:
            break
    if t < dur - 1e-6:
        if dur - t < 0.6 and cuts:
            cuts[-1]["end"] = round(dur, 4)
            cuts[-1]["dur"] = round(cuts[-1]["end"] - cuts[-1]["start"], 4)
        else:
            add(t, dur, a.aroll, t)
    cuts[0]["start"], cuts[-1]["end"] = 0.0, dur
    cuts[0]["dur"] = round(cuts[0]["end"] - cuts[0]["start"], 4)
    cuts[-1]["dur"] = round(cuts[-1]["end"] - cuts[-1]["start"], 4)

    overlays = []
    for c in chunks:
        if not c["text"]:
            continue
        text = c["text"] if len(c["text"]) <= 84 else c["text"][:81].rstrip() + "…"
        overlays.append({"text": text, "start": round(c["start"], 3),
                         "end": round(min(c["end"], dur), 3), "style": "caption"})
    l3 = a.lower_third or (cfg.get("doc") or {}).get("lower_third")
    if l3:
        overlays.append({"text": l3, "start": 1.0, "end": min(6.0, dur),
                         "style": "lower_third"})
    cfg["overlays"] = overlays
    json.dump(cfg, open(f"{root}/project.json", "w"), indent=1)

    tl = {"producer": "doc", "preset": p["name"], "bpm": None,
          "beats": [], "downbeats": [], "drops": [], "onsets": [],
          "sections": [{"start": 0.0, "end": dur, "label": "body"}],
          "cutlist": cuts,
          "meta": {"duration": dur, "fps": fps,
                   "qc": {"n_cuts": len(cuts), "beat_count": 0, "hero_times": [],
                          "drop_confidence": "none"}}}
    timeline.check(tl)
    timeline.write(root, tl)
    nb = sum(1 for c in cuts if c.get("src") != a.aroll)
    print(f"{len(cuts)} cuts ({nb} B-roll) · {len(overlays)} overlays → timeline.json "
          f"(producer=doc, A-roll={a.aroll})")


if __name__ == "__main__":
    main()
