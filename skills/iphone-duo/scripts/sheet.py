#!/usr/bin/env python3
"""Build one PNG of every captured permutation, each in its Duo device frame.

Rows are screens, columns are states, so a single glance shows the whole matrix: both displays,
both orientations, flat, book and laptop, for every screen. Cells that were skipped or failed
stay empty and are labelled, never silently dropped. Takes one or more `capture.py` manifests;
a later manifest fills a cell only when it succeeded, so a re-run of a few cells can patch a
full run.

    sheet.py --manifest run1/manifest.json --manifest run2/manifest.json --out sheet.png
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

STATE_ORDER = ["outer-portrait", "outer-landscape", "inner-landscape", "inner-portrait",
               "book-landscape", "laptop-portrait"]
FONT_CANDIDATES = ["/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/SFNS.ttf",
                   "/Library/Fonts/Arial.ttf"]
BACKGROUND = (28, 28, 30)
LABEL = (235, 235, 240)
MUTED = (120, 120, 130)


def load_font(size):
    """Returns a readable font, falling back to Pillow's default."""
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def gather(manifests):
    """Maps (screen, state) to a framed image path, and lists screens in first-seen order."""
    cells = {}
    screens = []
    for path in manifests:
        with open(path) as handle:
            captures = json.load(handle)["captures"]
        for record in captures:
            if record["screen"] not in screens:
                screens.append(record["screen"])
            if record["status"] == "ok" and record.get("framed") and os.path.exists(record["framed"]):
                cells[(record["screen"], record["state"])] = record["framed"]
    return cells, screens


def scaled(path, height):
    """Loads a framed image and scales it to the cell height."""
    image = Image.open(path).convert("RGBA")
    width = round(image.width * height / image.height)
    return image.resize((width, height), Image.LANCZOS)


def build(cells, screens, cell_height, gap):
    """Lays the cells out on one canvas and returns it."""
    states = [state for state in STATE_ORDER if any(key[1] == state for key in cells)]
    images = {key: scaled(path, cell_height) for key, path in cells.items()}
    column_widths = [max([image.width for key, image in images.items() if key[1] == state] or [cell_height // 2])
                     for state in states]
    label_font = load_font(max(28, cell_height // 14))
    header_font = load_font(max(34, cell_height // 11))
    left = max(int(label_font.getlength(screen)) for screen in screens) + gap * 2
    header = header_font.size + gap * 2
    width = left + sum(column_widths) + gap * (len(states) + 1)
    height = header + len(screens) * (cell_height + gap) + gap
    canvas = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    x = left + gap
    for state, column in zip(states, column_widths):
        draw.text((x + column // 2, gap), state, font=header_font, fill=LABEL, anchor="mt")
        x += column + gap
    for row, screen in enumerate(screens):
        y = header + row * (cell_height + gap)
        draw.text((gap, y + cell_height // 2), screen, font=label_font, fill=LABEL, anchor="lm")
        x = left + gap
        for state, column in zip(states, column_widths):
            image = images.get((screen, state))
            if image is not None:
                canvas.paste(image, (x + (column - image.width) // 2, y), image)
            else:
                draw.text((x + column // 2, y + cell_height // 2), "none", font=label_font, fill=MUTED, anchor="mm")
            x += column + gap
    return canvas


def main():
    parser = argparse.ArgumentParser(description="One PNG of every captured permutation in its device frame.")
    parser.add_argument("--manifest", action="append", required=True, help="a capture.py manifest.json (repeatable)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--screens", help="comma list of screens to include, in this order (default: all, first seen first)")
    parser.add_argument("--cell-height", type=int, default=640)
    parser.add_argument("--gap", type=int, default=36)
    parser.add_argument("--max-width", type=int, help="downscale the finished sheet to at most this width")
    arguments = parser.parse_args()

    cells, screens = gather(arguments.manifest)
    if arguments.screens:
        screens = [name for name in arguments.screens.split(",") if name]
    if not cells:
        sys.exit("sheet.py: no framed captures found; run capture.py with frames installed")
    canvas = build(cells, screens, arguments.cell_height, arguments.gap)
    if arguments.max_width and canvas.width > arguments.max_width:
        canvas = canvas.resize((arguments.max_width, round(canvas.height * arguments.max_width / canvas.width)), Image.LANCZOS)
    canvas.save(arguments.out, "PNG")
    print("%s  %dx%d  %d cells, %d screens" % (arguments.out, canvas.width, canvas.height, len(cells), len(screens)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
