"""Spotify OAuth PKCE, library/catalog access and playback control."""
import base64
from contextlib import contextmanager
import fcntl
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

STATE = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'omarchy/spotify-widget'
REDIRECT = 'http://127.0.0.1:8765/callback'
API = 'https://api.spotify.com/v1/'
PLAYBACK_SCOPES = {'user-read-playback-state', 'user-modify-playback-state'}
SCOPES = 'playlist-read-private playlist-read-collaborative user-read-playback-state user-read-currently-playing user-modify-playback-state'

class ApiError(ValueError):
    pass

@contextmanager
def state_lock(name):
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(STATE, 0o700)
    fd = os.open(STATE / name, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield

def read_state(name):
    try:
        with (STATE / name).open() as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except (ValueError, OSError):
        raise ApiError('Spotify connection settings could not be read. Please reconnect.')

def write_state(name, value):
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(STATE, 0o700)
    fd, path = tempfile.mkstemp(dir=STATE, prefix='.spotify-')
    try:
        with os.fdopen(fd, 'w') as file:
            json.dump(value, file)
            file.write('\n')
        os.replace(path, STATE / name)
    finally:
        if os.path.exists(path):
            os.unlink(path)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ApiError('Spotify returned an unexpected redirect. Please try again.')

OPENER = urllib.request.build_opener(NoRedirect)

def request_json(url, *, token=None, form=None, method=None, body=None):
    headers = {'Accept': 'application/json', 'User-Agent': 'Omarchy-Spotify-Widget/1.3'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    if body is not None:
        data = json.dumps(body).encode()
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with OPENER.open(req, timeout=12) as response:
        raw = response.read()
        return json.loads(raw) if raw else {}

def status():
    auth = read_state('oauth.json')
    return {'configured': bool(auth.get('client_id')), 'connected': bool(auth.get('refresh_token')), 'redirect_uri': REDIRECT,
            'playback_connected': PLAYBACK_SCOPES.issubset(set(auth.get('scope', '').split()))}

def configure(client_id):
    if not re.fullmatch(r'[A-Za-z0-9]{32}', client_id.strip()):
        raise ApiError('Enter the 32-character Client ID from your Spotify app settings.')
    with state_lock('oauth.lock'):
        old = read_state('oauth.json')
        if old.get('client_id') != client_id.strip():
            write_state('oauth.json', {'client_id': client_id.strip()})
            (STATE / 'library-cache.json').unlink(missing_ok=True)
    return status()

def store_tokens(tokens, auth):
    if not tokens.get('access_token'):
        raise ApiError('Spotify did not complete the connection. Please try again.')
    auth = dict(auth)
    auth['access_token'] = tokens['access_token']
    auth['refresh_token'] = tokens.get('refresh_token') or auth.get('refresh_token')
    auth['expires_at'] = time.time() + int(tokens.get('expires_in', 3600))
    if 'scope' in tokens:
        auth['scope'] = tokens['scope']
    if not auth['refresh_token']:
        raise ApiError('Spotify did not grant a renewable connection. Please reconnect.')
    write_state('oauth.json', auth)
    return auth

def authorize(client_id=''):
    if client_id:
        configure(client_id)
    auth = read_state('oauth.json')
    if not auth.get('client_id'):
        if not os.isatty(0):
            raise ApiError('Set up your Spotify app Client ID to connect.')
        print('Create an app at https://developer.spotify.com/dashboard', flush=True)
        print('Enable Web API. Redirect URI: ' + REDIRECT, flush=True)
        configure(input('Paste your Client ID (not the Client Secret): ').strip())
        auth = read_state('oauth.json')
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    expected_state = secrets.token_urlsafe(32)
    result = {}
    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            parsed = urllib.parse.urlsplit(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            correct = parsed.path == '/callback' and params.get('state') == [expected_state]
            if not correct:
                self.send_error(400, 'Invalid callback')
                return
            if params.get('error'):
                result['error'] = 'Spotify connection was cancelled. You can try again.'
            elif len(params.get('code', [])) == 1:
                result['code'] = params['code'][0]
            else:
                self.send_error(400, 'Missing authorization code')
                return
            page = b'<html><body style="font:18px sans-serif;background:#191b24;color:#ddd;padding:50px"><h2>Returning to your Spotify widget</h2><p>You can close this tab. The widget will confirm when the connection is complete.</p></body></html>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(page)))
            self.end_headers()
            self.wfile.write(page)
    try:
        server = HTTPServer(('127.0.0.1', 8765), Callback)
    except OSError:
        raise ApiError('Another connection is using port 8765. Finish that sign-in and try again.')
    server.timeout = 1
    try:
        params = {'client_id': auth['client_id'], 'response_type': 'code', 'redirect_uri': REDIRECT,
                  'scope': SCOPES, 'state': expected_state,
                  'code_challenge_method': 'S256', 'code_challenge': challenge}
        url = 'https://accounts.spotify.com/authorize?' + urllib.parse.urlencode(params)
        subprocess.Popen(['omarchy', 'launch', 'browser', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 300
        while not result and time.monotonic() < deadline:
            server.handle_request()
        if not result:
            raise ApiError('Spotify sign-in timed out. Please try connecting again.')
        if 'error' in result:
            raise ApiError(result['error'])
        tokens = request_json('https://accounts.spotify.com/api/token', form={
            'grant_type': 'authorization_code', 'code': result['code'], 'redirect_uri': REDIRECT,
            'client_id': auth['client_id'], 'code_verifier': verifier})
        with state_lock('oauth.lock'):
            store_tokens(tokens, auth)
        return status()
    finally:
        server.server_close()

def access_token(force=False):
    with state_lock('oauth.lock'):
        auth = read_state('oauth.json')
        if not auth.get('refresh_token'):
            raise ApiError('Connect your Spotify account to load your library and search results.')
        if not force and auth.get('access_token') and auth.get('expires_at', 0) > time.time() + 60:
            return auth['access_token']
        try:
            tokens = request_json('https://accounts.spotify.com/api/token', form={
                'grant_type': 'refresh_token', 'refresh_token': auth['refresh_token'], 'client_id': auth['client_id']})
        except urllib.error.HTTPError as e:
            if e.code in (400, 401):
                raise ApiError('Your Spotify connection expired or was revoked. Please reconnect.')
            raise
        return store_tokens(tokens, auth)['access_token']

def api_request(path, *, method='GET', body=None):
    url = path if path.startswith('https://') else API + path.lstrip('/')
    if not url.startswith(API):
        raise ApiError('Spotify returned an unexpected API address.')
    for attempt in range(2):
        try:
            return request_json(url, token=access_token(force=attempt == 1), method=method, body=body)
        except urllib.error.HTTPError as e:
            if e.code == 401 and attempt == 0:
                continue
            if e.code == 403:
                if path.startswith('me/player') and not status()['playback_connected']:
                    raise ApiError('Enable playback access to view the queue and select songs.')
                if path.startswith('playlists/'):
                    raise ApiError('Spotify allows this app to read songs only from playlists you own or collaborate on.')
                raise ApiError('Spotify denied access. Check the app’s allowed users and Premium subscription.')
            if e.code == 404:
                raise ApiError('Spotify could not find this playlist or playback device. Start Spotify and try again.')
            if e.code == 429:
                raise ApiError('Spotify has temporarily limited requests. Please try again later.')
            if e.code == 401:
                raise ApiError('Your Spotify connection expired. Please reconnect.')
            raise ApiError('Spotify could not complete this request. Please try again.')

def api_get(path):
    return api_request(path)

def cover(item):
    images = item.get('images') or (item.get('album') or {}).get('images') or []
    return images[-1].get('url', '') if images else ''

def playlists(fresh=False):
    if not status()['connected']:
        return None
    cached = read_state('library-cache.json')
    if not fresh and cached.get('fetched_at', 0) > time.time() - 180:
        return cached.get('items', [])
    items = []
    next_page = 'me/playlists?limit=50'
    while next_page:
        page = api_get(next_page)
        for item in page.get('items', []):
            if item and item.get('uri'):
                items.append({'uri': item['uri'], 'name': item['name'], 'cover': cover(item), 'source': 'spotify'})
        next_page = page.get('next')
    write_state('library-cache.json', {'fetched_at': time.time(), 'items': items})
    return items

def search(query):
    query = query.strip()
    if not query:
        return []
    data = api_get('search?' + urllib.parse.urlencode({'q': query, 'type': 'track,artist,album,playlist', 'limit': 5}))
    out = []
    for group, kind in [('tracks', 'Song'), ('artists', 'Artist'), ('albums', 'Album'), ('playlists', 'Playlist')]:
        for item in (data.get(group) or {}).get('items', []):
            if not item or not item.get('uri'):
                continue
            artists = ', '.join(artist.get('name', '') for artist in item.get('artists', []))
            out.append({'uri': item['uri'], 'name': item['name'], 'cover': cover(item),
                        'detail': kind + (' · ' + artists if artists else ''), 'kind': kind})
    return out

def disconnect():
    with state_lock('oauth.lock'):
        auth = read_state('oauth.json')
        write_state('oauth.json', {'client_id': auth['client_id']} if auth.get('client_id') else {})
        (STATE / 'library-cache.json').unlink(missing_ok=True)
        for cache in STATE.glob('playlist-*.json'):
            cache.unlink(missing_ok=True)
    return status()
