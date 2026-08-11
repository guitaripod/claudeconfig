#!/usr/bin/env python3
"""Fetch SteamGridDB artwork for an appid and install it under userdata/*/config/grid.

    steam_artwork.py search "elden ring"
    steam_artwork.py preview --game 5452291 [--limit 4] [--out /tmp/preview]
    steam_artwork.py install --appid 3828612727 --game 5452291 [--pick grid=2,hero=1]
    steam_artwork.py audit [--fix-icons]

Filenames Steam reads out of grid/ (all optional, all keyed by the 32-bit appid):
    <appid>p.png       600x900   portrait capsule (library list + grid)
    <appid>.png        920x430   wide capsule / header
    <appid>_hero.png   3840x1240 hero banner behind the game page
    <appid>_logo.png             transparent title treatment
    <appid>_icon.png   256x256   small icon (Big Picture and some views)
    <appid>_icon.ico             what the shortcuts.vdf `icon` field should point at

The API key comes from --key, $STEAMGRIDDB_KEY, or ~/.config/steamgriddb/key.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import steamlib as S  # noqa: E402

API = 'https://www.steamgriddb.com/api/v2'
UA = 'steam-add-game/1.0'
KINDS = {
    'grid': ('grids', {'dimensions': '600x900'}),
    'wide': ('grids', {'dimensions': '920x430'}),
    'hero': ('heroes', {}),
    'logo': ('logos', {}),
    'icon': ('icons', {}),
}


def api_key(explicit: str | None) -> str:
    if explicit:
        return explicit
    if os.environ.get('STEAMGRIDDB_KEY'):
        return os.environ['STEAMGRIDDB_KEY']
    p = os.path.expanduser('~/.config/steamgriddb/key')
    if os.path.exists(p):
        return open(p).read().strip()
    raise SystemExit('no SteamGridDB key: pass --key, set $STEAMGRIDDB_KEY, '
                     'or write ~/.config/steamgriddb/key')


def get(path: str, key: str, params: dict | None = None) -> dict:
    url = f'{API}/{path}'
    if params:
        url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {key}',
                                              'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def assets(game: int, kind: str, key: str) -> list[dict]:
    endpoint, params = KINDS[kind]
    data = get(f'{endpoint}/game/{game}', key, params)
    return data.get('data') or []


def download(url: str, dest: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, 'wb') as f:
        f.write(r.read())
    return dest


def magick(*args: str) -> None:
    exe = 'magick' if shutil_which('magick') else 'convert'
    subprocess.run([exe, *args], check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)


def shutil_which(name: str) -> str | None:
    import shutil
    return shutil.which(name)


def make_ico(src: str, dest: str) -> None:
    """Multi-resolution .ico (256 down to 16) so the icon stays sharp everywhere.

    A single-size 256px .ico renders as mush in the 16px library list, and a bare
    48px .ico from SteamGridDB looks blocky on the game page.
    """
    magick(f'{src}[0]', '-background', 'none', '-alpha', 'on', '-resize', '256x256',
           '(', '-clone', '0', '-resize', '128x128', ')',
           '(', '-clone', '0', '-resize', '64x64', ')',
           '(', '-clone', '0', '-resize', '48x48', ')',
           '(', '-clone', '0', '-resize', '32x32', ')',
           '(', '-clone', '0', '-resize', '16x16', ')', dest)


def cmd_search(args):
    key = api_key(args.key)
    q = urllib.parse.quote(args.query)
    for g in get(f'search/autocomplete/{q}', key).get('data', []):
        print(g['id'], '|', g['name'], '|', ','.join(g.get('types') or []))


def cmd_preview(args):
    """Download the top N of every kind and montage them, so the choice is visual.

    Ranking on SteamGridDB is server-side; scores are frequently all zero, so eyeball
    the montage with the Read tool rather than trusting the first result.
    """
    key = api_key(args.key)
    out = args.out or '/tmp/sgdb-preview'
    os.makedirs(out, exist_ok=True)
    picked = {}
    for kind in KINDS:
        items = assets(args.game, kind, key)[:args.limit]
        for n, a in enumerate(items, 1):
            ext = '.ico' if a['url'].endswith('.ico') else os.path.splitext(a['url'])[1]
            dest = os.path.join(out, f'{kind}{n}{ext}')
            download(a['url'], dest)
            picked.setdefault(kind, []).append(dest)
            print(kind, n, dest, a['url'])
    for kind, files in picked.items():
        m = os.path.join(out, f'montage-{kind}.png')
        magick('montage', '-label', '%f', *[f'{f}[0]' for f in files],
               '-tile', f'{len(files)}x1', '-geometry', '200x200+8+8',
               '-background', 'gray20', '-fill', 'white', m)
        print('montage', m)


def cmd_install(args):
    key = api_key(args.key)
    picks = dict(kv.split('=') for kv in args.pick.split(',')) if args.pick else {}
    grid = S.grid_dir(args.user)
    names = {'grid': f'{args.appid}p.png', 'wide': f'{args.appid}.png',
             'hero': f'{args.appid}_hero.png', 'logo': f'{args.appid}_logo.png'}
    for kind, fname in names.items():
        items = assets(args.game, kind, key)
        if not items:
            print(f'{kind}: none available')
            continue
        n = int(picks.get(kind, 1)) - 1
        url = items[min(n, len(items) - 1)]['url']
        dest = os.path.join(grid, fname)
        tmp = download(url, dest + '.dl')
        if url.endswith('.png'):
            os.replace(tmp, dest)
        else:
            magick(f'{tmp}[0]', dest)
            os.remove(tmp)
        print(f'{kind}: {dest}  <- {url}')

    icons = assets(args.game, 'icon', key)
    if icons:
        n = int(picks.get('icon', 1)) - 1
        src_url = icons[min(n, len(icons) - 1)]['url']
        ext = os.path.splitext(src_url)[1] or '.png'
        raw = download(src_url, os.path.join(grid, f'{args.appid}_icon.src{ext}'))
        make_ico(raw, os.path.join(grid, f'{args.appid}_icon.ico'))
        magick(f'{raw}[0]', '-resize', '256x256',
               os.path.join(grid, f'{args.appid}_icon.png'))
        os.remove(raw)
        print(f'icon: {grid}/{args.appid}_icon.ico (+ .png)  <- {src_url}')
        print('remember: point the shortcut\'s `icon` field at the .ico '
              '(steam_shortcut.py set-icon)')
    else:
        print('icon: none available')


AUDIT_KINDS = {
    'portrait': ('p.png', 'p.jpg'),
    'wide': ('.png', '.jpg'),
    'hero': ('_hero.png', '_hero.jpg'),
    'logo': ('_logo.png', '_logo.jpg'),
    'icon_png': ('_icon.png', '_icon.jpg'),
    'icon_ico': ('_icon.ico',),
}


def _art_file(grid: str, appid: int, suffixes) -> str | None:
    for s in suffixes:
        p = os.path.join(grid, f'{appid}{s}')
        if os.path.isfile(p) and os.path.getsize(p) > 0:
            return p
    return None


def _icon_source(grid: str, appid: int) -> str | None:
    """Best in-library source to synthesise a missing icon from.

    A real icon asset first, then the portrait, then the wide capsule. The logo is
    deliberately excluded — it is a wide transparent title treatment and squashes
    into an unreadable smear at 16px.
    """
    for kind in ('icon_ico', 'icon_png', 'portrait', 'wide'):
        hit = _art_file(grid, appid, AUDIT_KINDS[kind])
        if hit:
            return hit
    return None


def cmd_audit(args):
    """Report which non-Steam shortcuts are missing artwork, optionally filling icons.

    Only the two icon forms can be synthesised locally; a missing capsule, hero or logo
    is a real gap that needs `install` against a SteamGridDB game id. The `icon` field in
    shortcuts.vdf is checked too — a `<appid>_icon.ico` on disk that nothing points at
    still leaves the library entry blank.
    """
    grid = S.grid_dir(args.user)
    tree, _, _ = S.load_shortcuts(args.user)
    ents = S.entries(tree)
    incomplete = 0
    for _, (_, e) in ents.items():
        appid = S.entry_appid(e)
        name = e.get('AppName', ('str', '?'))[1]
        missing = [k for k, sfx in AUDIT_KINDS.items() if not _art_file(grid, appid, sfx)]
        if args.fix_icons and {'icon_png', 'icon_ico'} & set(missing):
            src = _icon_source(grid, appid)
            if src:
                if 'icon_png' in missing:
                    magick(f'{src}[0]', '-background', 'none', '-alpha', 'on',
                           '-resize', '256x256', os.path.join(grid, f'{appid}_icon.png'))
                    missing.remove('icon_png')
                if 'icon_ico' in missing:
                    make_ico(src, os.path.join(grid, f'{appid}_icon.ico'))
                    missing.remove('icon_ico')
        icon_field = e.get('icon', ('str', ''))[1]
        if not (icon_field and os.path.isfile(icon_field)):
            missing.append('icon_field')
        if missing:
            incomplete += 1
        status = 'COMPLETE' if not missing else 'MISSING: ' + ','.join(missing)
        print(f'{appid:>12}  {name[:44]:<44} {status}')
    print(f'\n{len(ents)} shortcuts, {incomplete} incomplete')
    if args.fix_icons:
        print('icon_field fixes need Steam stopped: steam_shortcut.py --apply set-icon --appid N')


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--key')
    p.add_argument('--user')
    sub = p.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('search')
    s.add_argument('query')
    s.set_defaults(fn=cmd_search)

    v = sub.add_parser('preview')
    v.add_argument('--game', type=int, required=True)
    v.add_argument('--limit', type=int, default=3)
    v.add_argument('--out')
    v.set_defaults(fn=cmd_preview)

    i = sub.add_parser('install')
    i.add_argument('--appid', required=True)
    i.add_argument('--game', type=int, required=True)
    i.add_argument('--pick', help='e.g. grid=2,hero=1,icon=3 (1-based, default 1)')
    i.set_defaults(fn=cmd_install)

    a = sub.add_parser('audit')
    a.add_argument('--fix-icons', action='store_true',
                   help='synthesise missing _icon.png/_icon.ico from existing art')
    a.set_defaults(fn=cmd_audit)

    args = p.parse_args()
    args.fn(args)


if __name__ == '__main__':
    main()
