#!/usr/bin/env python3
"""Stage an iPhone Duo release in App Store Connect so a person only has to review and submit.

`stage` finds or creates the editable iOS version, waits for the build to be VALID and attaches
it, sets and reads back What's New for every locale, uploads the ten Duo screenshots per locale
(one locale at a time, verified by listing), places the Header and Search Results images, and
prints `asc validate` verbatim. Every step is idempotent, `--dry-run` runs every asc call with
`--read-only`, and the script never edits age ratings, copyright or any declaration. `submit`
creates the review submission, adds the version and submits only with `--confirm`. Needs asc 5.12
or later; a ship directory holds shots/<locale>/NN-*.png, placements/header-16x9.png and
placements/search-3x2.png.

    asc-ship.py stage --app 6705124497 --platform IOS --version 4.2.0 --build 170 \\
        --ship ~/duo/ship --whatsnew ~/duo/ship/whatsnew.json [--dry-run]
    asc-ship.py submit --app 6705124497 --platform IOS --version-id <id> --confirm
"""
import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time

ASC_BINARY = os.environ.get("ASC_BIN", "asc")
DUO_DEVICE_TYPE = "IPHONE_DUO"
DUO_DISPLAY_TYPE = "APP_IPHONE_DUO"
DUO_SIZES = {(2034, 1398), (1398, 2034), (2853, 2007), (2007, 2853)}
SHOTS_PER_LOCALE = 10
EDITABLE_STATE = "PREPARE_FOR_SUBMISSION"
SETTLED_STATES = {
    "READY_FOR_SALE", "READY_FOR_DISTRIBUTION", "REPLACED_WITH_NEW_VERSION",
    "REMOVED_FROM_SALE", "DEVELOPER_REMOVED_FROM_SALE", "PREORDER_READY_FOR_SALE",
}
REORDER_ERROR = "Relationship when reorder Set"
REORDER_PAUSE = 25
REORDER_ATTEMPTS = 6
SETTLE_TIMEOUT = 600
SETTLE_INTERVAL = 10
WHATS_NEW_LIMIT = 4000
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
CREDENTIALS_FILE = os.environ.get("ASC_CREDENTIALS_ENV", "~/.config/midgar/credentials.env")
CREDENTIAL_KEYS = ("ASC_KEY_ID", "ASC_ISSUER_ID", "ASC_PRIVATE_KEY_PATH")
ASC_TIMEOUT = 900

HEADER = {
    "file": "header-16x9.png",
    "type": "PRODUCT_PAGE_HEADER_ASSET",
    "label": "Header",
    "sizes": {(5244, 2950), (3840, 1646)},
    "ratio_widths": None,
}
SEARCH = {
    "file": "search-3x2.png",
    "type": "APP_STORE_SEARCH_RESULTS_ASSET",
    "label": "Search",
    "sizes": {(5244, 2950)},
    "ratio_widths": (1920, 3840),
}
PLACEMENT_GROUP = "DEFAULT_PROFILE"
USABLE_IMAGE_STATES = ("APPROVED", "PREPARE_FOR_SUBMISSION")


class Fatal(Exception):
    """A condition that stops the run with a message and exit status 1."""


class AscError(Fatal):
    """An asc invocation that exited non-zero, keeping its streams for inspection."""

    def __init__(self, args, stdout, stderr):
        self.stdout = stdout
        self.stderr = stderr
        tail = (stderr.strip() or stdout.strip())[-600:]
        super().__init__("asc %s failed: %s" % (" ".join(shorten(a) for a in args), tail))


def say(text=""):
    """Prints a line and flushes so a long run can be followed live."""
    print(text, flush=True)


def shorten(text, limit=70):
    """Cuts a long argument for display and collapses newlines."""
    text = str(text).replace("\n", "\\n")
    return text if len(text) <= limit else text[:limit - 3] + "..."


def escape_literal(text):
    """Escapes a leading @ so asc does not read the value as @env: or @file:."""
    return "@" + text if text.startswith("@") else text


def asc_environment():
    """The process environment plus asc's API-key variables from the midgar vault.

    With the key in the environment asc skips the keychain, which otherwise hangs forever in a
    non-interactive session. Only the three ASC_* variables are taken from the file.
    """
    environment = dict(os.environ)
    try:
        with open(os.path.expanduser(CREDENTIALS_FILE), encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return environment
    for line in lines:
        match = re.match(r"^\s*(?:export\s+)?(ASC_[A-Z_]+)=(.*)$", line)
        if match and match.group(1) in CREDENTIAL_KEYS:
            value = match.group(2).strip().strip("\"'")
            environment[match.group(1)] = os.path.expandvars(os.path.expanduser(value))
    return environment


class Asc:
    """Runs the asc CLI; in dry-run mode every call carries --read-only and writes are refused."""

    def __init__(self, dry_run):
        self.dry_run = dry_run
        self.environment = asc_environment()

    def command(self, args):
        """The full argv for an asc invocation."""
        prefix = [ASC_BINARY, "--read-only"] if self.dry_run else [ASC_BINARY]
        return prefix + list(args)

    def run(self, args, write=False, check=True):
        """Runs asc and returns (returncode, stdout, stderr); a write in dry-run mode is a bug."""
        if write and self.dry_run:
            raise Fatal("internal error: write call in dry-run: asc %s" % " ".join(args))
        if write:
            say("    $ asc " + " ".join(shorten(a) for a in args))
        try:
            process = subprocess.run(self.command(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     universal_newlines=True, env=self.environment, timeout=ASC_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise AscError(args, "", "timed out after %ds (asc hangs on the keychain without ASC_* credentials)"
                           % ASC_TIMEOUT)
        if check and process.returncode != 0:
            raise AscError(args, process.stdout, process.stderr)
        return process.returncode, process.stdout, process.stderr

    def json(self, args, write=False, check=True):
        """Runs asc with --output json and returns the parsed document, or {} for no output."""
        _, stdout, _ = self.run(list(args) + ["--output", "json"], write=write, check=check)
        if not stdout.strip():
            return {}
        try:
            return json.loads(stdout)
        except ValueError:
            raise Fatal("asc %s did not print JSON: %s" % (" ".join(args[:3]), stdout[:300]))


class Run:
    """The inputs of a stage run and the state discovered while it proceeds."""

    def __init__(self, options):
        self.asc = Asc(options.dry_run)
        self.app = options.app
        self.platform = options.platform
        self.version = options.version
        self.build = str(options.build)
        self.ship = os.path.abspath(os.path.expanduser(options.ship))
        self.whatsnew_path = options.whatsnew
        self.dry_run = options.dry_run
        self.poll_interval = options.poll_interval
        self.build_timeout = options.build_timeout
        self.version_id = None
        self.whatsnew = {}
        self.shots = {}
        self.placement_files = {}


def read_png(path):
    """Returns width, height, bit depth, colour type and whether the PNG carries transparency."""
    with open(path, "rb") as handle:
        if handle.read(8) != PNG_SIGNATURE:
            raise Fatal("%s is not a PNG" % path)
        info = {"transparency": False}
        while True:
            head = handle.read(8)
            if len(head) < 8:
                break
            length, kind = struct.unpack(">I4s", head)
            if kind == b"IHDR":
                width, height, depth, colour = struct.unpack(">IIBB", handle.read(10))
                info.update(width=width, height=height, depth=depth, colour=colour)
                handle.seek(length - 10 + 4, 1)
                continue
            if kind == b"tRNS":
                info["transparency"] = True
            if kind == b"IDAT":
                break
            handle.seek(length + 4, 1)
    if "width" not in info:
        raise Fatal("%s has no IHDR chunk" % path)
    return info


def duo_size_allowed(width, height):
    """True for the four iPhone Duo screenshot sizes."""
    return (width, height) in DUO_SIZES


def placement_size_allowed(spec, width, height):
    """True for a size the placement accepts: listed exactly, or 3:2 within the spec's width range."""
    if (width, height) in spec["sizes"]:
        return True
    low_high = spec["ratio_widths"]
    return bool(low_high) and width * 2 == height * 3 and low_high[0] <= width <= low_high[1]


def png_problems(path, size_allowed):
    """Lists why a PNG cannot be uploaded: alpha, not 8-bit RGB, or a size the predicate refuses."""
    try:
        info = read_png(path)
    except Fatal as error:
        return [str(error)]
    problems = []
    if info["colour"] != 2 or info["depth"] != 8:
        problems.append("%s is not 8-bit RGB (colour type %d, depth %d)" % (path, info["colour"], info["depth"]))
    if info["transparency"]:
        problems.append("%s has a transparency chunk" % path)
    if not size_allowed(info["width"], info["height"]):
        problems.append("%s is %dx%d, not one of the allowed sizes" % (path, info["width"], info["height"]))
    return problems


def scan_shots(ship):
    """Maps each locale folder under <ship>/shots to its sorted PNG paths, validating all of them."""
    root = os.path.join(ship, "shots")
    if not os.path.isdir(root):
        raise Fatal("no shots directory at %s" % root)
    shots, problems = {}, []
    for locale in sorted(os.listdir(root)):
        folder = os.path.join(root, locale)
        if locale.startswith(".") or not os.path.isdir(folder):
            continue
        names = sorted(name for name in os.listdir(folder) if not name.startswith("."))
        paths = [os.path.join(folder, name) for name in names]
        extras = [name for name in names if not name.lower().endswith(".png")]
        if extras:
            problems.append("%s: non-PNG files %s" % (locale, extras))
        if len(names) != SHOTS_PER_LOCALE:
            problems.append("%s: %d files, expected %d" % (locale, len(names), SHOTS_PER_LOCALE))
        expected = ["%02d-" % number for number in range(1, len(names) + 1)]
        if [name[:3] for name in names] != expected:
            problems.append("%s: files are not numbered 01-, 02-, ... in order: %s" % (locale, names))
        for path in paths:
            problems.extend("%s: %s" % (locale, text) for text in png_problems(path, duo_size_allowed))
        shots[locale] = paths
    if not shots:
        problems.append("no locale folders under %s" % root)
    if problems:
        raise Fatal("screenshot inputs are invalid:\n  " + "\n  ".join(problems))
    return shots


def scan_placements(ship):
    """Maps Header and Search to their validated image paths."""
    files, problems = {}, []
    for spec in (HEADER, SEARCH):
        path = os.path.join(ship, "placements", spec["file"])
        if not os.path.isfile(path):
            problems.append("missing %s" % path)
            continue
        problems.extend(png_problems(path, lambda width, height: placement_size_allowed(spec, width, height)))
        files[spec["type"]] = path
    if problems:
        raise Fatal("placement inputs are invalid:\n  " + "\n  ".join(problems))
    return files


def load_whatsnew(path):
    """Reads and validates the {locale: text} What's New file."""
    if not path:
        return {}
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        raise Fatal("cannot read %s: %s" % (path, error))
    problems = []
    if not isinstance(data, dict):
        raise Fatal("%s must be a JSON object of locale to text" % path)
    for locale, text in data.items():
        if not isinstance(text, str) or not text.strip():
            problems.append("%s: empty or not a string" % locale)
        elif len(text) > WHATS_NEW_LIMIT:
            problems.append("%s: %d characters, the limit is %d" % (locale, len(text), WHATS_NEW_LIMIT))
    if problems:
        raise Fatal("What's New file is invalid:\n  " + "\n  ".join(problems))
    return data


def version_states(version):
    """The set of state strings a version reports across both state attributes."""
    attributes = version["attributes"]
    return {attributes.get(key) for key in ("appStoreState", "appVersionState") if attributes.get(key)}


def fetch_versions(run):
    """All App Store versions of the platform, newest first."""
    data = run.asc.json(["versions", "list", "--app", run.app, "--platform", run.platform, "--paginate"])["data"]
    return sorted(data, key=lambda item: item["attributes"].get("createdDate") or "", reverse=True)


def classify_versions(run, versions):
    """Returns the editable version or None, failing on in-flight versions or a clashing version string."""
    editable = [item for item in versions if EDITABLE_STATE in version_states(item)]
    in_flight = [item for item in versions
                 if EDITABLE_STATE not in version_states(item) and not version_states(item) <= SETTLED_STATES]
    if in_flight:
        item = in_flight[0]
        raise Fatal("version %s is %s; resolve it in App Store Connect before staging"
                    % (item["attributes"]["versionString"], "/".join(sorted(version_states(item)))))
    if len(editable) > 1:
        raise Fatal("more than one %s version: %s" % (
            EDITABLE_STATE, ", ".join(item["attributes"]["versionString"] for item in editable)))
    current = editable[0] if editable else None
    for item in versions:
        if item is not current and item["attributes"]["versionString"] == run.version:
            raise Fatal("version %s already exists as %s" % (run.version, "/".join(sorted(version_states(item)))))
    return current


def resource(document):
    """The resource dict of an asc document, whether asc wraps it in `data` or prints it flat."""
    data = document.get("data")
    return data if isinstance(data, dict) else document


def create_version(run):
    """Creates the version and returns its id; a version without localizations is an error."""
    created = run.asc.json(["versions", "create", "--app", run.app, "--version", run.version,
                            "--platform", run.platform], write=True)
    version_id = resource(created).get("id")
    if not version_id:
        raise Fatal("no version id in asc output: %s" % json.dumps(created)[:300])
    if not fetch_localizations(run, version_id):
        raise Fatal("created version %s (%s) has no localizations; delete it and re-run `asc versions create "
                    "--copy-metadata-from <previous version>`" % (run.version, version_id))
    return version_id


def step_version(run):
    """Step 1: reuse (renaming if needed) or create the editable version."""
    say("[1/6] Version")
    versions = fetch_versions(run)
    current = classify_versions(run, versions)
    if current is None:
        if run.dry_run:
            say("  would create version %s (%s); no editable version exists" % (run.version, run.platform))
            return
        run.version_id = create_version(run)
        say("  created version %s (%s)" % (run.version, run.version_id))
        return
    run.version_id = current["id"]
    existing = current["attributes"]["versionString"]
    if existing == run.version:
        say("  reusing editable version %s (%s)" % (existing, run.version_id))
    elif run.dry_run:
        say("  would rename editable version %s to %s (%s)" % (existing, run.version, run.version_id))
    else:
        run.asc.json(["versions", "update", "--version-id", run.version_id, "--version", run.version], write=True)
        say("  renamed editable version %s to %s (%s)" % (existing, run.version, run.version_id))


def fetch_build(run):
    """The build of the requested number on the platform with its marketing version and encryption data."""
    document = run.asc.json(["builds", "list", "--app", run.app, "--platform", run.platform,
                             "--build-number", run.build, "--processing-state", "all",
                             "--include", "preReleaseVersion,appEncryptionDeclaration"])
    builds = [item for item in document.get("data", []) if item["attributes"].get("version") == run.build]
    if not builds:
        return None
    build = builds[0]
    marketing = None
    pre_release = (build.get("relationships", {}).get("preReleaseVersion", {}).get("data") or {}).get("id")
    for item in document.get("included", []):
        if item["type"] == "preReleaseVersions" and item["id"] == pre_release:
            marketing = item["attributes"].get("version")
    declaration = (build.get("relationships", {}).get("appEncryptionDeclaration", {}).get("data") or {}).get("id")
    return {"id": build["id"], "state": build["attributes"].get("processingState"),
            "expired": build["attributes"].get("expired"), "marketing": marketing,
            "encryption": build["attributes"].get("usesNonExemptEncryption"), "declaration": declaration}


def wait_for_build(run):
    """Polls until the build is VALID; fails on a failed, invalid, expired or wrong-version build."""
    started = time.time()
    while True:
        build = fetch_build(run)
        elapsed = int(time.time() - started)
        if build is None:
            report = "build %s not visible yet" % run.build
        else:
            report = "build %s is %s" % (run.build, build["state"])
            if build["state"] in ("FAILED", "INVALID"):
                raise Fatal("build %s is %s in App Store Connect" % (run.build, build["state"]))
            if build["state"] == "VALID":
                return build
        if run.dry_run:
            say("  %s; a real run waits up to %d min (polling every %ds)"
                % (report, run.build_timeout // 60, run.poll_interval))
            return build
        if elapsed >= run.build_timeout:
            raise Fatal("timed out after %d min: %s" % (run.build_timeout // 60, report))
        say("  %s (waited %ds)" % (report, elapsed))
        time.sleep(run.poll_interval)


def check_export_compliance(build):
    """Fails unless the build's export compliance is answered; returns a one-line description."""
    if build["encryption"] is None:
        raise Fatal("build %s has no export compliance answer; set ITSAppUsesNonExemptEncryption in the app "
                    "or answer it in App Store Connect, then re-run" % build["marketing"])
    if build["encryption"] is False:
        return "answered, exempt (usesNonExemptEncryption=false)"
    if not build["declaration"]:
        raise Fatal("build uses non-exempt encryption but no encryption declaration is attached")
    return "answered, declaration %s attached" % build["declaration"]


def attached_build_id(run):
    """The build currently attached to the version, or None."""
    return run.asc.json(["versions", "view", "--version-id", run.version_id, "--include-build"]).get("buildId")


def step_build(run):
    """Step 2: wait for the build, attach it, confirm export compliance."""
    say("[2/6] Build %s" % run.build)
    build = wait_for_build(run)
    if build is None:
        say("  would wait for build %s, then attach it to the version" % run.build)
        return
    if build["state"] != "VALID":
        say("  would wait for build %s to become VALID, then attach it" % run.build)
        return
    if build["expired"]:
        raise Fatal("build %s is expired" % run.build)
    if build["marketing"] != run.version:
        raise Fatal("build %s is marketing version %s, not %s" % (run.build, build["marketing"], run.version))
    say("  build %s is VALID, marketing %s (%s)" % (run.build, build["marketing"], build["id"]))
    say("  export compliance: " + check_export_compliance(build))
    if run.version_id is None:
        say("  would attach build %s once the version exists" % run.build)
    elif attached_build_id(run) == build["id"]:
        say("  build %s already attached" % run.build)
    elif run.dry_run:
        say("  would attach build %s (%s) to the version" % (run.build, build["id"]))
    else:
        run.asc.json(["versions", "attach-build", "--version-id", run.version_id, "--build-id", build["id"]],
                     write=True)
        if attached_build_id(run) != build["id"]:
            raise Fatal("build %s did not attach to the version" % run.build)
        say("  attached build %s" % run.build)


def fetch_localizations(run, version_id):
    """Maps each locale of a version to its localization id and What's New."""
    data = run.asc.json(["localizations", "list", "--version", version_id, "--paginate"])["data"]
    return {item["attributes"]["locale"]: {"id": item["id"], "whatsNew": item["attributes"].get("whatsNew")}
            for item in data}


def step_whatsnew(run):
    """Step 3: set What's New per locale and read every locale back."""
    say("[3/6] What's New")
    if not run.whatsnew:
        say("  no --whatsnew file; skipped")
        return
    if run.version_id is None:
        say("  would set What's New for %d locales once the version exists" % len(run.whatsnew))
        return
    locales = fetch_localizations(run, run.version_id)
    missing = sorted(set(run.whatsnew) - set(locales))
    extra = sorted(set(locales) - set(run.whatsnew))
    if missing:
        say("  WARNING: locales in the JSON that the version lacks (not set): %s" % ", ".join(missing))
    if extra:
        raise Fatal("the version has locales the What's New JSON lacks: %s" % ", ".join(extra))
    for locale in sorted(set(run.whatsnew) & set(locales)):
        if locales[locale]["whatsNew"] == run.whatsnew[locale]:
            continue
        if run.dry_run:
            say("  would set %s" % locale)
            continue
        run.asc.json(["localizations", "update", "--id", locales[locale]["id"],
                      "--whats-new=" + escape_literal(run.whatsnew[locale])], write=True)
    if run.dry_run:
        return
    stored = fetch_localizations(run, run.version_id)
    differing = [locale for locale in sorted(set(run.whatsnew) & set(stored))
                 if stored[locale]["whatsNew"] != run.whatsnew[locale]]
    if differing:
        raise Fatal("What's New read back differs from the JSON for: %s" % ", ".join(differing))
    say("  %d locales set and read back identical" % len(set(run.whatsnew) & set(stored)))


def read_duo_set(run, locale):
    """The Duo screenshots of a locale in set order, as dicts of name, size, state and file size."""
    document = run.asc.json(["screenshots", "list", "--app", run.app, "--version-id", run.version_id,
                             "--locale", locale, "--platform", run.platform])
    for entry in document.get("sets", []):
        if entry["set"]["attributes"].get("screenshotDisplayType") != DUO_DISPLAY_TYPE:
            continue
        shots = []
        for shot in entry.get("screenshots", []):
            attributes = shot["attributes"]
            asset = attributes.get("imageAsset") or {}
            shots.append({"name": attributes.get("fileName"), "size": (asset.get("width"), asset.get("height")),
                          "state": (attributes.get("assetDeliveryState") or {}).get("state"),
                          "bytes": attributes.get("fileSize")})
        return shots
    return []


def local_shot(path):
    """One local screenshot as the same dict shape read_duo_set returns."""
    info = read_png(path)
    return {"name": os.path.basename(path), "bytes": os.path.getsize(path), "size": (info["width"], info["height"])}


def local_set(paths):
    """The expected Duo set for a locale folder, in order."""
    return [local_shot(path) for path in paths]


def already_staged(expected, remote):
    """True when the remote set is the local folder exactly: names, order, sizes, bytes, COMPLETE."""
    if len(expected) != len(remote):
        return False
    return all(want["name"] == have["name"] and want["bytes"] == have["bytes"] and want["size"] == have["size"]
               and have["state"] == "COMPLETE" for want, have in zip(expected, remote))


def judge_set(expected, remote):
    """Compares a remote set with the local folder and returns the table cells plus a list of problems."""
    names = [item["name"] for item in remote]
    problems = []
    count_ok = len(remote) == SHOTS_PER_LOCALE
    order_ok = names == [item["name"] for item in expected]
    duplicates = len(names) - len(set(names))
    states = sorted({str(item["state"]) for item in remote})
    sizes = {item["size"] for item in remote}
    sizes_ok = sizes <= DUO_SIZES
    if not count_ok:
        problems.append("%d screenshots, expected %d" % (len(remote), SHOTS_PER_LOCALE))
    if not order_ok:
        problems.append("order differs: %s" % names)
    if duplicates:
        problems.append("%d duplicate file names" % duplicates)
    if states != ["COMPLETE"]:
        problems.append("states %s" % states)
    if not sizes_ok:
        problems.append("sizes outside the Duo set: %s" % sorted(sizes - DUO_SIZES))
    cells = [str(len(remote)), "ok" if order_ok else "WRONG", str(duplicates), "/".join(states),
             "ok" if sizes_ok else "WRONG"]
    return cells, problems


def settle_set(run, locale):
    """Lists the locale's Duo set, waiting while screenshots are still being processed."""
    started = time.time()
    while True:
        remote = read_duo_set(run, locale)
        states = {item["state"] for item in remote}
        if states <= {"COMPLETE"} or "FAILED" in states or time.time() - started > SETTLE_TIMEOUT:
            return remote
        time.sleep(SETTLE_INTERVAL)


def upload_locale(run, locale):
    """Uploads one locale with --replace --confirm, pausing and retrying on the reorder-set error."""
    folder = os.path.dirname(run.shots[locale][0])
    arguments = ["screenshots", "upload", "--app", run.app, "--version-id", run.version_id, "--locale", locale,
                 "--path", folder, "--device-type", DUO_DEVICE_TYPE, "--platform", run.platform,
                 "--replace", "--confirm"]
    for attempt in range(1, REORDER_ATTEMPTS + 1):
        try:
            run.asc.run(arguments, write=True)
            return
        except AscError as error:
            if REORDER_ERROR not in error.stderr + error.stdout or attempt == REORDER_ATTEMPTS:
                raise
            say("    reorder-set error (attempt %d of %d); pausing %ds" % (attempt, REORDER_ATTEMPTS, REORDER_PAUSE))
            time.sleep(REORDER_PAUSE)


def print_table(header, rows):
    """Prints rows of strings as an aligned table."""
    widths = [max(len(row[column]) for row in [header] + rows) for column in range(len(header))]
    for row in [header] + rows:
        say("  " + "  ".join(cell.ljust(widths[column]) for column, cell in enumerate(row)).rstrip())


def step_screenshots(run):
    """Step 4: upload and verify the Duo set of every locale folder, one locale at a time."""
    say("[4/6] Duo screenshots (%s, %d locales)" % (DUO_DISPLAY_TYPE, len(run.shots)))
    if run.version_id is None:
        say("  would upload %d screenshots for each of: %s" % (SHOTS_PER_LOCALE, ", ".join(sorted(run.shots))))
        return
    on_version = fetch_localizations(run, run.version_id)
    absent = sorted(set(run.shots) - set(on_version))
    if absent:
        raise Fatal("shots folders for locales the version lacks: %s" % ", ".join(absent))
    unmatched = sorted(set(on_version) - set(run.shots))
    if unmatched:
        say("  WARNING: version locales without a shots folder (no Duo screenshots): %s" % ", ".join(unmatched))
    header = ["Locale", "Shots", "Order", "Dups", "State", "Sizes", "Result"]
    rows = []
    for locale in sorted(run.shots):
        expected = local_set(run.shots[locale])
        remote = read_duo_set(run, locale)
        if already_staged(expected, remote):
            action = "already staged"
        elif run.dry_run:
            rows.append([locale, str(len(remote)), "-", "-", "-", "-", "would upload"])
            continue
        else:
            say("  uploading %s" % locale)
            upload_locale(run, locale)
            remote = settle_set(run, locale)
            action = "uploaded"
        cells, problems = judge_set(expected, remote)
        rows.append([locale] + cells + [action if not problems else "MISMATCH"])
        if problems:
            print_table(header, rows)
            raise Fatal("%s: %s" % (locale, "; ".join(problems)))
    print_table(header, rows)


def library_images(run, file_name, size):
    """Usable creative-asset library images that are this file already uploaded (same name and bytes)."""
    document = run.asc.json(["asset-library", "images", "list", "--library-id", run.app,
                             "--category", "CREATIVE_ASSETS", "--paginate"])
    pattern = re.compile(r"^%s( \(\d+\))?$" % re.escape(file_name))
    return [item for item in document.get("data", [])
            if pattern.match(item["attributes"].get("referenceName") or "")
            and item["attributes"].get("fileSize") == size and item["attributes"].get("state") in USABLE_IMAGE_STATES]


def upload_library_image(run, spec, path):
    """Returns the library image id for a placement file, uploading it only if no identical one exists."""
    name = "duo-%s-%s" % (run.version, spec["file"])
    size = os.path.getsize(path)
    existing = library_images(run, name, size)
    if existing:
        say("  %s: reusing library image %s" % (spec["label"], existing[0]["id"]))
        return existing[0]["id"]
    if run.dry_run:
        say("  %s: would upload %s to the asset library" % (spec["label"], name))
        return None
    with tempfile.TemporaryDirectory() as folder:
        staged = os.path.join(folder, name)
        shutil.copyfile(path, staged)
        run.asc.json(["asset-library", "images", "upload", "--library-id", run.app, "--file", staged,
                      "--category", "CREATIVE_ASSETS"], write=True)
    uploaded = library_images(run, name, size)
    if not uploaded:
        raise Fatal("%s image %s is not usable in the library after upload" % (spec["label"], name))
    say("  %s: uploaded library image %s" % (spec["label"], uploaded[0]["id"]))
    return uploaded[0]["id"]


def has_placement(run, localization_id, placement_type):
    """True when the localization already has a placement of this type in the default profile."""
    document = run.asc.json(["localizations", "placements", "list", "--localization-id", localization_id,
                             "--placement-type", placement_type, "--placement-group", PLACEMENT_GROUP,
                             "--paginate"])
    return bool(document.get("data"))


def step_placements(run):
    """Step 5: place Header and Search for every locale, skipping those already placed."""
    say("[5/6] Header and Search Results placements")
    if run.version_id is None:
        say("  would upload both images once and place them for every locale of the new version")
        return
    locales = fetch_localizations(run, run.version_id)
    pending = {}
    for spec in (HEADER, SEARCH):
        pending[spec["type"]] = [locale for locale in sorted(locales)
                                 if not has_placement(run, locales[locale]["id"], spec["type"])]
        placed = sorted(set(locales) - set(pending[spec["type"]]))
        if placed:
            say("  %s already placed, skipping: %s" % (spec["label"], ", ".join(placed)))
    for spec in (HEADER, SEARCH):
        targets = pending[spec["type"]]
        if not targets:
            say("  %s: every locale already placed" % spec["label"])
            continue
        image_id = upload_library_image(run, spec, run.placement_files[spec["type"]])
        for locale in targets:
            if run.dry_run:
                say("  %s: would place for %s" % (spec["label"], locale))
                continue
            run.asc.json(["localizations", "placements", "create", "--localization-id", locales[locale]["id"],
                          "--image-id", image_id, "--placement-type", spec["type"],
                          "--placement-group", PLACEMENT_GROUP], write=True)
        if not run.dry_run:
            missing = [locale for locale in targets if not has_placement(run, locales[locale]["id"], spec["type"])]
            if missing:
                raise Fatal("%s placement missing after create for: %s" % (spec["label"], ", ".join(missing)))
            say("  %s: placed for %d locales" % (spec["label"], len(targets)))


def print_checks(checks):
    """Prints validate findings verbatim: severity, id, message, remediation and where."""
    for check in checks:
        say("  [%s] %s" % (check.get("severity", "?").upper(), check.get("id", "?")))
        say("      %s" % check.get("message", ""))
        if check.get("remediation"):
            say("      fix: %s" % check["remediation"])
        where = [str(check[key]) for key in ("locale", "field", "resourceType", "resourceId") if check.get(key)]
        if where:
            say("      at: %s" % " ".join(where))


def step_validate(run):
    """Step 6: run asc validate and print its errors and warnings; returns the error count."""
    say("[6/6] asc validate")
    if run.version_id is None:
        say("  version does not exist yet; nothing to validate")
        return 0
    _, stdout, stderr = run.asc.run(["validate", "--app", run.app, "--version-id", run.version_id,
                                     "--platform", run.platform, "--output", "json"], check=False)
    try:
        report = json.loads(stdout)
    except ValueError:
        raise Fatal("asc validate printed no report: %s" % (stderr.strip() or stdout.strip())[-400:])
    summary = report.get("summary", {})
    say("  errors %s, warnings %s, infos %s, blocking %s" % (
        summary.get("errors"), summary.get("warnings"), summary.get("infos"), summary.get("blocking")))
    print_checks([check for check in report.get("checks", []) if check.get("severity") in ("error", "warning")])
    return int(summary.get("errors") or 0)


def stage(options):
    """Runs the six staging steps and returns the process exit status."""
    run = Run(options)
    run.whatsnew = load_whatsnew(run.whatsnew_path)
    run.shots = scan_shots(run.ship)
    run.placement_files = scan_placements(run.ship)
    say("%s %s %s build %s, ship %s%s" % (run.app, run.platform, run.version, run.build, run.ship,
                                          "  [DRY RUN: no writes]" if run.dry_run else ""))
    step_version(run)
    step_build(run)
    step_whatsnew(run)
    step_screenshots(run)
    step_placements(run)
    errors = step_validate(run)
    say()
    if run.dry_run:
        say("Dry run complete; nothing was written.")
        return 0
    say("Staged version %s (%s). Review it in App Store Connect, then run: asc-ship.py submit --app %s "
        "--platform %s --version-id %s --confirm" % (run.version, run.version_id, run.app, run.platform,
                                                     run.version_id))
    if errors:
        say("Staging is complete but asc validate reports %d error(s) a person has to fix before submitting." % errors)
        return 2
    return 0


def submission_id(document):
    """Extracts the id from a single-resource asc document."""
    if resource(document).get("id"):
        return resource(document)["id"]
    raise Fatal("no submission id in asc output: %s" % json.dumps(document)[:300])


def submit(options):
    """Creates the review submission, adds the version and submits it; without --confirm only prints the plan."""
    asc = Asc(not options.confirm)
    view = asc.json(["versions", "view", "--version-id", options.version_id, "--include-build"])
    if view.get("platform") != options.platform:
        raise Fatal("version %s is platform %s, not %s" % (options.version_id, view.get("platform"), options.platform))
    if view.get("state") != EDITABLE_STATE:
        raise Fatal("version %s is %s, not %s" % (view.get("versionString"), view.get("state"), EDITABLE_STATE))
    if not view.get("buildId"):
        raise Fatal("version %s has no build attached" % view.get("versionString"))
    say("version %s (%s) is %s with build %s attached" % (view["versionString"], options.version_id,
                                                          view["state"], view.get("buildVersion")))
    existing = asc.json(["review", "submissions-list", "--app", options.app, "--platform", options.platform,
                         "--state", "READY_FOR_REVIEW"]).get("data", [])
    if not options.confirm:
        say("Would %s, add the version as an appStoreVersions item, and submit it. Pass --confirm to do it."
            % ("reuse review submission %s" % existing[0]["id"] if existing else "create a review submission"))
        return 0
    if existing:
        identifier = existing[0]["id"]
        say("reusing review submission %s" % identifier)
    else:
        identifier = submission_id(asc.json(["review", "submissions-create", "--app", options.app,
                                             "--platform", options.platform], write=True))
        say("created review submission %s" % identifier)
    asc.json(["review", "items", "add", "--submission", identifier, "--item-type", "appStoreVersions",
              "--item-id", options.version_id, "--if-exists", "skip"], write=True)
    asc.json(["review", "submissions-submit", "--id", identifier, "--confirm"], write=True)
    state = resource(asc.json(["review", "submissions-get", "--id", identifier])).get("attributes", {}).get("state")
    after = asc.json(["versions", "view", "--version-id", options.version_id])
    say("submission %s is %s; version %s is %s" % (identifier, state, after.get("versionString"), after.get("state")))
    return 0


def build_parser():
    """The command line: stage and submit subcommands."""
    parser = argparse.ArgumentParser(description="Stage and submit an iPhone Duo release with asc.")
    commands = parser.add_subparsers(dest="command", required=True)
    staging = commands.add_parser("stage", help="stage version, build, What's New, screenshots, placements")
    staging.add_argument("--app", required=True)
    staging.add_argument("--platform", required=True, choices=["IOS"])
    staging.add_argument("--version", required=True)
    staging.add_argument("--build", required=True, type=int)
    staging.add_argument("--ship", required=True)
    staging.add_argument("--whatsnew")
    staging.add_argument("--dry-run", action="store_true")
    staging.add_argument("--poll-interval", type=int, default=30)
    staging.add_argument("--build-timeout", type=int, default=2400)
    submission = commands.add_parser("submit", help="create the review submission and submit it")
    submission.add_argument("--app", required=True)
    submission.add_argument("--platform", required=True, choices=["IOS"])
    submission.add_argument("--version-id", required=True)
    submission.add_argument("--confirm", action="store_true")
    return parser


def main():
    """Entry point: dispatches the subcommand and turns failures into messages and exit statuses."""
    options = build_parser().parse_args()
    try:
        return stage(options) if options.command == "stage" else submit(options)
    except Fatal as error:
        print("asc-ship.py: %s" % error, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
