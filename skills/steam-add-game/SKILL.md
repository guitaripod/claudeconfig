---
description: Install a DRM-free/scene PC game from an archive set and integrate it fully into Steam on Linux — triage the release type, extract, install the Windows installer under wine, add a non-Steam shortcut with the right Proton and launch options, fetch SteamGridDB artwork and a multi-res icon, then launch it and verify it actually runs. Use when asked to "get this game running on Steam", "add artwork to it", set up a downloaded game folder, judge whether a release/repack will install at all, or fix icons/launch options on existing non-Steam shortcuts.
---

# Game → fully integrated Steam entry (Linux)

Takes a downloaded game directory (RAR set, ISO, or already-extracted tree) to a Steam
library entry that is indistinguishable from an owned game: correct Proton, house-style
launch options, portrait/wide/hero/logo artwork, a sharp icon, and a verified launch.

## When to use

- "Get this running on Steam" / "add this game to Steam" pointed at a folder
- "Add artwork to it", "fix the icon", "fix the launch args" for non-Steam shortcuts
- Applying a launch-option policy across the library

Not for owned Steam games that just need installing — that's the client's job.

## The five things that break naive attempts

1. **Steam owns those files while it runs.** `shortcuts.vdf`, `localconfig.vdf` and
   `config.vdf` are all rewritten from memory when Steam exits, silently discarding any
   edit made while it was up. Every write here must be: stop Steam → edit → start Steam →
   re-read the file to confirm the values survived. `steamlib.require_steam_stopped()`
   enforces the first half; you must still do the read-back.
2. **The appid is a hash, not a counter.**
   `zlib.crc32(exe_with_surrounding_quotes + appname) | 0x80000000`. Renaming the entry
   or moving the exe changes it and orphans the artwork. To launch:
   `steam steam://rungameid/<(appid << 32) | 0x02000000>` — omit the `0x02000000` and
   Steam silently does nothing.
3. **`pgrep -f <exe>` matches the shell that's watching for it.** A wait loop like
   `while pgrep -f eldenring.exe; do sleep 20; done` never exits, because the loop's own
   command line contains the pattern. Use `pgrep -x`.
4. **Launch options carry game arguments you must not drop.** Diablo III's is
   `--exec="launch D3"`; several titles carry `+com_skipIntroVideo 1`,
   `WINEDLLOVERRIDES=`, `-dx11`. Rewriting the string wholesale destroys them —
   `launch_policy.py --merge` re-attaches anything after `%command%` plus game-side env.
5. **The icon comes from the `icon` field, not the grid folder.** A `<appid>_icon.png` in
   `grid/` alone leaves the library entry blank. Point `icon` at a real `.ico` on disk.

## Phase 0 — Triage the release type, before downloading anything

Two families, and only one of them installs on this box.

**Scene releases — fine.** RUNE, EMPRESS, CODEX, TENOKE, FLT, DODI's *ISO* rips. Shipped
as a RAR set containing an ISO with `setup.exe` + `setup-N.bin`, an Inno Setup or plain
file-copy installer, and a crack directory that mirrors the install tree. These run
silently under plain wine — continue to Phase 1.

**Repacks — dead end, say so instead of starting.** FitGirl, DODI's repacks, Xatab,
KaOsKrew, ElAmigos when it ships `ISDone.dll`. They decompress at install time through
`ISDone.dll` + `unarc` with Razor12911's codecs, which fails under Wine/Proton
(`unarc` error `-11`, bogus "not enough memory"). Not fixable with a Proton version, a
prefix tweak, or `winetricks`. Confirmed on DODI; FitGirl is the canonical case.

**Marcus does not use FitGirl repacks.** If the only release for a title is a repack,
tell him up front and stop — don't sink hours into a VM install he didn't ask for.
The fallback, if he does want it, is the scripted qemu Windows VM. At repack sizes
(100 GB+) do **not** use the HTTP-over-`10.0.2.2` transfer from that note: attach the
target storage to the VM as a virtio block device (raw disk or partition, NTFS), install
into it, then mount it on the host — `ntfs3` reads it and Proton runs the game in place,
so there is no copy step. FitGirl installers also want Windows 7 compatibility mode and
≥4 GB free RAM; give the guest 8 GB+ and 8 vCPUs or a 1.5 h install becomes 3 h.

**EMPRESS cracks are a second, independent blocker.** Even installed correctly from a
Windows VM, the EMPRESS build of AC Odyssey silently exits ~20 s in under every Proton and
wine configuration tried (DXVK and wined3d, gamescope, esync/fsync/ntsync off, nvapi off,
core-affinity limits). The crack, not the install, is what fails. For anything that has to
run on Linux, prefer a non-EMPRESS release — and note AC Odyssey specifically was already
taken all the way through the VM route on 2026-07-28 and still did not run.

Tells, from the release notes alone: "Repack by …", "compression library by Razor12911",
"Selective Download", `fg-selective-*.bin`, "lossless … all files identical to originals
after installation", a multi-hour CPU-bound install time. Any of those means repack.

## Phase 1 — Identify and extract

```bash
ls <dir>                                     # .rar + .r00.. set, or .iso, or a game tree
unrar l <dir>/*.rar | head -20               # what's inside
df -h <target-drive>                         # extracted ISO + install ≈ 2× the ISO size
```

RAR set → ISO:

```bash
unrar x -o+ <dir>/rune-*.rar /path/staging/   # run in background; 66 GB takes ~10 min
```

Mount without root (`sudo` needs a password this box does not have non-interactively):

```bash
udisksctl loop-setup -r -f /path/staging/game.iso     # -> /dev/loopN
udisksctl mount -b /dev/loopN                         # -> /run/media/$USER/<label>
```

Identify the installer before running anything:

```bash
strings -n 8 "$M/setup.exe" | grep -iE "inno setup|installshield|nullsoft|nsis" | sort -u
```

## Phase 2 — Install

**Inno Setup** (`setup.exe` + `setup-N.bin`) runs fine under plain wine, silently:

```bash
export WINEPREFIX=/path/_tmp_wine WINEDEBUG=-all
wineboot -u
cd "$MOUNT"
wine setup.exe /SP- /SILENT /SUPPRESSMSGBOXES /NOCANCEL /NORESTART /NOICONS \
  '/DIR=Z:\path\to\Games\GAME NAME' '/LOG=Z:\tmp\inno.log'
```

Watch `/tmp/inno.log` for `Installation process succeeded.` — the wine stderr is full of
harmless `libEGL`/`wineusb` noise and is not a progress signal.

Then, if the release ships a crack directory that mirrors the install layout:

```bash
cp -rv "$MOUNT/RUNE/." "$INSTALL/"
```

Afterwards unmount, delete the ISO and the throwaway prefix — Steam builds its own
prefix under `compatdata/<appid>`.

If `strings` turns up `ISDone` or `unarc` rather than an installer name, you have a repack
and Phase 0 applies — stop here.

## Phase 3 — Shortcut, Proton, launch options

Pick the exe that bypasses anti-cheat when the release is offline-only
(`eldenring.exe`, not `start_protected_game.exe`).

```bash
python3 scripts/launch_policy.py --profile nonshooter        # or shooter
python3 scripts/steam_shortcut.py add \
  --name "ELDEN RING Shadow of the Erdtree" \
  --exe "/mnt/nvme8tb/Games/ELDEN RING/Game/eldenring.exe" \
  --launch "$(python3 scripts/launch_policy.py --profile nonshooter)" \
  --proton GE-Proton10-34 --apply
```

`add` prints the appid and the `rungameid`. Proton mapping lands in
`~/.steam/steam/config/config.vdf` → `CompatToolMapping`, **not** localconfig.

Profile choice: `nonshooter` wraps in `rpd-gamescope` (auto-sizes to the live output, so
Remote Play gets the dummy's mode and HDR follows the real display); `shooter` stays on
bare `mangohud`. Latency-critical PvP gets the `shooter` profile whatever its genre —
MOBAs, RTS ladder, fighting games. Never put gamescope in front of those.

## Phase 4 — Artwork

```bash
python3 scripts/steam_artwork.py search "elden ring"
python3 scripts/steam_artwork.py preview --game 5452291 --limit 3
# Read the montage-*.png files, then:
python3 scripts/steam_artwork.py install --appid 3828612727 --game 5452291 --pick icon=2
python3 scripts/steam_shortcut.py set-icon --appid 3828612727 --apply
```

The SteamGridDB key already lives at `~/.config/steamgriddb/key` on this box (machine-local,
never in this repo). The API 403s the default urllib User-Agent, which the script sets.

Look at the previews. SteamGridDB scores are usually all zero, so "first result" is not
"best result" — and the first `.ico` is often a 4-bit 48x48 relic while a 512px `.png`
of the same art sits two entries down. `install` always rebuilds the icon at
256/128/64/48/32/16 from the largest source available.

## Phase 5 — Verify

```bash
python3 scripts/steam_shortcut.py gameid --appid 3828612727
steam steam://rungameid/<gameid>
sleep 90 && pgrep -x eldenring.exe | wc -l          # >0 means it's actually alive
spectacle -b -n -f -o /tmp/shot.png                 # KDE Wayland screenshot
```

A shortcut that appears in the library is not a working shortcut. If nothing starts,
reproduce outside Steam to get real output — note the **absolute** path, since
`proton run` resolves a bare exe name against the wrong directory and dies with
`Failed to create process ...: 2`:

```bash
export STEAM_COMPAT_CLIENT_INSTALL_PATH=~/.local/share/Steam
export STEAM_COMPAT_DATA_PATH=~/.local/share/Steam/steamapps/compatdata/<appid>
export SteamAppId=<store appid> SteamGameId=<store appid> PROTON_LOG=1
~/.local/share/Steam/compatibilitytools.d/GE-Proton10-34/proton run "/abs/path/game.exe"
grep -iE "err:|Unhandled exception|Failed" ~/steam-<store appid>.log
```

`vkd3d_get_format: Invalid format 1xx` spam and `openxr` extension errors are normal.

Finally re-read the config to prove Steam's own rewrite kept the changes:

```bash
python3 scripts/steam_shortcut.py list
```

## HDR, when it comes up

`rpd-gamescope` already handles it dynamically: it reads the live output from
`kscreen-doctor`, appends `--hdr-enabled` only when that output reports HDR, and sets or
unsets `DXVK_HDR` to match. Nothing to configure per game.

Known dead end: **Elden Ring's in-game HDR toggle stays greyed out** even with
`server hdr output enabled: true` and `hdr formats exposed to client: true` from
gamescope's WSI layer. The game gates the toggle on the monitor's HDR state via Wine's
win32 DXGI display path, which reports SDR under XWayland regardless of the compositor
above it; the swapchain comes up `R8G8B8A8_UNORM / SRGB_NONLINEAR`.
`PROTON_ENABLE_HDR=1` does not change it. The only untried route is Proton's Wayland
driver (`PROTON_ENABLE_WAYLAND=1`, no gamescope). Don't burn time re-deriving this.

## Scripts

| script | purpose |
| --- | --- |
| `scripts/steamlib.py` | paths, appid/rungameid math, binary+text VDF read/write, Steam stop/start guards |
| `scripts/steam_shortcut.py` | `list` / `add` / `set-launch` / `set-icon` / `set-proton` / `gameid` |
| `scripts/steam_artwork.py` | `search` / `preview` / `install` against SteamGridDB |
| `scripts/launch_policy.py` | build a launch string per profile, merging existing game args |

All mutating commands are dry-run until `--apply`, and every write leaves a
`.bak-<tag>` next to the file it touched.
