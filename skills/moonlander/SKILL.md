---
name: moonlander
description: Change Marcus's ZSA Moonlander keyboard layout (keys, layers, tap dance, combos, macros, RGB, QMK features) by editing its QMK source and building and flashing it locally with the `moonlander` CLI, instead of Oryx. Use for "remap a key", "add a layer", "what is on my mouse layer", "put X on the Moonlander", "flash my keyboard", or any Moonlander, Oryx or Keymapp question.
---

# moonlander

`moonlander` (repo `~/Dev/moonlander`, on PATH from `~/.local/bin`) holds the layout as QMK C source in `~/Dev/moonlander/keymap/`, builds it in Docker and flashes it with ZSA's `zapp`. Every command prints JSON on stdout and errors on stderr.

```sh
moonlander status   # keyboard serial (Oryx layout/revision), repo origin, Oryx latest
moonlander pull     # overwrite keymap/ with Oryx's latest revision (--revision ID for another)
moonlander build    # compile to /mnt/nvme8tb/moonlander/moonlander.bin; compiler errors on stderr
moonlander flash    # zapp waits for the bootloader, then flashes
```

## Workflow

1. `moonlander status`. If `oryx_latest.revision` differs from `repo.oryx.revision`, he edited in Oryx since the last pull: ask before `pull`, it replaces local edits (git keeps them).
2. Edit `keymap/keymap.c` (and `config.h`, `rules.mk` for features). Keycodes are QMK's, from ZSA's fork at the branch in `oryx.json` (`firmware24` for `qmkVersion` 24): `/mnt/nvme8tb/moonlander/qmk-firmware24/quantum/keycodes.h` and `docs/` there. The no-comments rule applies here too.
3. `moonlander build` until it passes. A build that passes is the only proof an edit is valid.
4. Commit the keymap change in `~/Dev/moonlander` and push.
5. `moonlander flash` needs his hands: he holds the layer-2 key (`MO(2)`) and taps the top-right key of the right half (`QK_BOOT`), or presses the reset pinhole. Run it in the background, tell him to press it, and confirm zapp's success line. Afterwards `zapp devices` shows the keyboard back in normal mode.

## `LAYOUT_moonlander` order

Each layer lists 72 keys row by row, left half then right half: rows 0 to 2 have 7 + 7, row 3 has 6 + 6, row 4 has 5 keys plus the big red thumb key on the left, then the right red thumb key plus 5 keys, and row 5 is the two 3-key thumb clusters. The seventh key of rows 0 to 2 on each side is the inner column. Layer names are in `oryx.json` `layers` (0 Linux, 1 macOS, 2 Mouse).

## Traps

- Local builds and Oryx now diverge: Oryx shows the last pulled revision, not the flashed firmware. `zapp update`, `zapp flash <oryx url>` and Keymapp's flash all put Oryx's version back over local edits; never run them unless he asks to go back to Oryx.
- `config.h` keeps `SERIAL_NUMBER "x60G0/y70no"` so `status` and Keymapp still identify the layout; Keymapp's layout picture is then stale after local edits.
- First flash on a machine needs the udev rules once (`sudo`, his hands): `sudo cp ~/Dev/moonlander/udev/50-zsa.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules && sudo udevadm trigger`. arch has them when `/etc/udev/rules.d/50-zsa.rules` exists.
- The toolchain image `moonlander-qmk:firmware24` and the fork clone are what builds run from; keep them. A new Oryx QMK version (`qmkVersion` 25) clones `firmware25` and builds a new image on the next `build`; remove the old pair then.
