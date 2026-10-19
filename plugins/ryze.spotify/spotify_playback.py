#!/usr/bin/env python3
"""Playlist detail, live queue and explicit track selection for the widget."""
import argparse
import html
import json
import re
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import spotify_api as api


def playlist_id(uri):
    match = re.fullmatch(r'spotify:playlist:([A-Za-z0-9]{22})', uri)
    if not match:
        raise api.ApiError('Choose a valid Spotify playlist.')
    return match[1]


def spotify_track_uri(value):
    """Recognize Spotify identities only; never accept a filesystem playback URI."""
    uri = str(value or '')
    if uri.startswith('https://'):
        url = urllib.parse.urlsplit(uri)
        if url.hostname != 'open.spotify.com' or url.port not in (None, 443):
            return ''
        match = re.fullmatch(r'/(?:intl-[a-z]{2}/)?(track|episode)/([A-Za-z0-9]{22})/?', url.path)
        if match:
            uri = 'spotify:' + ':'.join(match.groups())
        elif re.fullmatch(r'/(?:intl-[a-z]{2}/)?local/[^/]*?/[^/]*?/[^/]*?/\d+/?', url.path):
            uri = 'spotify:local:' + url.path.split('/local/', 1)[1].rstrip('/').replace('/', ':')
    if re.fullmatch(r'spotify:(?:track|episode):[A-Za-z0-9]{22}', uri):
        return uri
    if re.fullmatch(r'spotify:local:[^:\r\n]*:[^:\r\n]*:[^:\r\n]*:\d+', uri):
        return uri
    return ''


def track(item, position=0, is_local=False):
    raw_uri = str(item.get('uri') or '')
    uri = spotify_track_uri(raw_uri)
    local = bool(is_local or item.get('is_local') or uri.startswith('spotify:local:'))
    artist = ', '.join(a.get('name', '') for a in item.get('artists') or [])
    if not artist:
        artist = (item.get('show') or {}).get('publisher', '')
    return {'uri': uri or raw_uri, 'name': item.get('name') or 'Unavailable song',
            'artist': artist, 'cover': api.cover(item), 'is_local': local,
            'duration_ms': item.get('duration_ms') or 0, 'position': position,
            # Local files have no catalogue availability; the desktop decides whether
            # its indexed file is available when given the playlist and position.
            'playable': bool(uri) and (local or item.get('is_playable') is not False)}


def playlist(uri, fresh=False):
    pid = playlist_id(uri)
    cached = api.read_state('playlist-' + pid + '.json')
    if not fresh and cached.get('format') == 2 and cached.get('fetched_at', 0) > time.time() - 180:
        return cached['playlist']
    meta = api.api_get('playlists/' + pid)
    out = []
    next_page = 'playlists/' + pid + '/items?limit=50'
    position = 0
    total = 0
    while next_page:
        page = api.api_get(next_page)
        total = page.get('total', total)
        for entry in page.get('items') or []:
            item = (entry.get('item') or entry.get('track')) if entry else None
            if item:
                out.append(track(item, position, bool(entry.get('is_local'))))
            position += 1
        next_page = page.get('next')
    owner = meta.get('owner') or {}
    data = {'uri': uri, 'name': meta.get('name', 'Playlist'),
            'cover': ((meta.get('images') or [{}])[0]).get('url', ''),
            'owner': owner.get('display_name') or owner.get('id', ''),
            'description': html.unescape(re.sub(r'<[^>]+>', '', meta.get('description') or '')),
            'public': meta.get('public'), 'total': total,
            'duration_ms': sum(t['duration_ms'] for t in out),
            'local_count': sum(t['is_local'] for t in out), 'items': out}
    api.write_state('playlist-' + pid + '.json', {'format': 2, 'fetched_at': time.time(), 'playlist': data})
    return data


def queue():
    if not api.status()['playback_connected']:
        raise api.ApiError('Enable playback access to view your Spotify queue.')
    state = api.api_get('me/player')
    state_item = state.get('item') or {}
    local_playing = bool(state_item.get('is_local') or spotify_track_uri(state_item.get('uri')).startswith('spotify:local:'))
    try:
        data = api.api_get('me/player/queue')
    except api.ApiError:
        if not local_playing:
            raise
        # Some Spotify clients reject queue requests during local-file playback.
        data = {}
    context_uri = (state.get('context') or {}).get('uri', '')
    library = api.read_state('library-cache.json').get('items') or []
    name = next((p['name'] for p in library if p.get('uri') == context_uri), '')
    current = data.get('currently_playing') or state_item or None
    return {'current': track(current) if current else None,
            'items': [track(item, i) for i, item in enumerate(data.get('queue') or []) if item],
            'context_uri': context_uri, 'context_name': name,
            'local_queue_unavailable': local_playing and not data.get('queue')}


def local_device():
    import spotify_desktop
    spotify_desktop.ensure()
    devices = api.api_get('me/player/devices').get('devices') or []
    hostname = socket.gethostname().lower()
    local = next((d for d in devices if d.get('type') == 'Computer'
                  and (d.get('name') or '').lower() == hostname), None)
    if not local or not local.get('id') or local.get('is_restricted'):
        raise api.ApiError('Spotify’s local playback device is unavailable. Open Spotify and try again.')
    return local


def local_track_uri():
    import spotify_desktop as desktop
    result = desktop.run(['busctl', '--user', '--json=short', 'get-property',
                          desktop.SERVICE, desktop.OBJECT, desktop.PLAYER, 'Metadata'])
    data = json.loads(result.stdout)['data']
    value = (data.get('xesam:url') or {}).get('data', '')
    uri = spotify_track_uri(value)
    if uri:
        return uri
    raise api.ApiError('Spotify has not reported its current song. Refresh the queue and try again.')


def play_queue(uri, position=-1):
    if not api.status()['playback_connected']:
        raise api.ApiError('Enable playback access to select songs in the widget.')
    uri = spotify_track_uri(uri)
    if not uri:
        raise api.ApiError('Choose a valid queued song.')
    import spotify_desktop as desktop
    local = local_device()
    state = api.api_get('me/player')
    if (state.get('device') or {}).get('id') != local['id']:
        raise api.ApiError('This queue is not active on this computer. Start Spotify here and refresh the queue.')
    data = api.api_get('me/player/queue')
    upcoming = [item for item in data.get('queue') or [] if item and item.get('uri')]
    matches = [i for i, item in enumerate(upcoming) if item['uri'] == uri]
    current = local_track_uri()
    command = ['busctl', '--user', 'call', desktop.SERVICE, desktop.OBJECT, desktop.PLAYER]
    if not matches:
        if current == uri:
            desktop.run(command + ['Play'])
            return
        raise api.ApiError('That song is no longer queued. Refresh the queue and choose it again.')
    index = position if position in matches else min(matches, key=lambda i: abs(i - max(0, position)))
    prefix = upcoming[:index + 1]
    # The Web API may briefly lag the desktop after a track transition.
    if prefix and prefix[0]['uri'] == current and (data.get('currently_playing') or {}).get('uri') != current:
        prefix = prefix[1:]
    for item in prefix:
        expected = item['uri']
        before = current
        desktop.run(command + ['Next'])
        # Wait for the local player between commands; never rebuild the queue.
        time.sleep(0.4 if expected == before else 0.15)
        deadline = time.monotonic() + 5
        while True:
            current = local_track_uri()
            if current == expected:
                break
            if time.monotonic() >= deadline:
                raise api.ApiError('Spotify’s queue changed during the jump. Refresh it and choose the song again.')
            time.sleep(0.15)
    desktop.run(command + ['Play'])


def play(uri, position=-1):
    if not api.status()['playback_connected']:
        raise api.ApiError('Enable playback access to select songs in the widget.')
    pid = playlist_id(uri)
    if position < -1:
        raise api.ApiError('Choose a valid song position.')
    local = local_device()
    body = {'context_uri': 'spotify:playlist:' + pid, 'position_ms': 0}
    if position >= 0:
        body['offset'] = {'position': position}
    api.api_request('me/player/play?' + urllib.parse.urlencode({'device_id': local['id']}), method='PUT', body=body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['playlist', 'queue', 'play', 'queue-play'])
    parser.add_argument('value', nargs='?', default='')
    parser.add_argument('extra', nargs='?', default='')
    args = parser.parse_args()
    try:
        result = {}
        if args.action == 'playlist':
            result['playlist'] = playlist(args.value, args.extra == 'fresh')
        elif args.action == 'queue':
            result['queue'] = queue()
        else:
            with api.state_lock('playback-control.lock'):
                position = int(args.extra) if args.extra else -1
                if args.action == 'queue-play':
                    play_queue(args.value, position)
                else:
                    play(args.value, position)
        print(json.dumps({'ok': True, **result}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError, TimeoutError) as error:
        message = str(error) if isinstance(error, api.ApiError) else 'Could not reach Spotify. Please try again.'
        print(json.dumps({'ok': False, 'error': message,
                          'needs_authorization': not api.status()['playback_connected']}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
