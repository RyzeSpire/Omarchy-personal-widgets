"""Fabricated local state only: no real account, bus, or connection changes."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("proton_status", ROOT / "plugins/ryze.proton-vpn/proton_status.py")
proton = importlib.util.module_from_spec(spec); spec.loader.exec_module(proton)


class ProtonStatus(unittest.TestCase):
    def test_kill_switch_and_other_vpns_are_not_connected(self):
        state, _ = proton.connection_state([
            dict(Id="pvpn-killswitch-ipv6", Type="dummy", State=2),
            dict(Id="Work VPN", Type="vpn", State=2, VpnState=5)])
        self.assertEqual(state, "disconnected")

    def test_connected_and_transition_states(self):
        for values, expected in [({"State": 2}, "connected"), ({"State": 1}, "connecting"),
                                 ({"State": 3}, "disconnecting"), ({"State": 4}, "disconnected")]:
            state, server = proton.connection_state([dict(Id="ProtonVPN TEST#1", Type="wireguard", **values)])
            self.assertEqual(state, expected)
            self.assertEqual(server, "TEST#1" if expected == "connected" else "")

    def test_openvpn_requires_authenticated_vpn_state(self):
        for vpn_state, expected in [(1, "connecting"), (4, "connecting"), (5, "connected"), (6, "disconnected")]:
            state, _ = proton.connection_state([dict(Id="ProtonVPN TEST#2", Type="vpn", State=2, VpnState=vpn_state)])
            self.assertEqual(state, expected)

    def desktop(self, running=False):
        desktop = proton.Desktop.__new__(proton.Desktop)
        desktop.dbus = MagicMock()
        desktop.session = MagicMock()
        desktop.running = MagicMock(return_value=running)
        desktop.tray_menu = MagicMock(return_value=(None, []))
        desktop.props = MagicMock(side_effect=[{"ActiveConnections": ["/test/tunnel"]},
                     dict(Id="ProtonVPN TEST#1", Type="wireguard", State=2)])
        return desktop

    def test_app_closed_does_not_hide_connected_tunnel(self):
        desktop = self.desktop()
        result = desktop.status()
        self.assertFalse(result["running"])
        self.assertEqual(result["state"], "connected")
        desktop.tray_menu.assert_not_called()
        desktop.session.get_object.assert_not_called()

    def test_unreadable_status_is_unknown(self):
        desktop = self.desktop(True)
        desktop.props.side_effect = RuntimeError("private error contents")
        result = desktop.status()
        self.assertEqual(result["state"], "unknown")
        self.assertNotIn("private", result["error"])

    def test_only_exact_enabled_visible_action_can_be_clicked(self):
        with patch.object(proton, "labels", return_value={"Connect"}):
            self.assertIsNone(proton.menu_action([(3, {"label": "Connect", "enabled": False}, [])], "connect"))
            self.assertIsNone(proton.menu_action([(3, {"label": "Connect", "visible": False}, [])], "connect"))
            self.assertIsNone(proton.menu_action([(3, {"label": "Connect to TEST#1"}, [])], "connect"))
            self.assertIsNone(proton.menu_action([(3, {"label": "Connect"}, []), (4, {"label": "Connect"}, [])], "connect"))
            self.assertEqual(proton.menu_action([(19, {"label": "Connect"}, [])], "connect"), 19)

    def test_actions_requery_menu_and_never_start_or_quit_app(self):
        desktop = self.desktop(True)
        menu = MagicMock()
        desktop.tray_menu.side_effect = [(menu, [(7, {"label": "Disconnect"}, [])]),
                                         (menu, [(42, {"label": "Disconnect"}, [])])]
        with patch.object(proton, "labels", return_value={"Disconnect"}), patch.object(proton.subprocess, "Popen") as launch:
            desktop.action("disconnect"); desktop.action("disconnect")
        self.assertEqual([c.args[0] for c in menu.Event.call_args_list], [7, 42])
        launch.assert_not_called()

    def test_absent_app_or_controls_never_issue_connection_action(self):
        desktop = self.desktop()
        with self.assertRaises(ValueError): desktop.action("connect")
        desktop.tray_menu.assert_not_called()
        desktop.running.return_value = True
        with self.assertRaises(ValueError): desktop.action("connect")

    def test_widget_install_update_remove_preserves_private_settings(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import manage
        with tempfile.TemporaryDirectory(prefix="proton widget ") as temp:
            home = Path(temp) / "home with spaces"; home.mkdir()
            state = home / ".local/state/omarchy-personal-widgets"
            private = home / ".config/Proton/VPN/settings.json"
            private.parent.mkdir(parents=True); private.write_bytes(b"private fixture")
            with contextlib.redirect_stdout(io.StringIO()):
                for _ in range(2):
                    plan = manage.install_plan(home, "DP-2", {"widgets"})
                    self.assertIn(".config/omarchy/plugins/ryze.proton-vpn/ProtonWidget.qml", plan)
                    self.assertNotIn(str(private.relative_to(home)), plan)
                    manage.apply_files(home, state, plan)
                self.assertEqual(manage.remove_files(home, state, True), 0)
            self.assertEqual(private.read_bytes(), b"private fixture")
            self.assertFalse((home / ".config/omarchy/plugins/ryze.proton-vpn/ProtonWidget.qml").exists())
