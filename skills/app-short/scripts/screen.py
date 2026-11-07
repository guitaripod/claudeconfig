#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "opencv-python-headless"]
# ///
"""Put real app footage on the green phone screen of a generated clip, at 1080x1920 and 30 fps.

    screen.py --clip ltx.mp4 --app take.mp4 --app-t0 4.5 [--app-speed 1.0] [--still] [--glow 0.06] --out broll.mp4

The screen is keyed per frame (bright, saturated green only, so a green sofa or forest stays), its four corners
are fitted and smoothed over time, and the app frame is warped onto them and shown only where the key says
screen, which keeps fingers, the Dynamic Island and rounded corners in front. Green spill around the phone is
neutralised. The app footage stays at full resolution, so the screen is the sharpest thing in the shot.
"""

import argparse
import itertools
import subprocess
import sys

import cv2
import numpy as np

W, H, FPS = 1080, 1920, 30


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clip", required=True)
    parser.add_argument("--app", required=True)
    parser.add_argument("--app-t0", type=float, default=0.0)
    parser.add_argument("--app-speed", type=float, default=1.0)
    parser.add_argument("--glow", type=float, default=0.03)
    parser.add_argument("--exposure", type=float, default=0.94)
    parser.add_argument("--blush", type=float, default=0.8, help="saturation kept in red skin tones (1 = untouched)")
    parser.add_argument("--grain", type=float, default=3.0, help="film grain on the scene, not the screen (0 = none)")
    parser.add_argument("--still", action="store_true", help="hold the app frame at --app-t0 for the whole clip")
    parser.add_argument("--out", required=True)
    parser.add_argument("--debug", default="")
    return parser.parse_args()


def reader(cmd: list[str], size: tuple[int, int]):
    """Yield RGB frames of the given size from an ffmpeg command writing rawvideo to stdout."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    assert proc.stdout is not None
    n = size[0] * size[1] * 3
    while True:
        data = proc.stdout.read(n)
        if len(data) < n:
            break
        yield np.frombuffer(data, np.uint8).reshape(size[1], size[0], 3)
    proc.kill()


def app_size(path: str) -> tuple[int, int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout
    w, h = out.strip().split(",")
    return int(w), int(h)


def green_alpha(frame: np.ndarray) -> np.ndarray:
    """Soft screen matte: how far green exceeds the other channels, gated to bright, saturated pixels."""
    f = frame.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    excess = g - np.maximum(r, b)
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    gate = (hsv[..., 1] > 90) & (hsv[..., 2] > 90) & (hsv[..., 0] > 35) & (hsv[..., 0] < 90)
    alpha = np.clip((excess - 25) / 45, 0, 1) * gate
    return alpha.astype(np.float32)


def loose_alpha(frame: np.ndarray) -> np.ndarray:
    """Ungated greenness for pixels already known to be on the screen, so its shaded edges key out too."""
    f = frame.astype(np.float32)
    excess = f[..., 1] - np.maximum(f[..., 0], f[..., 2])
    return np.clip((excess - 6) / 26, 0, 1).astype(np.float32)


def screen_region(alpha: np.ndarray, previous: np.ndarray | None) -> np.ndarray | None:
    """The largest keyed blob (nearest the previous screen when there was one), as a filled uint8 mask."""
    binary = (alpha > 0.5).astype(np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary)
    if count < 2:
        return None
    candidates = range(1, count)
    if previous is not None:
        cx, cy = previous.mean(axis=0)
        best = min(candidates, key=lambda i: (centroids[i][0] - cx) ** 2 + (centroids[i][1] - cy) ** 2 - stats[i, cv2.CC_STAT_AREA] * 4)
    else:
        best = max(candidates, key=lambda i: stats[i, cv2.CC_STAT_AREA])
    if stats[best, cv2.CC_STAT_AREA] < 2000:
        return None
    return (labels == best).astype(np.uint8)


def fit_quad(region: np.ndarray) -> np.ndarray:
    """Four screen corners (tl, tr, br, bl) from the blob's convex hull, pushed out past the rounded corners."""
    contours, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    hull = cv2.convexHull(max(contours, key=cv2.contourArea)).reshape(-1, 2).astype(np.float32)
    quad = None
    for eps in np.linspace(0.01, 0.08, 15):
        approx = cv2.approxPolyDP(hull, eps * cv2.arcLength(hull, True), True).reshape(-1, 2)
        if len(approx) == 4:
            quad = approx.astype(np.float32)
            break
    if quad is None:
        s, d = hull.sum(axis=1), hull[:, 0] - hull[:, 1]
        quad = np.array([hull[np.argmin(s)], hull[np.argmax(d)], hull[np.argmax(s)], hull[np.argmin(d)]], np.float32)
    center = quad.mean(axis=0)
    angles = np.arctan2(quad[:, 1] - center[1], quad[:, 0] - center[0])
    quad = quad[np.argsort(angles)]
    start = int(np.argmin(quad.sum(axis=1)))
    quad = np.roll(quad, -start, axis=0)
    return center + (quad - center) * 1.035


def smooth(quads: list[np.ndarray | None], radius: int = 3) -> list[np.ndarray]:
    """Average each frame's corners with its neighbours' to remove fitting jitter; gaps take the nearest fit."""
    known = [i for i, q in enumerate(quads) if q is not None]
    if not known:
        sys.exit("no green screen found in the clip")
    filled: list[np.ndarray] = [quads[min(known, key=lambda k: abs(k - i))] for i in range(len(quads))]  # type: ignore[misc]
    out = []
    for i in range(len(filled)):
        window = [filled[j] for j in range(max(0, i - radius), min(len(filled), i + radius + 1))]
        out.append(np.mean(window, axis=0))
    return out


def despill(frame: np.ndarray, near: np.ndarray) -> np.ndarray:
    """Pull green down to the larger of red and blue around the phone, where the screen's light spilled."""
    f = frame.astype(np.float32)
    limit = np.maximum(f[..., 0], f[..., 2])
    g = np.where(near > 0, np.minimum(f[..., 1], limit * 1.04 + 4), f[..., 1])
    f[..., 1] = g
    return np.clip(f, 0, 255).astype(np.uint8)


def neutralise_bezel(frame: np.ndarray, band: np.ndarray) -> np.ndarray:
    """Turn green or teal tints next to the screen (the bezel lit by the green) into neutral dark grey."""
    f = frame.astype(np.float32)
    tinted = (band > 0) & (f[..., 1] - f[..., 0] > 10)
    luma = f[..., 0] * 0.3 + f[..., 1] * 0.45 + f[..., 2] * 0.25
    f[tinted] = (luma[tinted] * 0.8)[:, None]
    return f.astype(np.uint8)


def calm_reds(frame: np.ndarray, keep: float) -> np.ndarray:
    """Pull saturation out of strong reds and magentas, where the models over-flush cheeks and noses."""
    if keep >= 1:
        return frame
    hsv = cv2.cvtColor(frame.astype(np.float32) / 255, cv2.COLOR_RGB2HSV)
    distance = np.minimum(hsv[..., 0], 360 - hsv[..., 0])
    weight = np.clip((28 - distance) / 16, 0, 1) * np.clip((hsv[..., 1] - 0.2) / 0.2, 0, 1)
    hsv[..., 1] *= 1 - (1 - keep) * weight
    return np.clip(cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB) * 255, 0, 255).astype(np.uint8)


def seat_screen(warped: np.ndarray, frame: np.ndarray, quad: np.ndarray, near: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    """Make the pasted screen sit in the shot: camera softness, exposure, the room's colour cast and a glass sheen."""
    screen = cv2.GaussianBlur(warped, (0, 0), 0.7).astype(np.float32) * args.exposure
    room = frame[near > 0].reshape(-1, 3).astype(np.float32).mean(axis=0)
    screen = screen * 0.93 + room * 0.07
    tl, tr, br, bl = quad
    span = np.linalg.norm(br - tl) + 1e-6
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    along = ((xx - tl[0]) * (br[0] - tl[0]) + (yy - tl[1]) * (br[1] - tl[1])) / (span * span)
    sheen = np.clip(1 - np.abs(along - 0.28) / 0.22, 0, 1) * 0.06
    screen = screen * (1 - sheen[..., None]) + 255 * sheen[..., None] + 255 * args.glow
    return screen


def main() -> None:
    args = parse_args()
    clip_cmd = ["ffmpeg", "-v", "error", "-i", args.clip, "-vf", f"fps={FPS},scale={W}:{H}:flags=lanczos",
                "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    frames = list(reader(clip_cmd, (W, H)))
    alphas = [green_alpha(f) for f in frames]
    quads, previous = [], None
    for alpha in alphas:
        region = screen_region(alpha, previous)
        quad = fit_quad(region) if region is not None else None
        quads.append(quad)
        previous = quad if quad is not None else previous
    corners = smooth(quads)

    aw, ah = app_size(args.app)
    app_cmd = ["ffmpeg", "-v", "error", "-i", args.app, "-vf",
               f"fps=60,trim=start={args.app_t0:.4f},setpts=(PTS-STARTPTS)/{args.app_speed},fps={FPS},"
               f"tpad=stop_mode=clone:stop=-1", "-frames:v", str(len(frames)), "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    app_frames = reader(app_cmd, (aw, ah))
    if args.still:
        app_frames = itertools.repeat(next(app_frames))
    source = np.array([[0, 0], [aw, 0], [aw, ah], [0, ah]], np.float32)

    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "12", "-preset", "medium",
                            "-pix_fmt", "yuv420p", args.out], stdin=subprocess.PIPE)
    assert enc.stdin is not None
    last_app = None
    rng = np.random.default_rng(7)
    for i, (frame, alpha, quad) in enumerate(zip(frames, alphas, corners)):
        app = next(app_frames, last_app)
        last_app = app
        matrix = cv2.getPerspectiveTransform(source, quad.astype(np.float32))
        warped = cv2.warpPerspective(app, matrix, (W, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
        inside = np.zeros((H, W), np.uint8)
        cv2.fillConvexPoly(inside, quad.astype(np.int32), 1)
        band = cv2.dilate(inside, np.ones((15, 15), np.uint8)).astype(np.float32)
        matte = cv2.GaussianBlur(np.maximum(alpha, loose_alpha(frame)) * band, (0, 0), 0.8)[..., None]
        near = cv2.dilate(inside, np.ones((81, 81), np.uint8))
        clean = neutralise_bezel(despill(calm_reds(frame, args.blush), near), cv2.dilate(inside, np.ones((31, 31), np.uint8)))
        lit = seat_screen(warped, clean, quad, near - inside, args)
        grain = rng.normal(0, args.grain, (H, W, 1)).astype(np.float32) if args.grain else 0
        out = (clean.astype(np.float32) + grain) * (1 - matte) + lit * matte
        out = np.clip(out, 0, 255).astype(np.uint8)
        enc.stdin.write(out.tobytes())
        if args.debug and i in (0, len(frames) // 2, len(frames) - 1):
            debug = out.copy()
            cv2.polylines(debug, [quad.astype(np.int32)], True, (255, 0, 0), 2)
            cv2.imwrite(f"{args.debug}_{i:03d}.png", cv2.cvtColor(debug, cv2.COLOR_RGB2BGR))
    enc.stdin.close()
    if enc.wait() != 0:
        sys.exit("encode failed")
    print(args.out)


if __name__ == "__main__":
    main()
