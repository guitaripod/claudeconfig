#!/usr/bin/env python3
"""Create and edit non-Steam shortcuts, their launch options and their Proton mapping.

    steam_shortcut.py list
    steam_shortcut.py add --name "ELDEN RING" --exe /path/game.exe [--dir D] \
                          [--launch "..."] [--proton GE-Proton10-34] [--apply]
    steam_shortcut.py set-launch --appid 3828612727 --launch "..." [--apply]
    steam_shortcut.py set-launch --steam-appid 1286830 --launch "..." [--apply]
    steam_shortcut.py set-icon  --appid 3828612727 [--icon /path.ico] [--apply]
    steam_shortcut.py set-proton --appid 3828612727 --proton GE-Proton10-34 [--apply]
    steam_shortcut.py gameid --appid 3828612727

Nothing is written without --apply. Steam must be stopped for any write.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import steamlib as S  # noqa: E402


def cmd_list(args):
    tree, _, _ = S.load_shortcuts(args.user)
    for _, (_, e) in S.entries(tree).items():
        appid = S.entry_appid(e)
        print(f"{appid}  {e['AppName'][1]}")
        print(f"    exe    {e['Exe'][1]}")
        print(f"    icon   {e.get('icon', ('str', ''))[1] or '(none)'}")
        print(f"    launch {e.get('LaunchOptions', ('str', ''))[1] or '(none)'}")
        print(f"    gameid {S.rungameid(appid)}")
    for appid, opts in sorted(S.read_launch_options(args.user).items(), key=lambda x: int(x[0])):
        print(f"steam:{appid}  {opts}")


def _new_entry(appid, name, exe, startdir, launch, icon):
    return OrderedDict([
        ('appid', ('int', appid)),
        ('AppName', ('str', name)),
        ('Exe', ('str', exe)),
        ('StartDir', ('str', startdir)),
        ('icon', ('str', icon)),
        ('ShortcutPath', ('str', '')),
        ('LaunchOptions', ('str', launch)),
        ('IsHidden', ('int', 0)),
        ('AllowDesktopConfig', ('int', 1)),
        ('AllowOverlay', ('int', 1)),
        ('OpenVR', ('int', 0)),
        ('Devkit', ('int', 0)),
        ('DevkitGameID', ('str', '')),
        ('DevkitOverrideAppID', ('int', 0)),
        ('LastPlayTime', ('int', 0)),
        ('FlatpakAppID', ('str', '')),
        ('sortas', ('str', '')),
        ('tags', ('map', OrderedDict())),
    ])


def cmd_add(args):
    exe = S.quoted(os.path.abspath(args.exe))
    startdir = S.quoted(args.dir or os.path.dirname(os.path.abspath(args.exe)) + '/')
    appid = S.shortcut_appid(exe, args.name)
    icon = args.icon or os.path.join(S.grid_dir(args.user), f'{appid}_icon.ico')

    tree, _, path = S.load_shortcuts(args.user)
    ents = S.entries(tree)
    for _, (_, e) in ents.items():
        if S.entry_appid(e) == appid:
            raise SystemExit(f'{appid} already present: {e["AppName"][1]}')
    idx = str(max((int(k) for k in ents if k.isdigit()), default=-1) + 1)
    ents[idx] = ('map', _new_entry(appid, args.name, exe, startdir,
                                   args.launch or '', icon))

    print(f'appid   {appid}')
    print(f'gameid  {S.rungameid(appid)}')
    print(f'icon    {icon}')
    if args.proton:
        S.set_compat_tool(appid, args.proton, apply=args.apply)
        print(f'proton  {args.proton}')
    if args.apply:
        S.save_shortcuts(tree, path, 'preadd')
        print('APPLIED')
    else:
        print('DRY RUN (pass --apply)')


def cmd_set_launch(args):
    if args.steam_appid:
        done = S.write_launch_options({args.steam_appid: args.launch},
                                      args.user, apply=args.apply)
        print('patched' if done else 'appid not found in localconfig.vdf', done)
    else:
        tree, _, path = S.load_shortcuts(args.user)
        hit = False
        for _, (_, e) in S.entries(tree).items():
            if S.entry_appid(e) == int(args.appid):
                e['LaunchOptions'] = ('str', args.launch)
                hit = True
        if not hit:
            raise SystemExit(f'no shortcut with appid {args.appid}')
        if args.apply:
            S.save_shortcuts(tree, path, 'prelaunch')
    print('APPLIED' if args.apply else 'DRY RUN (pass --apply)')


def cmd_set_icon(args):
    icon = args.icon or os.path.join(S.grid_dir(args.user), f'{args.appid}_icon.ico')
    if not os.path.exists(icon):
        raise SystemExit(f'{icon} does not exist; fetch artwork first')
    tree, _, path = S.load_shortcuts(args.user)
    hit = False
    for _, (_, e) in S.entries(tree).items():
        if S.entry_appid(e) == int(args.appid):
            e['icon'] = ('str', icon)
            hit = True
    if not hit:
        raise SystemExit(f'no shortcut with appid {args.appid}')
    if args.apply:
        S.save_shortcuts(tree, path, 'preicon')
    print(f'{args.appid} -> {icon}')
    print('APPLIED' if args.apply else 'DRY RUN (pass --apply)')


def cmd_set_proton(args):
    changed = S.set_compat_tool(args.appid, args.proton, apply=args.apply)
    print('changed' if changed else 'already set',
          '| APPLIED' if args.apply else '| DRY RUN')


def cmd_gameid(args):
    print(S.rungameid(int(args.appid)))


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--user')
    p.add_argument('--apply', action='store_true')
    sub = p.add_subparsers(dest='cmd', required=True)

    sub.add_parser('list').set_defaults(fn=cmd_list)

    a = sub.add_parser('add')
    a.add_argument('--name', required=True)
    a.add_argument('--exe', required=True)
    a.add_argument('--dir')
    a.add_argument('--launch')
    a.add_argument('--icon')
    a.add_argument('--proton')
    a.set_defaults(fn=cmd_add)

    sl = sub.add_parser('set-launch')
    sl.add_argument('--appid')
    sl.add_argument('--steam-appid')
    sl.add_argument('--launch', required=True)
    sl.set_defaults(fn=cmd_set_launch)

    i = sub.add_parser('set-icon')
    i.add_argument('--appid', required=True)
    i.add_argument('--icon')
    i.set_defaults(fn=cmd_set_icon)

    c = sub.add_parser('set-proton')
    c.add_argument('--appid', required=True)
    c.add_argument('--proton', required=True)
    c.set_defaults(fn=cmd_set_proton)

    g = sub.add_parser('gameid')
    g.add_argument('--appid', required=True)
    g.set_defaults(fn=cmd_gameid)

    args = p.parse_args()
    args.fn(args)


if __name__ == '__main__':
    main()
