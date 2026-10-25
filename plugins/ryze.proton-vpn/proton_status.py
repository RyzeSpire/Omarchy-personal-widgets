#!/usr/bin/env python3
"""Read-only local status; explicit actions delegate to the official GTK tray.

No Proton account imports, keyring access, HTTP requests, logs, or saved state.
"""
import gettext
import json
from pathlib import Path
import subprocess
import sys

APP = "proton.vpn.app.gtk"
TRAY_PREFIX = "org.kde.StatusNotifierItem-" + APP + "-"
NM = "org.freedesktop.NetworkManager"
ACTIVE = NM + ".Connection.Active"
PROPS = "org.freedesktop.DBus.Properties"
MENU = "com.canonical.dbusmenu"


def connection_state(connections):
    """Only official Proton tunnel connections count, never kill-switch devices."""
    tunnels = [c for c in connections if c.get("Id", "").startswith("ProtonVPN ")
               and c.get("Type") in ("wireguard", "vpn")]
    for c in tunnels:
        # OpenVPN's base active state can precede VPN authentication completion.
        if c.get("State") == 2 and (c["Type"] != "vpn" or c.get("VpnState") == 5):
            return "connected", c["Id"].removeprefix("ProtonVPN ")
    if any(c.get("State") == 1 or (c.get("Type") == "vpn" and c.get("State") == 2
                                   and c.get("VpnState") in (1, 2, 3, 4)) for c in tunnels):
        return "connecting", ""
    if any(c.get("State") == 3 for c in tunnels):
        return "disconnecting", ""
    return "disconnected", ""


def labels(action):
    """Accept source text and installed app translations without importing Proton."""
    text = {"connect": "Connect", "disconnect": "Disconnect"}[action]
    result = {text}
    # Locate catalogs from the installed package, without reading app profiles.
    for base in sys.path:
        catalogs = Path(base) / "proton/vpn/app/gtk/locale/binaries"
        if not catalogs.is_dir():
            continue
        for catalog in catalogs.glob("*/LC_MESSAGES/proton-vpn-gtk-app.mo"):
            with catalog.open("rb") as stream:
                result.add(gettext.GNUTranslations(stream).pgettext("button", text))
    return result


def menu_action(items, action):
    accepted = labels(action)
    matches = [(int(item_id), props) for item_id, props, _children in items
               if props.get("label") in accepted and props.get("type", "standard") == "standard"]
    if len(matches) != 1:
        return None
    item_id, props = matches[0]
    return item_id if props.get("enabled", True) and props.get("visible", True) else None


class Desktop:
    def __init__(self):
        import dbus
        self.dbus = dbus
        self.session = dbus.SessionBus()

    def props(self, bus, service, path, interface):
        obj = bus.get_object(service, path, introspect=False)
        return dict(obj.GetAll(interface, dbus_interface=PROPS, timeout=2))

    def running(self):
        return bool(self.session.name_has_owner(APP))

    def tray_menu(self):
        names = sorted(str(n) for n in self.session.list_names() if str(n).startswith(TRAY_PREFIX))
        if not names:
            return None, []
        # Require the tray to belong to the actual official app process.
        daemon = self.session.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus", introspect=False)
        def pid(name):
            return daemon.GetConnectionUnixProcessID(name, dbus_interface="org.freedesktop.DBus", timeout=2)
        owner = pid(APP)
        names = [n for n in names if pid(n) == owner]
        if not names:
            return None, []
        service = names[0]
        props = self.props(self.session, service, "/StatusNotifierItem", "org.kde.StatusNotifierItem")
        obj = self.session.get_object(service, str(props["Menu"]), introspect=False)
        _revision, layout = obj.GetLayout(0, 1, ["label", "enabled", "visible", "type"],
                                        signature="iias", dbus_interface=MENU, timeout=2)
        return obj, layout[2]

    def status(self):
        running = self.running()
        result = dict(ok=True, running=running, state="unknown", server="",
                      can_connect=False, can_disconnect=False, error="")
        try:
            bus = self.dbus.SystemBus()
            active = self.props(bus, NM, "/org/freedesktop/NetworkManager", NM)["ActiveConnections"]
            connections = []
            for path in active:
                props = self.props(bus, NM, str(path), ACTIVE)
                if str(props.get("Id", "")).startswith("ProtonVPN ") and props.get("Type") == "vpn":
                    props.update(self.props(bus, NM, str(path), NM + ".VPN.Connection"))
                connections.append(props)
            result["state"], result["server"] = connection_state(connections)
        except Exception:
            result["error"] = "Connection status unavailable. Check the official Proton VPN app."
        if running:
            try:
                _obj, items = self.tray_menu()
                result["can_connect"] = menu_action(items, "connect") is not None
                result["can_disconnect"] = menu_action(items, "disconnect") is not None
            except Exception:
                # A missing tray must not hide a connected tunnel or invent controls.
                pass
        return result

    def action(self, action):
        if action == "open":
            if self.running():
                obj = self.session.get_object(APP, "/proton/vpn/app/gtk", introspect=False)
                obj.Activate({}, signature="a{sv}", dbus_interface="org.freedesktop.Application", timeout=3)
            else:
                subprocess.Popen(["protonvpn-app"], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
            return
        if action not in ("connect", "disconnect"):
            raise ValueError("Unknown action.")
        if not self.running():
            raise ValueError("Open Proton VPN and sign in first.")
        obj, items = self.tray_menu()
        item_id = menu_action(items, action)
        if obj is None or item_id is None:
            raise ValueError("This control is unavailable. Open Proton VPN to continue.")
        # Resolve the current ID immediately before clicking; never use a cached ID.
        obj.Event(item_id, "clicked", self.dbus.Int32(0, variant_level=1), self.dbus.UInt32(0),
                  signature="isvu", dbus_interface=MENU, timeout=3)


def main():
    action = sys.argv[1] if len(sys.argv) == 2 else ""
    if action not in ("status", "open", "connect", "disconnect"):
        print(json.dumps(dict(ok=False, error="Expected status, open, connect or disconnect.")))
        return 2
    try:
        desktop = Desktop()
        if action == "status":
            result = desktop.status()
        else:
            desktop.action(action)
            result = dict(ok=True)
    except Exception as error:
        # D-Bus errors can carry private arguments; return a safe UI message only.
        message = str(error) if isinstance(error, ValueError) else "Proton VPN is unavailable. Open the official app and try again."
        result = dict(ok=False, running=False, state="unknown", server="", error=message)
    print(json.dumps(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
