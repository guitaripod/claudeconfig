#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow", "librosa", "soundfile"]
# ///
"""Render a vertical app short from real screen recordings.

The phone (real footage inside a `frames` bezel) is the only sharp element. Behind it sit the
same footage blurred into the app's palette, soft bokeh and a glow; above it, short text cards.
Cuts land on the music's beats when the spec gives segment lengths in beats.

    short.py spec.json                    render the video named by spec["out"]
    short.py spec.json --stills 0,1.5,-1  write PNG stills instead (negative = from the end)
    short.py spec.json --stills 0 --zones shade TikTok's UI areas on the stills

See ../SKILL.md for the spec format.
"""

import argparse
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import IO

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
BG_SMALL = (72, 156)
BOKEH_SCALE = 4


@dataclass
class Text:
    start: float
    end: float
    image: np.ndarray
    top: int
    countdown: int = 0
    center_y: int = 0
    radius: int = 92


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec")
    parser.add_argument("--stills", default="")
    parser.add_argument("--zones", action="store_true")
    parser.add_argument("--keep", action="store_true")
    return parser.parse_args()


def hex_rgb(value: str) -> np.ndarray:
    value = value.lstrip("#")
    return np.array([int(value[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"{cmd[0]} failed:\n{result.stderr[-3000:]}")
    return result.stdout


def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def beat_grid(path: Path, bpm: float, start_bar: int) -> tuple[np.ndarray, float]:
    """Detect beat times and return them shifted so the chosen downbeat is t = 0, plus that downbeat's file offset.

    The downbeat is the phase (of the first four beats) whose beats carry the most onset energy.
    """
    import librosa

    y, sr = librosa.load(str(path), sr=22050, mono=True)
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    _, beats = librosa.beat.beat_track(onset_envelope=onset, sr=sr, start_bpm=bpm, tightness=400)
    if len(beats) < 16:
        sys.exit(f"only {len(beats)} beats found in {path}")
    phase = max(range(4), key=lambda p: float(onset[beats[p::4]].mean()))
    times = librosa.frames_to_time(beats, sr=sr)[phase + 4 * start_bar:]
    return times - times[0], float(times[0])


def segment_bounds(spec: dict, beats: np.ndarray | None) -> list[tuple[float, float]]:
    """Turn segment lengths (seconds or beats) into exact [start, end) times on the video clock."""
    bounds, t, beat_index = [], 0.0, 0
    for seg in spec["segments"]:
        if "beats" in seg:
            if beats is None:
                length = seg["beats"] * 60.0 / spec["bpm"]
                end = t + length
            else:
                beat_index += seg["beats"]
                if beat_index >= len(beats):
                    sys.exit("the music is shorter than the cut; generate a longer bed")
                end = float(beats[beat_index])
        else:
            end = t + seg["dur"]
        bounds.append((t, end))
        t = end
    return bounds


def frame_index(t: float) -> int:
    return int(round(t * FPS))


def build_screen(spec: dict, root: Path, bounds: list[tuple[float, float]], work: Path) -> Path:
    """Cut, retime and concatenate the source takes into one 30 fps screen track; freezes hold the previous frame.

    Simulator recordings are variable frame rate and emit no frames while the screen is still, so each take is
    resampled to 60 fps before trimming: a seek into a still stretch would otherwise start at the next change.
    Segments past the end of their take hold the take's last frame; b-roll segments get black filler, since the
    phone is not drawn over them.
    """
    first = next(seg["clip"] for seg in spec["segments"] if seg.get("clip"))
    take_w, take_h = probe_size(root / first)
    inputs, chains, labels = [], [], []
    for i, (seg, (start, end)) in enumerate(zip(spec["segments"], bounds)):
        frames = frame_index(end) - frame_index(start)
        if seg.get("freeze"):
            if not chains:
                sys.exit("a freeze cannot be the first segment")
            prev = chains.pop()
            label = labels.pop()
            chains.append(prev.replace(f"[{label}]", f",tpad=stop_mode=clone:stop={frames}[{label}]"))
            labels.append(label)
            continue
        n = inputs.count("-i")
        label = f"v{i}"
        if seg.get("broll"):
            inputs += ["-f", "lavfi", "-i", f"color=c=black:s={take_w}x{take_h}:r={FPS}:d={frames / FPS + 1:.3f}"]
            chains.append(f"[{n}:v]trim=end_frame={frames},setpts=PTS-STARTPTS[{label}]")
        else:
            speed = seg.get("speed", 1.0)
            inputs += ["-i", str(root / seg["clip"])]
            chains.append(f"[{n}:v]fps=60,trim=start={seg['t0']:.4f},setpts=(PTS-STARTPTS)/{speed},fps={FPS},"
                          f"tpad=stop_mode=clone:stop=-1,trim=end_frame={frames},setpts=PTS-STARTPTS[{label}]")
        labels.append(label)
    graph = ";".join(chains) + ";" + "".join(f"[{label}]" for label in labels) + f"concat=n={len(labels)}:v=1:a=0[out]"
    out = work / "screen.mp4"
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[out]",
         "-c:v", "libx264", "-crf", "10", "-preset", "fast", "-pix_fmt", "yuv420p", "-r", str(FPS), str(out)])
    return out


def frame_device(screen: Path, color: str, work: Path) -> Path:
    out = work / "framed.mov"
    run(["frames", "--json", "video", "--alpha", "--strip-audio", "-c", color, "-o", str(out), str(screen)])
    return out


def probe_size(path: Path) -> tuple[int, int]:
    w, h = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                "-of", "csv=p=0", str(path)]).strip().split(",")
    return int(w), int(h)


def reader(path: Path, size: tuple[int, int], pix: str) -> tuple[subprocess.Popen, IO[bytes]]:
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"scale={size[0]}:{size[1]}:flags=lanczos",
                             "-pix_fmt", pix, "-f", "rawvideo", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    assert proc.stdout is not None
    return proc, proc.stdout


def read_frame(stream: IO[bytes], size: tuple[int, int], channels: int, last: np.ndarray | None) -> np.ndarray:
    """Read one raw frame; past the end of the stream, repeat the last one."""
    n = size[0] * size[1] * channels
    data = stream.read(n)
    if len(data) < n:
        if last is None:
            sys.exit("a video stream produced no frames")
        return last
    return np.frombuffer(data, np.uint8).reshape(size[1], size[0], channels)


def load_font(spec_font: dict, size: int) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(spec_font["file"], size)
    if spec_font.get("variation"):
        font.set_variation_by_name(spec_font["variation"])
    return font


def draw_tracked(draw: ImageDraw.ImageDraw, y: int, text: str, font: ImageFont.FreeTypeFont, fill, tracking: float) -> None:
    """Draw one centered line with extra letter spacing (tracking is a fraction of the font size)."""
    gap = font.size * tracking
    widths = [font.getlength(ch) for ch in text]
    x = (W - (sum(widths) + gap * (len(text) - 1))) / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + gap


def render_text_card(card: dict, style: dict) -> tuple[np.ndarray, int]:
    """Render a label + title card to a full-width RGBA strip with a soft shadow; returns the strip and its top y."""
    top = style.get("top", 170)
    canvas = Image.new("RGBA", (W, 420), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    y = 10
    if card.get("label"):
        font = load_font(style["label_font"], style.get("label_size", 32))
        draw_tracked(draw, y, card["label"].upper(), font, tuple(int(c) for c in hex_rgb(style["label"])) + (255,), 0.16)
        y += int(font.size * 1.75)
    if card.get("title"):
        font = load_font(style["title_font"], style.get("title_size", 76))
        for line in card["title"].split("\n"):
            draw.text((W / 2, y), line, font=font, fill=tuple(int(c) for c in hex_rgb(style["title"])) + (255,), anchor="mt")
            y += int(font.size * style.get("line_height", 1.12))
    alpha = canvas.getchannel("A")
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(10)).point(lambda a: int(a * 0.55)))
    out = Image.alpha_composite(shadow, canvas)
    return np.asarray(out).copy(), top - 10


def build_texts(spec: dict, bounds: list[tuple[float, float]]) -> list[Text]:
    texts = []
    for card in spec.get("texts", []):
        start = card["at"] if "at" in card else bounds[card["from"]][0] + card.get("delay", 0.0)
        end = card["until"] if "until" in card else bounds[card.get("to", card.get("from"))][1]
        if card.get("countdown"):
            center = card.get("y", spec["style"].get("top", 170) + 130)
            texts.append(Text(start, end, np.zeros((1, 1, 4), np.uint8), 0, card["countdown"], center, card.get("r", 92)))
            continue
        image, top = render_text_card(card, spec["style"])
        texts.append(Text(start, end, image, top))
    return texts


def text_alpha(t: float, text: Text, total: float) -> tuple[float, float]:
    """Opacity and upward slide for a card at time t: 0.22 s fade and 14 px rise in, 0.18 s fade out."""
    if t < text.start or t >= text.end:
        return 0.0, 0.0
    a_in = ease((t - text.start) / 0.22)
    a_out = 1.0 if text.end >= total - 1e-3 else ease((text.end - t) / 0.18)
    return min(a_in, a_out), (1 - a_in) * 14


def draw_countdown(frame: Image.Image, t: float, text: Text, style: dict) -> None:
    """A ring on a dark disc that empties over the hold, with the remaining whole seconds inside, centred at the card's y."""
    span = text.end - text.start
    progress = (t - text.start) / span
    remaining = max(1, math.ceil(text.countdown * (1 - progress)))
    alpha = int(255 * min(ease((t - text.start) / 0.15), ease((text.end - t) / 0.12)))
    layer = Image.new("RGBA", (W, 300), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, cy, r = W // 2, 150, text.radius
    accent = tuple(int(c) for c in hex_rgb(style["label"]))
    draw.ellipse((cx - r - 22, cy - r - 22, cx + r + 22, cy + r + 22), fill=(10, 10, 14, 150))
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=accent + (70,), width=10)
    draw.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * (1 - progress), fill=accent + (255,), width=10)
    font = load_font(style["title_font"], int(r * 1.2))
    draw.text((cx, cy + 4), str(remaining), font=font, fill=tuple(int(c) for c in hex_rgb(style["title"])) + (255,), anchor="mm")
    if alpha < 255:
        faded = np.asarray(layer.getchannel("A"), np.uint16) * alpha // 255
        layer.putalpha(Image.fromarray(faded.astype(np.uint8)))
    frame.alpha_composite(layer, (0, text.center_y - 150))


class Backdrop:
    """Palette gradient + the blurred screen + drifting bokeh + a glow behind the phone + vignette."""

    def __init__(self, palette: dict, device_box: tuple[int, int, int, int], seed: int):
        ys = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        self.base = hex_rgb(palette["bg_top"]) * (1 - ys) + hex_rgb(palette["bg_bottom"]) * ys
        self.base = np.broadcast_to(self.base, (H, W, 3)).copy()
        self.tint = hex_rgb(palette.get("tint", "#ffffff")) / 255.0
        self.screen_mix = palette.get("screen_mix", 0.35)
        x0, y0, x1, y1 = device_box
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - (x0 + x1) / 2) / ((x1 - x0) * 0.95)) ** 2 + ((yy - (y0 + y1) / 2) / ((y1 - y0) * 0.62)) ** 2)
        self.glow = (np.exp(-d ** 2 * 1.6) * palette.get("glow_strength", 0.55))[..., None] * hex_rgb(palette["glow"])
        v = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2)
        self.vignette = np.clip(1.05 - v ** 2 * 0.55, 0.45, 1.0)[..., None]
        rng = np.random.default_rng(seed)
        colors = [hex_rgb(c) for c in palette["bokeh"]]
        self.dots = [dict(x=rng.uniform(0, W), y=rng.uniform(0, H), r=rng.uniform(14, 60), a=rng.uniform(0.10, 0.42),
                          c=colors[i % len(colors)], vx=rng.uniform(-6, 6), vy=rng.uniform(-16, -4), ph=rng.uniform(0, 6.28))
                     for i in range(palette.get("bokeh_count", 34))]

    def bokeh(self, t: float) -> np.ndarray:
        sw, sh = W // BOKEH_SCALE, H // BOKEH_SCALE
        layer = np.zeros((sh, sw, 3), np.float32)
        for d in self.dots:
            x = ((d["x"] + d["vx"] * t) % (W + 120) - 60) / BOKEH_SCALE
            y = ((d["y"] + d["vy"] * t) % (H + 120) - 60) / BOKEH_SCALE
            r = d["r"] / BOKEH_SCALE
            a = d["a"] * (0.75 + 0.25 * math.sin(t * 0.9 + d["ph"]))
            x0, x1 = int(max(x - 2 * r, 0)), int(min(x + 2 * r + 1, sw))
            y0, y1 = int(max(y - 2 * r, 0)), int(min(y + 2 * r + 1, sh))
            if x0 >= x1 or y0 >= y1:
                continue
            gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            fall = np.exp(-(((gx - x) ** 2 + (gy - y) ** 2) / (r * r)) * 1.4)
            layer[y0:y1, x0:x1] += fall[..., None] * d["c"] * a
        return np.asarray(Image.fromarray(np.clip(layer, 0, 255).astype(np.uint8)).resize((W, H), Image.Resampling.BILINEAR), np.float32)

    def frame(self, small: np.ndarray, t: float) -> np.ndarray:
        blur = Image.fromarray(small).resize((270, 480), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(9))
        blur = np.asarray(blur.resize((W, H), Image.Resampling.BILINEAR), np.float32)
        out = self.base + blur * self.tint * self.screen_mix + self.glow + self.bokeh(t)
        return np.clip(out * self.vignette, 0, 255)


def top_scrim(height: int) -> Image.Image:
    """A dark gradient behind the cards on full-frame shots, so type stays legible over a bright window or sky."""
    ys = np.linspace(0, 1, height, dtype=np.float32)
    alpha = (0.62 * (1 - ys) ** 1.6 * 255).astype(np.uint8)
    layer = np.zeros((H, W, 4), np.uint8)
    layer[:height, :, 3] = alpha[:, None]
    return Image.fromarray(layer, "RGBA")


class Brolls:
    """Full-frame clips (her shots, already composited by screen.py) that replace the phone-on-backdrop layout."""

    def __init__(self, spec: dict, root: Path, bounds: list[tuple[float, float]]):
        self.spans = [(frame_index(s), frame_index(e), root / seg["broll"], seg.get("t0", 0.0))
                      for seg, (s, e) in zip(spec["segments"], bounds) if seg.get("broll")]
        self.open: tuple[int, subprocess.Popen, IO[bytes]] | None = None
        self.last: np.ndarray | None = None

    def frame(self, i: int) -> np.ndarray | None:
        span = next((sp for sp in self.spans if sp[0] <= i < sp[1]), None)
        if span is None:
            return None
        if self.open is None or self.open[0] != span[0]:
            if self.open:
                self.open[1].kill()
            proc = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{span[3]:.3f}", "-i", str(span[2]), "-vf",
                                     f"fps={FPS},scale={W}:{H}:flags=lanczos", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            assert proc.stdout is not None
            self.open, self.last = (span[0], proc, proc.stdout), None
        self.last = read_frame(self.open[2], (W, H), 3, self.last)
        return self.last


def zones_overlay(img: Image.Image) -> Image.Image:
    """Shade TikTok's UI areas: top tabs, right action rail, bottom caption and bar."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for box in [(0, 0, W, 150), (W - 140, 760, W, 1560), (0, 1440, W, H)]:
        draw.rectangle(box, fill=(255, 0, 0, 70))
    return Image.alpha_composite(img.convert("RGBA"), layer)


def encoder(out: Path, audio: dict | None, total: float) -> tuple[subprocess.Popen, IO[bytes]]:
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if audio:
        fade = audio.get("fade_out", 1.2)
        cmd += ["-ss", f"{audio['offset']:.4f}", "-i", str(audio["file"]),
                "-af", f"atrim=duration={total:.4f},afade=t=in:d=0.03,afade=t=out:st={total - fade:.4f}:d={fade},"
                       f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000",
                "-c:a", "aac", "-b:a", "192k", "-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", "-t", f"{total:.4f}", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    return proc, proc.stdin


def main() -> None:
    args = parse_args()
    spec_path = Path(args.spec).resolve()
    spec = json.loads(spec_path.read_text())
    root = Path(spec.get("root", spec_path.parent))
    work = Path(spec["work"])
    work.mkdir(parents=True, exist_ok=True)

    beats, audio = None, None
    if spec.get("music"):
        music = spec["music"]
        beats, offset = beat_grid(Path(music["file"]), spec["bpm"], music.get("start_bar", 0))
        audio = dict(music, offset=offset)
    bounds = segment_bounds(spec, beats)
    total = bounds[-1][1]
    n_frames = frame_index(total)

    screen = build_screen(spec, root, bounds, work)
    framed = frame_device(screen, spec["device"].get("color", "Silver"), work)
    fw, fh = probe_size(framed)
    dev = spec["device"]
    max_h = dev.get("height", 1020)
    push = dev.get("push", 0.08)
    max_size = (int(round(fw * max_h / fh / 2)) * 2, max_h)
    cx, cy = W // 2, dev.get("center_y", 930)
    device_box = (cx - max_size[0] // 2, cy - max_h // 2, cx + max_size[0] // 2, cy + max_h // 2)
    backdrop = Backdrop(spec["palette"], device_box, spec.get("seed", 7))
    texts = build_texts(spec, bounds)

    stills = [min(n_frames - 1, frame_index(total + t if t < 0 else t)) for t in map(float, filter(None, args.stills.split(",")))]
    out = Path(spec["out"])
    enc = None if stills else encoder(out, audio, total)

    brolls = Brolls(spec, root, bounds)
    scrim = top_scrim(spec["style"].get("top", 170) + 470)
    dev_proc, dev_stream = reader(framed, max_size, "rgba")
    bg_proc, bg_stream = reader(screen, BG_SMALL, "rgb24")
    dev_frame = bg_frame = shadow = None
    for i in range(n_frames):
        t = i / FPS
        dev_frame = read_frame(dev_stream, max_size, 4, dev_frame)
        bg_frame = read_frame(bg_stream, BG_SMALL, 3, bg_frame)
        broll = brolls.frame(i)
        if stills and i not in stills:
            continue
        if shadow is None:
            mask = Image.fromarray(dev_frame[..., 3]).filter(ImageFilter.GaussianBlur(28))
            shadow = Image.merge("RGBA", [Image.new("L", max_size, 0)] * 3 + [mask.point(lambda a: int(a * 0.62))])
        if broll is not None:
            canvas = Image.fromarray(broll).convert("RGBA")
            canvas.alpha_composite(scrim)
        else:
            canvas = Image.fromarray(backdrop.frame(bg_frame, t).astype(np.uint8)).convert("RGBA")
            zoom = (1 + push * ease(t / total)) / (1 + push)
            size = (int(round(max_size[0] * zoom)), int(round(max_size[1] * zoom)))
            x, y = cx - size[0] // 2, cy - size[1] // 2
            canvas.alpha_composite(shadow.resize(size, Image.Resampling.BILINEAR), (x, y + int(26 * zoom)))
            canvas.alpha_composite(Image.fromarray(dev_frame, "RGBA").resize(size, Image.Resampling.LANCZOS), (x, y))
        for text in texts:
            if text.countdown:
                if text.start <= t < text.end:
                    draw_countdown(canvas, t, text, spec["style"])
                continue
            a, rise = text_alpha(t, text, total)
            if a <= 0:
                continue
            img = text.image.copy()
            img[..., 3] = (img[..., 3].astype(np.float32) * a).astype(np.uint8)
            canvas.alpha_composite(Image.fromarray(img, "RGBA"), (0, int(text.top + rise)))
        fade = spec.get("fade_out", 0.35)
        if t > total - fade:
            k = ease((total - t) / fade)
            base = Image.new("RGBA", canvas.size, tuple(int(c) for c in hex_rgb(spec["palette"]["bg_bottom"])) + (255,))
            canvas = Image.blend(base, canvas, k)
        if enc is None:
            img = zones_overlay(canvas) if args.zones else canvas
            path = work / f"still_{i:04d}.png"
            img.convert("RGB").save(path)
            print(path)
        else:
            enc[1].write(canvas.convert("RGB").tobytes())
    dev_proc.kill()
    bg_proc.kill()
    if enc is not None:
        enc[1].close()
        if enc[0].wait() != 0:
            sys.exit("encode failed")
        print(out)
        print(f"duration {total:.2f}s, {n_frames} frames, cuts at " + ", ".join(f"{b[0]:.2f}" for b in bounds))
    if not args.keep and not stills:
        for name in ("screen.mp4", "framed.mov"):
            (work / name).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
