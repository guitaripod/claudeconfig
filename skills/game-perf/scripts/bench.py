#!/usr/bin/env python3
"""Headless benchmark rig: run a Steam/Proton game inside a hidden gamescope and measure it.

    bench.py exes APPID                         list candidate executables (largest first)
    bench.py start APPID --exe REL [--label L] [--refresh 144] [--launcher game-cores|taskset|none]
                   [--args=-nolauncher] [--env K=V ...]
    bench.py shot NAME [--crop WxH+X+Y]         screenshot (1280x720 unless cropped at full res)
    bench.py keys KEY [KEY ...]                 XTest keys: Return, Escape, Down, e, Shift_L+F2,
                                                Return@0.5 (hold), sleep:1.5, mouse:dx,dy,steps
    bench.py measure TAG [--seconds 33]         MangoHud per-frame log (--log-seconds at start) + nvidia-smi
    bench.py place all|p|p+helpers              live thread placement (start with --launcher none)
    bench.py stop                               kill the game, its wineserver and gamescope
    bench.py restore                            put the prefix's user.reg back as it was at first start

Nothing appears on the desktop and audio goes to a null sink. The first `start` backs up
the prefix's user.reg: an SDR headless display makes many games rewrite HDR settings, so
always `restore` before Marcus plays again. Steam must be running (Steamworks DRM).
"""

from __future__ import annotations

import argparse
import ctypes
import glob
import json
import os
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import steamtools  # noqa: E402

STATE_DIR = os.path.join(os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state")), "game-perf")
STATE = os.path.join(STATE_DIR, "bench.json")
NULL_SINK = "gameperf_null"
KEYSYMS = {
    "Return": 0xFF0D, "Escape": 0xFF1B, "space": 0x20, "Tab": 0xFF09, "BackSpace": 0xFF08,
    "Up": 0xFF52, "Down": 0xFF54, "Left": 0xFF51, "Right": 0xFF53, "Shift_L": 0xFFE1,
    "Control_L": 0xFFE3, "Alt_L": 0xFFE9, "F1": 0xFFBE, "F2": 0xFFBF, "F10": 0xFFC7, "F11": 0xFFC8,
}


def _state() -> dict:
    try:
        return json.load(open(STATE))
    except OSError:
        raise SystemExit("no bench session; run `bench.py start` first")
    except ValueError:
        raise SystemExit(f"{STATE} is corrupt; kill the bench gamescope by hand (pgrep -af 'gamescope --backend headless') and delete it")


def _save_state(state: dict) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, STATE)


def _start_time(pid: int) -> str:
    """Process start time in clock ticks, so a recycled pid is never mistaken for the bench gamescope."""
    try:
        raw = open(f"/proc/{pid}/stat").read()
        return raw[raw.rindex(")") + 2:].split()[19]
    except (OSError, ValueError, IndexError):
        return ""


def _our_gamescope(state: dict) -> bool:
    pid = state.get("gamescope_pid", 0)
    return bool(pid) and _start_time(pid) == state.get("gamescope_start") and "gamescope" in open(f"/proc/{pid}/cmdline", "rb").read().decode(errors="replace")


def _ensure_null_sink() -> None:
    sinks = subprocess.run(["pactl", "list", "short", "sinks"], capture_output=True, text=True).stdout
    if NULL_SINK not in sinks:
        subprocess.run(["pactl", "load-module", "module-null-sink", f"sink_name={NULL_SINK}",
                        f"sink_properties=device.description={NULL_SINK}"], capture_output=True)


def _drop_null_sink() -> None:
    mods = subprocess.run(["pactl", "list", "short", "modules"], capture_output=True, text=True).stdout
    for line in mods.splitlines():
        if "module-null-sink" in line and NULL_SINK in line:
            subprocess.run(["pactl", "unload-module", line.split()[0]], capture_output=True)


def cmd_exes(a) -> None:
    root = steamtools.install_dir(a.appid)
    hits = [(os.path.getsize(p), os.path.relpath(p, root)) for p in glob.glob(os.path.join(root, "**", "*.exe"), recursive=True)
            if not re.search(r"(redist|vcredist|directx|crash|crs-|error|report|unins|setup|launcher_helper|easyanticheat|be_service|battleye)", p, re.I)]
    for size, rel in sorted(hits, reverse=True)[:12]:
        print(f"{size/1e6:8.1f} MB  {rel}")


def cmd_start(a) -> None:
    if os.path.exists(STATE) and _our_gamescope(_state()):
        raise SystemExit("a bench session is already running; `bench.py stop` first")
    if not a.exe.lower().endswith(".exe"):
        raise SystemExit("bench.py runs Windows games through Proton only; for a native game use diagnose.py and MangoHud by hand")
    if steamtools.game_running():
        raise SystemExit("a Steam game is running (Marcus may be playing); not starting a bench")
    if not steamtools.steam_running():
        raise SystemExit("Steam is not running; the game needs it for DRM")
    compat = steamtools.compat_data(a.appid)
    exe = os.path.join(steamtools.install_dir(a.appid), a.exe)
    proton = a.proton or steamtools.proton_script(a.appid)
    label = a.label or time.strftime("run-%H%M%S")
    logdir = os.path.join(STATE_DIR, "logs", label)
    os.makedirs(logdir, exist_ok=True)
    backup = os.path.join(STATE_DIR, f"user.reg.{a.appid}.orig")
    if not os.path.exists(backup):
        shutil.copy2(os.path.join(compat, "pfx", "user.reg"), backup)
    _ensure_null_sink()
    conf = os.path.join(logdir, "mangohud.conf")
    open(conf, "w").write(f"fps\nframetime\ngpu_stats\ncpu_stats\nposition=top-left\nfont_size=24\n"
                          f"log_duration={a.log_seconds}\nlog_interval=0\ntoggle_logging=Shift_L+F2\noutput_folder={logdir}\n")
    launcher = {"game-cores": [os.path.expanduser("~/.local/bin/game-cores")], "taskset": ["taskset", "-c", "0-15"], "none": []}[a.launcher]
    env = [f"GAMEPERF_BENCH={label}", f"STEAM_COMPAT_DATA_PATH={compat}", f"STEAM_COMPAT_CLIENT_INSTALL_PATH={steamtools.STEAM_ROOT}",
           f"SteamAppId={a.appid}", f"SteamGameId={a.appid}", f"PULSE_SINK={NULL_SINK}",
           "MANGOHUD=1", f"MANGOHUD_CONFIGFILE={conf}", *a.env]
    cmd = ["/usr/bin/gamescope", "--backend", "headless", "-W", str(a.width), "-H", str(a.height), "-r", str(a.refresh), "--",
           "env", *env, *launcher, proton, "waitforexitandrun", exe, *a.args.split()]
    log = open(os.path.join(logdir, "gamescope.log"), "w")
    gs = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                          preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, []))
    state = {"appid": a.appid, "label": label, "logdir": logdir, "gamescope_pid": gs.pid, "gamescope_start": _start_time(gs.pid),
             "socket": "", "display": "", "launcher": a.launcher, "exe": os.path.basename(exe), "compat": compat, "proton": proton}
    _save_state(state)
    for _ in range(60):
        text = open(log.name, errors="replace").read()
        sock = re.search(r"wayland display '(gamescope-\d+)'", text)
        disp = re.search(r"Starting Xwayland on (:\d+)", text)
        if sock and disp:
            state.update(socket=sock.group(1), display=disp.group(1))
            break
        time.sleep(0.5)
    if not state["display"]:
        cmd_stop(None)
        raise SystemExit(f"gamescope did not report its sockets; stopped it. See {log.name}")
    _save_state(state)
    print(f"started {label}: gamescope pid {gs.pid}, socket {state['socket']}, X {state['display']}; logs {logdir}")


def cmd_shot(a) -> None:
    s = _state()
    out = os.path.join(STATE_DIR, f"{a.name}.png")
    if os.path.exists(out):
        os.remove(out)
    subprocess.run(["gamescopectl", "screenshot", out], env={**os.environ, "GAMESCOPE_WAYLAND_DISPLAY": s["socket"]}, capture_output=True, timeout=15)
    last = -1
    for _ in range(60):
        size = os.path.getsize(out) if os.path.exists(out) else 0
        if size and size == last:
            break
        last = size
        time.sleep(0.5)
    if not last:
        raise SystemExit("screenshot failed (no focused gamescope window yet?)")
    geometry = ["-crop", a.crop, "+repage"] if a.crop else ["-resize", "1280x720"]
    subprocess.run(["magick", out, *geometry, out], check=True)
    print(out)


def cmd_keys(a) -> None:
    s = _state()
    x, t = ctypes.CDLL("libX11.so.6"), ctypes.CDLL("libXtst.so.6")
    x.XOpenDisplay.restype = ctypes.c_void_p
    x.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    x.XFlush.argtypes = [ctypes.c_void_p]
    t.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
    t.XTestFakeRelativeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
    d = x.XOpenDisplay(s["display"].encode())
    if not d:
        raise SystemExit(f"cannot open X display {s['display']}")
    for item in a.keys:
        if item.startswith("sleep:"):
            time.sleep(float(item[6:]))
            continue
        if item.startswith("mouse:"):
            dx, dy, steps = (int(v) for v in item[6:].split(","))
            for _ in range(steps):
                t.XTestFakeRelativeMotionEvent(d, dx, dy, 0)
                x.XFlush(d)
                time.sleep(0.01)
            continue
        combo, _, hold = item.partition("@")
        names = combo.split("+")
        unknown = [k for k in names if k not in KEYSYMS and len(k) != 1]
        if unknown:
            raise SystemExit(f"unknown key name(s) {unknown}; use one character or one of {sorted(KEYSYMS)}")
        codes = [x.XKeysymToKeycode(d, KEYSYMS.get(k, ord(k) if len(k) == 1 else 0)) for k in names]
        if 0 in codes:
            raise SystemExit(f"no keycode for {combo!r} on this X server")
        for c in codes:
            t.XTestFakeKeyEvent(d, c, 1, 0)
            x.XFlush(d)
            time.sleep(0.03)
        time.sleep(float(hold) if hold else 0.12)
        for c in reversed(codes):
            t.XTestFakeKeyEvent(d, c, 0, 0)
            x.XFlush(d)
            time.sleep(0.03)
        time.sleep(0.4)


def cmd_measure(a) -> None:
    s = _state()
    logdir = s["logdir"]
    seen = set(glob.glob(os.path.join(logdir, "*.csv")))
    gpu = subprocess.Popen(["timeout", "-s", "KILL", f"{a.seconds}s", "nvidia-smi", "--query-gpu=utilization.gpu,power.draw",
                            "--format=csv,noheader,nounits", "-lms", "250"], stdout=subprocess.PIPE, text=True,
                           preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK, []))
    cmd_keys(argparse.Namespace(keys=["Shift_L+F2"]))
    out, _ = gpu.communicate()
    deadline = time.time() + 15
    new = []
    while time.time() < deadline and not new:
        new = [f for f in glob.glob(os.path.join(logdir, "*.csv")) if f not in seen and not f.endswith("_summary.csv")]
        time.sleep(1)
    if not new:
        raise SystemExit("MangoHud wrote no log (is the game's Vulkan swapchain up, and log_duration <= --seconds?)")
    rows = list(__import__("csv").reader(open(max(new, key=os.path.getmtime))))
    head = next(i for i, r in enumerate(rows) if r and r[0] == "fps")
    col = rows[head].index("frametime")
    ft = sorted(float(r[col]) for r in rows[head + 1:] if r and r[0])
    g = [list(map(float, l.split(","))) for l in out.splitlines() if l.strip()]
    p99 = ft[max(int(len(ft) * 0.99) - 1, 0)]
    print(f"{a.tag:24s} avg {1000/statistics.fmean(ft):6.1f} fps  1% low {1000/p99:6.1f}  jitter {statistics.pstdev(ft):4.2f} ms  "
          f"frames {len(ft):5d}  gpu {statistics.fmean(x[0] for x in g):4.1f}% {statistics.fmean(x[1] for x in g):4.0f} W  "
          f"load {open('/proc/loadavg').read().split()[0]}")


def _bench_processes(label: str) -> list[int]:
    """Pids carrying this session's GAMEPERF_BENCH marker, so a game Marcus launches through Steam is never touched."""
    marker = f"GAMEPERF_BENCH={label}".encode()
    found = []
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            env = open(f"/proc/{pid}/environ", "rb").read().split(b"\0")
        except OSError:
            continue
        if marker in env and int(pid) != os.getpid():
            found.append(int(pid))
    return found


def cmd_stop(_a) -> None:
    s = _state()
    if steamtools.game_running():
        raise SystemExit("a Steam-launched game is running and may share this prefix's wineserver; wait until it exits, then stop")
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for pid in _bench_processes(s["label"]):
            try:
                os.kill(pid, sig)
            except OSError:
                pass
        time.sleep(3)
    if _our_gamescope(s):
        try:
            os.killpg(s["gamescope_pid"], signal.SIGKILL)
        except OSError:
            pass
    _drop_null_sink()
    left = _bench_processes(s["label"])
    print("stopped" if not left else f"still alive in the prefix: {left}")


def _game_cores_module():
    """Loads ~/.local/bin/game-cores so live placement uses exactly the patterns Marcus plays with."""
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader("game_cores", os.path.expanduser("~/.local/bin/game-cores"))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader("game_cores", loader))
    loader.exec_module(module)
    return module


def cmd_place(a) -> None:
    s = _state()
    if s.get("launcher") == "game-cores":
        raise SystemExit("this session runs under game-cores, which re-pins every 2 s; start with --launcher none for live A/B")
    gc = _game_cores_module()
    p_cores, e_cores = gc._cpu_list("/sys/devices/cpu_core/cpus"), gc._cpu_list("/sys/devices/cpu_atom/cpus")
    helpers = re.compile(os.environ.get("GAME_CORES_HELPERS", gc.DEFAULT_HELPER_THREADS))
    moved = {"P": 0, "E": 0, "all": 0}
    for pid in _bench_processes(s["label"]):
        helper_process = bool(gc.HELPER_PROCESSES.search(gc._read(f"/proc/{pid}/cmdline").replace("\0", " ")))
        try:
            tids = os.listdir(f"/proc/{pid}/task")
        except OSError:
            continue
        for tid in tids:
            name = gc._read(f"/proc/{pid}/task/{tid}/comm").rstrip("\n")
            if a.layout == "all":
                cpus, key = p_cores | e_cores, "all"
            elif a.layout == "p":
                cpus, key = p_cores, "P"
            else:
                on_e = helper_process or bool(helpers.match(name))
                cpus, key = (e_cores, "E") if on_e else (p_cores, "P")
            gc._pin(int(tid), cpus)
            moved[key] += 1
    print(f"placed {a.layout}: {moved}")


def cmd_restore(_a) -> None:
    s = _state()
    backup = os.path.join(STATE_DIR, f"user.reg.{s['appid']}.orig")
    if steamtools.game_running() or _bench_processes(s["label"]):
        raise SystemExit("the game is running (bench or Steam); stop it first, the prefix's wineserver would overwrite user.reg")
    shutil.copy2(backup, os.path.join(s["compat"], "pfx", "user.reg"))
    os.remove(backup)
    print("user.reg restored; re-apply any registry setting you meant to keep")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("exes"); p.add_argument("appid"); p.set_defaults(fn=cmd_exes)
    p = sub.add_parser("start"); p.add_argument("appid"); p.add_argument("--exe", required=True)
    p.add_argument("--label"); p.add_argument("--refresh", type=int, default=144)
    p.add_argument("--width", type=int, default=3840); p.add_argument("--height", type=int, default=2160)
    p.add_argument("--launcher", choices=["game-cores", "taskset", "none"], default="game-cores")
    p.add_argument("--args", default=""); p.add_argument("--proton"); p.add_argument("--log-seconds", type=int, default=30)
    p.add_argument("--env", nargs="*", default=[]); p.set_defaults(fn=cmd_start)
    p = sub.add_parser("shot"); p.add_argument("name"); p.add_argument("--crop"); p.set_defaults(fn=cmd_shot)
    p = sub.add_parser("keys"); p.add_argument("keys", nargs="+"); p.set_defaults(fn=cmd_keys)
    p = sub.add_parser("measure"); p.add_argument("tag"); p.add_argument("--seconds", type=int, default=33); p.set_defaults(fn=cmd_measure)
    p = sub.add_parser("place"); p.add_argument("layout", choices=["all", "p", "p+helpers"]); p.set_defaults(fn=cmd_place)
    p = sub.add_parser("stop"); p.set_defaults(fn=cmd_stop)
    p = sub.add_parser("restore"); p.set_defaults(fn=cmd_restore)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
