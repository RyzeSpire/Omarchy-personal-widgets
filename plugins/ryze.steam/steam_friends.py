#!/usr/bin/env python3
"""Personal Steam Web API friends reader. Credentials never enter argv/stdout.

Only GetFriendList and GetPlayerSummaries are used. No login cookies, messages,
Steam authentication tokens, purchases, or presence changes are accessed.
"""
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

import steam_collections

BASE_ID = 76561197960265728
STATES = {0: 'Offline', 1: 'Online', 2: 'Busy', 3: 'Away', 4: 'Snooze', 5: 'Looking to trade', 6: 'Looking to play'}


class FriendsError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward the API key to another host.


def credential_path():
    return Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')/'omarchy/steam-widget/friends.json'


def cache_dir():
    return Path(os.environ.get('XDG_CACHE_HOME') or Path.home()/'.cache')/'omarchy/steam-widget'


def valid_id(value):
    value = str(value)
    return value.isdigit() and BASE_ID < int(value) <= BASE_ID + 0xffffffff


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise FriendsError('The widget state path is a symlink; choose a regular private file.')
    fd, temporary = tempfile.mkstemp(prefix='.'+path.name+'-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump(data, output, ensure_ascii=False)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def current_profile():
    # Imports are lazy: the normal Steam status/library actions never import network code.
    from steam_backend import steam_roots, read_vdf
    roots = steam_roots()
    try:
        config = steam_collections.profile_config(roots, read_vdf)
    except (OSError, ValueError):
        config = None
    if config is None:
        raise FriendsError('Sign in to the Steam desktop client once so this widget can identify your profile.')
    steamid = str(BASE_ID + int(config.parent.name))
    if not valid_id(steamid):
        raise FriendsError('Your local Steam profile could not be identified.')
    root = config.parents[2]
    name, avatar = 'Steam profile', ''
    try:
        local = read_vdf(config/'localconfig.vdf').get('UserLocalConfigStore', {})
        contacts = json.loads(local.get('WebStorage', {}).get('friendstore_playercache', '[]'))
        own = next((item for item in contacts if isinstance(item, dict) and str(item.get('steamid')) == steamid), {})
        name = str(own.get('persona_name') or name)
    except (OSError, ValueError, TypeError):
        pass
    path = root/'config/avatarcache'/(steamid+'.png')
    if path.is_file():
        avatar = path.resolve().as_uri()
    return {'steamid': steamid, 'name': name, 'avatar': avatar, 'status': 'Steam profile', 'group': 'unknown', 'game': ''}


def read_config():
    path = credential_path()
    if not path.exists():
        return None
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise FriendsError('The saved API key needs private file permissions (0600).')
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        if value.get('version') != 1 or not valid_id(value.get('steamid', '')) or not re.fullmatch(r'[A-Fa-f0-9]{32}', value.get('api_key', '')):
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise FriendsError('The saved Steam API configuration is unreadable. Reconnect your account.') from None
    return value


def api(method, key, params, timeout=7):
    namespaces = {'GetFriendList/v1': 'ISteamUser', 'GetPlayerSummaries/v2': 'ISteamUser',
                  'GetOwnedGames/v1': 'IPlayerService', 'GetSchemaForGame/v2': 'ISteamUserStats',
                  'GetPlayerAchievements/v1': 'ISteamUserStats'}
    if method not in namespaces:
        raise FriendsError('Unsupported Steam API method.')
    uri = 'https://api.steampowered.com/'+namespaces[method]+'/'+method+'/?'+urlencode(params)
    request = Request(uri, headers={'x-webapi-key': key, 'User-Agent': 'Omarchy-Steam-Widget/1.2', 'Accept': 'application/json'})
    try:
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise FriendsError('Steam returned an unusually large response.')
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except HTTPError as error:
        error.close()
        if error.code == 401 and method.startswith('GetFriendList'):
            message = 'Steam is hiding your friends list. Check your profile’s Friends List privacy setting, or verify your API key.'
        elif error.code in (401, 403):
            message = 'Steam rejected the API key. Check it or create a new key.'
        elif error.code == 429:
            message = 'Steam’s request limit was reached. Try again later.'
        else:
            message = 'Steam’s friends service is temporarily unavailable.'
        raise FriendsError(message) from None
    except (URLError, TimeoutError, OSError):
        raise FriendsError('Could not reach Steam. Check your connection and try Refresh.') from None
    except (ValueError, UnicodeError):
        raise FriendsError('Steam returned an unreadable friends response.') from None


def avatar_url(value):
    if not isinstance(value, str):
        return ''
    parsed = urlsplit(value)
    host = parsed.hostname or ''
    allowed = host == 'steamcdn-a.akamaihd.net' or host.endswith('.steamstatic.com') or host == 'steamstatic.com'
    return value if parsed.scheme == 'https' and allowed and not parsed.username and not parsed.query else ''


def person(player):
    identity = str(player.get('steamid', ''))
    if not valid_id(identity):
        raise FriendsError('Steam returned an invalid player identifier.')
    state = player.get('personastate')
    state = state if isinstance(state, int) and state in STATES else None
    game = str(player.get('gameextrainfo') or '')
    if not game and str(player.get('gameid', '')).isdigit():
        game = 'Playing a game'
    group = 'in_game' if game and state not in (None, 0) else 'offline' if state == 0 else 'online' if state else 'unknown'
    return {'steamid': identity, 'name': str(player.get('personaname') or 'Steam friend'),
            'avatar': avatar_url(player.get('avatarmedium') or player.get('avatarfull') or player.get('avatar')),
            'status': STATES.get(state, 'Status unavailable'), 'group': group, 'game': game if group == 'in_game' else ''}


def snapshot_path(steamid):
    if not valid_id(steamid):
        raise FriendsError('Your Steam profile could not be identified.')
    return cache_dir()/('friends-'+steamid+'.json')


def read_snapshot(steamid):
    path = snapshot_path(steamid)
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('steamid') == steamid and data.get('version') == 1 and isinstance(data.get('friends'), list):
            return data
    except (OSError, ValueError, AttributeError):
        pass
    return None


def configure(payload):
    key = payload.get('api_key', '').strip()
    if not re.fullmatch(r'[A-Fa-f0-9]{32}', key):
        raise FriendsError('Paste the 32-character Steam Web API key into the key field.')
    profile = current_profile()
    # Check the key first; a failed replacement preserves any working credentials.
    response = api('GetPlayerSummaries/v2', key, {'steamids': profile['steamid']})
    own = response.get('response', {}).get('players', [])
    if not any(isinstance(p, dict) and str(p.get('steamid')) == profile['steamid'] for p in own):
        raise FriendsError('Steam did not return your profile. Check the key and current Steam account.')
    atomic_json(credential_path(), {'version': 1, 'steamid': profile['steamid'], 'api_key': key})
    path = snapshot_path(profile['steamid'])
    if path.exists():
        path.unlink()
    return {'configured': True}


def refresh(fresh=False):
    profile = current_profile()
    config = read_config()
    if config is None or config['steamid'] != profile['steamid']:
        return {'configured': False, 'profile': profile, 'friends': [], 'stale': False, 'updated_at': 0, 'error': ''}
    previous = read_snapshot(profile['steamid'])
    if previous and not fresh and time.time() - previous['updated_at'] < 30:
        return {**previous, 'configured': True, 'stale': False, 'error': ''}
    directory = cache_dir()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(directory/'friends-refresh.lock', os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        latest = read_snapshot(profile['steamid'])
        # Serialize monitor instances; rapid manual refresh clicks do not flood Steam.
        if latest and time.time() - latest['updated_at'] < (5 if fresh else 30):
            return {**latest, 'configured': True, 'stale': False, 'error': ''}
        try:
            raw = api('GetFriendList/v1', config['api_key'], {'steamid': profile['steamid'], 'relationship': 'friend'})
            records = raw.get('friendslist', {}).get('friends')
            if not isinstance(records, list):
                raise FriendsError('Steam did not return a friends list. Check your Friends List privacy setting.')
            ids = list(dict.fromkeys(str(item.get('steamid')) for item in records if isinstance(item, dict)
                                     and item.get('relationship', 'friend') == 'friend' and valid_id(item.get('steamid', ''))))
            if len(ids) > 5000:
                raise FriendsError('The friends list exceeds the supported size.')
            targets = [profile['steamid']] + [value for value in ids if value != profile['steamid']]
            players = {}
            deadline = time.monotonic() + 25
            for start in range(0, len(targets), 100):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise FriendsError('Steam took too long to refresh the friends list. Try again.')
                result = api('GetPlayerSummaries/v2', config['api_key'], {'steamids': ','.join(targets[start:start+100])}, min(7, remaining))
                for player in result.get('response', {}).get('players', []):
                    if isinstance(player, dict) and str(player.get('steamid', '')) in targets:
                        normalized = person(player)
                        players[normalized['steamid']] = normalized
            friends = [players.get(value, {'steamid': value, 'name': 'Steam friend', 'avatar': '', 'status': 'Status unavailable', 'group': 'unknown', 'game': ''}) for value in ids if value != profile['steamid']]
            rank = {'in_game': 0, 'online': 1, 'offline': 2, 'unknown': 3}
            friends.sort(key=lambda item: (rank[item['group']], item['name'].casefold()))
            data = {'version': 1, 'steamid': profile['steamid'], 'profile': players.get(profile['steamid'], profile),
                    'friends': friends, 'updated_at': int(time.time())}
            atomic_json(snapshot_path(profile['steamid']), data)
            return {**data, 'configured': True, 'stale': False, 'error': ''}
        except FriendsError as error:
            return {**(latest or {'profile': profile, 'friends': [], 'updated_at': 0}),
                    'configured': True, 'stale': True, 'error': str(error)}


def disconnect():
    path = credential_path()
    if path.exists() or path.is_symlink():
        path.unlink()
    directory = cache_dir()
    if directory.exists():
        for pattern in ('friends-*.json', 'game-personal-*.json'):
            for path in directory.glob(pattern):
                if path.is_file() or path.is_symlink():
                    path.unlink()
    return {'configured': False}


def chat(steamid):
    if not valid_id(steamid):
        raise FriendsError('This Steam contact could not be identified.')
    profile = current_profile()
    config = read_config()
    snapshot = read_snapshot(profile['steamid'])
    if not config or config['steamid'] != profile['steamid'] or not snapshot or not any(item.get('steamid') == steamid for item in snapshot['friends']):
        raise FriendsError('Refresh your friends list before opening this conversation.')
    from steam_backend import dispatch, focus_client
    result = dispatch('steam://friends/message/'+steamid)
    result['focused'] = focus_client('friends')
    return result


def main(args):
    if args in (['refresh'], ['refresh', 'fresh']):
        return refresh(len(args) == 2)
    if args == ['configure']:
        value = json.loads(sys.stdin.readline(1024))
        if not isinstance(value, dict):
            raise FriendsError('Enter an API key in the setup field.')
        return configure(value)
    if args == ['disconnect']:
        return disconnect()
    if len(args) == 2 and args[0] == 'chat':
        return chat(args[1])
    raise FriendsError('Unknown friends command.')


if __name__ == '__main__':
    try:
        print(json.dumps({'ok': True, **main(sys.argv[1:])}, ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        error = sys.exc_info()[1]
        # Never stringify network/IO/JSON errors: request details can contain keys.
        message = str(error) if isinstance(error, FriendsError) else 'The friends widget could not read or save its private configuration.'
        print(json.dumps({'ok': False, 'error': message}, ensure_ascii=False))
        sys.exit(1)
