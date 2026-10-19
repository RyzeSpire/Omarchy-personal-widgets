#!/usr/bin/env python3
"""Create a source-only release; private archives and the Git database are excluded."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import sys

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'plugins', 'vendor', 'config', 'inventory', 'docs', 'scripts', 'tests', 'licenses', '.github'}
TOP = {'AGENTS.md', 'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', '.gitignore', 'profile.json', 'install.sh'}


def public_files():
    for path in sorted(ROOT.rglob('*')):
        rel = path.relative_to(ROOT)
        if not path.is_file() or path.is_symlink():
            continue
        if not ((len(rel.parts) == 1 and path.name in TOP) or rel.parts[0] in ALLOWED):
            continue
        if any(part in {'__pycache__', '.git', '.venv', '.pytest_cache', 'backups'} for part in rel.parts):
            continue
        if path.suffix in {'.pyc', '.gpg', '.age', '.lock', '.sqlite', '.log'}:
            continue
        yield path


def main():
    output = ROOT / 'dist'; output.mkdir(exist_ok=True)
    target = output / 'omarchy-personal-widgets.tar.gz'
    entries = list(public_files())
    checksums = {}
    with tarfile.open(target, 'w:gz') as archive:
        for path in entries:
            relative = str(path.relative_to(ROOT))
            data = path.read_bytes(); checksums[relative] = hashlib.sha256(data).hexdigest()
            info = tarfile.TarInfo('Omarchy-personal-widgets/' + relative)
            info.size = len(data); info.mode = path.stat().st_mode & 0o777; info.mtime = 0
            archive.addfile(info, io.BytesIO(data))
        data = (json.dumps(checksums, indent=2) + '\n').encode()
        info = tarfile.TarInfo('Omarchy-personal-widgets/SHA256SUMS.json'); info.size = len(data); info.mode = 0o644
        archive.addfile(info, io.BytesIO(data))
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / 'SHA256SUMS').write_text(checksum + '  ' + target.name + '\n')
    print('Source bundle:', target, '\nFiles:', len(entries), '\nSHA256:', checksum)


if __name__ == '__main__':
    main()
