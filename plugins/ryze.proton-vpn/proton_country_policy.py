#!/usr/bin/env python3
"""Filter native Proton catalogs and guard the adapted app's connection boundary."""
import inspect
import json
from pathlib import Path
import re
from types import MethodType


def configured_countries():
    path = Path(__file__).with_name("country-policy.json")
    if not path.exists():
        return frozenset({"BR"})
    data = json.loads(path.read_text())
    values = data.get("blocked_countries")
    if data.get("schema") != 1 or not isinstance(values, list) or not values:
        raise ValueError("Invalid Proton country policy; connections are disabled.")
    if any(not isinstance(code, str) or not re.fullmatch(r"[A-Za-z]{2}", code) for code in values):
        raise ValueError("Invalid blocked-country code; connections are disabled.")
    return frozenset(code.upper() for code in values)


BLOCKED_COUNTRIES = configured_countries()


def notice():
    if BLOCKED_COUNTRIES == {"BR"}:
        return "Brazil servers are hidden and blocked."
    return "Countries hidden and blocked: " + ", ".join(sorted(BLOCKED_COUNTRIES)) + "."


def allowed(server):
    if server is None:
        return False
    codes = [str(getattr(server, key, "") or "").upper()
             for key in ("entry_country", "exit_country", "host_country")]
    # Entry/exit must be known; host country is optional for non-virtual routes.
    if any(not re.fullmatch(r"[A-Z]{2}", code) for code in codes[:2]):
        return False
    if codes[2] and not re.fullmatch(r"[A-Z]{2}", codes[2]):
        return False
    if any(code in BLOCKED_COUNTRIES for code in codes):
        return False
    name = str(getattr(server, "name", "") or "").upper()
    if not name:
        return False
    return not any(re.search(r"(?:^|-)" + re.escape(code) + r"(?:[-#]|$)", name)
                   for code in BLOCKED_COUNTRIES)


def require_allowed(server):
    if not allowed(server):
        raise ValueError("This server is blocked by your country policy, or its route is unknown.")
    return server


class ServerListView:
    """Rebind native catalog methods to a filtered view; original cache is intact."""
    def __init__(self, catalog):
        self._catalog = catalog

    @property
    def logicals(self):
        return [server for server in self._catalog.logicals if allowed(server)]

    def __len__(self):
        return len(self.logicals)

    def __iter__(self):
        return iter(self.logicals)

    def __getitem__(self, item):
        return self.logicals[item]

    def get_by_name(self, name):
        return require_allowed(self._catalog.get_by_name(name))

    def get_by_id(self, identifier):
        return require_allowed(self._catalog.get_by_id(identifier))

    def __getattr__(self, name):
        descriptor = inspect.getattr_static(type(self._catalog), name, None)
        if isinstance(descriptor, property):
            return descriptor.fget(self)
        value = getattr(self._catalog, name)
        if inspect.ismethod(value) and value.__self__ is self._catalog:
            return MethodType(value.__func__, self)
        return value


class APIView:
    def __init__(self, api):
        self._api = api

    @property
    def server_list(self):
        return ServerListView(self._api.server_list)

    def __getattr__(self, name):
        return getattr(self._api, name)


def install(controller):
    """Guard GUI/startup/tray paths plus SDK reconnects, without package patches."""
    if getattr(controller, "_ryze_country_policy_installed", False):
        return
    original_api = controller._api
    active_blocked = False
    current_id = getattr(controller, "current_server_id", None)
    if current_id:
        try:
            active = original_api.server_list.get_by_id(current_id)
            active_blocked = active is not None and not allowed(active)
        except Exception:
            pass
    connector = controller.vpn_connector
    native_get = connector.get_vpn_server
    native_connect = connector.connect

    def checked_get(_connector, logical_server, *args, **kwargs):
        require_allowed(logical_server)
        return native_get(logical_server, *args, **kwargs)

    async def checked_connect(_connector, vpn_server, *args, **kwargs):
        # Re-resolve against the current catalog: retries cannot reuse a blocked DTO.
        logical = original_api.server_list.get_by_id(vpn_server.server_id)
        require_allowed(logical)
        if str(vpn_server.server_name) != str(logical.name):
            raise ValueError("The cached server route changed; refusing the connection.")
        return await native_connect(vpn_server, *args, **kwargs)

    connector.get_vpn_server = MethodType(checked_get, connector)
    connector.connect = MethodType(checked_connect, connector)
    controller._api = APIView(original_api)
    controller._ryze_country_policy_installed = True
    return active_blocked
