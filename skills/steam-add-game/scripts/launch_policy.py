#!/usr/bin/env python3
"""Build a launch-option string from Marcus's house style, preserving game-specific args.

    launch_policy.py --profile nonshooter
    launch_policy.py --profile shooter --extra "+com_skipIntroVideo 1"
    launch_policy.py --profile nonshooter --merge 'PROTON_DLSS_UPGRADE=1 MANGOHUD=1 ... %command% --exec="launch D3"'

Profiles:
  nonshooter   rpd-gamescope wrapper: resolves -W/-H/-r/-f/--hdr-enabled from whichever
               output is live at launch, so the game fills the Remote Play dummy at the
               client's mode and gets HDR only when the real display has it.
  shooter      plain mangohud, no compositor in the path. Also the right profile for any
               latency-critical PvP title regardless of genre (MOBA, RTS ladder,
               fighting game, racing sim) -- never wrap those in gamescope.

Both hide the HUD by default and toggle it with Ctrl_L+Right.
"""
from __future__ import annotations

import argparse
import re

RPD = '/home/marcus/Dev/remoteplay-display/rpd-gamescope'
HUD = 'full,no_display,toggle_hud=Control_L+Right'

PROFILES = {
    'nonshooter': f'PROTON_DLSS_UPGRADE=1 MANGOHUD_CONFIG={HUD} '
                  f'{RPD} --mangoapp -- obs-gamecapture %command%',
    'shooter': f'PROTON_DLSS_UPGRADE=1 MANGOHUD=1 MANGOHUD_CONFIG={HUD} '
               f'mangohud obs-gamecapture %command%',
}

CARRY_ENV = ('WINEDLLOVERRIDES=', 'DXVK_HUD=', 'SteamDeck=', 'steamdeck=',
             'PROTON_USE_WINED3D=', 'PROTON_NO_FSYNC=', 'DXVK_ASYNC=',
             'PROTON_ENABLE_WAYLAND=', 'PROTON_ENABLE_HDR=', 'VKD3D_CONFIG=')


def split_existing(old: str) -> tuple[list[str], str]:
    """Return (env/flags worth keeping, trailing game arguments after %command%)."""
    if '%command%' not in old:
        return [], old.strip()
    head, tail = old.split('%command%', 1)
    keep = [tok for tok in head.split() if tok.startswith(CARRY_ENV)]
    return keep, tail.strip()


def build(profile: str, merge: str = '', extra: str = '') -> str:
    base = PROFILES[profile]
    keep, trailing = split_existing(merge) if merge else ([], '')
    if keep:
        anchor = RPD if profile == 'nonshooter' else 'mangohud '
        i = base.index(anchor)
        base = base[:i] + ' '.join(keep) + ' ' + base[i:]
    parts = [base]
    if trailing:
        parts.append(trailing)
    if extra:
        parts.append(extra)
    return re.sub(r'\s+', ' ', ' '.join(parts)).strip()


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--profile', choices=sorted(PROFILES), required=True)
    p.add_argument('--merge', default='', help='existing LaunchOptions to preserve')
    p.add_argument('--extra', default='', help='extra game args to append')
    a = p.parse_args()
    print(build(a.profile, a.merge, a.extra))


if __name__ == '__main__':
    main()
