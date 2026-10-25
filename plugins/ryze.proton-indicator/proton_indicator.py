#!/usr/bin/env python3
"""Read local status or show the official app. No account or VPN-control APIs."""
import gettext
import json
import re
import subprocess
import sys
import sysconfig
from pathlib import Path
import time

APP = "proton.vpn.app.gtk"
NM = "org.freedesktop.NetworkManager"
PROPERTIES = "org.freedesktop.DBus.Properties"


def tunnel_state(connections):
    tunnels = [c for c in connections if str(c.get("Id", "")).startswith("ProtonVPN ")
               and c.get("Type") in ("wireguard", "vpn")]
    if any(c.get("State") == 2 and (c["Type"] != "vpn" or c.get("VpnState") == 5) for c in tunnels):
        return "connected"
    if any(c.get("State") == 1 or (c.get("Type") == "vpn" and c.get("State") == 2
                                   and c.get("VpnState") in (1, 2, 3, 4)) for c in tunnels):
        return "connecting"
    if any(c.get("State") == 3 for c in tunnels):
        return "disconnecting"
    return "disconnected"


class Desktop:
    def __init__(self):
        import dbus
        self.dbus = dbus
        self.session = dbus.SessionBus()

    def running(self):
        return bool(self.session.name_has_owner(APP))

    def status(self):
        running = self.running()
        if running:
            try:
                native = self.tray_state()
                if native is not None:
                    return dict(ok=True, running=True, state=native, source="official-app", error="")
            except Exception:
                pass
        try:
            bus = self.dbus.SystemBus()
            if not bus.name_has_owner(NM):
                raise RuntimeError("NetworkManager is unavailable")
            def properties(path, interface):
                obj = bus.get_object(NM, path, introspect=False)
                return dict(obj.GetAll(interface, dbus_interface=PROPERTIES, timeout=2))
            active = properties("/org/freedesktop/NetworkManager", NM)["ActiveConnections"]
            connections = []
            for path in active:
                props = properties(str(path), NM + ".Connection.Active")
                if str(props.get("Id", "")).startswith("ProtonVPN ") and props.get("Type") == "vpn":
                    props.update(properties(str(path), NM + ".VPN.Connection"))
                connections.append(props)
            return dict(ok=True, running=running, state=tunnel_state(connections), source="networkmanager", error="")
        except Exception:
            return dict(ok=False, running=running, state="unknown", error="VPN status unavailable.")

    def tray_items(self):
        pid = self.app_pid()
        daemon = self.session.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus", introspect=False)
        for name in self.session.list_names():
            if not str(name).startswith("org.kde.StatusNotifierItem-" + APP + "-"):
                continue
            owner = daemon.GetConnectionUnixProcessID(name, dbus_interface="org.freedesktop.DBus", timeout=2)
            if int(owner) != pid:
                continue
            obj = self.session.get_object(str(name), "/StatusNotifierItem", introspect=False)
            props = obj.GetAll("org.kde.StatusNotifierItem", dbus_interface=PROPERTIES, timeout=2)
            yield str(name), props

    def tray_state(self):
        for _name, props in self.tray_items():
            icon = str(props.get("IconName", "")).rsplit("/", 1)[-1].casefold()
            return {"state-connected.svg": "connected", "state-disconnected.svg": "disconnected", "state-error.svg": "disconnected"}.get(icon)
        return None

    def show_from_tray(self):
        # Only the native Show entry may be invoked. Never guess a menu index or
        # reuse one across clicks: the native menu also contains VPN controls.
        locale_dir = Path(sysconfig.get_path("purelib")) / "proton/vpn/app/gtk/locale/binaries"
        translation = gettext.translation("proton-vpn-gtk-app", str(locale_dir), fallback=True)
        show_labels = {"Show", translation.pgettext("button", "Show")}
        for name, props in self.tray_items():
            path = str(props.get("Menu", ""))
            if path != "/MenuBar":
                continue
            menu = self.session.get_object(name, path, introspect=False)
            interface = "com.canonical.dbusmenu"
            revision, layout = menu.GetLayout(0, 1, [], signature="iias", dbus_interface=interface, timeout=2)
            candidates = [(item[0], dict(item[1])) for item in layout[2]
                          if str(item[1].get("label", "")) in show_labels
                          and item[1].get("enabled", True) and item[1].get("visible", True)
                          and item[1].get("type", "standard") == "standard" and not item[2]]
            if len(candidates) != 1:
                continue
            item_id, properties = candidates[0]
            # Refuse if rebuilding the menu changed either its revision or entry.
            current_revision, current = menu.GetLayout(item_id, 0, [], signature="iias", dbus_interface=interface, timeout=2)
            if current_revision != revision or current[0] != item_id or dict(current[1]) != properties:
                continue
            menu.Event(item_id, "clicked", self.dbus.String(""), self.dbus.UInt32(0),
                       signature="isvu", dbus_interface=interface, timeout=2)
            return True
        return False

    def app_pid(self):
        daemon = self.session.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus", introspect=False)
        return int(daemon.GetConnectionUnixProcessID(APP, dbus_interface="org.freedesktop.DBus", timeout=2))

    def focus_window(self, pid):
        try:
            result = subprocess.run(["hyprctl", "-j", "clients"], check=True, capture_output=True, text=True, timeout=2)
            windows = json.loads(result.stdout)
            for window in windows:
                address = window.get("address", "")
                if window.get("pid") == pid and window.get("mapped") and not window.get("hidden") and re.fullmatch(r"0x[0-9a-fA-F]+", address):
                    subprocess.run(["hyprctl", "dispatch", 'hl.dsp.focus({ window = "address:' + address + '" })'], check=True,
                                   capture_output=True, text=True, timeout=2)
                    return True
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
        return False

    def open(self):
        if self.running():
            if self.focus_window(self.app_pid()):
                return
            try:
                shown = self.show_from_tray()
            except Exception:
                shown = False
            if not shown:
                obj = self.session.get_object(APP, "/proton/vpn/app/gtk", introspect=False)
                obj.Activate({}, signature="a{sv}", dbus_interface="org.freedesktop.Application", timeout=3)
        else:
            subprocess.Popen(["protonvpn-app"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.monotonic() + 8
        tray_attempted = False
        while time.monotonic() < deadline:
            if self.running():
                if self.focus_window(self.app_pid()):
                    return
                if not tray_attempted:
                    try:
                        tray_attempted = self.show_from_tray()
                    except Exception:
                        pass
            time.sleep(0.2)
        raise ValueError("Proton VPN is starting or hidden. Use its native tray if the window stays hidden.")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("status", "open"):
        print(json.dumps(dict(ok=False, error="Expected status or open.")))
        return 2
    try:
        desktop = Desktop()
        if sys.argv[1] == "status":
            result = desktop.status()
        else:
            desktop.open()
            result = dict(ok=True)
    except Exception as error:
        message = str(error) if isinstance(error, ValueError) else "Could not contact the official Proton VPN app."
        result = dict(ok=False, running=False, state="unknown", error=message)
    print(json.dumps(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
