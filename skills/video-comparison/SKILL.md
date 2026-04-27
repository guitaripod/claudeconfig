---
description: This skill should be used when the user asks to create a comparison video, side-by-side video, combine screen recordings, or make a demo video from multiple recordings.
---

# Video Comparison

Compose multiple screen recordings into a single labeled comparison video using ffmpeg and Python PIL.

## Output Defaults

- **Framerate**: 60fps (`-r 60`)
- **Codec**: libx264, `-crf 20`, `-pix_fmt yuv420p`
- **Audio**: none (`-an`)
- **Output path**: `~/Downloads/` unless specified
- **Duration**: longest input video; shorter ones loop via `-stream_loop -1`

## Layout

Horizontal (side-by-side) is the default. All videos are the same height with labels above each panel.

### Dimension Calculation

```
LABEL_H = 34
VID_H = 1080 - LABEL_H  (= 1046)
VID_W = round(VID_H * input_width / input_height)
GAP = 8
CANVAS_W = GAP + (VID_W + GAP) * N
CANVAS_H = 1080
```

Where N = number of input videos, and input_width/input_height come from `ffprobe` on the first input.

## Steps

### 1. Probe inputs

```bash
ffprobe -v error -show_entries stream=width,height,duration,r_frame_rate -of csv=p=0 "input.mov"
```

### 2. Generate label overlay with Python PIL

Create a transparent PNG at canvas size with labels centered over each panel:

```python
from PIL import Image, ImageDraw, ImageFont

img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("/System/Library/Fonts/SFCompact.ttf", 18)
except:
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except:
        font = ImageFont.load_default()

for i, text in enumerate(labels):
    x = GAP + i * (VID_W + GAP)
    draw.rounded_rectangle([x, 0, x + VID_W, LABEL_H], radius=6, fill=(20, 20, 20, 230))
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x + (VID_W - tw) // 2, (LABEL_H - th) // 2 - 1), text, fill=(255, 255, 255, 255), font=font)

img.save("/tmp/comparison_labels.png")
```

### 3. Compose with ffmpeg

Use `color` filter as background, scale each input with lanczos, overlay sequentially, then overlay labels on top. Apply `-stream_loop -1` to inputs shorter than the longest.

```bash
ffmpeg -y \
  -i "video1.mov" \
  -stream_loop -1 -i "video2.mov" \
  -i /tmp/comparison_labels.png \
  -filter_complex "
    color=black:s=${CANVAS_W}x${CANVAS_H}:d=${DURATION}:rate=60[bg];
    [0:v]scale=${VID_W}:${VID_H}:flags=lanczos[s0];
    [1:v]scale=${VID_W}:${VID_H}:flags=lanczos[s1];
    [bg][s0]overlay=x=${X0}:y=${LABEL_H}:shortest=1[o0];
    [o0][s1]overlay=x=${X1}:y=${LABEL_H}[o1];
    [2:v]format=argb[labels];
    [o1][labels]overlay=0:0[out]
  " \
  -map "[out]" -t ${DURATION} -r 60 -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p -an \
  output.mp4
```

Key rules:
- Only the first input (longest) omits `-stream_loop -1`
- Only the first overlay gets `shortest=1`
- Labels PNG is always the last input and last overlay

## Important

- Always `ffprobe` inputs first to get dimensions and durations
- The longest video determines total duration — identify it from probe results
- Never use `drawtext` filter (not available on macOS Homebrew ffmpeg)
- Never use ImageMagick for labels (font issues on macOS)
- Always use Python PIL for label generation
