#!/usr/bin/env python3
"""Optional system-side OBS camera setup, separate from user configuration."""
import argparse
import os
from pathlib import Path
import subprocess
import manage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'uninstall'], nargs='?', default='install')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--root', type=Path, default=Path('/'), help='Alternate staging root for tests')
    parser.add_argument('--load', action='store_true', help='Load v4l2loopback after installing (never unload an active camera)')
    args = parser.parse_args(); root = args.root.resolve()
    state = root / 'var/lib/omarchy-personal-widgets/camera'
    if args.load and root != Path('/'):
        raise ValueError('Cannot load a kernel module for a staging root.')
    if args.apply and root == Path('/') and os.geteuid() != 0:
        raise ValueError('Run this system-only step through sudo in a terminal.')
    if args.action == 'uninstall':
        return manage.remove_files(root, state, args.apply)
    files = {str(p.relative_to(manage.ROOT / 'config/system')): (p.read_bytes(), 0o644)
             for p in (manage.ROOT / 'config/system').rglob('*') if p.is_file()}
    for rel in files:
        print('Install', root / rel)
    if args.apply:
        manage.apply_files(root, state, files)
        if args.load:
            if root != Path('/'):
                raise ValueError('Cannot load a kernel module for a staging root.')
            subprocess.run(['modprobe', 'v4l2loopback'], check=True)
    else:
        print('Plan only. Install matching kernel headers and v4l2loopback-dkms before --apply --load.')
    print('OBS camera: /dev/video42, OBS Both Screens. Renew capture selections inside OBS.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print('Error:', error); raise SystemExit(1)
