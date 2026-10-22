import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import manage


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


private = load('private_data', 'private-data.py')
release = load('make_release', 'make-release.py')


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / 'new-user'; self.home.mkdir()
        self.state = self.home / '.local/state/omarchy-personal-widgets'
        self.silent = contextlib.redirect_stdout(io.StringIO()); self.silent.__enter__()

    def tearDown(self):
        self.silent.__exit__(None, None, None); self.temp.cleanup()

    def test_plan_never_writes_to_clean_home(self):
        files = manage.install_plan(self.home, 'DP-2', {'widgets', 'desktop', 'obs', 'vpn', 'vencord'})
        self.assertGreater(len(files), 60)
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertIn('.config/omarchy/plugins/ryze.spotify/SpotifyWidget.qml', files)
        self.assertNotIn(b'HDMI-A-1', files['.config/hypr/personal-widgets.lua'][0])

    def test_install_update_uninstall_restores_first_original(self):
        target = self.home / 'example'; target.write_bytes(b'original'); target.chmod(0o640)
        manage.apply_files(self.home, self.state, {'example': (b'one', 0o600), 'new': (b'new', 0o644)})
        manage.apply_files(self.home, self.state, {'example': (b'two', 0o600)})
        manage.remove_files(self.home, self.state, True)
        self.assertEqual(target.read_bytes(), b'original')
        self.assertEqual(target.stat().st_mode & 0o777, 0o640)
        self.assertFalse((self.home / 'new').exists())

    def test_remove_preserves_user_edits(self):
        manage.apply_files(self.home, self.state, {'example': (b'installed', 0o600)})
        (self.home / 'example').write_bytes(b'user edits')
        self.assertEqual(manage.remove_files(self.home, self.state, True), 1)
        self.assertEqual((self.home / 'example').read_bytes(), b'user edits')

    def test_remove_plan_is_read_only(self):
        manage.apply_files(self.home, self.state, {'example': (b'installed', 0o600)})
        before = (self.state / 'installation.json').read_bytes()
        manage.remove_files(self.home, self.state, False)
        self.assertEqual((self.home / 'example').read_bytes(), b'installed')
        self.assertEqual((self.state / 'installation.json').read_bytes(), before)

    def test_symlink_and_path_escape_rejected(self):
        outside = Path(self.temp.name) / 'outside'; outside.mkdir()
        (self.home / 'link').symlink_to(outside)
        for name in ('link/file', '../outside/file', '/etc/file'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                manage.apply_files(self.home, self.state, {name: (b'bad', 0o600)})
        self.assertEqual(list(outside.iterdir()), [])

    def test_failure_rolls_back_files(self):
        (self.home / 'one').write_bytes(b'original')
        real = manage.atomic_write
        def fail(path, data, mode=0o600):
            if path == self.home / 'two':
                raise OSError('simulated disk error')
            return real(path, data, mode)
        with patch.object(manage, 'atomic_write', side_effect=fail), self.assertRaises(OSError):
            manage.apply_files(self.home, self.state, {'one': (b'new', 0o600), 'two': (b'new', 0o600)})
        self.assertEqual((self.home / 'one').read_bytes(), b'original')
        self.assertFalse((self.state / 'installation.json').exists())

    def test_shell_merge_preserves_unrelated_modules_and_preferences(self):
        old = {'custom': 123, 'plugins': ['personal.other'], 'bar': {'layout': {'left': [{'id': 'personal.other'}]}}}
        saved = json.loads((ROOT / 'config/shell.json').read_text())
        result = manage.merge_shell(old, saved)
        self.assertEqual(result['custom'], 123)
        self.assertEqual(result['plugins'], ['personal.other'])
        self.assertIn({'id': 'personal.other'}, result['bar']['layout']['left'])

    def test_install_twice_has_same_payload(self):
        parts = {'widgets', 'desktop', 'obs', 'vpn', 'vencord'}
        first = manage.install_plan(self.home, 'DP-2', parts)
        manage.apply_files(self.home, self.state, first)
        second = manage.install_plan(self.home, 'DP-2', parts)
        self.assertEqual(first, second)
        ledger = (self.state / 'installation.json').read_bytes()
        manage.apply_files(self.home, self.state, second)
        self.assertEqual(json.loads(ledger)['files'], json.loads((self.state / 'installation.json').read_bytes())['files'])

    def test_previous_personal_hypr_integration_is_not_duplicated(self):
        path = self.home / '.config/hypr'; path.mkdir(parents=True)
        (path / 'hyprland.lua').write_bytes((ROOT / 'config/hypr/hyprland.lua').read_bytes())
        (path / 'bindings.lua').write_bytes((ROOT / 'config/hypr/bindings.lua').read_bytes())
        plan = manage.install_plan(self.home, 'DP-2', {'desktop', 'widgets'})
        self.assertNotIn(b'o.window("[Ss]potify"', plan['.config/hypr/hyprland.lua'][0])
        self.assertNotIn(b'ryze_spotify_close', plan['.config/hypr/bindings.lua'][0])
        self.assertEqual(plan['.config/hypr/hyprland.lua'][0].count(manage.INTEGRATION.encode()), 1)

    def test_keyboard_menu_binding_migrates_updates_and_uninstalls(self):
        directory = self.home / '.config/hypr'; directory.mkdir(parents=True)
        block = (ROOT / 'config/hypr/personal-widgets.lua').read_text().split('-- BEGIN RYZE KEYBOARD LAYOUT MENU', 1)[1]
        original = '-- My unrelated shortcut\no.bind("SUPER + X", "Example", "true")\n' + '-- BEGIN RYZE KEYBOARD LAYOUT MENU' + block
        path = directory / 'bindings.lua'; path.write_text(original)
        components = {'desktop', 'widgets'}
        first = manage.install_plan(self.home, 'DP-2', components)
        self.assertNotIn(b'mouse:274', first['.config/hypr/bindings.lua'][0])
        self.assertIn(b'SUPER + X', first['.config/hypr/bindings.lua'][0])
        self.assertEqual(first['.config/hypr/personal-widgets.lua'][0].count(b'mouse:274'), 1)
        self.assertIn('.config/omarchy/plugins/ryze.keyboard-layout/LayoutMenu.qml', first)
        manage.apply_files(self.home, self.state, first)
        second = manage.install_plan(self.home, 'DP-2', components)
        manage.apply_files(self.home, self.state, second)
        self.assertNotIn('mouse:274', path.read_text())
        manage.remove_files(self.home, self.state, True)
        self.assertEqual(path.read_text(), original)
        self.assertFalse((directory / 'personal-widgets.lua').exists())

    def test_incomplete_keyboard_shortcut_block_refuses_install(self):
        directory = self.home / '.config/hypr'; directory.mkdir(parents=True)
        path = directory / 'bindings.lua'
        path.write_text('-- BEGIN RYZE KEYBOARD LAYOUT MENU\n-- Preserve this incomplete edit\n')
        with self.assertRaisesRegex(ValueError, 'Incomplete keyboard menu'):
            manage.install_plan(self.home, 'DP-2', {'desktop', 'widgets'})
        self.assertIn('Preserve this incomplete edit', path.read_text())

    def test_vencord_preserves_private_existing_fields(self):
        target = self.home / '.config/Vencord/settings/settings.json'; target.parent.mkdir(parents=True)
        target.write_text(json.dumps({'cloud': {'token': 'private'}, 'unrelated': 123}))
        plan = manage.install_plan(self.home, 'DP-2', {'vencord'})
        config = json.loads(plan['.config/Vencord/settings/settings.json'][0])
        self.assertEqual(config['cloud']['token'], 'private')
        self.assertEqual(config['unrelated'], 123)

    def test_public_bundle_excludes_private_files_and_git(self):
        files = [str(p.relative_to(ROOT)) for p in release.public_files()]
        self.assertFalse(any('.git/' in p or p.endswith(('oauth.json', 'friends.json', '.gpg', '.pyc')) for p in files))
        self.assertIn('install.sh', files)
        self.assertIn('AGENTS.md', files)
        self.assertIn('config/home/.codex/AGENTS.md', files)
        scene = json.loads((ROOT / 'config/home/.config/obs-studio/basic/scenes/Both_Screens.json').read_text())
        self.assertFalse(any('RestoreToken' in s.get('settings', {}) for s in scene['sources']))
        self.assertNotIn('cloud', json.loads((ROOT / 'config/vencord-settings.json').read_text()))

    def test_global_policy_merge_preserves_existing_instructions_and_removal(self):
        target = self.home / '.codex/AGENTS.md'; target.parent.mkdir()
        original = '# Existing preferences\n\nKeep my unrelated coding conventions.\n'
        target.write_text(original)
        plan = manage.install_plan(self.home, 'DP-2', {'desktop', 'widgets'})
        text = plan['.codex/AGENTS.md'][0].decode()
        self.assertEqual(plan['.codex/AGENTS.md'][1], 0o600)
        self.assertIn(original.rstrip(), text)
        self.assertEqual(text.count('<!-- BEGIN OMARCHY-PACKAGING-POLICY -->'), 1)
        manage.apply_files(self.home, self.state, plan)
        again = manage.install_plan(self.home, 'DP-2', {'desktop', 'widgets'})
        self.assertEqual(again['.codex/AGENTS.md'][0], plan['.codex/AGENTS.md'][0])
        manage.remove_files(self.home, self.state, True)
        self.assertEqual(target.read_text(), original)

    def test_global_override_receives_policy_without_replacing_other_guidance(self):
        directory = self.home / '.codex'; directory.mkdir()
        (directory / 'AGENTS.md').write_text('Existing base rules\n')
        (directory / 'AGENTS.override.md').write_text('Existing active override\n')
        plan = manage.install_plan(self.home, 'DP-2', {'desktop', 'widgets'})
        self.assertNotIn('.codex/AGENTS.md', plan)
        self.assertIn('Existing active override', plan['.codex/AGENTS.override.md'][0].decode())
        self.assertIn('OMARCHY-PACKAGING-POLICY', plan['.codex/AGENTS.override.md'][0].decode())
        self.assertEqual((directory / 'AGENTS.md').read_text(), 'Existing base rules\n')

    def test_malformed_global_policy_fails_without_writing(self):
        target = self.home / '.codex/AGENTS.md'; target.parent.mkdir()
        original = '<!-- BEGIN OMARCHY-PACKAGING-POLICY -->\nunfinished user edit\n'
        target.write_text(original)
        with self.assertRaises(ValueError):
            manage.install_plan(self.home, 'DP-2', {'desktop', 'widgets'})
        self.assertEqual(target.read_text(), original)

    def test_private_export_is_opt_in_for_profiles_and_media(self):
        for name in ('.local/state/omarchy/spotify-widget/oauth.json', '.config/chromium/Local State', 'Music/Spotify_local/song.mp3'):
            p = self.home / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('test')
        found = private.collect(self.home)
        self.assertIn('.local/state/omarchy/spotify-widget/oauth.json', found)
        self.assertNotIn('.config/chromium/Local State', found)
        self.assertNotIn('Music/Spotify_local/song.mp3', found)
        found = private.collect(self.home, profiles=True, media=True)
        self.assertIn('Music/Spotify_local/song.mp3', found)

    def test_system_camera_install_and_remove_in_isolated_root(self):
        system = Path(self.temp.name) / 'system'; system.mkdir()
        script = ROOT / 'scripts/camera-system.py'
        result = subprocess.run([sys.executable, '-B', str(script), '--root', str(system), '--apply'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        target = system / 'etc/modprobe.d/ryze-obs-camera.conf'
        self.assertIn('video_nr=42', target.read_text())
        result = subprocess.run([sys.executable, '-B', str(script), 'uninstall', '--root', str(system), '--apply'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(target.exists())

    @unittest.skipUnless(__import__('shutil').which('gpg'), 'GPG not installed')
    def test_encrypted_private_roundtrip_with_fixture_only(self):
        import argparse
        fixture = self.home / '.local/state/omarchy/spotify-widget/oauth.json'
        fixture.parent.mkdir(parents=True); fixture.write_text('{"fixture": "not real credentials"}')
        output = Path(self.temp.name) / 'private.gpg'
        dest = Path(self.temp.name) / 'review'
        key_home = Path(self.temp.name) / 'gnupg'; key_home.mkdir(mode=0o700)
        real_popen = subprocess.Popen
        def fixture_gpg(command, **kwargs):
            kwargs['env'] = dict(kwargs.get('env', {}), GNUPGHOME=str(key_home))
            command = [command[0], '--batch', '--pinentry-mode', 'loopback', '--passphrase', 'fixture-only-passphrase', *command[1:]]
            return real_popen(command, **kwargs)
        args = argparse.Namespace(home=self.home, output=output, profiles=False, media=False, keyrings=False, apply=True, archive=output, dest=dest)
        try:
            with patch.object(private.sys.stdin, 'isatty', return_value=True), patch.object(private.os, 'ttyname', return_value='/dev/null'), patch.object(private.subprocess, 'Popen', side_effect=fixture_gpg):
                private.export(args)
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                self.assertNotIn(b'not real credentials', output.read_bytes())
                private.restore(args)
            self.assertEqual((dest / fixture.relative_to(self.home)).read_bytes(), fixture.read_bytes())
        finally:
            subprocess.run(['gpgconf', '--homedir', str(key_home), '--kill', 'gpg-agent'], capture_output=True)

    def test_dry_run_cli_no_files_and_no_system_commands(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/manage.py'), '--home', str(self.home), '--monitor', 'DP-2'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(self.home.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
