#!/usr/bin/env python3
"""Preview or apply the standalone, user-scoped Sober lifecycle."""
import argparse
import os
import shlex
import shutil
import subprocess

APP = 'org.vinegarhq.Sober'
FLATHUB = 'https://dl.flathub.org/repo/flathub.flatpakrepo'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'update', 'uninstall'), nargs='?', default='install')
    parser.add_argument('--apply', action='store_true', help='Execute; otherwise only print commands')
    args = parser.parse_args()
    commands = []
    if args.action == 'install':
        if not shutil.which('flatpak'):
            commands.append(['omarchy', 'pkg', 'add', 'flatpak'])
        commands.extend([
            ['flatpak', 'remote-add', '--user', '--if-not-exists', 'flathub', FLATHUB],
            ['flatpak', 'install', '--user', '--noninteractive', '-y', 'flathub', APP],
        ])
    elif args.action == 'update':
        commands.append(['flatpak', 'update', '--user', '-y', APP])
    else:
        commands.append(['flatpak', 'uninstall', '--user', '-y', APP])
    for command in commands:
        print(shlex.join(command), flush=True)
    if not args.apply:
        print('Preview only. Add --apply to execute. No accounts or app data are included.')
        return 0
    if os.geteuid() == 0:
        parser.error('Run as your normal desktop user; user Flatpaks must not belong to root.')
    if args.action != 'install' and not shutil.which('flatpak'):
        parser.error('Flatpak is not installed.')
    for command in commands:
        subprocess.run(command, check=True)
    print('Account sign-in/first-run Roblox download are interactive. Uninstall preserves app data and shared runtimes.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
