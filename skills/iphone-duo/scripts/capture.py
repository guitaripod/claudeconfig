#!/usr/bin/env python3
"""Capture an app on every iPhone Duo state the simulator can reach, then frame the results.

Drives the Duo simulator through `duoctl` (fold, unfold, partial fold, rotate, screenshot of
the display that is actually showing), launches the app once per screen and state with the
variables that route it to that screen, validates every capture against the four App Store
Connect slot sizes, retries black or mis-sized captures, and frames the good ones with `frames`.

    capture.py --udid UDID --bundle-id ID --out DIR \
        --screen items:DEMO=1,DEMO_SCREEN=items --screen settings:DEMO=1,DEMO_SCREEN=settings \
        --screen-arg settings="-screenshotRoute settings"

Every duoctl call carries `-d UDID`, so parallel agents on separate simulators cannot drive each
other's; the script refuses to run against a duoctl without that flag.

States (name, hinge angle, interface orientation):
    outer-portrait   closed, portrait     -> App Store slot 1398x2034
    outer-landscape  closed, landscape-flipped -> App Store slot 2034x1398 (camera and bar column on the left, as Apple's frame artwork draws it)
    inner-landscape  open, landscape      -> App Store slot 2853x2007
    inner-portrait   open, portrait       -> App Store slot 2007x2853
    book-landscape   127 degrees, landscape (vertical fold, inner display)
    laptop-portrait  127 degrees, portrait  (horizontal fold, inner display)

Continuity: `--states fold-cycle` (explicit, never in the default set) launches each screen once on
the open inner display, folds the device closed, then opens it again without relaunching, and
captures all three, so state carried across the fold (the open item, scroll position, a sheet) can
be compared: fold-open, fold-closed, fold-reopen.

Before the first state the simulator is reset to a known pose (device closed on the cover display,
portrait, the first screen in the foreground), and the home screen of each pose is photographed
with the app terminated, so a later capture that matches it is rejected as a dead app. A refused
rotation wedges the cover display: the script does one `simctl shutdown` and `boot`, relaunches,
retries, and records the recovery in the manifest before it records `skipped`.

The status bar is overridden (9:41, full battery and bars) for the run and cleared afterwards, also
on errors; `--keep-status-bar` leaves the simulator's own.

`--screen-arg NAME=ARG` appends launch arguments (split like a shell, so `-route x` is two) after the
bundle id for one screen, for apps that read UserDefaults arguments. `--allow-identical SCREEN[:STATE]`
records a screen that legitimately looks like another in a pose as identical-ok instead of failed.

Writes DIR/raw/, DIR/framed/, DIR/home/ and DIR/manifest.json, and exits 1 if any capture failed. A
state the app refuses (an orientation it does not support on the outer display) is recorded as
skipped, never as a pass.

Coverage spec: `--spec FILE` takes the list of cells App Store Connect actually asks for, so
"every permutation" is enforced rather than remembered. Each cell names a placement, a pixel
size, a minimum count and, optionally, the states that may satisfy it:

    {"cells": [{"name": "header inner landscape", "size": [2853, 2007], "min": 3,
                "states": ["inner-landscape", "book-landscape"]}]}

The run prints each cell as met or short and exits 1 while any cell is short.

Not covered, because no scriptable route exists: Split View halves, Picture in Picture,
multiple windows, software keyboard, camera. Use `duoctl tap` and `duoctl swipe` for the
parts of those that can be driven, and capture the rest by hand.
"""
import argparse
import json
import os
import re
import shlex
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
    ("outer-landscape", 0, "landscape-flipped", "outer-landscape"),
    ("inner-landscape", 180, "landscape", "inner-landscape"),
    ("inner-portrait", 180, "portrait", "inner-portrait"),
    ("book-landscape", 127, "landscape", "inner-landscape"),
    ("laptop-portrait", 127, "portrait", "inner-portrait"),
]

FOLD_CYCLE = [
    ("fold-open", 180, "landscape", "inner-landscape"),
    ("fold-closed", 0, "portrait", "outer-portrait"),
    ("fold-reopen", 180, "landscape", "inner-landscape"),
]

ATTEMPTS = 4
HOME_SETTLE = 2.0
NEUTRAL_SETTLE = 2.0
REOPEN_SETTLE = 4.0
MAX_RECOVERIES = 3
BOOT_TIMEOUT = 120
ROTATION_REFUSED = ("rotation refused by duoctl; ask the app's own scene to rotate "
                    "(UIWindowScene.requestGeometryUpdate behind a DEBUG launch argument)")
STATUS_BAR_OVERRIDE = ["override", "--time", "9:41", "--batteryState", "charged", "--batteryLevel", "100",
                       "--cellularBars", "4", "--wifiBars", "3"]


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


def strip_alpha(path):
    """Rewrites a capture as opaque RGB. Simulator screenshots carry an alpha channel that App Store Connect rejects."""
    try:
        from PIL import Image
    except ImportError:
        return False
    with Image.open(path) as image:
        if "A" not in image.getbands():
            return True
        flattened = image.convert("RGB")
    flattened.save(path, "PNG")
    return True


def is_black(path):
    """True when the image is effectively all black. Returns False if Pillow is unavailable."""
    try:
        from PIL import Image, ImageStat
    except ImportError:
        return False
    with Image.open(path) as image:
        small = image.convert("L").resize((64, 64))
        return ImageStat.Stat(small).mean[0] < 2.0


DUPLICATE_DIFFERENCE = 2.0


def thumbnail(path):
    """A 64x64 RGB thumbnail as a flat list of channel values, or None when Pillow is unavailable."""
    try:
        from PIL import Image
    except ImportError:
        return None
    with Image.open(path) as image:
        return list(image.convert("RGB").resize((64, 64)).tobytes())


def mean_difference(first, second):
    """Mean absolute difference per channel value between two thumbnails, from 0 to 255."""
    return sum(abs(a - b) for a, b in zip(first, second)) / len(first)


def permits(allowed, record):
    """True when --allow-identical names this record's screen, alone or with its state."""
    return (record["screen"], None) in allowed or (record["screen"], record["state"]) in allowed


def flag_duplicates(records, allowed=frozenset()):
    """Fails a capture that is practically identical to a different screen in the same state.

    Two screens that render the same pixels almost always mean routing failed and both shots show
    the launch screen. Colour is compared, not just layout, because different records share a
    layout; the bound tolerates a changing status-bar counter and nothing more. A pair that
    --allow-identical names on either side stays ok and is marked identical-ok.
    """
    seen = {}
    for record in records:
        if record["status"] != "ok":
            continue
        digest = thumbnail(record["raw"])
        if digest is None:
            return
        twins = [other for other, other_digest in seen.get(record["state"], [])
                 if other["screen"] != record["screen"] and mean_difference(digest, other_digest) < DUPLICATE_DIFFERENCE]
        blocking = [other for other in twins if not (permits(allowed, record) or permits(allowed, other))]
        if blocking:
            record["status"] = "failed"
            record["note"] = "looks identical to %s: routing probably failed" % blocking[0]["screen"]
            continue
        if twins:
            record["identical"] = "identical-ok"
            record["note"] = "identical to %s, allowed by --allow-identical" % twins[0]["screen"]
        seen.setdefault(record["state"], []).append((record, digest))


class Duo:
    """One booted iPhone Duo simulator, driven through duoctl and simctl."""

    def __init__(self, udid, bundle_id, settle):
        self.udid = udid
        self.bundle_id = bundle_id
        self.settle = settle
        self.appearance = "light"
        self.status_bar_on = False
        self.last_launch = None
        self.neutral = None
        self.home = {}
        self.home_files = {}
        self.recoveries = []
        self.unrecoverable = set()

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

    def set_pose(self, hinge, orientation, label=""):
        """Moves the hinge, then the interface orientation. Returns (ok, note).

        A refused rotation is retried once after a shutdown and boot, because the cover display
        wedges after refusals and then refuses everything. A pose that still refuses afterwards
        is not recovered again.
        """
        ok, note, refused = self.try_pose(hinge, orientation)
        key = (hinge, orientation)
        if ok or not refused or key in self.unrecoverable or len(self.recoveries) >= MAX_RECOVERIES:
            return ok, note
        recovered = self.recover("%s %s refused" % (label or "pose", orientation), label)
        if not recovered:
            return False, note
        ok, note, refused = self.try_pose(hinge, orientation)
        if not ok and refused:
            self.unrecoverable.add(key)
        self.recoveries[-1]["fixed"] = ok
        return ok, note or "recovered after a refused rotation (simctl shutdown, boot)"

    def try_pose(self, hinge, orientation):
        """One attempt at a pose. Returns (ok, note, whether the rotation was refused)."""
        if hinge == 0:
            status, output = self.duoctl("close")
        elif hinge == 180:
            status, output = self.duoctl("open")
        else:
            status, output = self.duoctl("hinge", str(hinge))
        if status != 0:
            return False, "hinge failed: " + output.splitlines()[-1] if output else "hinge failed", False
        status, output = self.rotate(orientation)
        if status != 0:
            note = ROTATION_REFUSED if hinge == 0 else (
                "orientation %s not accepted by the app on the inner display" % orientation)
            return False, note, True
        current = self.state() or {}
        expected_screen = "cover" if hinge == 0 else "inner"
        if current.get("activeScreen") != expected_screen:
            return False, "expected the %s screen, got %s" % (expected_screen, current.get("activeScreen")), False
        if str(current.get("orientation")).split("-")[0] != orientation.split("-")[0]:
            return False, "expected %s, got %s" % (orientation, current.get("orientation")), False
        return True, "", False

    def recover(self, reason, label):
        """Shuts the simulator down, boots it, restores appearance and status bar, relaunches the app.

        Returns True when duoctl answers again. The attempt is appended to `recoveries`, which the
        manifest carries.
        """
        entry = {"reason": reason, "state": label, "recovered": False, "fixed": False}
        self.recoveries.append(entry)
        print("RECOVER  %s: simctl shutdown, boot" % reason, flush=True)
        run(["xcrun", "simctl", "shutdown", self.udid])
        run(["xcrun", "simctl", "boot", self.udid])
        run(["xcrun", "simctl", "bootstatus", self.udid, "-b"])
        deadline = time.time() + BOOT_TIMEOUT
        while time.time() < deadline and self.state() is None:
            time.sleep(2)
        if self.state() is None:
            return False
        entry["recovered"] = True
        self.set_appearance(self.appearance)
        if self.status_bar_on:
            self.override_status_bar()
        if self.last_launch:
            self.launch(*self.last_launch)
            time.sleep(self.settle)
        return True

    def bring_neutral(self):
        """Puts the first screen back in the foreground before a pose change.

        The foreground screen decides whether a rotation is accepted: a screen that is portrait-only
        (a settings sheet, say) refuses the landscape of the next state, however many times the
        simulator is rebooted. Rotating with a screen that rotates freely avoids both the refusal
        and the reboot.
        """
        if self.neutral and self.last_launch != self.neutral:
            self.launch(*self.neutral)
            time.sleep(min(self.settle, NEUTRAL_SETTLE))

    def rotate(self, orientation):
        """Rotates the active display, trying the opposite landscape when the first is refused.

        A display usually accepts both landscapes. Closed, the outer display's camera and bar
        column sit on the left in `landscape-flipped`, which is where Apple's frame artwork draws
        the camera; the other direction puts the bar on the right and the frame's camera over
        the content. The order is not cosmetic.
        """
        status, output = self.duoctl("rotate", orientation)
        alternate = {"landscape": "landscape-flipped", "landscape-flipped": "landscape"}.get(orientation)
        if status != 0 and alternate:
            status, output = self.duoctl("rotate", alternate)
        return status, output

    def set_appearance(self, appearance):
        self.appearance = appearance
        run(["xcrun", "simctl", "ui", self.udid, "appearance", appearance])

    def override_status_bar(self):
        """Pins the status bar to 9:41 with full battery and bars. Returns (ok, output)."""
        status, output = run(["xcrun", "simctl", "status_bar", self.udid] + STATUS_BAR_OVERRIDE)
        self.status_bar_on = status == 0
        return status == 0, output

    def clear_status_bar(self):
        run(["xcrun", "simctl", "status_bar", self.udid, "clear"])
        self.status_bar_on = False

    def launch(self, environment, arguments):
        self.last_launch = (environment, arguments)
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

    def home_reference(self, key, directory):
        """Photographs the home screen of the current pose once, with the app terminated.

        Terminating the app returns to SpringBoard without any GUI scripting. A later capture
        that matches this picture is a dead or backgrounded app. The caller launches the app again.
        """
        if key in self.home:
            return
        run(["xcrun", "simctl", "terminate", self.udid, self.bundle_id])
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, key + ".png")
        self.home[key] = None
        for _ in range(2):
            time.sleep(HOME_SETTLE)
            status, output = self.duoctl("screenshot", path)
            if status == 0 and os.path.exists(path) and not is_black(path):
                self.home[key] = thumbnail(path)
                if self.home[key] is not None:
                    self.home_files[key] = path
                return

    def capture(self, path, expected_slot, relaunch, home_key=None, settle=None):
        """Screenshots the showing display, retrying a dead app, black, wrongly sized or home screen images."""
        note = "no attempt"
        wait = self.settle if settle is None else settle
        for attempt in range(ATTEMPTS):
            time.sleep(wait + attempt * 2)
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
            if not strip_alpha(path):
                note = "Pillow missing: capture still has an alpha channel and App Store Connect will reject it"
            if self.shows_home(path, home_key):
                note = "capture matches the home screen: the app is not in the foreground"
                relaunch()
                continue
            if not self.is_running():
                note = "app died during capture"
                relaunch()
                continue
            return True, size, ""
        return False, image_size(path) if os.path.exists(path) else None, note

    def shows_home(self, path, home_key):
        """True when the capture is practically the home screen photographed for this pose."""
        reference = self.home.get(home_key)
        digest = thumbnail(path) if reference is not None else None
        return digest is not None and mean_difference(digest, reference) < DUPLICATE_DIFFERENCE


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


def coverage(records, spec_path):
    """Compares successful captures against a coverage spec and returns the unmet cell names."""
    with open(spec_path) as handle:
        cells = json.load(handle)["cells"]
    good = [record for record in records if record["status"] == "ok"]
    unmet = []
    for cell in cells:
        size = tuple(cell["size"])
        states = cell.get("states")
        have = len([record for record in good if tuple(record["size"]) == size
                    and (not states or record["state"] in states)])
        need = cell.get("min", 1)
        met = have >= need
        print("%-5s %-40s %dx%d  %d of %d" % ("MET" if met else "SHORT", cell["name"], size[0], size[1], have, need))
        if not met:
            unmet.append(cell["name"])
    return unmet


def run_fold_cycle(duo, args, screen, environment, launch_args, raw_dir, records, home_dir):
    """Launches a screen on the open inner display, then folds closed and open again, capturing each.

    The reopened display gets `--reopen-settle` seconds, because the layout is still animating
    back to the split for a moment after the unfold.
    """
    duo.bring_neutral()
    posed, note = duo.set_pose(180, "landscape", "fold-cycle")
    launched = False
    if posed:
        duo.home_reference(home_key("inner-landscape", "light"), home_dir)
        launched, output = duo.launch(environment, launch_args)
        note = "" if launched else "launch failed: " + output[-120:]
    for name, hinge, orientation, slot in FOLD_CYCLE:
        raw = os.path.join(raw_dir, "%s__%s.png" % (screen, name))
        record = {"screen": screen, "state": name, "appearance": "light", "slot": slot, "raw": raw,
                  "status": "skipped", "note": note, "size": None, "device": None, "framed": None}
        if launched:
            stepped, note = duo.set_pose(hinge, orientation, name)
            if stepped:
                settle = max(duo.settle, args.reopen_settle) if name == "fold-reopen" else None
                ok, size, note = duo.capture(raw, slot, lambda: duo.launch(environment, launch_args),
                                             home_key(slot, "light"), settle)
                record.update(status="ok" if ok else "failed", note=note, size=size)
            else:
                record.update(note=note)
        records.append(record)
        print("%-8s %-22s %-16s %s %s" % (record["status"].upper(), screen, name, record["size"] or "", record["note"]))


def home_key(state, appearance):
    """The key of a home-screen reference: the pose and the appearance it was photographed in."""
    return "%s-%s" % (state, appearance)


def warm_up(duo, screen, home_dir, appearance):
    """Resets the simulator to a known pose before the first state and photographs its home screen.

    The device is closed on the cover display in portrait, then the first screen is launched, so
    the first state does not start from whatever the simulator was left in (a landscape start
    used to fail every cell). That screen is also the neutral one the script returns to before each
    later pose change. Returns the manifest entry.
    """
    name, environment, launch_args = screen
    duo.neutral = (environment, launch_args)
    posed, note = duo.set_pose(0, "portrait", "warm-up")
    if posed:
        duo.home_reference(home_key("outer-portrait", appearance), home_dir)
        launched, output = duo.launch(environment, launch_args)
        posed = launched
        note = "" if launched else "launch failed: " + output[-120:]
        time.sleep(duo.settle)
    print("%-8s warm-up on %s: %s" % ("READY" if posed else "WARNING", name, note or "closed, portrait, app foreground"))
    return {"screen": name, "ok": posed, "note": note}


def parse_arguments():
    parser = argparse.ArgumentParser(description="Capture an app on every iPhone Duo state.")
    parser.add_argument("--udid", help="Duo simulator UDID (default: the only booted iPhone Duo)")
    parser.add_argument("--bundle-id", help="bundle identifier of the app to launch")
    parser.add_argument("--out", help="output directory")
    parser.add_argument("--screen", action="append", default=[], metavar="NAME[:K=V,K=V]",
                        help="a screen to capture and the launch variables that route to it (repeatable)")
    parser.add_argument("--screen-arg", action="append", default=[], metavar="NAME=ARG",
                        help="launch arguments for one screen, split like a shell and appended after the bundle id "
                             "(repeatable), e.g. --screen-arg items='-screenshotRoute items'")
    parser.add_argument("--allow-identical", action="append", default=[], metavar="SCREEN[:STATE]",
                        help="a screen that may legitimately look like another in a pose: identical-ok, not failed "
                             "(repeatable)")
    parser.add_argument("--env", default="", metavar="K=V,K=V", help="launch variables for every screen")
    parser.add_argument("--arg", action="append", default=[], help="launch argument for every screen (repeatable)")
    parser.add_argument("--states", default="", help="comma list of states (default: all)")
    parser.add_argument("--appearance", default="light", help="comma list of light,dark (default: light)")
    parser.add_argument("--settle", type=float, default=4.0, help="seconds to wait after each launch")
    parser.add_argument("--reopen-settle", type=float, default=REOPEN_SETTLE,
                        help="seconds to wait after the unfold of --states fold-cycle before the capture "
                             "(default: %(default)s, at least --settle)")
    parser.add_argument("--keep-status-bar", action="store_true",
                        help="do not override the status bar (9:41, full battery and bars)")
    parser.add_argument("--only", default="", metavar="SCREEN:STATE,...",
                        help="capture only these screen and state pairs, grouped by state to save pose changes")
    parser.add_argument("--spec", help="JSON coverage spec of the cells App Store Connect requires")
    parser.add_argument("--list-states", action="store_true")
    return parser.parse_args()


def require_device_flag():
    """Exits unless duoctl takes -d/--device, without which parallel runs drive each other's simulators."""
    status, output = run(["duoctl", "--help"])
    if status != 0 or "--device" not in output:
        sys.exit("capture.py: this duoctl has no -d/--device flag, so it could drive another agent's "
                 "simulator; update duoctl (see references/capture.md)")


def require_reachable(udid):
    """Exits unless duoctl can read the state of this simulator, naming the cause."""
    status, output = run(["duoctl", "-d", udid, "state"])
    if status != 0:
        sys.exit("capture.py: duoctl cannot reach %s (is it booted?): %s" % (udid, output[-200:]))


def parse_screen_arguments(items, names):
    """Maps screen names to their launch arguments from NAME=ARG items, rejecting unknown screens."""
    arguments = {}
    for item in items:
        name, separator, text = item.partition("=")
        if not separator or name not in names:
            sys.exit("capture.py: --screen-arg takes NAME=ARG for a --screen name, got %r" % item)
        arguments.setdefault(name, []).extend(shlex.split(text))
    return arguments


def parse_allowed(items, names):
    """Parses --allow-identical SCREEN[:STATE] items into (screen, state or None) pairs."""
    known = set(state[0] for state in STATES) | set(state[0] for state in FOLD_CYCLE)
    allowed = set()
    for item in items:
        name, _, state = item.partition(":")
        if name not in names or (state and state not in known):
            sys.exit("capture.py: --allow-identical takes SCREEN[:STATE] for a known screen and state, got %r" % item)
        allowed.add((name, state or None))
    return allowed


def resolve_udid(requested):
    """Returns the requested UDID, or the only booted iPhone Duo, or exits."""
    if requested:
        return requested
    status, output = run(["xcrun", "simctl", "list", "devices", "booted"])
    found = [line for line in output.splitlines() if "Duo" in line and "(Booted)" in line]
    if len(found) != 1:
        sys.exit("capture.py: boot exactly one iPhone Duo or pass --udid (found %d)" % len(found))
    return re.search(r"[0-9A-Fa-f]{8}-(?:[0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}", found[0]).group(0)


def run_matrix(duo, args, screens, wanted, only, appearances, raw_dir, home_dir, records):
    """Captures every wanted state for every screen and appearance, then the fold-cycle when asked."""
    for appearance in appearances:
        duo.set_appearance(appearance)
        for name, hinge, orientation, slot in STATES:
            if name not in wanted:
                continue
            if only and not any(pair[1] == name for pair in only):
                continue
            duo.bring_neutral()
            posed, pose_note = duo.set_pose(hinge, orientation, name)
            if posed:
                duo.home_reference(home_key(name, appearance), home_dir)
            for screen, environment, launch_args in screens:
                if only and (screen, name) not in only:
                    continue
                suffix = "" if len(appearances) == 1 else "-" + appearance
                raw = os.path.join(raw_dir, "%s__%s%s.png" % (screen, name, suffix))
                record = {"screen": screen, "state": name, "appearance": appearance, "slot": slot,
                          "raw": raw, "status": "skipped", "note": pose_note, "size": None,
                          "device": None, "framed": None}
                if posed:
                    launched, launch_output = duo.launch(environment, launch_args)
                    if not launched:
                        record.update(status="failed", note="launch failed: " + launch_output[-120:])
                    else:
                        ok, size, note = duo.capture(
                            raw, slot, lambda: duo.launch(environment, launch_args), home_key(name, appearance))
                        record.update(status="ok" if ok else "failed", note=note or pose_note, size=size)
                records.append(record)
                print("%-8s %-22s %-16s %s %s" % (record["status"].upper(), screen, name,
                                                  record["size"] or "", record["note"]))

    if args.fold_cycle:
        duo.set_appearance("light")
        for screen, environment, launch_args in screens:
            run_fold_cycle(duo, args, screen, environment, launch_args, raw_dir, records, home_dir)


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
    require_device_flag()

    udid = resolve_udid(args.udid)
    require_reachable(udid)
    requested = [name for name in args.states.split(",") if name]
    args.fold_cycle = "fold-cycle" in requested
    wanted = [name for name in requested if name != "fold-cycle"] or ([] if args.fold_cycle else [state[0] for state in STATES])
    unknown = set(wanted) - set(state[0] for state in STATES)
    if unknown:
        sys.exit("capture.py: unknown states %s" % ", ".join(sorted(unknown)))
    appearances = [value for value in args.appearance.split(",") if value]
    global_env = parse_pairs(args.env)
    parsed = []
    for spec in args.screen:
        name, _, variables = spec.partition(":")
        parsed.append((name, dict(global_env, **parse_pairs(variables))))
    names = set(name for name, _ in parsed)
    extra_arguments = parse_screen_arguments(args.screen_arg, names)
    allowed = parse_allowed(args.allow_identical, names)
    screens = [(name, environment, args.arg + extra_arguments.get(name, [])) for name, environment in parsed]

    only = set()
    for pair in filter(None, args.only.split(",")):
        if ":" not in pair:
            sys.exit("capture.py: --only takes SCREEN:STATE pairs, got %r" % pair)
        only.add(tuple(pair.split(":", 1)))
    if only:
        stray = [pair for pair in only if pair[0] not in names or pair[1] not in [state[0] for state in STATES]]
        if stray:
            sys.exit("capture.py: --only names an unknown screen or state: %s" % stray)
        wanted = [state for state in wanted if any(pair[1] == state for pair in only)]

    duo = Duo(udid, args.bundle_id, args.settle)
    initial = duo.state() or {}
    raw_dir = os.path.join(args.out, "raw")
    home_dir = os.path.join(args.out, "home")
    os.makedirs(raw_dir, exist_ok=True)
    records = []
    status_bar = "kept"
    warm = {}

    try:
        if not args.keep_status_bar:
            overridden, output = duo.override_status_bar()
            status_bar = "override" if overridden else "override failed: " + output[-120:]
        duo.set_appearance(appearances[0])
        warm = warm_up(duo, screens[0], home_dir, appearances[0])
        run_matrix(duo, args, screens, wanted, only, appearances, raw_dir, home_dir, records)
    finally:
        if duo.status_bar_on:
            duo.clear_status_bar()
        duo.duoctl("close" if initial.get("activeScreen") == "cover" else "open")
        duo.duoctl("rotate", initial.get("orientation") or "portrait")
        duo.set_appearance("light")

    flag_duplicates(records, allowed)
    framed = frame_all([r["raw"] for r in records if r["status"] == "ok"], os.path.join(args.out, "framed"))
    for record in records:
        if record["raw"] in framed:
            record["device"], record["framed"] = framed[record["raw"]]

    with open(os.path.join(args.out, "manifest.json"), "w") as handle:
        json.dump({"udid": udid, "bundleId": args.bundle_id, "statusBar": status_bar, "warmUp": warm,
                   "recoveries": duo.recoveries, "homeReferences": duo.home_files, "captures": records},
                  handle, indent=2)

    counts = {}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    identical = len([record for record in records if record.get("identical")])
    print("capture.py: %s%s; %d recoveries; manifest %s" % (
        ", ".join("%d %s" % (count, status) for status, count in sorted(counts.items())),
        " (%d identical-ok)" % identical if identical else "", len(duo.recoveries),
        os.path.join(args.out, "manifest.json")))
    unmet = coverage(records, args.spec) if args.spec else []
    return 1 if counts.get("failed") or unmet else 0


if __name__ == "__main__":
    sys.exit(main())
