#!/usr/bin/env python3
"""Capture an app on every iPhone Duo state the simulator can reach, then frame the results.

Drives the Duo simulator through `duoctl` (fold, unfold, partial fold, rotate, screenshot of
the display that is actually showing), launches the app once per screen and state with the
variables that route it to that screen, validates every capture against the four App Store
Connect slot sizes, retries black or mis-sized captures, and frames the good ones with `frames`.

    capture.py --udid UDID --bundle-id ID --out DIR \
        --screen items:DEMO=1,DEMO_SCREEN=items --screen settings:DEMO=1,DEMO_SCREEN=settings

States (name, hinge angle, interface orientation):
    outer-portrait   closed, portrait     -> App Store slot 1398x2034
    outer-landscape  closed, landscape    -> App Store slot 2034x1398
    inner-landscape  open, landscape      -> App Store slot 2853x2007
    inner-portrait   open, portrait       -> App Store slot 2007x2853
    book-landscape   127 degrees, landscape (vertical fold, inner display)
    laptop-portrait  127 degrees, portrait  (horizontal fold, inner display)

Writes DIR/raw/, DIR/framed/ and DIR/manifest.json, and exits 1 if any capture failed. A state
the app refuses (an orientation it does not support on the outer display) is recorded as
skipped, never as a pass.

Not covered, because no scriptable route exists: Split View halves, Picture in Picture,
multiple windows, software keyboard, camera. Use `duoctl tap` and `duoctl swipe` for the
parts of those that can be driven, and capture the rest by hand.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

SLOT_SIZES = {
    (1398, 2034): "outer-portrait",
    (2034, 1398): "outer-landscape",
    (2007, 2853): "inner-portrait",
    (2853, 2007): "inner-landscape",
}

STATES = [
    ("outer-portrait", 0, "portrait", "outer-portrait"),
    ("outer-landscape", 0, "landscape", "outer-landscape"),
    ("inner-landscape", 180, "landscape", "inner-landscape"),
    ("inner-portrait", 180, "portrait", "inner-portrait"),
    ("book-landscape", 127, "landscape", "inner-landscape"),
    ("laptop-portrait", 127, "portrait", "inner-portrait"),
]

ATTEMPTS = 4


def run(command, env=None):
    """Runs a command and returns (exit status, combined output)."""
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True, env=env)
    return process.returncode, process.stdout.strip()


def parse_pairs(text):
    """Parses `K=V,K=V` into a dict, rejecting entries without an equals sign."""
    pairs = {}
    for item in filter(None, text.split(",")):
        if "=" not in item:
            sys.exit("capture.py: expected KEY=VALUE, got %r" % item)
        key, value = item.split("=", 1)
        pairs[key] = value
    return pairs


def image_size(path):
    """Returns (width, height) of an image using sips, which ships with macOS."""
    status, output = run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path])
    if status != 0:
        return None
    values = {}
    for line in output.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    try:
        return int(values["pixelWidth"]), int(values["pixelHeight"])
    except (KeyError, ValueError):
        return None


def is_black(path):
    """True when the image is effectively all black. Returns False if Pillow is unavailable."""
    try:
        from PIL import Image, ImageStat
    except ImportError:
        return False
    with Image.open(path) as image:
        small = image.convert("L").resize((64, 64))
        return ImageStat.Stat(small).mean[0] < 2.0


class Duo:
    """One booted iPhone Duo simulator, driven through duoctl and simctl."""

    def __init__(self, udid, bundle_id, settle):
        self.udid = udid
        self.bundle_id = bundle_id
        self.settle = settle

    def duoctl(self, *arguments):
        return run(["duoctl", "-d", self.udid] + list(arguments))

    def state(self):
        status, output = self.duoctl("state")
        if status != 0:
            return None
        try:
            return json.loads(output)
        except ValueError:
            return None

    def set_pose(self, hinge, orientation):
        """Moves the hinge, then the interface orientation. Returns (ok, note)."""
        if hinge == 0:
            status, output = self.duoctl("close")
        elif hinge == 180:
            status, output = self.duoctl("open")
        else:
            status, output = self.duoctl("hinge", str(hinge))
        if status != 0:
            return False, "hinge failed: " + output.splitlines()[-1] if output else "hinge failed"
        status, output = self.rotate(orientation)
        if status != 0:
            return False, ("orientation %s not accepted by the app (if every state fails, the simulator "
                           "may be wedged: simctl shutdown, then boot it)" % orientation)
        current = self.state() or {}
        expected_screen = "cover" if hinge == 0 else "inner"
        if current.get("activeScreen") != expected_screen:
            return False, "expected the %s screen, got %s" % (expected_screen, current.get("activeScreen"))
        if not str(current.get("orientation")).startswith(orientation):
            return False, "expected %s, got %s" % (orientation, current.get("orientation"))
        return True, ""

    def rotate(self, orientation):
        """Rotates the active display, trying the opposite landscape when the first is refused.

        A display usually accepts both landscapes. The outer display's camera sits top left in
        one of them, which is the one Apple's frame artwork expects, so the order is not cosmetic.
        """
        status, output = self.duoctl("rotate", orientation)
        if status != 0 and orientation == "landscape":
            status, output = self.duoctl("rotate", "landscape-flipped")
        return status, output

    def set_appearance(self, appearance):
        run(["xcrun", "simctl", "ui", self.udid, "appearance", appearance])

    def launch(self, environment, arguments):
        env = dict(os.environ)
        for key, value in environment.items():
            env["SIMCTL_CHILD_" + key] = value
        command = ["xcrun", "simctl", "launch", "--terminate-running-process", self.udid, self.bundle_id]
        status, output = run(command + arguments, env=env)
        return status == 0, output

    def is_running(self):
        """True when the app has a live process in the simulator."""
        status, output = run(["xcrun", "simctl", "spawn", self.udid, "launchctl", "list"])
        label = "UIKitApplication:" + self.bundle_id
        for line in output.splitlines():
            if label in line:
                return line.split()[0].isdigit()
        return False

    def capture(self, path, expected_slot, relaunch):
        """Screenshots the showing display, retrying a dead app, black or wrongly sized images."""
        note = "no attempt"
        for attempt in range(ATTEMPTS):
            time.sleep(self.settle + attempt * 2)
            if not self.is_running():
                note = "app was not running"
                relaunch()
                continue
            status, output = self.duoctl("screenshot", path)
            if status != 0 or not os.path.exists(path):
                note = "screenshot failed: " + output[-120:]
                continue
            size = image_size(path)
            if size is None:
                note = "unreadable image"
                continue
            if SLOT_SIZES.get(size) != expected_slot:
                note = "size %dx%d is not the %s slot" % (size[0], size[1], expected_slot)
                continue
            if is_black(path):
                note = "black capture"
                continue
            if not self.is_running():
                note = "app died during capture"
                relaunch()
                continue
            return True, size, ""
        return False, image_size(path) if os.path.exists(path) else None, note


def frame_all(raw_paths, framed_dir):
    """Frames every raw capture with `frames`, returning {raw path: (device, framed path)}."""
    if not raw_paths or shutil.which("frames") is None:
        return {}
    os.makedirs(framed_dir, exist_ok=True)
    status, output = run(["frames", "--json", "-o", framed_dir] + raw_paths)
    if status != 0:
        print("capture.py: frames failed: " + output[-300:], file=sys.stderr)
        return {}
    try:
        data = json.loads(output)
    except ValueError:
        return {}
    entries = data.get("frames") if isinstance(data, dict) and "frames" in data else [data]
    return {entry["source"]: (entry.get("device"), entry.get("output")) for entry in entries}


def parse_arguments():
    parser = argparse.ArgumentParser(description="Capture an app on every iPhone Duo state.")
    parser.add_argument("--udid", help="Duo simulator UDID (default: the only booted iPhone Duo)")
    parser.add_argument("--bundle-id", help="bundle identifier of the app to launch")
    parser.add_argument("--out", help="output directory")
    parser.add_argument("--screen", action="append", default=[], metavar="NAME[:K=V,K=V]",
                        help="a screen to capture and the launch variables that route to it (repeatable)")
    parser.add_argument("--env", default="", metavar="K=V,K=V", help="launch variables for every screen")
    parser.add_argument("--arg", action="append", default=[], help="launch argument for every screen (repeatable)")
    parser.add_argument("--states", default="", help="comma list of states (default: all)")
    parser.add_argument("--appearance", default="light", help="comma list of light,dark (default: light)")
    parser.add_argument("--settle", type=float, default=4.0, help="seconds to wait after each launch")
    parser.add_argument("--list-states", action="store_true")
    return parser.parse_args()


def resolve_udid(requested):
    """Returns the requested UDID, or the only booted iPhone Duo, or exits."""
    if requested:
        return requested
    status, output = run(["xcrun", "simctl", "list", "devices", "booted"])
    found = [line for line in output.splitlines() if "Duo" in line and "(Booted)" in line]
    if len(found) != 1:
        sys.exit("capture.py: boot exactly one iPhone Duo or pass --udid (found %d)" % len(found))
    return re.search(r"[0-9A-Fa-f]{8}-(?:[0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}", found[0]).group(0)


def main():
    args = parse_arguments()
    if args.list_states:
        for name, hinge, orientation, slot in STATES:
            print("%-16s hinge %-3s %-10s slot %s" % (name, hinge, orientation, slot))
        return 0
    if not (args.bundle_id and args.out and args.screen):
        sys.exit("capture.py: --bundle-id, --out and at least one --screen are required")
    if shutil.which("duoctl") is None:
        sys.exit("capture.py: duoctl is not on PATH; see references/capture.md to install it")

    udid = resolve_udid(args.udid)
    wanted = [name for name in args.states.split(",") if name] or [state[0] for state in STATES]
    unknown = set(wanted) - set(state[0] for state in STATES)
    if unknown:
        sys.exit("capture.py: unknown states %s" % ", ".join(sorted(unknown)))
    appearances = [value for value in args.appearance.split(",") if value]
    global_env = parse_pairs(args.env)
    screens = []
    for spec in args.screen:
        name, _, variables = spec.partition(":")
        screens.append((name, dict(global_env, **parse_pairs(variables))))

    duo = Duo(udid, args.bundle_id, args.settle)
    initial = duo.state() or {}
    raw_dir = os.path.join(args.out, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    records = []

    for appearance in appearances:
        duo.set_appearance(appearance)
        for name, hinge, orientation, slot in STATES:
            if name not in wanted:
                continue
            posed, pose_note = duo.set_pose(hinge, orientation)
            for screen, environment in screens:
                suffix = "" if len(appearances) == 1 else "-" + appearance
                raw = os.path.join(raw_dir, "%s__%s%s.png" % (screen, name, suffix))
                record = {"screen": screen, "state": name, "appearance": appearance, "slot": slot,
                          "raw": raw, "status": "skipped", "note": pose_note, "size": None,
                          "device": None, "framed": None}
                if posed:
                    launched, launch_output = duo.launch(environment, args.arg)
                    if not launched:
                        record.update(status="failed", note="launch failed: " + launch_output[-120:])
                    else:
                        ok, size, note = duo.capture(
                            raw, slot, lambda: duo.launch(environment, args.arg))
                        record.update(status="ok" if ok else "failed", note=note, size=size)
                records.append(record)
                print("%-8s %-22s %-16s %s %s" % (record["status"].upper(), screen, name,
                                                  record["size"] or "", record["note"]))

    duo.duoctl("close" if initial.get("activeScreen") == "cover" else "open")
    duo.duoctl("rotate", initial.get("orientation") or "portrait")
    duo.set_appearance("light")

    framed = frame_all([r["raw"] for r in records if r["status"] == "ok"], os.path.join(args.out, "framed"))
    for record in records:
        if record["raw"] in framed:
            record["device"], record["framed"] = framed[record["raw"]]

    with open(os.path.join(args.out, "manifest.json"), "w") as handle:
        json.dump({"udid": udid, "bundleId": args.bundle_id, "captures": records}, handle, indent=2)

    counts = {}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    print("capture.py: %s; manifest %s" % (
        ", ".join("%d %s" % (count, status) for status, count in sorted(counts.items())),
        os.path.join(args.out, "manifest.json")))
    return 1 if counts.get("failed") else 0


if __name__ == "__main__":
    sys.exit(main())
