#!/usr/bin/env python3
"""Preview or apply the standalone, user-scoped Sober lifecycle."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess

APP = 'org.vinegarhq.Sober'
FLATHUB = 'https://dl.flathub.org/repo/flathub.flatpakrepo'


def launcher_links(home, remove=False):
    """Bridge Flatpak exports into the standard XDG user search directories."""
    exported = home / '.local/share/flatpak/exports/share'
    paths = {
        home / '.local/share/applications' / (APP + '.desktop'):
            exported / 'applications' / (APP + '.desktop'),
        home / '.local/share/icons/hicolor/scalable/apps' / (APP + '.svg'):
            exported / 'icons/hicolor/scalable/apps' / (APP + '.svg'),
    }
    def owned(link, target):
        return link.is_symlink() and os.readlink(link) == str(target)
    # Check the complete plan before creating links; never replace user files.
    if not remove:
        for link, target in paths.items():
            if not target.is_file():
                raise ValueError('Missing installed Sober export: ' + str(target))
            if (link.exists() or link.is_symlink()) and not owned(link, target):
                raise ValueError('Preserve existing launcher/icon; review it first: ' + str(link))
    for link, target in paths.items():
        if remove:
            if owned(link, target):
                link.unlink()
        elif not owned(link, target):
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'update', 'uninstall', 'launcher'), nargs='?', default='install')
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
    elif args.action == 'uninstall':
        commands.append(['flatpak', 'uninstall', '--user', '-y', APP])
    for command in commands:
        print(shlex.join(command), flush=True)
    print('Launcher/icon links:', 'remove only owned links' if args.action == 'uninstall' else 'link installed Flatpak exports into standard user XDG directories')
    if not args.apply:
        print('Preview only. Add --apply to execute. No accounts or app data are included.')
        return 0
    if os.geteuid() == 0:
        parser.error('Run as your normal desktop user; user Flatpaks must not belong to root.')
    if args.action != 'install' and not shutil.which('flatpak'):
        parser.error('Flatpak is not installed.')
    for command in commands:
        subprocess.run(command, check=True)
    launcher_links(Path.home(), remove=args.action == 'uninstall')
    print('Account sign-in/first-run Roblox download are interactive. Uninstall preserves app data and shared runtimes.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
