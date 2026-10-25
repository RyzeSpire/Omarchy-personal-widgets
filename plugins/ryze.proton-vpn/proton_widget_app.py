#!/usr/bin/env python3
"""Launch the installed official GTK app with a small local server-picker API.

No client fork, package patch, separate VPN session, or persisted account copy.
"""
import json
import math
import re
import sys
import time
import unicodedata
from types import MethodType

BUS = "io.github.ryzespire.ProtonWidget"
OBJECT = "/io/github/ryzespire/ProtonWidget"
APP = "proton.vpn.app.gtk"
PAGE_SIZE = 50


def folded(text):
    plain = unicodedata.normalize("NFKD", str(text)).casefold()
    return " ".join(re.findall(r"[^\W_]+", "".join(c for c in plain if not unicodedata.combining(c))))


def number(value, fallback):
    try:
        result = float(value)
        return result if math.isfinite(result) else fallback
    except (TypeError, ValueError):
        return fallback


class Picker:
    """Only the official app's own controller can perform a connection."""
    def __init__(self, controller, schedule=lambda callback: callback(), before_request=lambda: None):
        self.controller = controller
        self.schedule = schedule
        self.before_request = before_request
        self.pending = False
        self.error = ""
        self.target = ""
        self.rows = []
        self.cache_until = 0

    def info(self):
        ready = bool(self.controller.user_logged_in)
        allowed = ready and not self.controller.server_selection_requires_upgrade
        return dict(ok=True, schema=1, ready=ready, selection_allowed=allowed,
                    pending=self.pending, error=self.error, target=self.target)

    def validate(self, name):
        if not isinstance(name, str) or not name or len(name) > 80:
            raise ValueError("Choose a server from the list.")
        info = self.info()
        if not info["ready"]:
            raise ValueError("Sign in to the official Proton VPN app first.")
        if not info["selection_allowed"]:
            raise ValueError("Your Proton plan does not allow specific server selection.")
        server = self.controller._api.server_list.get_by_name(name)
        if server.name != name or not server.enabled or int(server.tier) > int(self.controller.user_tier):
            raise ValueError("This server is unavailable for your account. Refresh the list.")
        return server

    def query(self, query, offset=0):
        if not isinstance(query, str) or len(query) > 128:
            raise ValueError("Search is limited to 128 characters.")
        if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= 100000:
            raise ValueError("Invalid page.")
        info = self.info()
        if not info["ready"]:
            raise ValueError("Sign in to Proton VPN to load servers.")
        if time.monotonic() >= self.cache_until:
            rows = []
            for server in self.controller._api.server_list.logicals:
                if not server.enabled or int(server.tier) > int(self.controller.user_tier):
                    continue
                row = dict(name=str(server.name), country=str(server.exit_country_name),
                           country_code=str(server.exit_country), city=str(server.location or ""),
                           entry_country=str(server.entry_country_name),
                           load=round(max(0, min(100, number(server.load, 0)))),
                           score=number(server.score, 1000000),
                           secure_core=any(int(feature) == 1 for feature in server.features),
                           tor=any(int(feature) == 2 for feature in server.features),
                           free=int(server.tier) == 0)
                row["search"] = folded(" ".join(str(row[k]) for k in ("name", "country", "country_code", "city", "entry_country")))
                rows.append(row)
            self.rows = sorted(rows, key=lambda row: (row["score"], row["name"]))
            self.cache_until = time.monotonic() + 5
        terms = folded(query).split()
        matches = [row for row in self.rows if all(term in row["search"] for term in terms)]
        result = [{k: v for k, v in row.items() if k not in ("search", "score")} for row in matches[offset:offset + PAGE_SIZE]]
        return dict(ok=True, rows=result, total=len(matches), offset=offset, page_size=PAGE_SIZE,
                    selection_allowed=info["selection_allowed"],
                    notice="" if info["selection_allowed"] else "Your Proton plan restricts specific server selection.")

    def connect(self, name):
        if self.pending:
            raise ValueError("A connection request is already running.")
        server = self.validate(name)
        return self.request(lambda: self.controller.connect_to_server(server.name), server.name)

    def request(self, callback, target=""):
        if not self.controller.user_logged_in:
            raise ValueError("Sign in to the official Proton VPN app first.")
        if self.pending:
            raise ValueError("A connection request is already running.")
        try:
            self.before_request()
        except Exception:
            raise ValueError("Could not prevent saved Proton tunnels from auto-connecting. Check the official app.") from None
        self.pending = True
        self.error = ""
        self.target = target
        try:
            future = callback()
        except Exception:
            self.pending = False
            raise
        def complete(done):
            def update():
                self.pending = False
                try:
                    done.result()
                except Exception:
                    self.error = "Proton could not connect to the selected server. Check the official app."
                return False
            self.schedule(update)
        future.add_done_callback(complete)
        return dict(ok=True, accepted=True, target=target)


def skip_migration_startup(_controller, *_args):
    """Bound with MethodType: compatible with Proton's weak signal handlers."""
    return None


def main():
    check = "--check" in sys.argv
    resume = "--widget-resume" in sys.argv
    argv = [arg for arg in sys.argv if arg not in ("--check", "--widget-resume")]
    # Repeated launcher invocations must not create another Proton controller/session.
    if not check:
        import dbus
        from dbus.mainloop.glib import DBusGMainLoop
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()
        if bus.name_has_owner(APP):
            remote = bus.get_object(APP, "/proton/vpn/app/gtk", introspect=False)
            remote.Activate({}, signature="a{sv}", dbus_interface="org.freedesktop.Application", timeout=3)
            return 0
    from gi.repository import Gio, GLib
    from proton.vpn.app.gtk.app import App
    from proton.vpn.app.gtk.controller import Controller
    from proton.vpn.app.gtk.utils.executor import AsyncExecutor
    from proton.vpn.app.gtk.utils.exception_handler import ExceptionHandler
    from importlib.metadata import version
    required = ("connect_to_server", "user_logged_in", "server_selection_requires_upgrade")
    if not all(hasattr(Controller, name) for name in required):
        raise RuntimeError("The installed Proton app is incompatible with this adapter.")
    if check:
        print(json.dumps(dict(ok=True, app_version=version("proton-vpn-gtk-app"))))
        return 0
    xml = """<node><interface name="io.github.ryzespire.ProtonWidget">
      <method name="Info"><arg direction="out" type="s"/></method>
      <method name="QuickConnect"><arg direction="out" type="s"/></method>
      <method name="Disconnect"><arg direction="out" type="s"/></method>
      <method name="Search"><arg direction="in" type="s"/><arg direction="in" type="u"/><arg direction="out" type="s"/></method>
      <method name="Validate"><arg direction="in" type="s"/><arg direction="out" type="s"/></method>
      <method name="Connect"><arg direction="in" type="s"/><arg direction="out" type="s"/></method>
    </interface></node>"""
    class WidgetApp(App):
        def do_startup(self):
            super().do_startup()
            from proton_autoconnect import guard
            self.picker = Picker(self._controller, GLib.idle_add, guard)
            interface = Gio.DBusNodeInfo.new_for_xml(xml).interfaces[0]
            connection = self.get_dbus_connection()
            self.widget_registration = connection.register_object(OBJECT, interface, self.on_widget_call, None, None)
            self.widget_owner = Gio.bus_own_name_on_connection(connection, BUS, Gio.BusNameOwnerFlags.NONE, None, None)

        def on_widget_call(self, _connection, _sender, _path, _interface, method, parameters, invocation):
            try:
                args = parameters.unpack()
                if method == "Info": result = self.picker.info()
                elif method == "Search": result = self.picker.query(*args)
                elif method == "Validate":
                    server = self.picker.validate(*args)
                    result = dict(ok=True, name=server.name)
                elif method == "Connect": result = self.picker.connect(*args)
                elif method == "QuickConnect": result = self.picker.request(self._controller.connect_to_fastest_server)
                elif method == "Disconnect": result = self.picker.request(self._controller.disconnect)
                else: raise ValueError("Unsupported widget request.")
            except Exception as error:
                message = str(error) if isinstance(error, ValueError) else "Proton server selection is unavailable. Check the official app."
                result = dict(ok=False, error=message)
            invocation.return_value(GLib.Variant("(s)", (json.dumps(result),)))

    from proton_autoconnect import guard
    # Persistent profile flags are repaired before app startup or any explicit request.
    guard()
    with AsyncExecutor() as executor, ExceptionHandler() as exception_handler:
        controller = Controller.get(executor, exception_handler)
        if resume:
            # Preserve the active tunnel for an internal GUI-only migration restart.
            controller.run_startup_actions = MethodType(skip_migration_startup, controller)
        return WidgetApp(controller).run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
