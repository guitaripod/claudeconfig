#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "opencv-python-headless"]
# ///
"""Put real app footage on the green phone screen of a generated clip, at 1080x1920 and 30 fps.

    screen.py --clip ltx.mp4 --app take.mp4 --app-t0 4.5 [--app-speed 1.0] [--still | --hold-at 1.2] --out broll.mp4

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
    parser.add_argument("--exposure", type=float, default=1.0, help="UI white relative to the scene's bright tones around the phone")
    parser.add_argument("--saturation", type=float, default=0.88)
    parser.add_argument("--reflection", type=float, default=0.18)
    parser.add_argument("--plate-width", type=int, default=768, help="native width of the generated clip")
    parser.add_argument("--lift", type=float, default=0.025, help="UI black lifted to this fraction of white")
    parser.add_argument("--spill", type=float, default=0.34, help="strength of the screen's glow on fingers and face")
    parser.add_argument("--hold-at", type=float, default=None, help="play the app from --app-t0 for this many seconds, then hold")
    parser.add_argument("--blush", type=float, default=0.8, help="saturation kept in red skin tones (1 = untouched)")
    parser.add_argument("--grain", type=float, default=3.0, help="sensor grain over the whole frame, screen included (0 = none)")
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
    """Four screen corners (tl, tr, br, bl): a line fitted to each straight edge, intersected with its neighbours.

    The keyed screen has rounded corners and a Dynamic Island notch, so a polygon fit lands on the curves and skews
    the quad. Instead the hull's boundary is split into its four sides (away from the corner arcs), each side gets a
    robust line fit, and the corners are where those lines meet, which is exact under perspective.
    """
    contours, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    hull = cv2.convexHull(max(contours, key=cv2.contourArea))
    filled = np.zeros_like(region)
    cv2.fillConvexPoly(filled, hull, 1)
    contours, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    points = max(contours, key=cv2.contourArea).reshape(-1, 2).astype(np.float32)
    box = order_corners(cv2.boxPoints(cv2.minAreaRect(points)).astype(np.float32))
    short = min(np.linalg.norm(box[1] - box[0]), np.linalg.norm(box[3] - box[0]))
    keep_out = short * 0.2
    lines = []
    for i in range(4):
        a, b = box[i], box[(i + 1) % 4]
        direction = (b - a) / np.linalg.norm(b - a)
        normal = np.array([-direction[1], direction[0]])
        along = (points - a) @ direction
        offset = np.abs((points - a) @ normal)
        side = points[(offset < short * 0.12) & (along > keep_out) & (along < np.linalg.norm(b - a) - keep_out)]
        if len(side) < 10:
            return box
        vx, vy, x0, y0 = cv2.fitLine(side, cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
        lines.append((np.array([x0, y0]), np.array([vx, vy])))
    corners = [intersect(lines[(i + 3) % 4], lines[i]) for i in range(4)]
    return order_corners(np.array(corners, np.float32))


def intersect(first: tuple[np.ndarray, np.ndarray], second: tuple[np.ndarray, np.ndarray]) -> np.ndarray:
    (p, r), (q, s) = first, second
    cross = r[0] * s[1] - r[1] * s[0]
    t = ((q - p)[0] * s[1] - (q - p)[1] * s[0]) / (cross + 1e-9)
    return p + t * r


def order_corners(quad: np.ndarray) -> np.ndarray:
    """Sort four points into tl, tr, br, bl."""
    center = quad.mean(axis=0)
    quad = quad[np.argsort(np.arctan2(quad[:, 1] - center[1], quad[:, 0] - center[0]))]
    return np.roll(quad, -int(np.argmin(quad.sum(axis=1))), axis=0)


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


def luma(f: np.ndarray) -> np.ndarray:
    return f[..., 0] * 0.2126 + f[..., 1] * 0.7152 + f[..., 2] * 0.0722


def masked_blur(values: np.ndarray, mask: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian blur of values inside mask only (normalised convolution), so the bezel doesn't bleed in."""
    weight = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigma)
    return cv2.GaussianBlur(values * mask, (0, 0), sigma) / np.maximum(weight, 1e-4)


def despill(frame: np.ndarray, near: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pull green down around the phone where the screen's light spilled; also return how much was removed."""
    f = frame.astype(np.float32)
    limit = np.maximum(f[..., 0], f[..., 2]) * 1.04 + 4
    removed = np.where(near > 0, np.clip(f[..., 1] - limit, 0, None), 0)
    f[..., 1] -= removed
    return np.clip(f, 0, 255), removed


def neutralise_bezel(f: np.ndarray, band: np.ndarray) -> np.ndarray:
    """Turn green or teal tints next to the screen (the bezel lit by the green) into neutral dark grey."""
    tinted = (band > 0) & (f[..., 1] - f[..., 0] > 10)
    gray = f[..., 0] * 0.3 + f[..., 1] * 0.45 + f[..., 2] * 0.25
    f[tinted] = (gray[tinted] * 0.8)[:, None]
    return f


def calm_reds(frame: np.ndarray, keep: float) -> np.ndarray:
    """Pull saturation out of strong reds, and harder out of magentas, where the models over-flush cheeks and noses."""
    if keep >= 1:
        return frame
    hsv = cv2.cvtColor(frame.astype(np.float32) / 255, cv2.COLOR_RGB2HSV)
    distance = np.minimum(hsv[..., 0], 360 - hsv[..., 0])
    saturated = np.clip((hsv[..., 1] - 0.2) / 0.2, 0, 1)
    red = np.clip((28 - distance) / 16, 0, 1) * saturated
    magenta = np.clip((40 - np.abs(hsv[..., 0] - 325)) / 20, 0, 1) * saturated
    hsv[..., 1] *= (1 - (1 - keep) * red) * (1 - 0.5 * magenta)
    return np.clip(cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB) * 255, 0, 255).astype(np.uint8)


def plate_light(frame: np.ndarray, inside: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The light the generated scene put on the green glass: low-frequency shading, and reflections (whitening).

    A lit green screen in the plate already carries the shot's falloff, glare and reflected room light; dividing
    its luma by its median gives a shading pass, and the rise of min(R, B) above its median marks where the glass
    reflected something bright. Both get carried onto the app so it sits under the same light.
    """
    f = frame.astype(np.float32)
    core = cv2.erode(inside, np.ones((13, 13), np.uint8)).astype(np.float32)
    if core.sum() < 500:
        return np.ones(inside.shape, np.float32), np.zeros(inside.shape, np.float32)
    y = luma(f)
    shade = masked_blur(y / max(float(np.median(y[core > 0])), 1.0), core, 18)
    shade = np.where(inside > 0, np.clip(shade, 0.72, 1.28), 1.0).astype(np.float32)
    white = np.minimum(f[..., 0], f[..., 2])
    spec = np.clip(white - float(np.median(white[core > 0])) - 6, 0, None) * inside
    return shade, cv2.GaussianBlur(spec.astype(np.float32), (0, 0), 1.5)


def seat_screen(warped: np.ndarray, inside: np.ndarray, quad: np.ndarray, frame: np.ndarray, shade: np.ndarray,
                spec: np.ndarray, room: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    """Make the app look filmed on that phone.

    - Same camera: resample the screen down to the generated plate's own resolution and back, so it is exactly as
      soft as everything else, then lift its blacks.
    - Same exposure: scale the UI's whites to the brightness of the scene around the phone, not to full white.
    - Same light: white-balance toward the room, take some saturation out, apply the plate's shading and
      reflections, and lay a soft, blurred, mirrored reflection of the surroundings across the glass that moves
      with the phone.
    - Same object: a dark rim where the glass meets the bezel and a faint highlight along the top edge.
    """
    small = cv2.resize(warped, (args.plate_width, round(H * args.plate_width / W)), interpolation=cv2.INTER_AREA)
    screen = cv2.resize(small, (W, H), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    gray = luma(screen)[..., None]
    screen = gray + (screen - gray) * args.saturation
    gains = (room / max(float(room.mean()), 1.0)) ** 0.6
    screen *= gains
    ring = cv2.dilate(inside, np.ones((301, 301), np.uint8)) - cv2.dilate(inside, np.ones((41, 41), np.uint8))
    scene = luma(frame.astype(np.float32))[ring > 0]
    target = np.clip(np.percentile(scene, 85) * args.exposure, 120, 228) if scene.size else 200.0
    screen = screen * (target / 255) * (1 - args.lift) + target * args.lift
    screen *= shade[..., None] ** 0.9
    screen = 255 - (255 - screen) * (255 - np.clip(spec, 0, 255)[..., None]) / 255
    screen = reflect(screen, frame, inside, quad, args.reflection)
    distance = cv2.distanceTransform(inside, cv2.DIST_L2, 3)
    rim = 1 - 0.22 * np.clip(1 - distance / 3.5, 0, 1)
    screen *= rim[..., None]
    tl, tr = quad[0], quad[1]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    edge = tr - tl
    to_top = np.abs((xx - tl[0]) * edge[1] - (yy - tl[1]) * edge[0]) / (np.linalg.norm(edge) + 1e-6)
    lip = np.clip(1 - to_top / 2.5, 0, 1) * inside * 0.1
    return screen * (1 - lip[..., None]) + 255 * lip[..., None]


def reflect(screen: np.ndarray, frame: np.ndarray, inside: np.ndarray, quad: np.ndarray, strength: float) -> np.ndarray:
    """Glass reflection: the scene around the phone, mirrored and heavily blurred, in a soft diagonal band whose
    position follows the phone's centre, so it slides across the glass as she moves, plus a faint white sheen at
    the band's core so the glass reads even when the room around it is dark."""
    if strength <= 0:
        return screen
    env = cv2.GaussianBlur(cv2.flip(frame, 1), (0, 0), 45).astype(np.float32)
    cx, cy = quad.mean(axis=0)
    height = float(np.linalg.norm(quad[3] - quad[0])) + 1e-6
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    phase = ((xx - cx) * 0.55 + (yy - cy)) / height + (cx - W / 2) / W * 0.8
    band = np.exp(-((phase + 0.18) / 0.22) ** 2) + 0.35 * np.clip(-(yy - cy) / height + 0.1, 0, 1)
    alpha = (band * strength * inside)[..., None]
    sheen = (np.exp(-((phase + 0.18) / 0.12) ** 2) * strength * 0.45 * inside)[..., None]
    lit = 255 - (255 - screen) * (255 - env * alpha) / 255
    return lit * (1 - sheen) + 255 * sheen


def screen_light(base: np.ndarray, screen: np.ndarray, inside: np.ndarray, removed: np.ndarray, strength: float) -> np.ndarray:
    """Light from the lit screen on the fingers, face and bezel, in the app's colour: the green spill that despill
    removed comes back tinted like the app, plus a soft falloff glow around the screen."""
    pixels = screen[inside > 0]
    if len(pixels) == 0:
        return base
    tint = pixels.mean(axis=0)
    tint = tint / max(float(tint.max()), 1.0)
    source = luma(screen) * inside
    glow = (cv2.GaussianBlur(source, (0, 0), 12) * 0.6 + cv2.GaussianBlur(source, (0, 0), 45)) / 255 * strength
    outside = (1 - inside)[..., None]
    lit = base + (removed[..., None] * 0.8 + glow[..., None] * 255) * tint * outside
    return np.clip(lit, 0, 255)


def warp(app: np.ndarray, source: np.ndarray, quad: np.ndarray) -> np.ndarray:
    matrix = cv2.getPerspectiveTransform(source, quad.astype(np.float32))
    return cv2.warpPerspective(app, matrix, (W, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)


def warp_with_blur(app: np.ndarray, source: np.ndarray, corners: list[np.ndarray], i: int) -> np.ndarray:
    """Warp the app onto frame i's corners; when the phone moves fast, average sub-frame warps (a 180-degree shutter)."""
    quad = corners[i]
    prev = corners[max(i - 1, 0)]
    speed = float(np.abs(quad - prev).mean())
    if speed < 1.5:
        return warp(app, source, quad)
    steps = [prev + (quad - prev) * t for t in (0.5, 0.75, 1.0)]
    return np.mean([warp(app, source, q).astype(np.float32) for q in steps], axis=0).astype(np.uint8)


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
    hold = 0 if args.still else (round(args.hold_at * FPS) if args.hold_at is not None else None)
    source = np.array([[0, 0], [aw, 0], [aw, ah], [0, ah]], np.float32)

    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "12", "-preset", "medium",
                            "-pix_fmt", "yuv420p", args.out], stdin=subprocess.PIPE)
    assert enc.stdin is not None
    app = None
    rng = np.random.default_rng(7)
    for i, (frame, alpha) in enumerate(zip(frames, alphas)):
        if app is None or hold is None or i <= hold:
            app = next(app_frames, app)
        quad = corners[i]
        warped = warp_with_blur(app, source, corners, i)
        inside = np.zeros((H, W), np.uint8)
        cv2.fillConvexPoly(inside, quad.astype(np.int32), 1)
        band = cv2.dilate(inside, np.ones((15, 15), np.uint8)).astype(np.float32)
        matte = cv2.GaussianBlur(np.maximum(alpha, loose_alpha(frame)) * band, (0, 0), 0.8)[..., None]
        near = cv2.dilate(inside, np.ones((81, 81), np.uint8))
        shade, spec = plate_light(frame, inside)
        clean, removed = despill(calm_reds(frame, args.blush), near)
        clean = neutralise_bezel(clean, cv2.dilate(inside, np.ones((31, 31), np.uint8)))
        room = clean[(near - inside) > 0].reshape(-1, 3).mean(axis=0)
        lit = seat_screen(warped, inside, quad, clean, shade, spec, room, args)
        scene = screen_light(clean, lit, inside, removed, args.spill)
        out = scene * (1 - matte) + lit * matte
        if args.grain:
            out += rng.normal(0, args.grain, (H, W, 1)).astype(np.float32)
        out = np.clip(out, 0, 255).astype(np.uint8)
        enc.stdin.write(out.tobytes())
        if args.debug and i in (0, len(frames) // 2, len(frames) - 1):
            cv2.imwrite(f"{args.debug}_{i:03d}.png", cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
    enc.stdin.close()
    if enc.wait() != 0:
        sys.exit("encode failed")
    print(args.out)


if __name__ == "__main__":
    main()
