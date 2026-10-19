"""Friends checks use temporary private state, mocked HTTP and mocked launches."""
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import steam_friends as friends

OWNER = str(friends.BASE_ID + 1)
FIRST = str(friends.BASE_ID + 2)
SECOND = str(friends.BASE_ID + 3)
KEY = 'a' * 32


class FriendsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='steam-friends-test-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        env = patch.dict(os.environ, {'XDG_CONFIG_HOME':str(self.base/'config'), 'XDG_CACHE_HOME':str(self.base/'cache')})
        env.start(); self.addCleanup(env.stop)
        profile = patch.object(friends, 'current_profile', return_value={'steamid':OWNER,'name':'Test profile','avatar':'','status':'Steam profile','group':'unknown','game':''})
        profile.start(); self.addCleanup(profile.stop)

    def player(self, steamid=OWNER, name='Test profile', state=1, game=''):
        return {'steamid':steamid, 'personaname':name, 'personastate':state, 'gameextrainfo':game, 'avatarmedium':'https://avatars.steamstatic.com/test.jpg'}

    def config(self):
        friends.atomic_json(friends.credential_path(), {'version':1,'steamid':OWNER,'api_key':KEY})

    def test_unconfigured_uses_profile_without_network_or_creating_state(self):
        with patch.object(friends, 'api') as api:
            result = friends.refresh()
        self.assertFalse(result['configured'])
        self.assertEqual(result['friends'], [])
        api.assert_not_called()
        self.assertFalse(friends.cache_dir().exists())
        self.assertFalse(friends.credential_path().exists())

    def test_configuration_private_and_failed_replacement_preserves_key(self):
        with patch.object(friends, 'api', return_value={'response':{'players':[self.player()]}}):
            result = friends.configure({'api_key':KEY})
        self.assertNotIn(KEY, json.dumps(result))
        path = friends.credential_path()
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
        original = path.read_bytes()
        with patch.object(friends, 'api', side_effect=friends.FriendsError('Steam rejected the API key.')):
            with self.assertRaises(friends.FriendsError):
                friends.configure({'api_key':'b'*32})
        self.assertEqual(path.read_bytes(), original)
        with self.assertRaises(friends.FriendsError):
            friends.configure({'api_key':'invalid'})
        path.chmod(0o644)
        with self.assertRaisesRegex(friends.FriendsError, 'permissions'):
            friends.read_config()

    def test_api_key_is_in_header_not_url_and_errors_are_redacted(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):return None
            def read(self,*args):return b'{"response":{"players":[]}}'
        with patch.object(friends, 'build_opener') as opener:
            opener.return_value.open.return_value = Response()
            friends.api('GetPlayerSummaries/v2',KEY,{'steamids':OWNER})
            request = opener.return_value.open.call_args.args[0]
            self.assertNotIn(KEY, request.full_url)
            self.assertEqual(request.get_header('X-webapi-key'), KEY)
            self.assertEqual(request.host, 'api.steampowered.com')
        for status in (401,403,429,500,302):
            with patch.object(friends, 'build_opener') as opener:
                opener.return_value.open.side_effect=HTTPError('https://example.invalid/'+KEY,status,'secret '+KEY,{},None)
                with self.assertRaises(friends.FriendsError) as caught:
                    friends.api('GetFriendList/v1',KEY,{'steamid':OWNER})
                self.assertNotIn(KEY,str(caught.exception))
        self.assertIsNone(friends.NoRedirect().redirect_request(None,None,302,'',{},'https://example.invalid/'))

    def test_presence_visibility_and_avatar_allowlist(self):
        self.assertEqual(friends.person(self.player(FIRST,state=1,game='Test Game'))['group'],'in_game')
        offline = friends.person(self.player(FIRST,state=0,game='Old Game'))
        self.assertEqual(offline['group'],'offline')
        self.assertEqual(offline['game'],'')
        self.assertEqual(friends.person({'steamid':FIRST,'personaname':'Private profile'})['group'],'unknown')
        self.assertEqual(friends.person(self.player(FIRST,state=4))['status'],'Snooze')
        for uri in ('http://avatars.steamstatic.com/a.jpg','https://steamstatic.com.evil.invalid/a.jpg','file:///etc/passwd','https://evil.invalid/a.jpg','https://avatars.steamstatic.com/a.jpg?key=secret'):
            self.assertEqual(friends.avatar_url(uri),'')

    def test_refresh_cache_grouping_and_failed_refresh_keep_last_snapshot(self):
        self.config()
        replies = [{'friendslist':{'friends':[{'steamid':FIRST,'relationship':'friend'},{'steamid':SECOND,'relationship':'friend'}]}},
                   {'response':{'players':[self.player(),self.player(FIRST,'Game friend',1,'Test Game'),self.player(SECOND,'Offline friend',0)]}}]
        with patch.object(friends,'api',side_effect=replies) as api:
            result = friends.refresh()
        self.assertEqual([p['group'] for p in result['friends']],['in_game','offline'])
        self.assertNotIn(KEY,json.dumps(result))
        self.assertEqual(api.call_count,2)
        with patch.object(friends,'api') as api:
            self.assertFalse(friends.refresh()['stale'])
            api.assert_not_called()
        snapshot = friends.read_snapshot(OWNER)
        snapshot['updated_at'] = int(time.time())-60
        friends.atomic_json(friends.snapshot_path(OWNER),snapshot)
        with patch.object(friends,'api',side_effect=friends.FriendsError('Network unavailable.')):
            stale=friends.refresh(True)
        self.assertTrue(stale['stale'])
        self.assertEqual(stale['friends'],result['friends'])
        self.assertEqual(stale['error'],'Network unavailable.')

    def test_different_local_account_never_displays_old_friends(self):
        self.config()
        with patch.object(friends,'current_profile',return_value={'steamid':SECOND,'name':'Another profile','avatar':''}), patch.object(friends,'api') as api:
            result=friends.refresh()
        self.assertFalse(result['configured'])
        self.assertEqual(result['friends'],[])
        api.assert_not_called()

    def test_private_list_no_fake_offline_friends(self):
        self.config()
        with patch.object(friends,'api',side_effect=friends.FriendsError('Friends List is private.')):
            result=friends.refresh(True)
        self.assertTrue(result['configured'])
        self.assertTrue(result['stale'])
        self.assertEqual(result['friends'],[])
        self.assertEqual(result['error'],'Friends List is private.')

    def test_chat_validates_membership_and_never_sends_messages(self):
        self.config()
        friends.atomic_json(friends.snapshot_path(OWNER),{'version':1,'steamid':OWNER,'friends':[{'steamid':FIRST}],'updated_at':int(time.time())})
        with patch('steam_backend.dispatch',return_value={'submitted':True}) as dispatch, patch('steam_backend.focus_client',return_value=True):
            self.assertTrue(friends.chat(FIRST)['submitted'])
            self.assertEqual(dispatch.call_args.args[0],'steam://friends/message/'+FIRST)
            with self.assertRaises(friends.FriendsError):friends.chat(SECOND)
            with self.assertRaises(friends.FriendsError):friends.chat('malformed')
            self.assertEqual(dispatch.call_count,1)

    def test_disconnect_only_removes_friends_data(self):
        self.config()
        friends.atomic_json(friends.snapshot_path(OWNER),{'version':1,'steamid':OWNER,'friends':[],'updated_at':int(time.time())})
        unrelated=friends.cache_dir()/'unrelated.json'
        unrelated.write_text('{"keep":true}')
        result=friends.disconnect()
        self.assertFalse(result['configured'])
        self.assertFalse(friends.credential_path().exists())
        self.assertFalse(friends.snapshot_path(OWNER).exists())
        self.assertTrue(unrelated.exists())


if __name__=='__main__':unittest.main()
