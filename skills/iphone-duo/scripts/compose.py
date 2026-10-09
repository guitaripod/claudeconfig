#!/usr/bin/env python3
"""Compose the App Store product page Header and Search Results images from framed Duo shots.

These two placements are creative assets, not screenshots: one image each per localization, no
alpha, PNG. This builds text-free compositions (so one set serves every locale) of framed device
shots over a two-colour gradient, at every size Apple accepts for them:

    header-16x9.png   5244 x 2950  accepted by Header and Search Results (universal)
    header-21x9.png   3840 x 1646  accepted by Header
    search-3x2.png    3000 x 2000  accepted by Search Results (3:2 between 1920x1280 and 3840x2560)

    compose.py --out DIR --hero inner-landscape_framed.png --second outer-portrait_framed.png \\
        --background "#08C4D0,#5B4FE9"

Read the current limits first with `scripts/asc-specs.py`; the sizes above are the ones it
reported on 2026-10-09 and are checked, not assumed, after rendering. A product page that needs
text or a different hierarchy is a design task: use these as the device layer.
"""
import argparse
import os
import sys

from PIL import Image, ImageChops, ImageFilter

CANVASES = [
    ("header-16x9.png", (5244, 2950), 0.80, 0.70),
    ("header-21x9.png", (3840, 1646), 0.84, 0.74),
    ("search-3x2.png", (3000, 2000), 0.64, 0.56),
]

OVERLAP = 0.10
SHADOW_OPACITY = 0.38


def parse_colour(text):
    """Parses #RRGGBB into an (r, g, b) tuple."""
    text = text.strip().lstrip("#")
    if len(text) != 6:
        sys.exit("compose.py: colours are #RRGGBB, got %r" % text)
    return tuple(int(text[index:index + 2], 16) for index in (0, 2, 4))


def gradient(size, first, second):
    """A diagonal two-colour gradient the size of the canvas."""
    width, height = size
    horizontal = Image.linear_gradient("L").rotate(90, expand=True).resize(size)
    vertical = Image.linear_gradient("L").resize(size)
    mask = ImageChops.add(horizontal, vertical, scale=2)
    return Image.composite(Image.new("RGB", size, second), Image.new("RGB", size, first), mask)


def fit_height(image, height):
    """Scales an image to a height, keeping its aspect ratio."""
    width = round(image.width * height / image.height)
    return image.resize((width, round(height)), Image.LANCZOS)


def shadow_for(image, blur):
    """A soft dark silhouette of the image's alpha, for depth under a device."""
    alpha = image.getchannel("A").point(lambda value: int(value * SHADOW_OPACITY))
    silhouette = Image.new("RGBA", image.size, (0, 0, 0, 0))
    silhouette.putalpha(alpha)
    return silhouette.filter(ImageFilter.GaussianBlur(blur))


def paste_device(canvas, device, position, blur):
    """Pastes a device with its shadow onto an RGB canvas."""
    shadow = shadow_for(device, blur)
    canvas.paste(shadow, (position[0], position[1] + round(blur * 0.8)), shadow)
    canvas.paste(device, position, device)


def render(size, hero, second, colours, hero_fraction, second_fraction):
    """Renders one composition: the hero device left of centre, the second overlapping its right edge."""
    width, height = size
    canvas = gradient(size, *colours)
    hero_device = fit_height(hero, height * hero_fraction)
    second_device = fit_height(second, height * second_fraction) if second is not None else None
    overlap = round(hero_device.width * OVERLAP) if second_device is not None else 0
    total = hero_device.width + (second_device.width - overlap if second_device is not None else 0)
    left = (width - total) // 2
    baseline = round(height * 0.93)
    blur = height * 0.018
    paste_device(canvas, hero_device, (left, baseline - hero_device.height), blur)
    if second_device is not None:
        paste_device(canvas, second_device, (left + hero_device.width - overlap, baseline - second_device.height), blur)
    return canvas


def verify(path, expected):
    """Confirms the written file has the expected size and no alpha channel."""
    with Image.open(path) as image:
        if image.size != expected:
            sys.exit("compose.py: %s is %s, expected %s" % (path, image.size, expected))
        if "A" in image.getbands():
            sys.exit("compose.py: %s has an alpha channel, which App Store Connect rejects" % path)


def main():
    parser = argparse.ArgumentParser(description="Compose Header and Search Results images from framed shots.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--hero", required=True, help="framed device image shown largest (usually inner landscape)")
    parser.add_argument("--second", help="framed device image overlapping it (usually outer portrait)")
    parser.add_argument("--background", default="#08C4D0,#5B4FE9", help="two #RRGGBB colours, comma separated")
    arguments = parser.parse_args()

    colours = [parse_colour(part) for part in arguments.background.split(",")]
    if len(colours) != 2:
        sys.exit("compose.py: --background takes exactly two colours")
    hero = Image.open(arguments.hero).convert("RGBA")
    second = Image.open(arguments.second).convert("RGBA") if arguments.second else None
    os.makedirs(arguments.out, exist_ok=True)
    for name, size, hero_fraction, second_fraction in CANVASES:
        path = os.path.join(arguments.out, name)
        render(size, hero, second, colours, hero_fraction, second_fraction).save(path, "PNG")
        verify(path, size)
        print("%-18s %dx%d" % (name, size[0], size[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
