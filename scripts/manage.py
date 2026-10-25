#!/usr/bin/env python3
"""Plan, install, update and reverse the personal setup without touching accounts."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
PROFILE = json.loads((ROOT / 'profile.json').read_text())
INTEGRATION = 'require("hypr.personal-widgets")'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def deep_merge(old, new):
    if not isinstance(old, dict) or not isinstance(new, dict):
        return new
    result = dict(old)
    for key, value in new.items():
        result[key] = deep_merge(result.get(key), value)
    return result


def read_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()


def destination(base, relative):
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('Unsafe destination: ' + str(relative))
    path = base / rel
    # Refuse existing symlink-managed dotfiles rather than write through them.
    current = base
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Symlink destination needs manual handling: ' + str(current))
    if not path.resolve().is_relative_to(base.resolve()):
        raise ValueError('Destination escapes the target directory.')
    return path


def atomic_write(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.personal-widgets-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


@contextmanager
def state_lock(state):
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(state, 0o700)
    with (state / 'operation.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def apply_files(base, state, files):
    """Keep original backups across upgrades, and rollback a failed transaction."""
    base = base.resolve()
    with state_lock(state):
        ledger_path = state / 'installation.json'
        ledger = read_json(ledger_path, {'schema': 1, 'files': {}})
        transaction = 'history/' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8]
        originals = dict(ledger['files'])
        prepared = []
        for relative, (data, mode) in files.items():
            path = destination(base, relative)
            if path.exists() and not path.is_file():
                raise ValueError('Expected a regular file: ' + str(path))
            before = path.read_bytes() if path.exists() else None
            before_mode = path.stat().st_mode & 0o777 if before is not None else mode
            if before == data and before_mode == mode:
                continue
            backup = transaction + '/before/' + relative
            if before is not None:
                atomic_write(state / backup, before, before_mode)
            prepared.append((relative, path, data, mode, before, before_mode))
            original = originals.get(relative, {}).get('original', {
                'exists': before is not None, 'backup': backup if before is not None else None,
                'mode': before_mode})
            originals[relative] = {'original': original, 'installed_sha256': digest(data)}
        written = []
        try:
            for relative, path, data, mode, before, before_mode in prepared:
                atomic_write(path, data, mode)
                written.append((path, before, before_mode))
            ledger['files'] = originals
            ledger['updated_at'] = datetime.now(timezone.utc).isoformat()
            atomic_write(ledger_path, json_bytes(ledger))
        except BaseException:
            for path, before, before_mode in reversed(written):
                if before is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_write(path, before, before_mode)
            raise
        print('Installed/updated', len(prepared), 'files. Backups:', state)


def remove_files(base, state, apply=False):
    ledger_path = state / 'installation.json'
    if not ledger_path.exists():
        print('No installation record at', ledger_path)
        return 0
    def remove():
        ledger = read_json(ledger_path, {})
        remaining = {}
        for relative, record in ledger.get('files', {}).items():
            path = destination(base, relative)
            if path.exists() and (not path.is_file() or digest(path.read_bytes()) != record['installed_sha256']):
                print('KEEP modified file:', relative)
                remaining[relative] = record
                continue
            print(('Restore ' if record['original']['exists'] else 'Remove  ') + relative)
            if apply:
                original = record['original']
                if original['exists']:
                    data = (state / original['backup']).read_bytes()
                    if relative == '.config/omarchy/shell.json':
                        data = clean_shell_backup(data)
                    atomic_write(path, data, original['mode'])
                else:
                    path.unlink(missing_ok=True)
        if apply:
            ledger['files'] = remaining
            atomic_write(ledger_path, json_bytes(ledger))
        return len(remaining)
    if apply:
        with state_lock(state):
            return remove()
    return remove()


def auto_monitor():
    if shutil.which('hyprctl'):
        try:
            result = subprocess.run(['hyprctl', '-j', 'monitors'], capture_output=True, text=True, timeout=3, check=True)
            monitors = [m for m in json.loads(result.stdout) if not m.get('disabled')]
            external = [m for m in monitors if not m['name'].startswith(('eDP', 'LVDS', 'DSI'))]
            if external:
                return next((m['name'] for m in external if m['name'] == 'HDMI-A-1'), external[0]['name'])
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            pass
    return PROFILE['secondary_monitor']



RETIRED_PROTON_WIDGET = 'io.github.grichard99.omaproton-vpn'


def strip_retired_widgets(config):
    """Remove only the retired widget's shell references; retain other settings."""
    layout = config.get('bar', {}).get('layout', {})
    for section, entries in layout.items():
        if isinstance(entries, list):
            layout[section] = [entry for entry in entries if
                (entry.get('id') if isinstance(entry, dict) else entry) != RETIRED_PROTON_WIDGET]
    plugins = config.get('plugins')
    if isinstance(plugins, list):
        config['plugins'] = [entry for entry in plugins if
            (entry.get('id') if isinstance(entry, dict) else entry) != RETIRED_PROTON_WIDGET]
    elif isinstance(plugins, dict):
        plugins.pop(RETIRED_PROTON_WIDGET, None)
    return config


def clean_shell_backup(data):
    original = json.loads(data)
    cleaned = strip_retired_widgets(json.loads(data))
    return json_bytes(cleaned) if cleaned != original else data


def retire_proton_widget(home, state):
    """Retire old active code/state and forget ledger entries that could restore it."""
    relatives = ('.config/omarchy/plugins/' + RETIRED_PROTON_WIDGET,
                 '.local/state/omarchy-protonvpn')
    with state_lock(state):
        ledger_path = state / 'installation.json'
        ledger = read_json(ledger_path, {'schema': 1, 'files': {}})
        archive = state / 'history' / ('retire-proton-widget-' + uuid.uuid4().hex)
        moved = []
        try:
            for relative in relatives:
                source = destination(home, relative)
                if source.exists() or source.is_symlink():
                    archive.mkdir(parents=True, exist_ok=True, mode=0o700)
                    target = archive / ('plugin' if relative.startswith('.config/') else 'widget-state')
                    source.rename(target)
                    moved.append((source, target))
            ledger['files'] = {key: value for key, value in ledger.get('files', {}).items()
                if not any(key == rel or key.startswith(rel + '/') for rel in relatives)}
            atomic_write(ledger_path, json_bytes(ledger))
        except BaseException:
            for source, target in reversed(moved):
                target.rename(source)
            raise
        print('Retired Proton widget; official account/settings data left in place.')


def merge_shell(old, saved):
    # Keep unrelated modules, keys and plugin enable/disable preferences.
    new = deep_merge(old, {k: v for k, v in saved.items() if k != 'plugins'})
    old_layout = old.get('bar', {}).get('layout', {})
    layout = new['bar']['layout']
    known = {entry['id'] for entries in layout.values() for entry in entries}
    for section, entries in old_layout.items():
        for entry in entries:
            if entry['id'] not in known:
                layout.setdefault(section, []).append(entry)
                known.add(entry['id'])
    return strip_retired_widgets(new)


def install_plan(home, monitor, components):
    files = {}
    def put(relative, data, mode=0o600):
        destination(home, relative)
        files[relative] = (data.encode() if isinstance(data, str) else data, mode)
    if 'widgets' in components:
        for kind in ('plugins', 'vendor'):
            if not (ROOT / kind).is_dir():
                continue
            for plugin in sorted((ROOT / kind).iterdir()):
                for source in sorted(plugin.rglob('*')):
                    if source.is_symlink():
                        raise ValueError('Unexpected symlink in plugin source.')
                    if not source.is_file() or '__pycache__' in source.parts:
                        continue
                    relative = '.config/omarchy/plugins/' + plugin.name + '/' + str(source.relative_to(plugin))
                    data = source.read_bytes()
                    if source.suffix in ('.py', '.qml', '.lua'):
                        data = data.decode().replace('HDMI-A-1', monitor).encode()
                    put(relative, data, source.stat().st_mode & 0o777)
        # Only the widgets component owns this launcher; rollback restores any original.
        desktop_home = str(home).replace('\\', '\\\\\\\\').replace('"', '\\\\"').replace('`', '\\\\`').replace('$', '\\\\$').replace('%', '%%')
        launcher = (ROOT / 'config/proton-app.desktop').read_text().replace('@HOME@', desktop_home)
        put('.local/share/applications/proton.vpn.app.gtk.desktop', launcher, 0o644)
        saved = read_json(ROOT / 'config/shell.json', {})
        put('.config/omarchy/shell.json', json_bytes(merge_shell(read_json(home / '.config/omarchy/shell.json', {}), saved)))
    for source in sorted((ROOT / 'config/home').rglob('*')):
        if not source.is_file():
            continue
        relative = str(source.relative_to(ROOT / 'config/home'))
        is_obs = 'obs-studio/' in relative or relative.endswith('DiscordBothScreens.desktop')
        if (is_obs and 'obs' not in components) or (not is_obs and 'desktop' not in components):
            continue
        text = source.read_text().replace('@HOME@', str(home)).replace('HDMI-A-1', monitor)
        if relative == '.codex/AGENTS.md':
            override = home / '.codex/AGENTS.override.md'
            if override.is_file() and override.read_text().strip():
                relative = '.codex/AGENTS.override.md'
            current = home / relative
            original = current.read_text() if current.exists() else ''
            begin = '<!-- BEGIN OMARCHY-PACKAGING-POLICY -->'
            end = '<!-- END OMARCHY-PACKAGING-POLICY -->'
            if (begin in original) != (end in original):
                raise ValueError('Incomplete existing packaging policy block; preserve and review it first.')
            block = text[text.index(begin):text.index(end) + len(end)]
            if begin in original:
                text = original[:original.index(begin)] + block + original[original.index(end) + len(end):]
            else:
                text = (original.rstrip() + '\n\n' if original.strip() else '') + block + '\n'
        policy_file = relative in ('.codex/AGENTS.md', '.codex/AGENTS.override.md')
        put(relative, text, 0o600 if policy_file else source.stat().st_mode & 0o777)
    if 'desktop' in components:
        steam_workspace = PROFILE['workspaces'].get('steam', 6)
        if isinstance(steam_workspace, bool) or not isinstance(steam_workspace, int) or not 1 <= steam_workspace <= 99:
            raise ValueError('Steam workspace must be an integer from 1 to 99.')
        steam_module = (ROOT / 'config/hypr/steam-workspace.lua').read_text().replace('@STEAM_WORKSPACE@', str(steam_workspace))
        put('.config/hypr/steam-workspace.lua', steam_module, 0o644)
        module = (ROOT / 'config/hypr/personal-widgets.lua').read_text().replace('HDMI-A-1', monitor)
        put('.config/hypr/personal-widgets.lua', module, 0o644)
        old_tail = '-- Keep Spotify' + (ROOT / 'config/hypr/hyprland.lua').read_text().split('-- Keep Spotify', 1)[1]
        fallback = (ROOT / 'config/hypr/hyprland.lua').read_text().replace(old_tail, '')
        main_file = home / '.config/hypr/hyprland.lua'
        current = main_file.read_text() if main_file.exists() else fallback
        begin = '-- BEGIN RYZE STEAM WORKSPACE'
        end = '-- END RYZE STEAM WORKSPACE'
        if (begin in current) != (end in current):
            raise ValueError('Incomplete Steam workspace block; preserve and review it first.')
        if begin in current:
            start = current.index(begin)
            stop = current.index(end, start) + len(end)
            current = current[:start] + current[stop:]
        current = current.replace(old_tail, '').replace('-- Personal widget integrations.\n' + INTEGRATION + '\n', '').replace(INTEGRATION, '').rstrip()
        put('.config/hypr/hyprland.lua', current + '\n\n-- Personal widget integrations.\n' + INTEGRATION + '\n', 0o644)
        binding_file = home / '.config/hypr/bindings.lua'
        if binding_file.exists():
            old_close = '-- Ask before closing' + (ROOT / 'config/hypr/bindings.lua').read_text().split('-- Ask before closing', 1)[1]
            original = binding_file.read_text()
            cleaned = original
            begin = '-- BEGIN RYZE KEYBOARD LAYOUT MENU'
            end = '-- END RYZE KEYBOARD LAYOUT MENU'
            if (begin in cleaned) != (end in cleaned):
                raise ValueError('Incomplete keyboard menu binding block; preserve and review it first.')
            if begin in cleaned:
                start = cleaned.index(begin)
                stop = cleaned.index(end, start) + len(end)
                cleaned = cleaned[:start] + cleaned[stop:]
            cleaned = cleaned.replace(old_close, '')
            if cleaned != original:
                put('.config/hypr/bindings.lua', cleaned.rstrip() + '\n', 0o644)
        mime_file = home / '.config/mimeapps.list'
        import configparser
        mime = configparser.ConfigParser(interpolation=None, strict=False)
        mime.optionxform = str
        if mime_file.exists():
            mime.read(mime_file)
        if not mime.has_section('Default Applications'):
            mime.add_section('Default Applications')
        for key in ('text/html', 'x-scheme-handler/http', 'x-scheme-handler/https', 'x-scheme-handler/about', 'x-scheme-handler/unknown'):
            mime['Default Applications'][key] = 'firefox.desktop'
        import io
        buffer = io.StringIO(); mime.write(buffer)
        put('.config/mimeapps.list', buffer.getvalue())
    for component, preset, relative in (
        ('vpn', 'proton-settings.json', '.config/Proton/VPN/settings.json'),
        ('vencord', 'vencord-settings.json', '.config/Vencord/settings/settings.json')):
        if component in components:
            put(relative, json_bytes(deep_merge(read_json(home / relative, {}), read_json(ROOT / 'config' / preset, {}))))
    return files


def validate_desktop():
    if not os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
        print('Desktop validation deferred until a Hyprland login.')
        return
    subprocess.run(['hyprctl', 'reload'], check=True)
    errors = subprocess.check_output(['hyprctl', 'configerrors'], text=True).strip()
    if errors and errors.lower() not in ('ok', 'no errors'):
        raise ValueError('Hyprland reported configuration errors:\n' + errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'uninstall', 'check'], nargs='?', default='install')
    parser.add_argument('--apply', action='store_true', help='Write changes (otherwise print a plan)')
    parser.add_argument('--home', type=Path, default=Path.home(), help='Target home; use an empty temporary home to test')
    parser.add_argument('--monitor', default='auto', help='Secondary connector, e.g. DP-2; auto detects connected external output')
    parser.add_argument('--components', default='widgets,desktop,obs,vpn,vencord')
    parser.add_argument('--packages', action='store_true', help='Explicitly install curated dependencies using Omarchy')
    parser.add_argument('--reload', action='store_true', help='Restart the shell after applying; does not restart apps')
    parser.add_argument('--theme', action='store_true', help='Apply the recorded packaged theme/background')
    args = parser.parse_args()
    home = args.home.expanduser().resolve()
    live = home == Path.home().resolve()
    if live and (os.environ.get('XDG_CONFIG_HOME', str(home / '.config')) != str(home / '.config') or os.environ.get('XDG_STATE_HOME', str(home / '.local/state')) != str(home / '.local/state')):
        raise ValueError('This restore profile uses standard XDG directories; adapt its destinations before applying to custom XDG roots.')
    state = home / '.local/state/omarchy-personal-widgets'
    if args.action == 'check':
        required = ('omarchy', 'hyprctl', 'python3', 'foot', 'mise', 'spotify', 'discord', 'steam', 'protonvpn-app', 'obs', 'busctl', 'xkbcli')
        missing = [command for command in required if not shutil.which(command)]
        print('Missing commands:', ', '.join(missing) or 'none')
        if shutil.which('pacman'):
            missing_packages = [name for name in PROFILE['dependency_packages'] if subprocess.run(['pacman', '-Q', name], capture_output=True).returncode]
            print('Missing packages:', ', '.join(missing_packages) or 'none')
        print('Accounts: reconnect Spotify, Steam API, Proton, Discord and GitHub independently.')
        return bool(missing)
    if args.action == 'uninstall':
        if args.apply:
            retire_proton_widget(home, state)
        conflicts = remove_files(home, state, args.apply)
        if args.apply and live:
            validate_desktop()
            if args.reload:
                subprocess.run(['omarchy', 'restart', 'shell'], check=True)
        print('Account data and backup history are retained.')
        return bool(conflicts)
    components = set(args.components.split(','))
    if not components <= {'widgets', 'desktop', 'obs', 'vpn', 'vencord'}:
        raise ValueError('Unknown component selection.')
    if 'desktop' in components and 'widgets' not in components:
        raise ValueError('Desktop integrations require the widgets component.')
    monitor = auto_monitor() if args.monitor == 'auto' else args.monitor
    if not re.fullmatch(r'[A-Za-z0-9_.:-]+', monitor):
        raise ValueError('Invalid monitor connector.')
    files = install_plan(home, monitor, components)
    print('Target:', home, '\nSecondary monitor preference:', monitor)
    for relative, (data, mode) in files.items():
        path = home / relative
        print(('UPDATE ' if path.exists() else 'CREATE ') + relative)
    if not args.apply:
        print('Plan only. Add --apply to install. --packages adds dependencies; --theme applies appearance.')
        return 0
    if args.packages or args.reload or args.theme:
        if not live:
            raise ValueError('System/session options are disabled for a staged home.')
    if args.packages:
        subprocess.run(['omarchy', 'pkg', 'add', *PROFILE['dependency_packages']], check=True)
        print('Codex/GitHub tools use mise; install them separately after reading docs/RESTORE.md.')
    if live:
        if not shutil.which('omarchy'):
            raise ValueError('Install Omarchy Quattro first; this is not an operating-system installer.')
        print('Close OBS/Vencord/Proton before replacing their settings. The installer does not stop applications.')
    apply_files(home, state, files)
    if 'widgets' in components:
        retire_proton_widget(home, state)
    if live:
        validate_desktop()
        if args.theme:
            subprocess.run(['omarchy', 'theme', 'set', PROFILE['theme']], check=True)
            theme = Path(subprocess.check_output(['omarchy', 'theme', 'dir', PROFILE['theme']], text=True).strip())
            image = theme / 'backgrounds' / PROFILE['background']
            if image.exists():
                subprocess.run(['omarchy', 'theme', 'bg', 'set', str(image)], check=True)
        if args.reload:
            subprocess.run(['omarchy', 'restart', 'shell'], check=True)
    print('Next: account sign-in, Codex mise setup, OBS camera driver/portal selection. See docs/RESTORE.md.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print('Error:', error, file=sys.stderr)
        raise SystemExit(1)
