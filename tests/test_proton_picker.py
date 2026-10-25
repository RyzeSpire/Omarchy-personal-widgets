"""Native-app adapter tests with fabricated servers; never connect a real VPN."""
import contextlib
from concurrent.futures import Future
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
adapter = load("proton_widget_app", "plugins/ryze.proton-vpn/proton_widget_app.py")
status = load("picker_proton_status", "plugins/ryze.proton-vpn/proton_status.py")


def server(name="TEST#1", country="Example", city="Test City", tier=0, enabled=True, score=10):
    return SimpleNamespace(name=name, exit_country_name=country, exit_country="ZZ", location=city,
                           entry_country_name=country, load=30, score=score, features=[], tier=tier, enabled=enabled)


def controller(rows):
    mapping = {row.name: row for row in rows}
    return SimpleNamespace(user_logged_in=True, user_tier=2, server_selection_requires_upgrade=False,
                           _api=SimpleNamespace(server_list=SimpleNamespace(logicals=rows, get_by_name=lambda name: mapping[name])),
                           connect_to_server=MagicMock(return_value=Future()))


class PickerTests(unittest.TestCase):
    def test_country_city_name_and_accent_search(self):
        c = controller([server("XX#1", "Example", "São Paulo"), server("YY#9", "Other", "North")])
        picker = adapter.Picker(c)
        for query in ["sao paulo", "EXAMPLE", "XX#1", "example paulo"]:
            self.assertEqual([row["name"] for row in picker.query(query)["rows"]], ["XX#1"])
        self.assertEqual(picker.query("absent")["total"], 0)
        c.connect_to_server.assert_not_called()

    def test_unavailable_and_higher_tier_are_omitted(self):
        c = controller([server("AVAILABLE#1"), server("OFFLINE#1", enabled=False), server("PRIVATE#1", tier=3)])
        rows = adapter.Picker(c).query("")["rows"]
        self.assertEqual([row["name"] for row in rows], ["AVAILABLE#1"])
        self.assertFalse(any(key in rows[0] for key in ("ID", "Servers", "Score", "StatusID", "account", "ip")))

    def test_pagination_and_bounds(self):
        picker = adapter.Picker(controller([server(f"TEST#{i:03}", score=i) for i in range(121)]))
        first = picker.query(""); second = picker.query("", 50)
        self.assertEqual(first["total"], 121); self.assertEqual(len(first["rows"]), 50)
        self.assertEqual(second["rows"][0]["name"], "TEST#050")
        for offset in (-1, True, 100001):
            with self.assertRaises(ValueError): picker.query("", offset)
        with self.assertRaises(ValueError): picker.query("a" * 129)

    def test_plan_restrictions_and_signin_are_respected(self):
        c = controller([server()]); c.server_selection_requires_upgrade = True
        picker = adapter.Picker(c)
        self.assertFalse(picker.query("")["selection_allowed"])
        with self.assertRaises(ValueError): picker.connect("TEST#1")
        c.user_logged_in = False
        with self.assertRaises(ValueError): picker.query("")
        c.connect_to_server.assert_not_called()

    def test_validate_does_not_connect_and_rechecks_live_state(self):
        row = server(); c = controller([row]); picker = adapter.Picker(c)
        self.assertEqual(picker.validate(row.name), row)
        picker.query("")
        row.enabled = False
        with self.assertRaises(ValueError): picker.connect(row.name)
        row.enabled = True; row.tier = 3
        with self.assertRaises(ValueError): picker.connect(row.name)
        c.connect_to_server.assert_not_called()

    def test_selection_uses_only_official_controller(self):
        c = controller([server()]); picker = adapter.Picker(c)
        result = picker.connect("TEST#1")
        self.assertTrue(result["accepted"]); self.assertTrue(picker.info()["pending"])
        c.connect_to_server.assert_called_once_with("TEST#1")
        with self.assertRaises(ValueError): picker.connect("TEST#1")
        c.connect_to_server.return_value.set_result(None)
        self.assertFalse(picker.info()["pending"])

    def test_general_controls_do_not_require_specific_server_permission(self):
        c = controller([server()]); c.server_selection_requires_upgrade = True
        c.disconnect = MagicMock(return_value=Future())
        picker = adapter.Picker(c)
        self.assertTrue(picker.request(c.disconnect)["accepted"])
        c.disconnect.assert_called_once_with()
        c.disconnect.return_value.set_result(None)
        self.assertFalse(picker.pending)
        c.user_logged_in = False
        with self.assertRaises(ValueError): picker.request(c.disconnect)
        self.assertEqual(c.disconnect.call_count, 1)

    def test_bar_controls_use_the_same_official_app_adapter(self):
        desktop = status.Desktop.__new__(status.Desktop); desktop.session = MagicMock()
        desktop.running = lambda: True
        desktop.picker_call = MagicMock(return_value={"ok": True})
        desktop.tray_menu = MagicMock()
        desktop.action("disconnect"); desktop.action("connect")
        self.assertEqual([call.args[0] for call in desktop.picker_call.call_args_list], ["Disconnect", "QuickConnect"])
        desktop.tray_menu.assert_not_called()

    def test_failed_request_is_reported_without_private_exception(self):
        c = controller([server()]); picker = adapter.Picker(c); picker.connect("TEST#1")
        c.connect_to_server.return_value.set_exception(RuntimeError("private auth data"))
        self.assertFalse(picker.pending)
        self.assertTrue(picker.error); self.assertNotIn("private", picker.error)

    def test_sync_failure_does_not_leave_busy(self):
        c = controller([server()]); c.connect_to_server.side_effect = RuntimeError("failure")
        picker = adapter.Picker(c)
        with self.assertRaises(RuntimeError): picker.connect("TEST#1")
        self.assertFalse(picker.pending)

    def test_auto_connect_guard_runs_before_native_connect(self):
        events = []
        c = controller([server()])
        c.connect_to_server.side_effect = lambda name: (events.append(name), Future())[1]
        picker = adapter.Picker(c, before_request=lambda: events.append("guard"))
        picker.connect("TEST#1")
        self.assertEqual(events, ["guard", "TEST#1"])

    def test_guard_failure_refuses_server_switch_without_fallback(self):
        c = controller([server()])
        def fail(): raise RuntimeError("private details")
        picker = adapter.Picker(c, before_request=fail)
        with self.assertRaisesRegex(ValueError, "saved Proton tunnels"): picker.connect("TEST#1")
        self.assertFalse(picker.pending)
        c.connect_to_server.assert_not_called()

    def test_bad_load_and_scores_have_safe_defaults(self):
        row = server(); row.load = float("nan"); row.score = float("inf")
        result = adapter.Picker(controller([row])).query("")
        json.dumps(result, allow_nan=False)
        self.assertEqual(result["rows"][0]["load"], 0)

    def test_bridge_must_belong_to_official_app_process(self):
        desktop = status.Desktop.__new__(status.Desktop); desktop.session = MagicMock()
        desktop.running = lambda: True
        daemon = desktop.session.get_object.return_value
        daemon.GetConnectionUnixProcessID.side_effect = [100, 200]
        with self.assertRaises(ValueError): desktop.picker()
        self.assertEqual(desktop.session.get_object.call_count, 1)

    def test_absent_bridge_has_no_autostart(self):
        desktop = status.Desktop.__new__(status.Desktop); desktop.session = MagicMock()
        desktop.running = lambda: False
        with self.assertRaises(ValueError): desktop.picker()
        desktop.session.get_object.assert_not_called()

    def test_migration_restart_callback_is_a_bound_method_and_does_not_connect(self):
        from types import MethodType
        import inspect
        c = controller([server()])
        callback = MethodType(adapter.skip_migration_startup, c)
        self.assertTrue(inspect.ismethod(callback))
        callback(None); callback(None)
        c.connect_to_server.assert_not_called()

    def test_launcher_update_and_rollback_with_unusual_home(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import manage
        from gi.repository import GLib
        with tempfile.TemporaryDirectory(prefix="proton picker ") as temp:
            home = Path(temp) / 'home with spaces "quotes" $cash `tick`'; home.mkdir()
            state = home / ".local/state/omarchy-personal-widgets"
            relative = ".local/share/applications/proton.vpn.app.gtk.desktop"
            original = home / relative; original.parent.mkdir(parents=True)
            original.write_text("original personal launcher")
            plan = manage.install_plan(home, "DP-2", {"widgets"})
            key = GLib.KeyFile(); key.load_from_data(plan[relative][0].decode(), len(plan[relative][0]), GLib.KeyFileFlags.NONE)
            _ok, args = GLib.shell_parse_argv(key.get_string("Desktop Entry", "Exec"))
            self.assertEqual(args[-1], str(home / ".config/omarchy/plugins/ryze.proton-vpn/proton_widget_app.py"))
            with contextlib.redirect_stdout(io.StringIO()):
                for _ in range(2): manage.apply_files(home, state, plan)
                self.assertEqual(manage.remove_files(home, state, True), 0)
            self.assertEqual(original.read_text(), "original personal launcher")
            self.assertFalse(any(key.endswith('proton.vpn.app.gtk.desktop') for key in manage.install_plan(home, "DP-2", {"desktop"})))
