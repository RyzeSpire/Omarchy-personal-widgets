"""Country restrictions with fake catalogs/connectors; no network connections."""
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import json
import tempfile
from unittest.mock import patch, MagicMock
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/ryze.proton-vpn"))
import proton_country_policy as policy
import proton_widget_app as app


def server(name="US#1", entry="US", exit="US", host=None, score=10):
    return SimpleNamespace(id=name, name=name, entry_country=entry, exit_country=exit, host_country=host,
                           entry_country_name=entry, exit_country_name=exit, score=score, tier=0,
                           enabled=True, location="Test City", features=[], load=15)


class Catalog:
    def __init__(self, rows): self.logicals = rows
    def get_by_name(self, name): return next(s for s in self.logicals if s.name == name)
    def get_by_id(self, identifier): return next(s for s in self.logicals if s.id == identifier)
    def get_fastest(self): return min(self.logicals, key=lambda s: s.score)
    def group_by_country(self): return {s.exit_country for s in self.logicals}


class Connector:
    def __init__(self): self.calls = []
    def get_vpn_server(self, logical, _config=None):
        self.calls.append(("build", logical.name))
        return SimpleNamespace(server_id=logical.id, server_name=logical.name)
    async def connect(self, vpn_server, **_kwargs):
        self.calls.append(("connect", vpn_server.server_name))
        return "native connection result"


def controller(rows, current=None):
    return SimpleNamespace(_api=SimpleNamespace(server_list=Catalog(rows)), vpn_connector=Connector(),
                           current_server_id=current, user_logged_in=True, user_tier=2,
                           server_selection_requires_upgrade=False)


class CountryPolicyTests(unittest.TestCase):
    def test_missing_policy_keeps_brazil_default(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(policy, "__file__", str(Path(temp) / "policy.py")):
            self.assertEqual(policy.configured_countries(), {"BR"})

    def test_invalid_policy_cannot_silently_disable_restrictions(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(policy, "__file__", str(Path(temp) / "policy.py")):
            path = Path(temp) / "country-policy.json"
            for data in ({"schema": 1, "blocked_countries": []}, {"schema": 1, "blocked_countries": ["Brazil"]},
                         {"schema": 2, "blocked_countries": ["BR"]}):
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError): policy.configured_countries()

    def test_native_iteration_indexing_and_length_stay_filtered(self):
        view = policy.ServerListView(Catalog([server(), server("BR#1", entry="BR", exit="BR")]))
        self.assertEqual(len(view), 1)
        self.assertEqual([row.name for row in view], ["US#1"])
        self.assertEqual(view[0].name, "US#1")

    def test_unadapted_enabled_tray_cannot_bypass_policy(self):
        import proton_status
        desktop = proton_status.Desktop.__new__(proton_status.Desktop)
        desktop.session = MagicMock(); desktop.session.name_has_owner.return_value = False
        desktop.running = lambda: True
        desktop.tray_menu = MagicMock(return_value=(MagicMock(), [(1, {"label": "Connect", "enabled": True}, [])]))
        with self.assertRaisesRegex(ValueError, "blocked-country policy"): desktop.action("connect")
        desktop.tray_menu.assert_not_called()

    def test_exit_entry_host_name_and_missing_metadata_are_blocked(self):
        rows = [server("BR#1", entry="BR", exit="BR"), server("CH-BR#1", entry="CH", exit="BR"),
                server("BR-US#1", entry="BR"), server("US#9", host="BR"),
                server("br#1"), server("US#8", entry=""), server("US#7", exit=None)]
        for row in rows:
            with self.subTest(name=row.name): self.assertFalse(policy.allowed(row))

    def test_other_countries_and_brussels_remain_allowed(self):
        for row in (server(), server("BE#1", entry="BE", exit="BE"), server("CH-US#1", entry="CH")):
            self.assertTrue(policy.allowed(row))

    def test_catalog_filter_and_grouping_do_not_modify_native_cache(self):
        rows = [server(), server("BR#1", entry="BR", exit="BR")]
        raw = Catalog(rows); view = policy.ServerListView(raw)
        self.assertEqual([s.name for s in view.logicals], ["US#1"])
        self.assertEqual(view.group_by_country(), {"US"})
        self.assertEqual(raw.logicals, rows)
        with self.assertRaises(ValueError): view.get_by_name("BR#1")
        with self.assertRaises(ValueError): view.get_by_id("BR#1")

    def test_fastest_uses_allowed_subset_even_if_brazil_is_faster(self):
        raw = Catalog([server("BR#1", entry="BR", exit="BR", score=0), server(score=20)])
        self.assertEqual(raw.get_fastest().name, "BR#1")
        self.assertEqual(policy.ServerListView(raw).get_fastest().name, "US#1")

    def test_no_allowed_fastest_does_not_fall_back(self):
        view = policy.ServerListView(Catalog([server("BR#1", entry="BR", exit="BR")]))
        with self.assertRaises(ValueError): view.get_fastest()

    def test_widget_search_and_direct_selection_exclude_brazil(self):
        c = controller([server(), server("BR#1", entry="BR", exit="BR")])
        picker = app.Picker(c)
        self.assertEqual([row["name"] for row in picker.query("")["rows"]], ["US#1"])
        self.assertEqual(picker.query("BR#1")["total"], 0)
        with self.assertRaises(ValueError): picker.validate("BR#1")
        self.assertEqual(picker.info()["blocked_countries"], ["BR"])

    def test_native_dto_build_rejects_blocked_route(self):
        blocked = server("BR#1", entry="BR", exit="BR")
        c = controller([server(), blocked]); policy.install(c)
        with self.assertRaises(ValueError): c.vpn_connector.get_vpn_server(blocked)
        self.assertEqual(c.vpn_connector.calls, [])

    def test_sdk_reconnection_cannot_reuse_prebuilt_blocked_dto(self):
        c = controller([server(), server("BR#1", entry="BR", exit="BR")]); policy.install(c)
        dto = SimpleNamespace(server_id="BR#1", server_name="BR#1")
        with self.assertRaises(ValueError): asyncio.run(c.vpn_connector.connect(dto))
        self.assertEqual(c.vpn_connector.calls, [])

    def test_sdk_resolves_current_route_and_refuses_changed_name(self):
        good = server(); c = controller([good]); raw = c._api.server_list; policy.install(c)
        dto = c.vpn_connector.get_vpn_server(good)
        good.exit_country = "BR"
        with self.assertRaises(ValueError): asyncio.run(c.vpn_connector.connect(dto))
        good.exit_country = "US"; dto.server_name = "BR#1"
        with self.assertRaises(ValueError): asyncio.run(c.vpn_connector.connect(dto))
        self.assertFalse(any(kind == "connect" for kind, _name in c.vpn_connector.calls))

    def test_allowed_native_connection_and_idempotent_install(self):
        c = controller([server()]); policy.install(c); original = c.vpn_connector.connect
        policy.install(c)
        self.assertEqual(c.vpn_connector.connect, original)
        dto = c.vpn_connector.get_vpn_server(c._api.server_list.get_fastest())
        self.assertEqual(asyncio.run(c.vpn_connector.connect(dto)), "native connection result")

    def test_current_blocked_route_is_flagged_for_disconnect_only(self):
        blocked = server("BR#1", entry="BR", exit="BR")
        self.assertTrue(policy.install(controller([blocked], current=blocked.id)))
        self.assertFalse(policy.install(controller([server()], current="US#1")))

    def test_fresh_native_catalog_remains_filtered(self):
        c = controller([server()]); raw_api = c._api; policy.install(c)
        raw_api.server_list = Catalog([server("BR#2", entry="BR", exit="BR"), server("CA#1", entry="CA", exit="CA")])
        self.assertEqual([s.name for s in c._api.server_list.logicals], ["CA#1"])
