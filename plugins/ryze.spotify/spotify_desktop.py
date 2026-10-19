#!/usr/bin/env python3
"""Keep Spotify's audio engine available without occupying normal workspaces."""
import argparse
import fcntl
import os
import json
import re
import subprocess
import time
import spotify_api

SERVICE = 'org.mpris.MediaPlayer2.spotify'
OBJECT = '/org/mpris/MediaPlayer2'
PLAYER = 'org.mpris.MediaPlayer2.Player'
WORKSPACE = 'special:spotify'


def run(args, *, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check, timeout=5)


def clients():
    return [w for w in json.loads(run(['hyprctl', '-j', 'clients']).stdout)
            if w.get('class', '').lower() == 'spotify' and w.get('mapped')]


def dispatch(expression):
    response = run(['hyprctl', 'dispatch', expression]).stdout.strip()
    if response != 'ok':
        raise ValueError('Spotify window could not be moved. Please try again.')


def move(window, workspace):
    address = window.get('address', '')
    if not re.fullmatch(r'0x[0-9a-fA-F]+', address):
        raise ValueError('Spotify window could not be found.')
    dispatch('hl.dsp.window.move({ workspace = ' + json.dumps(workspace) +
             ', follow = false, window = ' + json.dumps('address:' + address) + ' })')


def remember_workspaces():
    # Remember each monitor's workspace before Open Spotify reveals workspace 0.
    previous = spotify_api.read_state('desktop-workspaces.json')
    for monitor in json.loads(run(['hyprctl', '-j', 'monitors']).stdout):
        workspace = monitor['activeWorkspace']['id']
        if workspace > 0 and workspace != 10:
            previous[monitor['name']] = workspace
    spotify_api.write_state('desktop-workspaces.json', previous)


def leave_empty_workspace():
    # Quit is asynchronous: wait for Spotify's window to disappear before leaving.
    deadline = time.monotonic() + 3
    while True:
        occupants = [w for w in json.loads(run(['hyprctl', '-j', 'clients']).stdout)
                     if w.get('mapped') and w['workspace']['id'] == 10]
        if not occupants:
            break
        if any(w.get('class', '').lower() != 'spotify' for w in occupants) or time.monotonic() >= deadline:
            return
        time.sleep(.1)
    previous = spotify_api.read_state('desktop-workspaces.json')
    workspaces = json.loads(run(['hyprctl', '-j', 'workspaces']).stdout)
    for monitor in json.loads(run(['hyprctl', '-j', 'monitors']).stdout):
        if monitor['activeWorkspace']['id'] != 10:
            continue
        target = previous.get(monitor['name'])
        existing = next((w for w in workspaces if w['id'] == target), None)
        if not isinstance(target, int) or target <= 0 or target == 10 or (existing and existing['monitor'] != monitor['name']):
            target = next((w['id'] for w in workspaces if w['id'] > 0 and w['id'] != 10 and w['monitor'] == monitor['name']), None)
        if target is None:
            occupied_ids = {w['id'] for w in workspaces}
            target = next(i for i in range(1, 100) if i != 10 and i not in occupied_ids)
        dispatch('hl.dsp.focus({ monitor = ' + json.dumps(monitor['name']) + ' })')
        dispatch('hl.dsp.focus({ workspace = ' + json.dumps(str(target)) + ', on_current_monitor = true })')
        # Hyprland removes an empty, inactive, nonpersistent workspace itself.


def hide():
    windows = clients()
    for window in windows:
        if window['workspace']['name'] != WORKSPACE:
            move(window, WORKSPACE)
    # Focusing a parked window elsewhere can reveal its special workspace.
    for monitor in json.loads(run(['hyprctl', '-j', 'monitors']).stdout):
        if monitor.get('specialWorkspace', {}).get('name') == WORKSPACE:
            dispatch('hl.dsp.workspace.toggle_special("spotify")')
    leave_empty_workspace()
    return windows


def ready():
    return run(['busctl', '--user', '--auto-start=no', 'get-property', SERVICE,
                OBJECT, PLAYER, 'PlaybackStatus'], check=False).returncode == 0


def ensure(*, visible=False):
    windows = clients()
    starting_background = not visible and not windows
    if not windows and (visible or not ready()):
        subprocess.Popen(['uwsm-app', '--', '/usr/bin/spotify'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    deadline = time.monotonic() + 25
    hidden_since = None
    while time.monotonic() < deadline:
        windows = clients() if visible else hide()
        if visible:
            if windows:
                return windows
        elif ready():
            if not starting_background:
                return windows
            # Spotify may expose MPRIS before its window maps or restores focus.
            # Wait for that window, then keep parking it through startup settling.
            if windows:
                if hidden_since is None:
                    hidden_since = time.monotonic()
                if time.monotonic() - hidden_since >= 1.2:
                    return windows
            else:
                hidden_since = None
        else:
            hidden_since = None
        time.sleep(.3)
    raise ValueError('Spotify is taking too long to start. Use Open Spotify to check its sign-in.')


def show():
    # Omarchy maps the 0 key to the tenth (last) workspace.
    target = 10
    remember_workspaces()
    windows = ensure(visible=True)
    window = windows[0]
    move(window, str(target))
    dispatch('hl.dsp.focus({ window = ' + json.dumps('address:' + window['address']) + ' })')


def quit_spotify():
    # Never launch or reveal Spotify just to terminate it.
    if ready():
        run(['busctl', '--user', '--auto-start=no', 'call', SERVICE, OBJECT,
             'org.mpris.MediaPlayer2', 'Quit'])
    elif clients():
        raise ValueError('Spotify is not responding to playback controls. Try quitting it from the app.')
    deadline = time.monotonic() + 5
    while ready():
        if time.monotonic() >= deadline:
            raise ValueError('Spotify did not finish quitting. Please try again.')
        time.sleep(.1)
    leave_empty_workspace()


def request_close():
    # Only one close prompt may exist, even when the shortcut is repeated.
    spotify_api.STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(spotify_api.STATE / 'close-prompt.lock', os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        if not clients() and not ready():
            return
        playing = run(['busctl', '--user', '--auto-start=no', 'get-property',
                       SERVICE, OBJECT, PLAYER, 'PlaybackStatus'], check=False)
        prompt = 'Music is playing. Close Spotify?' if '"Playing"' in playing.stdout else 'Close Spotify?'
        choice = subprocess.run([
            'omarchy', 'menu', 'select', prompt,
            '󰖰\tMinimize to widget\tKeep music playing in the background',
            '󰅖\tQuit Spotify\tStop music and close Spotify completely',
            '--', '--width', '520'], capture_output=True, text=True)
        # Escape and outside clicks cancel; no close request has been sent yet.
        if choice.returncode != 0:
            return
        selected = choice.stdout.strip().split('\t', 1)[0]
        with spotify_api.state_lock('desktop.lock'):
            if selected == 'Minimize to widget':
                hide()
            elif selected == 'Quit Spotify':
                quit_spotify()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['background', 'show', 'play', 'open-uri', 'request-close', 'quit'])
    parser.add_argument('uri', nargs='?', default='')
    args = parser.parse_args()
    try:
        if (args.action == 'open-uri' or (args.action == 'show' and args.uri)) and not re.fullmatch(r'spotify:(?:track|album|artist|playlist):[A-Za-z0-9]{22}', args.uri):
            raise ValueError('Choose a valid Spotify result.')
        if args.action == 'request-close':
            request_close()
            print(json.dumps({'ok': True}))
            return 0
        if args.action == 'quit':
            # Wait for any queue/playlist operation before shutting its player down.
            with spotify_api.state_lock('playback-control.lock'):
                with spotify_api.state_lock('desktop.lock'):
                    quit_spotify()
            print(json.dumps({'ok': True}))
            return 0
        with spotify_api.state_lock('desktop.lock'):
            if args.action == 'show':
                show()
                if args.uri:
                    subprocess.Popen(['uwsm-app', '--', '/usr/bin/spotify', args.uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            else:
                ensure()
                if args.action == 'play':
                    run(['busctl', '--user', 'call', SERVICE, OBJECT, PLAYER, 'Play'])
                elif args.action == 'open-uri':
                    run(['busctl', '--user', 'call', SERVICE, OBJECT, PLAYER, 'OpenUri', 's', args.uri])
                    time.sleep(.2)
                    hide()
        print(json.dumps({'ok': True}))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        message = str(error) if isinstance(error, ValueError) else ('Spotify could not quit. Please try again.' if args.action == 'quit' else 'Spotify could not start. Use Open Spotify to check its sign-in.')
        print(json.dumps({'ok': False, 'error': message}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
