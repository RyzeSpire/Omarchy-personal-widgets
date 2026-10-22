#!/usr/bin/env python3
"""Local Steam library and launch helper. No Steam account/API credentials."""
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote
import steam_collections

TOKEN = re.compile(r'\s+|//[^\n]*|"((?:\\.|[^"\\])*)"|([{}])')
SHORTCUTS = {
    'library': 'steam://open/games',
    'friends': 'steam://open/friends',
    'store': 'steam://store',
    'settings': 'steam://open/settings',
    'bigpicture': 'steam://open/bigpicture',
}


def parse_vdf(text):
    """Parse Steam's text KeyValues, preserving Unicode and escaped paths."""
    tokens = []
    pos = 0
    while pos < len(text):
        match = TOKEN.match(text, pos)
        if not match:
            raise ValueError('Unrecognized Steam manifest format')
        if match.group(1) is not None:
            value = re.sub(r'\\([\\"nrt])', lambda m: {'n': '\n', 'r': '\r', 't': '\t'}.get(m[1], m[1]), match[1])
            tokens.append(('string', value))
        elif match.group(2):
            tokens.append((match[2], match[2]))
        pos = match.end()
    index = 0

    def block(nested=False):
        nonlocal index
        result = {}
        while index < len(tokens):
            kind, key = tokens[index]
            index += 1
            if kind == '}':
                if nested:
                    return result
                raise ValueError('Unbalanced Steam manifest')
            if kind != 'string' or index >= len(tokens):
                raise ValueError('Missing Steam manifest value')
            kind, value = tokens[index]
            index += 1
            if kind == '{':
                value = block(True)
            elif kind != 'string':
                raise ValueError('Invalid Steam manifest value')
            result[key] = value
        if nested:
            raise ValueError('Unclosed Steam manifest')
        return result

    return block()


def read_vdf(path):
    return parse_vdf(path.read_text(encoding='utf-8-sig', errors='replace'))


def steam_roots():
    candidates = []
    if os.environ.get('STEAM_DIR'):
        candidates.append(Path(os.environ['STEAM_DIR']).expanduser())
    home = Path.home()
    candidates += [home/'.local/share/Steam', home/'.steam/steam', home/'.steam/root']
    return list(dict.fromkeys(path.resolve() for path in candidates if (path/'steamapps').is_dir()))


def library_paths(roots):
    paths, warnings = [], []
    for root in roots:
        paths.append(root)
        index = root/'steamapps/libraryfolders.vdf'
        if not index.exists():
            continue
        try:
            folders = read_vdf(index).get('libraryfolders', {})
            if not isinstance(folders, dict):
                raise ValueError('Invalid library index')
            for key, folder in folders.items():
                if not key.isdigit():
                    continue
                value = folder.get('path', '') if isinstance(folder, dict) else folder
                if value:
                    path = Path(value).expanduser()
                    if (path/'steamapps').is_dir():
                        paths.append(path.resolve())
        except (OSError, ValueError, TypeError):
            warnings.append('A Steam library index could not be read.')
    return list(dict.fromkeys(paths)), warnings


def state_dir():
    return Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'omarchy/steam-widget'


def read_favorites():
    path = state_dir()/'favorites.json'
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('appids'), list):
        raise ValueError('Unknown favorites format')
    if any(not isinstance(value, str) or not value.isdigit() for value in data['appids']):
        raise ValueError('Invalid favorites data')
    return set(data['appids'])


def app_id(value):
    if not re.fullmatch(r'[1-9][0-9]{0,9}', value) or int(value) > 0xffffffff:
        raise ValueError('Invalid Steam game ID')
    return value


def set_favorite(value, enabled):
    value = app_id(value)
    directory = state_dir()
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    lock_fd = os.open(directory/'favorites.lock', os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(lock_fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        favorites = read_favorites()  # Preserve unreadable/unknown state instead of overwriting it.
        favorites.add(value) if enabled else favorites.discard(value)
        fd, temporary = tempfile.mkstemp(prefix='.favorites-', dir=directory)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as output:
                json.dump({'version': 1, 'appids': sorted(favorites, key=int)}, output)
                output.write('\n')
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, directory/'favorites.json')
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return {'appid': value, 'favorite': enabled}


def is_tool(name):
    folded = name.casefold()
    return folded.startswith(('proton ', 'steam linux runtime', 'steamworks common redistributables')) or folded == 'proton'


def artwork(roots, value):
    for filename in ('library_capsule.jpg', 'library_header.jpg'):
        for root in roots:
            directory = root/'appcache/librarycache'/value
            if directory.is_dir():
                images = sorted(directory.glob('*/'+filename))
                images += sorted(directory.glob(filename))
                if images:
                    return images[0].resolve().as_uri()
    for root in roots:
        cache = root/'appcache/librarycache'
        for filename in (value+'_library_600x900.jpg', value+'_header.jpg'):
            path = cache/filename
            if path.is_file():
                return path.resolve().as_uri()
    return ''


def library():
    roots = steam_roots()
    paths, warnings = library_paths(roots)
    try:
        favorites = read_favorites()
    except (OSError, ValueError, TypeError):
        favorites = set()
        warnings.append('Favorites could not be read; your saved file has been left untouched.')
    games = {}
    for path in paths:
        for manifest in sorted((path/'steamapps').glob('appmanifest_*.acf')):
            try:
                state = read_vdf(manifest)['AppState']
                value = app_id(str(state['appid']))
                name = state['name']
                if not isinstance(name, str) or is_tool(name):
                    continue
                install = Path(state['installdir'])
                common = (path/'steamapps/common').resolve()
                directory = (common/install).resolve()
                if common not in directory.parents or not directory.is_dir():
                    continue
                flags = int(state.get('StateFlags', 0))
                if not flags & 4:
                    continue
                game = {'appid': value, 'name': name, 'artwork': artwork(roots, value),
                        'size': max(0, int(state.get('SizeOnDisk', 0))),
                        'last_played': max(0, int(state.get('LastPlayed', 0))),
                        'favorite': value in favorites}
                games.setdefault(value, game)
            except (OSError, ValueError, KeyError, TypeError):
                warnings.append('An incomplete or unreadable game manifest was skipped.')
    collection_data = steam_collections.load(roots, list(games.values()), read_vdf, artwork, favorites)
    return {**collection_data, 'games': sorted(games.values(), key=lambda game: (-game['last_played'], game['name'].casefold())),
            'warnings': list(dict.fromkeys(warnings)), 'steam_found': bool(roots),
            'client_available': bool(shutil.which('steam'))}


def status():
    running = False
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            if path.stat().st_uid != os.getuid():
                continue
            name = (path/'comm').read_text().strip().casefold()
            if name in ('steam', 'steamwebhelper'):
                running = True
                break
        except OSError:
            continue
    return {'running': running, 'client_available': bool(shutil.which('steam'))}


def dispatch(uri):
    client = shutil.which('steam')
    if not client:
        raise ValueError('Steam is not installed or is missing from PATH.')
    wrapper = shutil.which('uwsm-app')
    environment = os.environ.copy()
    scale = environment.setdefault('STEAM_FORCE_DESKTOPUI_SCALING', '0.9')
    arguments = [client, '-forcedesktopscaling', scale, uri]
    command = [wrapper, '--', *arguments] if wrapper else arguments
    subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True, env=environment)
    return {'submitted': True}



def focus_client(target):
    """Reveal the native client on its existing workspace, without moving it."""
    if not shutil.which('hyprctl'):
        return False
    deadline = time.monotonic() + 20
    title_hint = {'friends': 'friends', 'settings': 'settings', 'bigpicture': 'big picture', 'properties': 'properties'}.get(target, '')
    while time.monotonic() < deadline:
        try:
            windows = json.loads(subprocess.check_output(['hyprctl', '-j', 'clients'], text=True, timeout=3))
            windows = [window for window in windows if window.get('mapped') and window.get('class', '').casefold() == 'steam']
            preferred = [window for window in windows if
                         (title_hint in window.get('title', '').casefold() if title_hint else window.get('title', '') == 'Steam')]
            # Give secondary client windows time to map, rather than selecting a game or unrelated app.
            if preferred or (windows and time.monotonic() >= deadline - 17):
                window = (preferred or windows)[0]
                address = window.get('address', '')
                if not re.fullmatch(r'0x[0-9a-fA-F]+', address):
                    raise ValueError('Steam window could not be identified.')
                expression = 'hl.dsp.focus({ window=' + json.dumps('address:'+address) + ' })'
                response = subprocess.check_output(['hyprctl', 'dispatch', expression], text=True, timeout=3)
                if response.strip() != 'ok':
                    raise ValueError('Steam could not be brought into view.')
                return True
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            return False
        time.sleep(0.2)
    return False


def open_client(target):
    result = dispatch(SHORTCUTS[target])
    result['focused'] = focus_client(target)
    return result


def launch(value):
    value = app_id(value)
    if not any(game['appid'] == value for game in library()['games']):
        raise ValueError('This game is no longer installed. Refresh the library.')
    return dispatch('steam://rungameid/'+value)


def store_search(query):
    query = query.strip()
    if not query or len(query) > 200:
        raise ValueError('Enter a store search of 1–200 characters.')
    result = dispatch('steam://openurl/https://store.steampowered.com/search/?term='+quote(query, safe=''))
    result['focused'] = focus_client('store')
    return result


def details(value):
    value = app_id(value)
    if not any(game['appid'] == value for game in library()['catalog']):
        raise ValueError('This title is no longer in the local library cache. Refresh the library.')
    result = dispatch('steam://nav/games/details/'+value)
    result['focused'] = focus_client('library')
    return result


def main(args):
    if args == ['status']:
        return status()
    if args == ['library']:
        return library()
    if len(args) == 2 and args[0] == 'details':
        return details(args[1])
    if len(args) == 2 and args[0] == 'store-search':
        return store_search(args[1])
    if len(args) == 2 and args[0] == 'launch':
        return launch(args[1])
    if len(args) == 2 and args[0] == 'open' and args[1] in SHORTCUTS:
        return open_client(args[1])
    if len(args) == 3 and args[0] == 'favorite' and args[2] in ('on', 'off'):
        return set_favorite(args[1], args[2] == 'on')
    raise ValueError('Unknown Steam widget command')


if __name__ == '__main__':
    try:
        print(json.dumps({'ok': True, **main(sys.argv[1:])}, ensure_ascii=False))
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=False))
        sys.exit(1)
