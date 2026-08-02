"""Shared Steam config plumbing: paths, non-Steam appids, binary + text VDF editing.

Every mutating helper here assumes Steam is NOT running. Steam rewrites shortcuts.vdf,
localconfig.vdf and config.vdf from memory when it exits, silently discarding edits made
while it was up.
"""
from __future__ import annotations

import glob
import os
import re
import shutil
import struct
import subprocess
import time
import zlib
from collections import OrderedDict

STEAM_ROOT = os.path.expanduser('~/.steam/steam')


def userdata_config(user_id: str | None = None) -> str:
    """Path to userdata/<id>/config, auto-detecting the only user when unambiguous."""
    base = os.path.join(STEAM_ROOT, 'userdata')
    if user_id:
        return os.path.join(base, user_id, 'config')
    ids = [d for d in os.listdir(base) if d.isdigit() and d != '0']
    if len(ids) != 1:
        raise SystemExit(f'ambiguous userdata ids {ids}; pass --user')
    return os.path.join(base, ids[0], 'config')


def grid_dir(user_id: str | None = None) -> str:
    d = os.path.join(userdata_config(user_id), 'grid')
    os.makedirs(d, exist_ok=True)
    return d


def shortcuts_path(user_id: str | None = None) -> str:
    return os.path.join(userdata_config(user_id), 'shortcuts.vdf')


def localconfig_path(user_id: str | None = None) -> str:
    return os.path.join(userdata_config(user_id), 'localconfig.vdf')


def config_path() -> str:
    return os.path.join(STEAM_ROOT, 'config', 'config.vdf')


def quoted(path: str) -> str:
    """Steam stores Exe/StartDir wrapped in literal double quotes; the appid hash
    is computed over that quoted form, so never strip them."""
    return path if path.startswith('"') else f'"{path}"'


def shortcut_appid(exe: str, appname: str) -> int:
    """Legacy 32-bit id Steam derives for a non-Steam shortcut.

    This is the number used for grid/ artwork filenames and CompatToolMapping keys.
    `exe` must include its surrounding quotes exactly as stored in shortcuts.vdf.
    """
    return zlib.crc32((quoted(exe) + appname).encode('utf-8')) | 0x80000000


def rungameid(appid: int) -> int:
    """steam://rungameid/<n> value for a non-Steam shortcut."""
    return (appid << 32) | 0x02000000


def steam_running() -> bool:
    return subprocess.run(['pgrep', '-x', 'steam'],
                          stdout=subprocess.DEVNULL).returncode == 0


def game_running(exe_name: str) -> bool:
    """True while a wine game process is alive.

    Uses -x deliberately: `pgrep -f eldenring.exe` also matches the *watching* shell,
    whose own command line contains the pattern, so a wait loop never exits.
    """
    return subprocess.run(['pgrep', '-x', exe_name],
                          stdout=subprocess.DEVNULL).returncode == 0


def stop_steam(timeout: int = 120) -> bool:
    if not steam_running():
        return True
    subprocess.run(['steam', '-shutdown'], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not steam_running():
            time.sleep(5)
            return True
        time.sleep(2)
    return False


def start_steam(wait: int = 45) -> None:
    subprocess.Popen(['steam'], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    time.sleep(wait)


def require_steam_stopped() -> None:
    if steam_running():
        raise SystemExit('Steam is running; stop it first (steam -shutdown) or Steam '
                         'will overwrite these files when it exits.')


def backup(path: str, tag: str) -> str:
    dest = f'{path}.bak-{tag}'
    shutil.copy(path, dest)
    return dest


def _read_str(data: bytes, i: int) -> tuple[str, int]:
    end = data.index(b'\x00', i)
    return data[i:end].decode('utf-8', 'replace'), end + 1


def parse_binary_vdf(data: bytes, i: int = 0) -> tuple[OrderedDict, int]:
    """Parse Valve's binary KV (types 0x00 map, 0x01 string, 0x02 int32, 0x08 end).

    Values become ('str', s) / ('int', n) / ('map', OrderedDict) so a parse/serialize
    round trip is byte-identical and unknown keys survive untouched.
    """
    out: OrderedDict = OrderedDict()
    while i < len(data):
        t = data[i]
        if t == 0x08:
            return out, i + 1
        key, i = _read_str(data, i + 1)
        if t == 0x00:
            val, i = parse_binary_vdf(data, i)
            out[key] = ('map', val)
        elif t == 0x01:
            s, i = _read_str(data, i)
            out[key] = ('str', s)
        elif t == 0x02:
            out[key] = ('int', struct.unpack('<i', data[i:i + 4])[0])
            i += 4
        else:
            raise ValueError(f'unknown binary vdf type 0x{t:02x} at {i}')
    return out, i


def serialize_binary_vdf(node: OrderedDict) -> bytes:
    out = bytearray()
    for key, (kind, val) in node.items():
        kb = key.encode('utf-8') + b'\x00'
        if kind == 'map':
            out += b'\x00' + kb + serialize_binary_vdf(val)
        elif kind == 'str':
            out += b'\x01' + kb + val.encode('utf-8') + b'\x00'
        elif kind == 'int':
            out += b'\x02' + kb + struct.pack('<I', val & 0xFFFFFFFF)
        else:
            raise ValueError(kind)
    return bytes(out) + b'\x08'


def load_shortcuts(user_id: str | None = None) -> tuple[OrderedDict, bytes, str]:
    path = shortcuts_path(user_id)
    raw = open(path, 'rb').read()
    tree, _ = parse_binary_vdf(raw)
    return tree, raw, path


def save_shortcuts(tree: OrderedDict, path: str, tag: str) -> None:
    require_steam_stopped()
    backup(path, tag)
    open(path, 'wb').write(serialize_binary_vdf(tree))


def entries(tree: OrderedDict) -> OrderedDict:
    """The numeric-index map under the top-level "shortcuts" key."""
    for key, (kind, val) in tree.items():
        if key.lower() == 'shortcuts' and kind == 'map':
            return val
    raise SystemExit('shortcuts.vdf has no "shortcuts" root')


def entry_appid(entry: OrderedDict) -> int:
    return entry['appid'][1] & 0xFFFFFFFF


_LAUNCH_RE = re.compile(r'"LaunchOptions"\s+"((?:[^"\\]|\\.)*)"')
_APPID_RE = re.compile(r'\n\t+"(\d+)"\n\t+\{')


def vdf_escape(s: str) -> str:
    return s.replace('\\', '\\\\').replace('"', '\\"')


def vdf_unescape(s: str) -> str:
    return s.replace('\\"', '"').replace('\\\\', '\\')


def read_launch_options(user_id: str | None = None) -> dict[str, str]:
    """appid -> LaunchOptions for installed Steam games, from localconfig.vdf."""
    d = open(localconfig_path(user_id), encoding='utf-8', errors='replace').read()
    found: dict[str, str] = {}
    for m in _LAUNCH_RE.finditer(d):
        ids = _APPID_RE.findall(d[:m.start()])
        if ids:
            found[ids[-1]] = vdf_unescape(m.group(1))
    return found


def write_launch_options(updates: dict[str, str], user_id: str | None = None,
                         tag: str = 'launchopts', apply: bool = False) -> list[str]:
    """Set LaunchOptions for the given Steam appids. Returns the appids changed."""
    path = localconfig_path(user_id)
    d = open(path, encoding='utf-8').read()
    done: list[str] = []

    def repl(m: re.Match) -> str:
        ids = _APPID_RE.findall(d[:m.start()])
        appid = ids[-1] if ids else None
        if appid in updates:
            done.append(appid)
            return '"LaunchOptions"\t\t"' + vdf_escape(updates[appid]) + '"'
        return m.group(0)

    new = _LAUNCH_RE.sub(repl, d)
    if apply and new != d:
        require_steam_stopped()
        backup(path, tag)
        open(path, 'w', encoding='utf-8').write(new)
    return done


def set_compat_tool(appid: int | str, tool: str, priority: int = 250,
                    apply: bool = False) -> bool:
    """Add/replace a CompatToolMapping entry in config.vdf (NOT localconfig.vdf)."""
    path = config_path()
    d = open(path, encoding='utf-8').read()
    i = d.find('"CompatToolMapping"')
    if i < 0:
        raise SystemExit('no CompatToolMapping block in config.vdf')
    brace = d.index('{', i)
    block = '\t\t\t\t\t"%s"\n\t\t\t\t\t{\n\t\t\t\t\t\t"name"\t\t"%s"\n' \
            '\t\t\t\t\t\t"config"\t\t""\n\t\t\t\t\t\t"priority"\t\t"%d"\n\t\t\t\t\t}\n' \
            % (appid, tool, priority)
    existing = re.search(r'\n\t+"%s"\n\t+\{.*?\n\t+\}\n' % appid, d[brace:], re.S)
    if existing:
        new = d[:brace] + d[brace:].replace(existing.group(0), '\n' + block, 1)
    else:
        new = d[:brace + 1] + '\n' + block + d[brace + 1:]
    if apply and new != d:
        require_steam_stopped()
        backup(path, 'compattool')
        open(path, 'w', encoding='utf-8').write(new)
    return new != d


def proton_tools() -> list[str]:
    """Installed compatibilitytools.d entries, newest-looking last."""
    out = []
    for root in (os.path.expanduser('~/.local/share/Steam/compatibilitytools.d'),
                 os.path.join(STEAM_ROOT, 'compatibilitytools.d')):
        out += [os.path.basename(p) for p in glob.glob(os.path.join(root, '*'))
                if os.path.isdir(p)]
    return sorted(set(out))
