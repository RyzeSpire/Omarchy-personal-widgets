"""Isolated tests: no Steam launches or changes to the user's library/state."""
import json
import os
from pathlib import Path
import tempfile
import struct
import unittest
from unittest.mock import patch

import steam_backend as backend
import steam_collections as collections


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='steam-widget-test-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base/'native Steam'
        (self.root/'steamapps/common').mkdir(parents=True)
        self.roots_patch = patch.object(backend, 'steam_roots', return_value=[self.root])
        self.roots_patch.start()
        self.addCleanup(self.roots_patch.stop)
        self.environment = patch.dict(os.environ, {'XDG_STATE_HOME': str(self.base/'private-state')})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def game(self, root, appid='123', name='Café™ Adventures', install='Adventure', flags=4):
        common = root/'steamapps/common'
        common.mkdir(parents=True, exist_ok=True)
        if '..' not in install:
            (common/install).mkdir(exist_ok=True)
        (root/'steamapps'/('appmanifest_'+appid+'.acf')).write_text(
            '"AppState" {"appid" "'+appid+'" "name" "'+name+'" "installdir" "'+install+'" '
            '"StateFlags" "'+str(flags)+'" "SizeOnDisk" "1234" "LastPlayed" "42"}', encoding='utf-8')


class BackendTests(Fixture):
    def test_vdf_unicode_nested_escapes_and_comments(self):
        value = backend.parse_vdf('// comment\n"root" { "name" "Café™" "path" "C:\\\\Games" "quoted" "a\\\"b" }')
        self.assertEqual(value['root'], {'name': 'Café™', 'path': 'C:\\Games', 'quoted': 'a"b'})
        for malformed in ('"root" {', '"root"', '}', 'junk'):
            with self.assertRaises(ValueError):
                backend.parse_vdf(malformed)

    def test_multiple_libraries_artwork_and_tool_filter(self):
        external = self.base/'external library'
        self.game(self.root)
        self.game(self.root, '124', 'Proton Experimental', 'Proton')
        self.game(self.root, '126', 'Pending Game', 'Pending', flags=2)
        self.game(external, '125', 'Another Game')
        (self.root/'steamapps/libraryfolders.vdf').write_text(
            '"libraryfolders" { "0" {"path" "'+str(self.root)+'"} "1" {"path" "'+str(external)+'"} }')
        cover = self.root/'appcache/librarycache/123/hash/library_capsule.jpg'
        cover.parent.mkdir(parents=True)
        cover.write_bytes(b'artwork fixture')
        result = backend.library()
        self.assertEqual({game['appid'] for game in result['games']}, {'123', '125'})
        game = next(game for game in result['games'] if game['appid'] == '123')
        self.assertEqual(game['artwork'], cover.as_uri())
        self.assertEqual(game['name'], 'Café™ Adventures')
        self.assertFalse((backend.state_dir()/'favorites.json').exists())

    def test_unsafe_install_directory_skipped(self):
        (self.base/'outside').mkdir()
        self.game(self.root, install='../../../outside')
        self.assertEqual(backend.library()['games'], [])

    def test_favorites_atomic_private_and_preserved_on_error(self):
        backend.set_favorite('123', True)
        backend.set_favorite('125', True)
        backend.set_favorite('123', False)
        self.assertEqual(backend.read_favorites(), {'125'})
        path = backend.state_dir()/'favorites.json'
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(list(path.parent.glob('.favorites-*')), [])
        path.write_text('{bad json')
        with self.assertRaises(ValueError):
            backend.set_favorite('123', True)
        self.assertEqual(path.read_text(), '{bad json')
        self.assertTrue(backend.library()['warnings'])

    def test_launch_protocol_without_starting_client(self):
        self.game(self.root)
        def executable(name):
            return '/usr/bin/'+name if name in ('steam', 'uwsm-app') else None
        with patch.object(backend.shutil, 'which', side_effect=executable), patch.object(backend.subprocess, 'Popen') as popen, patch.object(backend, 'focus_client', return_value=True):
            self.assertTrue(backend.launch('123')['submitted'])
            self.assertEqual(popen.call_args.args[0], ['/usr/bin/uwsm-app', '--', '/usr/bin/steam', '-forcedesktopscaling', os.environ.get('STEAM_FORCE_DESKTOPUI_SCALING', '0.9'), 'steam://rungameid/123'])
            backend.main(['open', 'friends'])
            self.assertEqual(popen.call_args.args[0][-1], 'steam://open/friends')
            for value in ('123;echo hi', '../123', '0', '4294967296', '999'):
                with self.assertRaises(ValueError):
                    backend.launch(value)
            with self.assertRaises(ValueError):
                backend.main(['open', 'untrusted-target'])
            self.assertEqual(popen.call_count, 2)
        with patch.object(backend.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'not installed'):
                backend.dispatch('steam://open/games')

    def test_scaling_is_steam_only_and_preserves_uri_without_wrapper(self):
        with patch.dict(os.environ, {'GDK_SCALE': '2'}):
            os.environ.pop('STEAM_FORCE_DESKTOPUI_SCALING', None)
            before = os.environ.copy()
            with patch.object(backend.shutil, 'which', side_effect=lambda name: '/usr/bin/steam' if name == 'steam' else None), patch.object(backend.subprocess, 'Popen') as popen:
                backend.dispatch('steam://open/games')
                self.assertEqual(popen.call_args.args[0], ['/usr/bin/steam', '-forcedesktopscaling', '0.9', 'steam://open/games'])
                child = popen.call_args.kwargs['env']
                self.assertEqual(child['STEAM_FORCE_DESKTOPUI_SCALING'], '0.9')
                self.assertEqual(child['GDK_SCALE'], '2')
                self.assertEqual(dict(os.environ), before)
                os.environ['STEAM_FORCE_DESKTOPUI_SCALING'] = '1.1'
                backend.dispatch('steam://open/friends')
                self.assertEqual(popen.call_args.args[0][-2:], ['1.1', 'steam://open/friends'])
                self.assertEqual(popen.call_args.kwargs['env']['STEAM_FORCE_DESKTOPUI_SCALING'], '1.1')

    def test_focus_selects_client_and_preserves_workspace(self):
        clients = [{'mapped': True, 'class': 'steam_app_123', 'title': 'Game', 'address': '0x12'},
                   {'mapped': True, 'class': 'steam', 'title': 'Friends List', 'address': '0x13'},
                   {'mapped': True, 'class': 'steam', 'title': 'Steam', 'address': '0x14'}]
        with patch.object(backend.shutil, 'which', return_value='/usr/bin/hyprctl'), patch.object(backend.subprocess, 'check_output', side_effect=[json.dumps(clients), 'ok\n']) as call:
            self.assertTrue(backend.focus_client('library'))
            self.assertEqual(call.call_args.args[0], ['hyprctl', 'dispatch', 'hl.dsp.focus({ window="address:0x14" })'])
        clients[2]['address'] = 'malformed-address'
        with patch.object(backend.shutil, 'which', return_value='/usr/bin/hyprctl'), patch.object(backend.subprocess, 'check_output', return_value=json.dumps(clients)):
            with self.assertRaises(ValueError):
                backend.focus_client('library')

    def test_corrupt_manifest_does_not_hide_other_games(self):
        self.game(self.root)
        (self.root/'steamapps/appmanifest_456.acf').write_text('"AppState" {')
        result = backend.library()
        self.assertEqual(len(result['games']), 1)
        self.assertTrue(result['warnings'])


class CollectionTests(Fixture):
    def metadata(self, version=41):
        keys = ['appinfo', 'common', 'name', 'type', 'icon']
        def key(value):
            return struct.pack('<I', keys.index(value)) if version == 41 else value.encode()+b'\x00'
        def string(k, v):
            return b'\x01'+key(k)+v.encode('utf-8')+b'\x00'
        entries = b''
        for appid, name, kind in [(123, 'Café™ Adventures', 'Game'), (125, 'Another Game', 'game'), (126, 'Useful Software', 'Application'), (127, 'A Hidden Game', 'Game'), (128, 'Unrelated Store Page', 'Game')]:
            payload = b'\x00'+key('appinfo')+b'\x00'+key('common')+string('name', name)+string('type', kind)+string('icon', '')+b'\x08\x08\x08'
            entries += struct.pack('<II', appid, 60+len(payload))+b'\x00'*60+payload
        entries += struct.pack('<I', 0)
        header = struct.pack('<II', 0x07564429 if version == 41 else 0x07564428, 1)
        table = struct.pack('<I', len(keys))+b''.join(k.encode()+b'\x00' for k in keys)
        if version == 41:
            data = header+struct.pack('<Q', 16+len(entries))+entries+table
        else:
            data = header+entries
        path = self.root/'appcache/appinfo.vdf'
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data)
        return path

    def collection(self, key, name, added, removed=None):
        return ['user-collections.'+key, {'value': json.dumps({'name':name, 'added':added, 'removed':removed or []})}]

    def test_binary_formats_and_bounds(self):
        for version in (40, 41):
            path = self.metadata(version)
            metadata = collections.app_metadata(path)
            self.assertEqual(metadata['123']['name'], 'Café™ Adventures')
            self.assertEqual(metadata['126']['type'], 'application')
            path.write_bytes(path.read_bytes()[:30])
            with self.assertRaises(ValueError):
                collections.app_metadata(path)

    def test_pending_collection_edits_and_deletions(self):
        cloud = self.base/'cloud'
        cloud.mkdir()
        (cloud/'cloud-storage-namespaces.json').write_text('[[1,"5"],[3,"0"]]')
        data = [self.collection('favorite', 'Favorites', [123,125], [125]), self.collection('mine', 'My games', [123]), self.collection('deleted', 'Old collection', [123])]
        (cloud/'cloud-storage-namespace-1.json').write_text(json.dumps(data))
        updates = [self.collection('mine','My games',[125]), ['user-collections.deleted', {'is_deleted':True}]]
        (cloud/'cloud-storage-namespace-1.modified.json').write_text(json.dumps(updates))
        result = collections.collection_records(cloud)
        self.assertEqual({c['name']:c['appids'] for c in result}, {'Favorites':['123'], 'My games':['125']})

    def test_real_categories_local_scope_and_hidden_exclusion(self):
        self.game(self.root)
        self.metadata()
        config = self.root/'userdata/1/config'
        cloud = config/'cloudstorage'
        cloud.mkdir(parents=True)
        (config/'localconfig.vdf').write_text('"UserLocalConfigStore" {"Software" {"Valve" {"Steam" {"apps" {"125" {"LastPlayed" "1"}}}}}}')
        records = [self.collection('favorite','Favorites',[123,126]), self.collection('mine','My games',[123]), self.collection('hidden','Hidden',[127])]
        (cloud/'cloud-storage-namespace-1.json').write_text(json.dumps(records))
        result = backend.library()
        self.assertEqual({g['appid'] for g in result['catalog']}, {'123','125','126'})
        self.assertNotIn('128', {g['appid'] for g in result['catalog']})  # Store metadata is not ownership.
        self.assertEqual({c['name']:c['appids'] for c in result['collections']}, {'Favorites':['123','126'],'My games':['123'],'Uncategorized':['125']})
        self.assertEqual(next(g for g in result['catalog'] if g['appid']=='123')['installed'], True)
        self.assertFalse(next(g for g in result['catalog'] if g['appid']=='125')['installed'])

    def test_missing_collection_cache_keeps_installed_picker(self):
        self.game(self.root)
        result = backend.library()
        self.assertEqual(len(result['games']),1)
        self.assertTrue(result['catalog'][0]['installed'])
        self.assertTrue(result['collections_notice'])

    def test_account_selection_never_merges_profiles(self):
        first = self.root/'userdata/1/config'
        second = self.root/'userdata/2/config'
        first.mkdir(parents=True); second.mkdir(parents=True)
        (self.root/'config').mkdir()
        login = self.root/'config/loginusers.vdf'
        login.write_text('"users" {"76561197960265730" {"MostRecent" "1"}}')
        self.assertEqual(collections.profile_config([self.root],backend.read_vdf),second)
        login.write_text('"users" {}')
        with self.assertRaises(ValueError):
            collections.profile_config([self.root],backend.read_vdf)

    def test_store_search_and_details_mocked(self):
        self.game(self.root)
        with patch.object(backend, 'dispatch', return_value={'submitted':True}) as dispatch, patch.object(backend, 'focus_client', return_value=True):
            backend.store_search('Café & test')
            self.assertEqual(dispatch.call_args.args[0], 'steam://openurl/https://store.steampowered.com/search/?term=Caf%C3%A9%20%26%20test')
            backend.details('123')
            self.assertEqual(dispatch.call_args.args[0], 'steam://nav/games/details/123')
            with self.assertRaises(ValueError):
                backend.details('999')
            with self.assertRaises(ValueError):
                backend.store_search(' ')
            self.assertEqual(dispatch.call_count,2)


if __name__ == '__main__':
    unittest.main()
