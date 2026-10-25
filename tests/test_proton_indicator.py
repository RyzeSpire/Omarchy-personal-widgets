"""Status/opener fixtures only; no real app, account or network changes."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("proton_indicator", ROOT / "plugins/ryze.proton-indicator/proton_indicator.py")
indicator = importlib.util.module_from_spec(spec); spec.loader.exec_module(indicator)


class IndicatorTests(unittest.TestCase):
    def desktop(self, running=True):
        desktop = indicator.Desktop.__new__(indicator.Desktop)
        desktop.dbus = MagicMock()
        desktop.session = MagicMock()
        desktop.session.name_has_owner.return_value = running
        desktop.tray_state = MagicMock(return_value=None)
        desktop.show_from_tray = MagicMock(return_value=False)
        return desktop

    def test_kill_switch_and_unrelated_vpns_do_not_count(self):
        self.assertEqual(indicator.tunnel_state([dict(Id="pvpn-killswitch", Type="dummy", State=2),
            dict(Id="Office VPN", Type="vpn", State=2, VpnState=5)]), "disconnected")

    def test_wireguard_states_and_openvpn_authentication(self):
        for state, expected in [(1, "connecting"), (2, "connected"), (3, "disconnecting"), (4, "disconnected")]:
            self.assertEqual(indicator.tunnel_state([dict(Id="ProtonVPN TEST#1", Type="wireguard", State=state)]), expected)
        for state, expected in [(1, "connecting"), (4, "connecting"), (5, "connected"), (6, "disconnected")]:
            self.assertEqual(indicator.tunnel_state([dict(Id="ProtonVPN TEST#1", Type="vpn", State=2, VpnState=state)]), expected)

    def test_app_off_and_tunnel_connected_are_independent_read_only_states(self):
        desktop = self.desktop(False)
        obj = desktop.dbus.SystemBus.return_value.get_object.return_value
        obj.GetAll.side_effect = [{"ActiveConnections": ["/fake/tunnel"]}, dict(Id="ProtonVPN TEST#1", Type="wireguard", State=2)]
        with patch.object(indicator.subprocess, "Popen") as launch:
            result = desktop.status()
        self.assertTrue(result["ok"]); self.assertFalse(result["running"])
        self.assertEqual(result["state"], "connected")
        desktop.session.get_object.assert_not_called(); launch.assert_not_called()
        self.assertTrue(all(call.kwargs["dbus_interface"] == indicator.PROPERTIES for call in obj.GetAll.call_args_list))

    def test_native_status_takes_precedence_over_an_activated_but_unready_tunnel(self):
        desktop = self.desktop()
        desktop.tray_state.return_value = "disconnected"
        result = desktop.status()
        self.assertEqual(result["state"], "disconnected")
        self.assertEqual(result["source"], "official-app")
        desktop.dbus.SystemBus.assert_not_called()

    def test_unknown_network_state_does_not_claim_disconnection(self):
        desktop = self.desktop()
        desktop.dbus.SystemBus.side_effect = RuntimeError("private details")
        result = desktop.status()
        self.assertTrue(result["running"]); self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "unknown"); self.assertNotIn("private", result["error"])

    def test_existing_window_is_focused_without_activation_or_new_controller(self):
        desktop = self.desktop(); desktop.app_pid = lambda: 42
        desktop.focus_window = MagicMock(return_value=True)
        with patch.object(indicator.subprocess, "Popen") as launch: desktop.open()
        desktop.focus_window.assert_called_once_with(42)
        desktop.session.get_object.assert_not_called(); launch.assert_not_called()

    def test_hidden_app_uses_only_standard_desktop_activation(self):
        desktop = self.desktop(); desktop.app_pid = lambda: 42
        desktop.focus_window = MagicMock(side_effect=[False, True])
        with patch.object(indicator.subprocess, "Popen") as launch: desktop.open()
        desktop.session.get_object.return_value.Activate.assert_called_once_with({}, signature="a{sv}", dbus_interface="org.freedesktop.Application", timeout=3)
        launch.assert_not_called()

    def test_hidden_app_can_use_native_show_without_activation(self):
        desktop = self.desktop(); desktop.app_pid = lambda: 42
        desktop.focus_window = MagicMock(side_effect=[False, True])
        desktop.show_from_tray.return_value = True
        with patch.object(indicator.subprocess, "Popen") as launch: desktop.open()
        desktop.show_from_tray.assert_called_once()
        desktop.session.get_object.assert_not_called(); launch.assert_not_called()

    def test_native_show_rejects_controls_ambiguous_entries_and_changed_layouts(self):
        for labels, changed, expected in [(["Connect", "Show", "Quit"], False, True),
                (["Connect", "Disconnect", "Quit"], False, False),
                (["Show", "Show"], False, False), (["Show"], True, False)]:
            desktop = self.desktop()
            desktop.tray_items = lambda: iter([("native.tray", {"Menu": "/MenuBar"})])
            menu = desktop.session.get_object.return_value
            items = [(i + 1, {"label": label, "enabled": True}, []) for i, label in enumerate(labels)]
            selected = next((i for i in items if i[1]["label"] == "Show"), items[0])
            menu.GetLayout.side_effect = [(5, (0, {}, items)), (6 if changed else 5, selected)]
            self.assertEqual(indicator.Desktop.show_from_tray(desktop), expected)
            if expected:
                self.assertEqual(menu.Event.call_args.args[:2], (selected[0], "clicked"))
            else:
                menu.Event.assert_not_called()

    def test_closed_app_starts_official_executable_only(self):
        desktop = self.desktop(); desktop.running = MagicMock(side_effect=[False, True])
        desktop.app_pid = lambda: 42; desktop.focus_window = lambda _pid: True
        with patch.object(indicator.subprocess, "Popen") as launch: desktop.open()
        self.assertEqual(launch.call_args.args[0], ["protonvpn-app"])
        desktop.session.get_object.assert_not_called()

    def test_focus_requires_verified_app_pid_and_valid_window_address(self):
        desktop = self.desktop()
        result = SimpleNamespace(stdout=json.dumps([dict(pid=999, mapped=True, address="0xabc"),
            dict(pid=42, mapped=True, address="not-an-address"), dict(pid=42, mapped=True, address="0xdef")]))
        with patch.object(indicator.subprocess, "run", side_effect=[result, SimpleNamespace()]) as run:
            self.assertTrue(desktop.focus_window(42))
        self.assertEqual(run.call_args_list[1].args[0], ["hyprctl", "dispatch", 'hl.dsp.focus({ window = "address:0xdef" })'])

    def test_connection_commands_are_not_available(self):
        import sys
        for action in ("connect", "disconnect", "select", "settings", "signin"):
            with patch.object(sys, "argv", ["helper", action]), patch.object(indicator, "Desktop") as desktop, patch("builtins.print"):
                self.assertEqual(indicator.main(), 2)
                desktop.assert_not_called()
