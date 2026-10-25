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
PICKER_BUS = "io.github.ryzespire.ProtonWidget"
PICKER_OBJECT = "/io/github/ryzespire/ProtonWidget"


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

    def picker(self):
        if not self.running() or not self.session.name_has_owner(PICKER_BUS):
            raise ValueError("Start Proton VPN from its launcher or this widget to enable server search.")
        daemon = self.session.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus", introspect=False)
        def pid(name):
            return daemon.GetConnectionUnixProcessID(name, dbus_interface="org.freedesktop.DBus", timeout=2)
        if pid(APP) != pid(PICKER_BUS):
            raise ValueError("The server picker is not part of the official app process.")
        return self.session.get_object(PICKER_BUS, PICKER_OBJECT, introspect=False)

    def picker_call(self, method, *args):
        obj = self.picker()
        signature = {"Info": "", "Search": "su", "Validate": "s", "Connect": "s", "QuickConnect": "", "Disconnect": "", "PreviewFastest": ""}[method]
        result = getattr(obj, method)(*args, signature=signature, dbus_interface=PICKER_BUS, timeout=8)
        data = json.loads(str(result))
        if not isinstance(data, dict):
            raise ValueError("Invalid server picker response.")
        return data

    def status(self):
        running = self.running()
        result = dict(ok=True, running=running, state="unknown", server="",
                      can_connect=False, can_disconnect=False, picker_available=False, selection_allowed=False, picker_pending=False, picker_error="", blocked_countries=[], error="")
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
        if running:
            try:
                info = self.picker_call("Info")
                result.update(picker_available=info.get("ok") is True,
                              selection_allowed=info.get("selection_allowed") is True,
                              picker_pending=info.get("pending") is True,
                              picker_error=info.get("error", ""),
                              blocked_countries=info.get("blocked_countries", []))
                if result["picker_available"]:
                    ready = info.get("ready") is True and not result["picker_pending"]
                    result["can_connect"] = ready and result["state"] == "disconnected"
                    result["can_disconnect"] = ready and result["state"] in ("connected", "connecting")
            except Exception:
                pass
        if not result["picker_available"]:
            # An unadapted app cannot enforce this widget's country policy.
            result["can_connect"] = False
        return result

    def action(self, action):
        if action == "open":
            if self.running():
                obj = self.session.get_object(APP, "/proton/vpn/app/gtk", introspect=False)
                obj.Activate({}, signature="a{sv}", dbus_interface="org.freedesktop.Application", timeout=3)
            else:
                subprocess.Popen([sys.executable, "-B", str(Path(__file__).with_name("proton_widget_app.py"))], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
            return
        if action not in ("connect", "disconnect"):
            raise ValueError("Unknown action.")
        if not self.running():
            raise ValueError("Open Proton VPN and sign in first.")
        if self.session.name_has_owner(PICKER_BUS):
            response = self.picker_call("QuickConnect" if action == "connect" else "Disconnect")
            if not response.get("ok"):
                raise ValueError(response.get("error", "Could not complete the Proton request."))
            return
        if action == "connect":
            raise ValueError("Start Proton VPN through its launcher to enforce the blocked-country policy.")
        obj, items = self.tray_menu()
        item_id = menu_action(items, action)
        if obj is None or item_id is None:
            raise ValueError("This control is unavailable. Open Proton VPN to continue.")
        # Resolve the current ID immediately before clicking; never use a cached ID.
        obj.Event(item_id, "clicked", self.dbus.Int32(0, variant_level=1), self.dbus.UInt32(0),
                  signature="isvu", dbus_interface=MENU, timeout=3)


def main():
    args = sys.argv[1:]
    action = args[0] if args else ""
    if not ((action in ("status", "open", "connect", "disconnect", "preview-fastest") and len(args) == 1)
            or (action == "search" and len(args) == 3)
            or (action in ("select", "validate") and len(args) == 2)):
        print(json.dumps(dict(ok=False, error="Invalid widget request.")))
        return 2
    try:
        desktop = Desktop()
        if action == "status":
            result = desktop.status()
        elif action == "preview-fastest":
            result = desktop.picker_call("PreviewFastest")
        elif action == "search":
            result = desktop.picker_call("Search", args[1], desktop.dbus.UInt32(int(args[2])))
        elif action in ("select", "validate"):
            result = desktop.picker_call("Connect" if action == "select" else "Validate", args[1])
        else:
            desktop.action(action)
            result = dict(ok=True)
    except Exception as error:
        message = str(error) if isinstance(error, ValueError) else "Proton VPN is unavailable. Open the official app and try again."
        result = dict(ok=False, running=False, state="unknown", server="", error=message)
    print(json.dumps(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
