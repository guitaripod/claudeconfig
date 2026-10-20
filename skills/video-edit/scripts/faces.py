#!/usr/bin/env python3
"""faces.py <workdir> [--fps 2] [--width 480] — subject pass.

Decodes every source at a low frame rate, detects the largest face per frame
with YuNet (OpenCV's DNN detector; Haar cascades are gone in OpenCV 5), and
writes:
  faces.npz     per source: [area, cx, cy, sharpness, count] per sampled frame
  scenes.json   per clip: face_max, face_mean, face_cx, face_cy, face_sharp,
                face_frames

The face is a ranking signal, not an identity check: it tells assign_clips which
window actually contains the subject and where to centre a crop. Presets opt in
with scan.subject = "face" (hard filter) or "auto" (filter only when enough
clips have a face, so sports footage is not gutted by missed detections).
"""
import argparse
import glob
import json
import os
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.environ.get("VIDEO_EDIT_FACE_MODEL") or os.path.join(
    os.path.dirname(HERE), "models", "face_detection_yunet_2026may.onnx")


def detector(width, height):
    if not os.path.exists(MODEL):
        sys.exit(f"face model missing: {MODEL}\n"
                 "download face_detection_yunet_2026may.onnx from opencv_zoo/models/"
                 "face_detection_yunet into skills/video-edit/models/")
    det = cv2.FaceDetectorYN_create(MODEL, "", (width, height), 0.6, 0.3, 5000)
    det.setInputSize((width, height))
    return det


def decode(path, fps, width):
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
        capture_output=True, text=True).stdout.strip()
    ow, oh = (int(x) for x in probe.split(",")[:2])
    h = int(round(oh * width / ow / 2.0)) * 2
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path,
        "-vf", f"fps={fps},scale={width}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
        capture_output=True).stdout
    n = len(raw) // (width * h * 3)
    if n < 1:
        return np.zeros((1, h, width, 3), np.uint8), (width, h)
    return np.frombuffer(raw[:n * width * h * 3], np.uint8).reshape(n, h, width, 3), (width, h)


def largest(det, frame):
    _, faces = det.detect(frame)
    if faces is None or not len(faces):
        return None, 0
    k = int(np.argmax([f[2] * f[3] for f in faces]))
    x, y, w, h = (float(v) for v in faces[k][:4])
    return (x, y, w, h), len(faces)


def track(frames, W, H):
    det = detector(W, H)
    out = np.zeros((len(frames), 5), np.float32)
    for k, frame in enumerate(frames):
        box, count = largest(det, frame)
        if box is None:
            continue
        x, y, w, h = box
        roi = cv2.cvtColor(frame[max(int(y), 0):int(y + h), max(int(x), 0):int(x + w)],
                           cv2.COLOR_BGR2GRAY)
        sharp = float(cv2.Laplacian(roi, cv2.CV_64F).var()) if roi.size else 0.0
        out[k] = [w * h / float(W * H), (x + w / 2) / W, (y + h / 2) / H, sharp, count]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--fps", type=float, default=2.0)
    ap.add_argument("--width", type=int, default=480)
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    scenes = json.load(open(f"{root}/scenes.json"))
    by = {}
    for c in scenes["clips"]:
        by.setdefault(c["src"], []).append(c)
    tracks, det = {}, 0
    for path in sorted(glob.glob(f"{root}/src/*.mp4")):
        sid = os.path.splitext(os.path.basename(path))[0]
        if sid not in by:
            continue
        frames, (W, H) = decode(path, a.fps, a.width)
        tr = track(frames, W, H)
        tracks[sid] = tr
        n_face = int((tr[:, 0] > 0).sum())
        det += n_face
        for c in by[sid]:
            i0 = int(c["start"] * a.fps)
            i1 = max(int(c["end"] * a.fps), i0 + 1)
            seg = tr[i0:i1]
            if not len(seg):
                seg = tr[max(i0 - 1, 0):i0 + 1]
            ar = seg[:, 0]
            wsum = ar.sum()
            c["face_max"] = round(float(ar.max()), 5)
            c["face_mean"] = round(float(ar.mean()), 5)
            c["face_cx"] = round(float((seg[:, 1] * ar).sum() / wsum), 4) if wsum else 0.5
            c["face_cy"] = round(float((seg[:, 2] * ar).sum() / wsum), 4) if wsum else 0.5
            c["face_sharp"] = round(float(seg[:, 3].max()), 2)
            c["face_frames"] = round(float((ar > 0).mean()), 3)
        print(f"  {sid[:24]:24s} {n_face:4d}/{len(tr):4d} frames with a face")
    np.savez(f"{root}/faces.npz", cfps=np.array([a.fps]), **tracks)
    json.dump(scenes, open(f"{root}/scenes.json", "w"), indent=1)
    clips = scenes["clips"]
    have = sum(1 for c in clips if c["face_max"] > 0)
    print(f"{det} face frames · {have}/{len(clips)} clips with a face → faces.npz")
    if have == 0:
        print("no faces found: use scan.subject = \"none\" (or check the footage)")


if __name__ == "__main__":
    main()
