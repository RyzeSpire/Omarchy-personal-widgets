#!/usr/bin/env python3
"""Read-only validation of the public bundle; never calls account/playback APIs."""
import ast
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import importlib.util
spec = importlib.util.spec_from_file_location('make_release', ROOT / 'scripts/make-release.py')
release = importlib.util.module_from_spec(spec); spec.loader.exec_module(release)


def main():
    errors = []
    counts = {'python': 0, 'json': 0, 'qml': 0, 'lua': 0, 'plugins': 0}
    for path in release.public_files():
        rel = str(path.relative_to(ROOT))
        if path.suffix in {'.py', '.json', '.qml', '.lua', '.md', '.ini', '.sh', '.txt', '.toml', '.conf'}:
            text = path.read_text()
            if re.search(re.escape(str(Path.home())) + r'(?:/|\b)', text):
                errors.append(rel + ': source-machine home path remains')
            if re.search(r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|-----BEGIN (?:RSA |OPENSSH |EC |PGP )?PRIVATE KEY', text):
                errors.append(rel + ': potential credential material')
        try:
            if path.suffix == '.py':
                ast.parse(path.read_text()); counts['python'] += 1
            elif path.suffix == '.json':
                json.loads(path.read_text()); counts['json'] += 1
            elif path.suffix == '.qml':
                counts['qml'] += 1
                parser = shutil.which('qmlformat') or ('/usr/lib/qt6/bin/qmlformat' if Path('/usr/lib/qt6/bin/qmlformat').exists() else None)
                if parser:
                    result = subprocess.run([parser, str(path)], capture_output=True, text=True)
                    if result.returncode:
                        errors.append(rel + ': QML parse error: ' + result.stderr[:300])
            elif path.suffix == '.lua' and shutil.which('luac'):
                counts['lua'] += 1
                result = subprocess.run(['luac', '-p', str(path)], capture_output=True, text=True)
                if result.returncode:
                    errors.append(rel + ': Lua parse error: ' + result.stderr[:300])
            if path.name == 'manifest.json' and path.parent.parent.name in ('plugins', 'vendor'):
                manifest = json.loads(path.read_text()); counts['plugins'] += 1
                if manifest.get('schemaVersion') != 1 or not (path.parent / manifest['entryPoints']['barWidget']).is_file():
                    errors.append(rel + ': invalid plugin entry point')
                if shutil.which('omarchy'):
                    result = subprocess.run(['omarchy', 'plugin', 'validate', str(path.parent)], capture_output=True, text=True)
                    if result.returncode:
                        errors.append(rel + ': manifest schema validation failed: ' + result.stderr[:300])
        except (ValueError, SyntaxError, KeyError) as error:
            errors.append(rel + ': ' + str(error))
    print('Validated:', json.dumps(counts))
    for error in errors:
        print('ERROR', error)
    if not shutil.which('omarchy'):
        print('Omarchy schema command unavailable; structural manifest validation only.')
    if not (shutil.which('qmlformat') or Path('/usr/lib/qt6/bin/qmlformat').exists()):
        print('QML parser unavailable; run validation again on the target Omarchy desktop.')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
