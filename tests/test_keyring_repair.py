"""Keyring repair tests use fabricated data only."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("repair_keyring", Path(__file__).resolve().parents[1] / "scripts/repair-keyring.py")
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)

PREFIX = "[keyring]\ndisplay-name=Fixture\nctime=1\nmtime=2\n\n[1]\nitem-type=0\ndisplay-name=Fixture item\n"
SUFFIX = "mtime=2\nctime=1\n\n[1:attribute0]\nname=fixture\ntype=string\nvalue=local-only\n"
BROKEN = PREFIX + 'secret={"certificate":"-----BEGIN TEST-----\nabc=\n-----END TEST-----","nested":{"enabled":true}}\n' + SUFFIX


class KeyringRepairTests(unittest.TestCase):
    def test_multiline_json_is_preserved_and_metadata_unchanged(self):
        fixed, count, entries = repair.repair_text(BROKEN)
        self.assertEqual((count, entries), (1, 1))
        self.assertTrue(fixed.startswith(PREFIX))
        self.assertTrue(fixed.endswith(SUFFIX))
        value = repair.parse_keyfile(fixed).get_string("1", "secret")
        self.assertEqual(json.loads(value), {"certificate": "-----BEGIN TEST-----\nabc=\n-----END TEST-----", "nested": {"enabled": True}})
        self.assertIn("\\\\n", fixed)

    def test_valid_file_is_unchanged_and_second_run_is_noop(self):
        fixed, _, _ = repair.repair_text(BROKEN)
        self.assertEqual(repair.repair_text(fixed), (fixed, 0, 1))

    def test_other_malformed_content_and_duplicate_json_refused(self):
        with self.assertRaises(repair.RepairError):
            repair.repair_text(PREFIX + "unrelated damaged text\n" + SUFFIX)
        duplicate = PREFIX + 'secret={"x":1,\n"x":2}\n' + SUFFIX
        with self.assertRaises(repair.RepairError):
            repair.repair_text(duplicate)

    def test_apply_keeps_exact_private_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "fixture.keyring"
            source.write_text(BROKEN)
            source.chmod(0o600)
            fixed, _, _ = repair.repair_text(BROKEN)
            backup = repair.apply_repair(source, BROKEN.encode(), fixed.encode(), root / "private-state")
            self.assertEqual(backup.read_bytes(), BROKEN.encode())
            self.assertEqual(source.read_text(), fixed)
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            self.assertEqual(backup.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(source.stat().st_mode & 0o777, 0o600)

    def test_changed_file_symlink_and_git_backup_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "fixture.keyring"
            source.write_text(BROKEN)
            with self.assertRaises(repair.RepairError):
                repair.apply_repair(source, b"stale", b"replacement", root / "private")
            link = root / "link.keyring"
            link.symlink_to(source)
            with self.assertRaises(repair.RepairError):
                repair.checked_file(link)
            (root / ".git").mkdir()
            with self.assertRaises(repair.RepairError):
                repair.apply_repair(source, source.read_bytes(), b"replacement", root / "private")
            self.assertEqual(source.read_text(), BROKEN)


if __name__ == "__main__":
    unittest.main()
