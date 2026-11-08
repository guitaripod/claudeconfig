#!/usr/bin/env python3
"""Live snapshot of why a running Proton/Wine game leaves the GPU idle (or not).

    diagnose.py [--seconds 8] [--pid PID]

Without --pid it picks the Wine process with the most CPU time whose command line ends in
.exe (the game). Prints GPU state and throttle reasons, per-thread CPU split into user and
kernel time with E-core residency, spin-wait suspects, Wine/MangoHud overhead, the game's
relevant environment, and background contention (local LLM traffic, shader pre-caching,
load, pressure). Read-only: safe to run while Marcus plays.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import time

HZ = os.sysconf("SC_CLK_TCK")
ENV_KEYS = re.compile(r"^(PROTON_|DXVK|VKD3D|WINE(?!PREFIX|DLLPATH|_LD)|MANGOHUD|DXVK_NVAPI|__GL_SYNC|ENABLE_GAMESCOPE|WAYLANDDRV|SteamAppId=)")


def sh(*cmd: str) -> str:
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def cpu_set(path: str) -> set[int]:
    try:
        text = open(path).read().strip()
    except OSError:
        return set()
    out: set[int] = set()
    for part in filter(None, text.split(",")):
        a, _, b = part.partition("-")
        out.update(range(int(a), int(b or a) + 1))
    return out


def read(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return f.read().decode(errors="replace")
    except OSError:
        return ""


def stat_fields(path: str) -> list[str] | None:
    raw = read(path)
    try:
        return raw[raw.rindex(")") + 2:].split()
    except ValueError:
        return None


def comm(path: str) -> str:
    return read(path).rstrip("\n") or "?"


def find_game() -> int:
    """The busiest live process whose command line ends in .exe (args allowed after it)."""
    best, best_ticks = 0, -1
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            cmd = open(f"/proc/{pid}/cmdline", "rb").read().split(b"\0")[0].decode(errors="replace")
        except OSError:
            continue
        if not re.search(r"\.exe$", cmd, re.I) or re.search(r"(steam|explorer|services|winedevice|crs-handler|rpcss|plugplay|svchost|start)\.exe$", cmd, re.I):
            continue
        f = stat_fields(f"/proc/{pid}/stat")
        if f and f[0] != "Z" and int(f[11]) + int(f[12]) > best_ticks:
            best, best_ticks = int(pid), int(f[11]) + int(f[12])
    if not best:
        raise SystemExit("no running .exe game found; pass --pid")
    return best


def threads(pid: int) -> dict[int, tuple[str, int, int, int]]:
    out = {}
    try:
        tids = os.listdir(f"/proc/{pid}/task")
    except OSError:
        raise SystemExit(f"process {pid} exited")
    for tid in tids:
        f = stat_fields(f"/proc/{pid}/task/{tid}/stat")
        if f:
            out[int(tid)] = (comm(f"/proc/{pid}/task/{tid}/comm"), int(f[11]), int(f[12]), int(f[36]))
    return out


def gpu_report() -> None:
    q = "name,utilization.gpu,clocks.gr,clocks.max.gr,power.draw,power.limit,temperature.gpu,memory.used,memory.total,pstate"
    print("GPU:", sh("nvidia-smi", f"--query-gpu={q}", "--format=csv,noheader").strip())
    perf = sh("nvidia-smi", "-q", "-d", "PERFORMANCE")
    active = [l.split(":")[0].strip() for l in perf.splitlines() if l.strip().endswith(": Active")]
    print("  clock event reasons active:", ", ".join(active) or "none", "(Reliability alone = normal boost voltage limit)")
    procs = sh("nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader").strip().splitlines()
    heavy = [p for p in procs if re.search(r"llama|python|vllm|comfy|ollama", p, re.I)]
    print(f"  {len(procs)} compute processes on the GPU; ML ones: {'; '.join(h.strip()[:90] for h in heavy) or 'none'}")


def contention_report() -> None:
    print("Load:", open("/proc/loadavg").read().split()[:3], " PSI cpu/io/mem some avg10:",
          [open(f"/proc/pressure/{r}").readline().split()[1] for r in ("cpu", "io", "memory")])
    fossil = sh("pgrep", "-fc", "fossilize_replay").strip()
    print(f"  fossilize_replay processes (Steam/prebake shader pre-caching): {fossil}")
    posts = sh("journalctl", "--user", "-u", "llama-swap", "--since", "-10min", "--no-pager", "-o", "cat").count("POST ")
    print(f"  local LLM requests through llama-swap in the last 10 min: {posts}")
    top = sh("ps", "-eo", "pcpu,comm", "--sort=-pcpu").splitlines()[1:9]
    print("  top processes:", "; ".join(" ".join(l.split()) for l in top))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int)
    ap.add_argument("--seconds", type=float, default=8)
    a = ap.parse_args()
    pid = a.pid or find_game()
    e_cores = cpu_set("/sys/devices/cpu_atom/cpus")
    if not os.path.isdir(f"/proc/{pid}"):
        raise SystemExit(f"no process {pid}")
    print(f"Game pid {pid}: {read(f'/proc/{pid}/cmdline').split(chr(0))[0]}")
    gpu_report()

    before = threads(pid)
    samples, on_e = 0, {}
    t0 = time.monotonic()
    t_end = time.time() + a.seconds
    util = []
    while time.time() < t_end:
        for tid in list(before):
            f = stat_fields(f"/proc/{pid}/task/{tid}/stat")
            if f and int(f[36]) in e_cores:
                on_e[tid] = on_e.get(tid, 0) + 1
        u = sh("nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits").strip()
        util.append(int(u) if u.isdigit() else 0)
        samples += 1
        time.sleep(0.25)
    after = threads(pid)
    secs = time.monotonic() - t0
    rows = []
    for tid, (name, u0, s0, _) in before.items():
        if tid in after:
            u1, s1 = after[tid][1], after[tid][2]
            usr, sys_ = (u1 - u0) / HZ / secs * 100, (s1 - s0) / HZ / secs * 100
            rows.append((usr + sys_, usr, sys_, tid, name, 100 * on_e.get(tid, 0) / max(samples, 1)))
    rows.sort(reverse=True)
    total = sum(r[0] for r in rows)
    print(f"\nGPU util over {secs:.0f}s: avg {sum(util)/max(len(util),1):.0f}%  min {min(util or [0])}  max {max(util or [0])}")
    print(f"Game CPU {total:.0f}% across {len(rows)} threads. Hot threads (usr/sys, share of samples on E-cores):")
    for tot, usr, sys_, tid, name, e in rows[:14]:
        if tot < 3:
            break
        flag = "  <- pegged" if tot > 90 else ""
        print(f"  {tot:5.0f}%  usr {usr:4.0f} sys {sys_:4.0f}  E {e:3.0f}%  {tid:>8} {name}{flag}")
    print("  A thread pegged at ~100% usr that stays pegged in the pause menu is a spin-wait, not the bottleneck.")
    print("  Nothing near 100% while the GPU idles = latency-bound thread chain: placement and CPU-cost settings matter.")

    for name in ("wineserver",):
        for w in sh("pgrep", "-x", name).split():
            f0 = stat_fields(f"/proc/{w}/stat")
            time.sleep(1)
            f1 = stat_fields(f"/proc/{w}/stat")
            if f0 and f1:
                print(f"{name} {w}: {(int(f1[11])+int(f1[12])-int(f0[11])-int(f0[12]))/HZ*100:.0f}% of a core")
    mh = [r for r in rows if r[4].startswith("mangohud-nvidia")]
    if mh:
        print(f"mangohud-nvidia thread: {mh[0][2]:.0f}% kernel time (NVML polling; ~20% means the unpatched 0.8.4 process-list poll)")
    print("mangohud package:", sh("pacman", "-Q", "mangohud").strip())

    env = read(f"/proc/{pid}/environ").split("\0")
    print("\nGame env:", " ".join(e for e in env if ENV_KEYS.match(e) and not re.search(r"KEY|TOKEN|SECRET|PASS", e)))
    print("Affinity:", sh("taskset", "-pc", str(pid)).strip().split(":")[-1].strip())
    print()
    contention_report()


if __name__ == "__main__":
    main()
