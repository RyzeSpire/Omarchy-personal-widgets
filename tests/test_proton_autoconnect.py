"""Fake nmcli profiles only; no real network or credential operations."""
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("proton_autoconnect", ROOT / "plugins/ryze.proton-vpn/proton_autoconnect.py")
guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
A = "00000000-0000-4000-8000-000000000001"
B = "00000000-0000-4000-8000-000000000002"
C = "00000000-0000-4000-8000-000000000003"
D = "00000000-0000-4000-8000-000000000004"


class FakeNM:
    def __init__(self):
        self.rows = {A: ["wireguard", "yes", "ProtonVPN TEST#1"],
                     B: ["dummy", "yes", "pvpn-killswitch"],
                     C: ["vpn", "yes", "Office VPN"],
                     D: ["wifi", "yes", "WiFi"]}
        self.writes = []
        self.fail = False
    def __call__(self, args):
        if args[:2] == ["-t", "-f"]:
            return "\n".join(":".join([key, *value]) for key, value in self.rows.items())
        if self.fail: raise RuntimeError("modify failed")
        self.writes.append(args)
        self.rows[args[3]][1] = args[-1]
        return ""


class AutoConnectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="proton flags ")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "private" / "originals.json"
        self.nm = FakeNM()

    def test_scan_is_read_only_and_only_tunnels_qualify(self):
        self.assertEqual(set(guard.profiles(self.nm)), {A})
        self.assertFalse(self.path.exists())
        self.assertEqual(self.nm.writes, [])

    def test_repeated_apply_preserves_kill_switch_and_unrelated_profiles(self):
        self.assertEqual(guard.guard(self.path, self.nm), 1)
        self.assertEqual(guard.guard(self.path, self.nm), 0)
        self.assertEqual(self.nm.rows[A][1], "no")
        for key in (B, C, D): self.assertEqual(self.nm.rows[key][1], "yes")
        self.assertEqual(json.loads(self.path.read_text()), {A: True})
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(self.nm.writes[0], ["connection", "modify", "uuid", A, "connection.autoconnect", "no"])

    def test_new_tunnel_is_guarded_on_next_request(self):
        guard.guard(self.path, self.nm)
        self.nm.rows[C] = ["wireguard", "yes", "ProtonVPN NEW#2"]
        self.assertEqual(guard.guard(self.path, self.nm), 1)
        self.assertEqual(self.nm.rows[C][1], "no")
        self.assertEqual(set(json.loads(self.path.read_text())), {A, C})

    def test_original_saved_before_failed_mutation(self):
        self.nm.fail = True
        with self.assertRaises(RuntimeError): guard.guard(self.path, self.nm)
        self.assertEqual(json.loads(self.path.read_text()), {A: True})
        self.assertEqual(self.nm.rows[A][1], "yes")

    def test_explicit_restore_only_changes_owned_existing_false_values(self):
        guard.guard(self.path, self.nm)
        self.nm.rows[C] = ["vpn", "no", "ProtonVPN OTHER#9"]
        self.assertEqual(guard.restore(self.path, self.nm), 1)
        self.assertEqual(self.nm.rows[A][1], "yes")
        self.assertEqual(self.nm.rows[C][1], "no")
        self.assertEqual(json.loads(self.path.read_text()), {})

    def test_restore_drops_deleted_profiles_without_touching_new_ones(self):
        guard.guard(self.path, self.nm)
        del self.nm.rows[A]
        self.assertEqual(guard.restore(self.path, self.nm), 0)
        self.assertEqual(json.loads(self.path.read_text()), {})
