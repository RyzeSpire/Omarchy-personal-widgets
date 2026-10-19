#!/usr/bin/env python3
"""Spotify library, catalog, authorization and desktop navigation."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import spotify_api

STATE = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'omarchy/spotify-widget'


def playlist_uri(value):
    value = value.strip()
    match = re.fullmatch(r'spotify:playlist:([A-Za-z0-9]{22})', value)
    if not match:
        url = urllib.parse.urlsplit(value)
        if url.scheme != 'https' or url.hostname != 'open.spotify.com' or url.port not in (None, 443):
            raise ValueError('Paste a Spotify playlist link or URI.')
        match = re.fullmatch(r'/(?:intl-[a-z]{2}/)?playlist/([A-Za-z0-9]{22})/?', url.path)
    if not match:
        raise ValueError('This link is not a Spotify playlist.')
    return 'spotify:playlist:' + match.group(1)


def read_playlists():
    try:
        items = json.loads((STATE / 'playlists.json').read_text())
    except FileNotFoundError:
        return []
    if not isinstance(items, list):
        raise ValueError('The saved playlist list could not be read.')
    return items


def update_playlists(transform):
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE / 'playlists.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        items = transform(read_playlists())
        fd, name = tempfile.mkstemp(dir=STATE, prefix='.playlists-')
        try:
            with os.fdopen(fd, 'w') as file:
                json.dump(items, file, ensure_ascii=False)
                file.write('\n')
            os.replace(name, STATE / 'playlists.json')
        finally:
            if os.path.exists(name):
                os.unlink(name)
    return items


def save_playlist(link, name):
    uri = playlist_uri(link)
    playlist_id = uri.rsplit(':', 1)[1]
    url = 'https://open.spotify.com/playlist/' + playlist_id
    cover = ''
    try:
        endpoint = 'https://open.spotify.com/oembed?' + urllib.parse.urlencode({'url': url})
        req = urllib.request.Request(endpoint, headers={'User-Agent': 'Omarchy-Spotify-Widget/1.2'})
        with urllib.request.urlopen(req, timeout=8) as response:
            meta = json.load(response)
        name = name.strip() or str(meta.get('title') or '')
        thumbnail = str(meta.get('thumbnail_url') or '')
        if urllib.parse.urlsplit(thumbnail).scheme == 'https':
            cover = thumbnail
    except (urllib.error.URLError, TimeoutError, ValueError):
        pass
    name = name.strip()
    if not name:
        raise ValueError('Spotify could not read this playlist. Enter a name to save the link.')
    item = {'uri': uri, 'name': name[:160], 'cover': cover}
    return update_playlists(lambda items: [item] + [i for i in items if i.get('uri') != uri])


def search_in_spotify(query):
    query = query.strip()
    if not query:
        raise ValueError('Enter a song, artist, album, or playlist.')
    uri = 'spotify:search:' + urllib.parse.quote(query, safe='')
    subprocess.Popen(['uwsm-app', '--', '/usr/bin/spotify', uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    subprocess.run(['omarchy', 'launch', 'spotify'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def library_items(fresh=False):
    shortcuts = [{**item, 'source': 'shortcut'} for item in read_playlists()]
    remote = spotify_api.playlists(fresh=fresh)
    if remote is None:
        return shortcuts, {'connected': False}
    saved = {item['uri'] for item in shortcuts}
    return shortcuts + [item for item in remote if item['uri'] not in saved], {'connected': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['list', 'save', 'remove', 'search', 'open', 'status', 'configure', 'authorize', 'disconnect', 'catalog'])
    parser.add_argument('value', nargs='?', default='')
    parser.add_argument('name', nargs='?', default='')
    args = parser.parse_args()
    try:
        extra = {}
        if args.action in ('status', 'configure', 'authorize', 'disconnect'):
            if args.action == 'configure':
                extra = spotify_api.configure(args.value)
            elif args.action == 'authorize':
                extra = spotify_api.authorize(args.value)
            elif args.action == 'disconnect':
                extra = spotify_api.disconnect()
            else:
                extra = spotify_api.status()
            items = []
        elif args.action == 'catalog':
            items = spotify_api.search(args.value)
            extra = {'mode': 'catalog', 'connected': True}
        elif args.action == 'list':
            items, extra = library_items(fresh=args.value == 'fresh')
        elif args.action == 'save':
            items = save_playlist(args.value, args.name)
        elif args.action == 'remove':
            uri = playlist_uri(args.value)
            items = update_playlists(lambda items: [i for i in items if i.get('uri') != uri])
        elif args.action == 'open':
            uri = args.value.strip()
            if not re.fullmatch(r'spotify:(?:track|album|artist|playlist):[A-Za-z0-9]{22}', uri):
                raise ValueError('Choose a valid Spotify result.')
            subprocess.Popen(['uwsm-app', '--', '/usr/bin/spotify', uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            subprocess.run(['omarchy', 'launch', 'spotify'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            items = []
        else:
            search_in_spotify(args.value)
            items = []
        if args.action in ('save', 'remove'):
            items, extra = library_items()
        print(json.dumps({'ok': True, 'items': items, **extra}, ensure_ascii=False))
    except (ValueError, OSError, subprocess.SubprocessError, TimeoutError):
        # Keep credentials and network error details out of widget output.
        import sys
        exc = sys.exception()
        message = str(exc) if isinstance(exc, ValueError) else 'Could not reach Spotify. Check your connection and try again.'
        print(json.dumps({'ok': False, 'error': message}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
