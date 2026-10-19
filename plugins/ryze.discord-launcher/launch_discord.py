#!/usr/bin/env python3
"""Launch native Discord on workspace 8 and detect background Discord processes."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time


def hypr(*args):
    return subprocess.check_output(['hyprctl', *args], text=True, timeout=4)


def is_discord_process(name, executable):
    # Electron renderer/updater/crash-handler processes count even without a window.
    name = name.lower()
    executable = executable.lower().removesuffix(' (deleted)')
    return name in {'discord', 'discordcanary', 'discordptb'} or any(
        '/' + directory + '/' in executable
        for directory in ('discord', 'discordcanary', 'discordptb'))


def desktop_running():
    uid = os.getuid()
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != uid:
                continue
            name = (proc / 'comm').read_text().strip()
            try:
                executable = os.readlink(proc / 'exe')
            except OSError:
                executable = ''
            if is_discord_process(name, executable):
                return True
        except OSError:
            # Processes can exit while /proc is being inspected.
            continue
    return False


def status():
    native = desktop_running()
    web = False
    if not native:
        try:
            web = any(w.get('mapped') and w.get('class', '').lower().startswith('chrome-discord.com__')
                      for w in json.loads(hypr('-j', 'clients')))
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    return {'running': native or web, 'desktop_running': native, 'web_running': web}


def discord_windows():
    windows = json.loads(hypr('-j', 'clients'))
    return [w for w in windows if w.get('mapped') and
            w.get('class', '').lower() in {'discord', 'discordcanary', 'discordptb'}]


def focus(window):
    address = window.get('address', '')
    if not re.fullmatch(r'0x[0-9a-fA-F]+', address):
        raise ValueError('Discord window could not be identified.')
    monitors = json.loads(hypr('-j', 'monitors'))
    if any(m.get('name') == 'HDMI-A-1' for m in monitors):
        workspaces = json.loads(hypr('-j', 'workspaces'))
        workspace = next((w for w in workspaces if w.get('id') == 8), None)
        if workspace and workspace.get('monitor') != 'HDMI-A-1':
            hypr('dispatch', 'hl.dsp.workspace.move({ workspace="8", monitor="HDMI-A-1" })')
    response = hypr('dispatch', 'hl.dsp.window.move({ workspace="8", follow=true, window=' +
                    json.dumps('address:' + address) + ' })').strip()
    if response != 'ok':
        raise ValueError('Discord could not be moved to workspace 8.')
    response = hypr('dispatch', 'hl.dsp.focus({ window=' + json.dumps('address:' + address) + ' })').strip()
    if response != 'ok':
        raise ValueError('Discord could not be focused.')


def launch():
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', '/run/user/' + str(os.getuid())))
    fd = os.open(runtime / 'omarchy-discord-launch.lock', os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        windows = discord_windows()
        if not windows:
            executable = shutil.which('discord') or shutil.which('Discord')
            if not executable:
                raise ValueError('The Discord desktop app is not installed.')
            # Calling its launcher also restores an already-running tray instance.
            subprocess.Popen(['uwsm-app', '--', executable],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
            deadline = time.monotonic() + 25
            while not windows and time.monotonic() < deadline:
                time.sleep(.25)
                windows = discord_windows()
        if not windows:
            raise ValueError('Discord took too long to open. Please try again.')
        focus(windows[0])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['launch', 'status'], nargs='?', default='launch')
    args = parser.parse_args()
    try:
        if args.action == 'launch':
            launch()
        print(json.dumps({'ok': True, **status()}))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        message = str(error) if isinstance(error, ValueError) else 'Could not open Discord on workspace 8.'
        print(json.dumps({'ok': False, 'error': message}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
