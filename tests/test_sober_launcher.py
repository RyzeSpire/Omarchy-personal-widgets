"""Sober export links: isolated lifecycle fixtures, no Flatpak or session calls."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('sober_setup', Path(__file__).resolve().parents[1] / 'scripts/sober.py')
sober = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sober)


class SoberLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'home with spaces'
        exports = self.home / '.local/share/flatpak/exports/share'
        self.desktop = exports / 'applications/org.vinegarhq.Sober.desktop'
        self.icon = exports / 'icons/hicolor/scalable/apps/org.vinegarhq.Sober.svg'
        for path in (self.desktop, self.icon):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('export')
        self.link = self.home / '.local/share/applications/org.vinegarhq.Sober.desktop'
        self.icon_link = self.home / '.local/share/icons/hicolor/scalable/apps/org.vinegarhq.Sober.svg'

    def test_install_repeat_and_upstream_update(self):
        sober.launcher_links(self.home)
        sober.launcher_links(self.home)
        self.assertEqual(os.readlink(self.link), str(self.desktop))
        self.desktop.write_text('updated export')
        self.assertEqual(self.link.read_text(), 'updated export')
        self.assertEqual(self.icon_link.read_text(), 'export')

    def test_uninstall_removes_owned_even_after_exports_disappear(self):
        sober.launcher_links(self.home)
        self.desktop.unlink()
        self.icon.unlink()
        sober.launcher_links(self.home, remove=True)
        self.assertFalse(self.link.is_symlink())
        self.assertFalse(self.icon_link.is_symlink())

    def test_conflict_is_preserved_without_partial_install(self):
        self.icon_link.parent.mkdir(parents=True)
        self.icon_link.write_text('personal icon')
        with self.assertRaisesRegex(ValueError, 'Preserve existing'):
            sober.launcher_links(self.home)
        self.assertFalse(self.link.exists())
        sober.launcher_links(self.home, remove=True)
        self.assertEqual(self.icon_link.read_text(), 'personal icon')

    def test_missing_export_does_not_leave_partial_links(self):
        self.icon.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing installed'):
            sober.launcher_links(self.home)
        self.assertFalse(self.link.exists())
