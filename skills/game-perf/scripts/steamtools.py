"""Steam plumbing for game-perf: find a game's install, prefix and Proton, and edit its launch options.

Steam rewrites localconfig.vdf from memory when it exits, so launch options are only written
with Steam stopped, and Steam is started again afterwards through systemd so it does not
inherit the agent shell's signal mask.
"""

from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

STEAM_ROOT = os.path.realpath(os.path.expanduser("~/.steam/steam"))
STEAM_START = ["/usr/bin/steam", "-cef-force-glx"]


def library_paths() -> list[str]:
    """Every Steam library root listed in libraryfolders.vdf."""
    text = open(os.path.join(STEAM_ROOT, "steamapps", "libraryfolders.vdf"), encoding="utf-8").read()
    paths = re.findall(r'"path"\s+"([^"]+)"', text)
    return [os.path.realpath(p) for p in paths] or [STEAM_ROOT]


def app_manifest(appid: str) -> tuple[str, dict[str, str]]:
    """Returns (library root, manifest fields) for an installed appid."""
    for lib in library_paths():
        path = os.path.join(lib, "steamapps", f"appmanifest_{appid}.acf")
        if os.path.exists(path):
            fields = dict(re.findall(r'^\s*"(\w+)"\s+"([^"]*)"', open(path, encoding="utf-8").read(), re.M))
            return lib, fields
    raise SystemExit(f"appid {appid} is not installed in any Steam library")


def install_dir(appid: str) -> str:
    lib, fields = app_manifest(appid)
    return os.path.join(lib, "steamapps", "common", fields["installdir"])


def compat_data(appid: str) -> str:
    """The Proton prefix root (the directory holding pfx/) for appid, preferring the game's own library as Steam does."""
    home, _ = app_manifest(appid)
    for lib in [home] + [l for l in library_paths() if l != home]:
        path = os.path.join(lib, "steamapps", "compatdata", appid)
        if os.path.isdir(os.path.join(path, "pfx")):
            return path
    raise SystemExit(f"no compatdata/{appid}/pfx in any library; launch the game once through Steam first")


def _mapping_name(appid: str) -> str:
    """The compat tool name Steam maps appid to, or the global default ("0") mapping."""
    text = open(os.path.join(STEAM_ROOT, "config", "config.vdf"), encoding="utf-8", errors="replace").read()
    at = text.find('"CompatToolMapping"')
    if at < 0:
        raise SystemExit("config.vdf has no CompatToolMapping; set a Proton for the game in Steam once")
    block = text[at:]
    for key in (appid, "0"):
        m = re.search(r'"%s"\s*\{[^}]*?"name"\s+"([^"]*)"' % re.escape(key), block)
        if m and m.group(1):
            return m.group(1)
    raise SystemExit(f"no compat tool mapped for {appid} and no default")


def proton_script(appid: str) -> str:
    """Absolute path of the proton script Steam would run for appid."""
    name = _mapping_name(appid)
    custom = os.path.join(STEAM_ROOT, "compatibilitytools.d")
    for vdf in glob.glob(os.path.join(custom, "*", "compatibilitytool.vdf")):
        if re.search(r'"%s"\s*(//[^\n]*)?\s*\{' % re.escape(name), open(vdf, errors="replace").read()):
            return os.path.join(os.path.dirname(vdf), "proton")
    if os.path.exists(os.path.join(custom, name, "proton")):
        return os.path.join(custom, name, "proton")
    valve = {"proton_experimental": "Proton - Experimental", "proton_hotfix": "Proton Hotfix"}
    m = re.fullmatch(r"proton_(\d+)", name)
    patterns = [valve[name]] if name in valve else [f"Proton {m.group(1)}.0*"] if m else [name]
    hits = sorted({h for lib in library_paths() for pattern in patterns
                   for h in glob.glob(os.path.join(lib, "steamapps", "common", pattern, "proton"))})
    if len(hits) == 1:
        return hits[0]
    if hits:
        raise SystemExit(f"{name!r} matches several Proton builds {hits}; pass --proton")
    raise SystemExit(f"cannot locate compat tool {name!r} for {appid}; pass --proton")


def localconfig() -> str:
    ids = [d for d in os.listdir(os.path.join(STEAM_ROOT, "userdata")) if d.isdigit() and d != "0"]
    if len(ids) != 1:
        raise SystemExit(f"ambiguous Steam userdata ids {ids}")
    return os.path.join(STEAM_ROOT, "userdata", ids[0], "config", "localconfig.vdf")


def _app_block(text: str, appid: str) -> tuple[int, int]:
    """Span of the per-app block under UserLocalConfigStore/Software/Valve/Steam/apps."""
    apps = text.find('\t\t\t\t"apps"\n')
    start = text.find(f'\n\t\t\t\t\t"{appid}"\n', apps)
    if apps < 0 or start < 0:
        raise SystemExit(f"appid {appid} has no block in localconfig.vdf; launch it once through Steam")
    end = text.find("\n\t\t\t\t\t}\n", start)
    return start, end


def _unescape(value: str) -> str:
    return value.replace('\\"', '"').replace("\\\\", "\\")


def get_launch_options(appid: str) -> str:
    text = open(localconfig(), encoding="utf-8").read()
    start, end = _app_block(text, appid)
    m = re.search(r'\n\t{6}"LaunchOptions"\t\t"((?:[^"\\]|\\.)*)"', text[start:end])
    return _unescape(m.group(1)) if m else ""


def steam_running() -> bool:
    return subprocess.run(["pgrep", "-x", "steam"], capture_output=True).returncode == 0


def bench_running() -> bool:
    """True while any process carries a game-perf bench marker (a headless game under the Steam client)."""
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            if b"GAMEPERF_BENCH=" in open(f"/proc/{pid}/environ", "rb").read():
                return True
        except OSError:
            continue
    return False


def game_running() -> bool:
    """True while any Steam-launched game (its reaper) is alive, judged by argv so a shell quoting the words never counts."""
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            argv = open(f"/proc/{pid}/cmdline", "rb").read().split(b"\0")
        except OSError:
            continue
        if len(argv) > 1 and argv[0].endswith(b"/reaper") and argv[1] == b"SteamLaunch":
            return True
    return False


def stop_steam(timeout: int = 90) -> None:
    if game_running() or bench_running():
        raise SystemExit("a game (Steam-launched or bench) is running; refusing to stop Steam")
    subprocess.run(["/usr/bin/steam", "-shutdown"], capture_output=True)
    deadline = time.time() + timeout
    while steam_running() and time.time() < deadline:
        time.sleep(1)
    if steam_running():
        raise SystemExit("Steam did not exit")


def start_steam() -> None:
    unit = f"app-steam-gameperf-{os.getpid()}-{time.time_ns()}"
    subprocess.run(["systemd-run", "--user", "--collect", "--quiet", f"--unit={unit}", *STEAM_START], check=True)
    deadline = time.time() + 90
    while not steam_running():
        if time.time() > deadline:
            raise SystemExit("Steam did not come back within 90 s; start it by hand")
        time.sleep(1)


def _with_options(text: str, appid: str, options: str) -> str:
    """Returns localconfig text with appid's LaunchOptions set, validating everything first."""
    if re.search(r"[\x00-\x1f]", options):
        raise SystemExit("launch options contain control characters (newline/tab); refusing")
    start, end = _app_block(text, appid)
    block = text[start:end]
    line = '\t\t\t\t\t\t"LaunchOptions"\t\t"' + options.replace("\\", "\\\\").replace('"', '\\"') + '"'
    existing = re.findall(r'\n\t{6}"LaunchOptions"\t\t"(?:[^"\\]|\\.)*"', block)
    if len(existing) > 1:
        raise SystemExit("LaunchOptions appears twice in the app block; edit by hand")
    block = block.replace(existing[0], "\n" + line) if existing else block.replace("\n\t\t\t\t\t{\n", "\n\t\t\t\t\t{\n" + line + "\n", 1)
    out = text[:start] + block + text[end:]
    if out.count("{") != text.count("{") or out.count("}") != text.count("}"):
        raise SystemExit("brace balance changed; aborting without writing")
    return out


def _write_atomic(path: str, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".localconfig-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    shutil.copymode(path, tmp)
    os.replace(tmp, path)


def set_launch_options(appid: str, options: str) -> str:
    """Stops Steam, writes the options (backing up localconfig.vdf), starts Steam; returns the backup path."""
    path = localconfig()
    _with_options(open(path, encoding="utf-8").read(), appid, options)
    stop_steam()
    try:
        backup = f"{path}.bak-gameperf-{appid}-{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(path, backup)
        _write_atomic(path, _with_options(open(path, encoding="utf-8").read(), appid, options))
    finally:
        start_steam()
    if get_launch_options(appid) != options:
        raise SystemExit("launch options did not read back as written")
    return backup


def restore_backup(backup: str) -> None:
    """Puts a localconfig.vdf backup back with Steam stopped, then starts Steam."""
    stop_steam()
    try:
        shutil.copy2(backup, localconfig())
    finally:
        start_steam()


def main() -> None:
    usage = ("steamtools.py info APPID | get APPID | set APPID 'OPTIONS' | backups APPID | restore BACKUP\n"
             "set and restore stop and restart Steam and refuse while a game runs.")
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(usage)
        return
    cmd, rest = args[0], args[1:]
    if cmd == "info" and len(rest) == 1:
        _, fields = app_manifest(rest[0])
        print(f"name: {fields.get('name')}\ninstall: {install_dir(rest[0])}\nprefix: {compat_data(rest[0])}\nproton: {proton_script(rest[0])}")
        print(f"launch options: {get_launch_options(rest[0])}")
    elif cmd == "get" and len(rest) == 1:
        print(get_launch_options(rest[0]))
    elif cmd == "set" and len(rest) == 2:
        print("backup:", set_launch_options(rest[0], rest[1]))
    elif cmd == "backups" and len(rest) == 1:
        print("\n".join(sorted(glob.glob(localconfig() + ".bak-*"))))
    elif cmd == "restore" and len(rest) == 1:
        restore_backup(rest[0])
        print("restored", rest[0])
    else:
        raise SystemExit(usage)


if __name__ == "__main__":
    main()
