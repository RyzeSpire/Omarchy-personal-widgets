#!/usr/bin/env python3
"""Export personal state into an encrypted archive; never store it in this repo."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import sys

REPO = Path(__file__).resolve().parents[1]
# Explicit lists keep notifications, clipboard history and old backups out.
STATE = ['.local/state/omarchy/spotify-widget', '.local/state/omarchy/steam-widget',
         '.config/omarchy/steam-widget', '.local/state/omarchy-protonvpn',
         '.config/Proton', '.local/state/wireplumber', '.config/Vencord/settings',
         '.config/spotify', '.config/mise/config.toml', '.codex/config.toml', '.codex/skills']
PROFILES = ['.config', '.mozilla',
            '.local/share/Steam/config', '.local/share/Steam/userdata', '.config/obs-studio', '.config/dconf/user']
SKIP = {'__pycache__', 'Cache', 'Code Cache', 'GPUCache', 'ShaderCache', 'DawnGraphiteCache',
        'DawnWebGPUCache', 'logs', 'Crashpad', 'crash-reports', 'blob_storage', 'node_modules', 'backups', '.git'}


def private_path(path):
    path = path.expanduser().resolve()
    if path.is_relative_to(REPO):
        raise ValueError('Private exports must be outside the Git repository.')
    return path


def collect(home, profiles=False, media=False, keyrings=False):
    relative = STATE + (PROFILES if profiles else [])
    if media:
        relative += ['Music/Spotify_local']
    if keyrings:
        relative += ['.local/share/keyrings']
    files = {}
    for item in relative:
        path = home / item
        if not path.exists() or path.is_symlink():
            continue
        candidates = path.rglob('*') if path.is_dir() else [path]
        for source in candidates:
            if source.is_symlink() or not source.is_file() or set(source.relative_to(home).parts) & SKIP:
                continue
            files[str(source.relative_to(home))] = source
    return files


def export(args):
    output = private_path(args.output)
    files = collect(args.home, args.profiles, args.media, args.keyrings)
    print('Private export:', len(files), 'files.', sum(p.stat().st_size for p in files.values()), 'bytes before compression.')
    print('Destination:', output)
    if not args.apply:
        print('Plan only. Close apps, then add --apply. GPG asks for an encryption passphrase in your terminal.')
        return
    if not shutil.which('gpg'):
        raise ValueError('GnuPG is required.')
    if not sys.stdin.isatty():
        raise ValueError('Run private export in an interactive terminal so GPG can ask for a passphrase.')
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    environment = dict(os.environ, GPG_TTY=os.ttyname(sys.stdin.fileno()))
    try:
        with os.fdopen(fd, 'wb') as encrypted:
            process = subprocess.Popen(['gpg', '--symmetric', '--cipher-algo', 'AES256', '--compress-algo', 'none'],
                                       stdin=subprocess.PIPE, stdout=encrypted, env=environment)
            try:
                with tarfile.open(fileobj=process.stdin, mode='w|gz') as archive:
                    for name, source in sorted(files.items()):
                        info = archive.gettarinfo(str(source), arcname=name)
                        info.uid = info.gid = 0; info.uname = info.gname = ''
                        if not info.isfile():
                            continue
                        with source.open('rb') as data:
                            archive.addfile(info, data)
                process.stdin.close()
                if process.wait() != 0:
                    raise ValueError('GPG encryption failed.')
            except BaseException:
                process.stdin.close()
                process.wait()
                raise
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    print('Encrypted private archive created. Keep its passphrase separately; never upload it to GitHub.')


def restore(args):
    source = private_path(args.archive)
    dest = private_path(args.dest)
    if dest == args.home.resolve() or (dest.exists() and any(dest.iterdir())):
        raise ValueError('Decrypt only into an empty review directory, not your live home.')
    print('Decrypt to review directory:', dest)
    if not args.apply:
        print('Plan only. Add --apply to decrypt; copying data back into apps is a separate step.')
        return
    if not sys.stdin.isatty():
        raise ValueError('Run decryption in an interactive terminal.')
    dest.mkdir(parents=True, mode=0o700, exist_ok=True)
    process = subprocess.Popen(['gpg', '--decrypt', str(source)], stdout=subprocess.PIPE,
                               env=dict(os.environ, GPG_TTY=os.ttyname(sys.stdin.fileno())))
    try:
        with tarfile.open(fileobj=process.stdout, mode='r|gz') as archive:
            for member in archive:
                rel = Path(member.name)
                target = dest / rel
                if rel.is_absolute() or '..' in rel.parts or not member.isfile() or not target.resolve().is_relative_to(dest):
                    raise ValueError('Unsafe entry in archive.')
                # Extract only regular files with private permissions; no link/device restore.
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with target.open('xb') as output, archive.extractfile(member) as data:
                    shutil.copyfileobj(data, output)
                target.chmod(0o600)
        process.stdout.close()
        if process.wait() != 0:
            raise ValueError('GPG authentication/decryption failed. Do not use any partially extracted data.')
    except BaseException:
        process.stdout.close(); process.terminate(); process.wait()
        raise
    print('Decrypted into staging only. Review and selectively restore while apps are closed. Reauthorization may still be needed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['export', 'restore'])
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--output', type=Path, default=Path.home() / 'omarchy-private-migration.tar.gz.gpg')
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--dest', type=Path, default=Path.home() / 'omarchy-migration-review')
    parser.add_argument('--profiles', action='store_true', help='Include all ~/.config plus Firefox/Steam profiles (close apps first); caches/backups excluded')
    parser.add_argument('--media', action='store_true', help='Include Music/Spotify_local, including archives')
    parser.add_argument('--keyrings', action='store_true', help='Include all login keyrings; may need the original login password')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(); args.home = args.home.expanduser().resolve()
    if args.action == 'restore' and not args.archive:
        parser.error('restore requires --archive')
    export(args) if args.action == 'export' else restore(args)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError) as error:
        print('Error:', error, file=sys.stderr); raise SystemExit(1)
