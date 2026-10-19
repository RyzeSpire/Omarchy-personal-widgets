"""Game-details verification: temporary fixtures, mocked API and native actions."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import steam_game_info as game
import steam_friends as account

OWNER=str(account.BASE_ID+1)
FRIEND=str(account.BASE_ID+2)
PRIVATE=str(account.BASE_ID+3)


class GameInfoTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='steam-game-info-test-')
        self.addCleanup(temp.cleanup)
        self.base=Path(temp.name)
        self.root=self.base/'Steam'
        self.config=self.root/'userdata/1/config'
        self.config.mkdir(parents=True)
        self.fixture={'appid':'123','name':'Test Game','installed':False,'favorite':False,'type':'game','size':0,'last_played':0,'artwork':''}
        self.catalog={'catalog':[self.fixture],'collections':[{'id':'test','name':'My games','appids':['123']}]}
        for mock in (patch.dict(os.environ,{'XDG_CACHE_HOME':str(self.base/'cache'),'XDG_CONFIG_HOME':str(self.base/'settings')}),
                     patch.object(game.desktop,'library',side_effect=lambda:self.catalog),
                     patch.object(game.desktop,'steam_roots',return_value=[self.root]),
                     patch.object(account,'current_profile',return_value={'steamid':OWNER,'name':'Test profile'})):
            mock.start();self.addCleanup(mock.stop)
        (self.config/'localconfig.vdf').write_text('"UserLocalConfigStore" {"Software" {"Valve" {"Steam" {"apps" {"123" {"Playtime" "755" "LastPlayed" "1658779095"}}}}}}')

    def local_achievements(self):
        cache=self.config/'librarycache/123.json'
        cache.parent.mkdir(exist_ok=True)
        cache.write_text(json.dumps([['achievements',{'data':{'nTotal':58,'nAchieved':0,'vecUnachieved':[{'strID':'a','strName':'Test achievement','strDescription':'Finish a test','strImage':'https://shared.steamstatic.com/a.jpg','bAchieved':False}]}}]])+json.dumps(['descriptions',{'data':{'strSnippet':'A short description.'}}])+']')

    def test_local_history_artwork_and_partial_cache_records(self):
        self.local_achievements()
        image=self.root/'appcache/librarycache/123/hash/library_hero.jpg'
        image.parent.mkdir(parents=True);image.write_bytes(b'fixture')
        info=game.local_info('123')
        self.assertEqual(info['playtime_minutes'],755)
        self.assertEqual(info['last_played'],1658779095)
        self.assertEqual(info['achievements']['total'],58)
        self.assertEqual(info['achievements']['unlocked'],0)
        self.assertEqual(info['description'],'A short description.')
        self.assertEqual(info['hero'],image.as_uri())
        self.assertEqual(info['collections'],['My games'])
        with self.assertRaises(ValueError):game.local_info('999')

    def test_unknown_progress_and_missing_history_are_not_zero(self):
        (self.config/'localconfig.vdf').write_text('"UserLocalConfigStore" {}')
        info=game.local_info('123')
        self.assertIsNone(info['playtime_minutes'])
        self.assertIsNone(info['last_played'])
        self.assertFalse(info['achievements']['available'])
        self.assertIsNone(info['achievements']['unlocked'])

    def test_plain_text_and_image_allowlist(self):
        self.assertEqual(game.text('<p>Safe <b>text</b></p><script>hidden()</script>'),'Safe text')
        self.assertEqual(game.image_url('https://evil.invalid/a.jpg'),'')
        self.assertEqual(game.image_url('file:///etc/passwd'),'')
        self.assertEqual(game.image_url('https://shared.steamstatic.com/a.jpg?t=1'),'https://shared.steamstatic.com/a.jpg')
        self.assertEqual(game.image_url('https://steamcdn-a.akamaihd.net/steamcommunity/public/images/apps/123/test.jpg'),'https://shared.fastly.steamstatic.com/community_assets/images/apps/123/test.jpg')

    def test_owned_game_service_uses_json_filter_and_privacy_unknown(self):
        with patch.object(account,'api',return_value={'response':{'game_count':1,'games':[{'appid':123,'playtime_forever':755}]}}) as api:
            record,visible=game.owned_game('mock-key',OWNER,'123')
        params=json.loads(api.call_args.args[2]['input_json'])
        self.assertEqual(params['appids_filter'],[123])
        self.assertEqual(params['steamid'],OWNER)
        self.assertEqual(record['playtime_forever'],755)
        self.assertTrue(visible)
        with patch.object(account,'api',return_value={'response':{}}):
            self.assertEqual(game.owned_game('mock-key',OWNER,'123'),(None,False))
        with patch.object(account,'api',return_value={'response':{'game_count':0}}):
            self.assertEqual(game.owned_game('mock-key',OWNER,'123'),(None,True))

    def test_achievements_private_failure_does_not_fabricate_unlocks(self):
        responses=[{'game':{'availableGameStats':{'achievements':[{'name':'secret','displayName':'Spoiler','description':'Spoiler description','hidden':1,'icon':'https://shared.steamstatic.com/a.jpg','icongray':'https://shared.steamstatic.com/b.jpg'}]}}},
                   {'playerstats':{'success':True,'achievements':[{'apiname':'secret','achieved':0}]}}]
        with patch.object(account,'api',side_effect=responses):
            result=game.achievements('123',{'steamid':OWNER},'mock-key')
        self.assertEqual(result['items'][0]['name'],'Hidden achievement')
        self.assertEqual(result['items'][0]['description'],'')
        self.assertEqual(result['total'],1)
        self.assertEqual(result['unlocked'],0)
        with patch.object(account,'api',return_value={'playerstats':{'success':False}}):
            with self.assertRaises(account.FriendsError):game.achievements('123',{'steamid':OWNER},'mock-key')

    def test_info_falls_back_to_cache_when_api_fails(self):
        self.local_achievements()
        with (patch.object(game,'current_api',return_value=({'steamid':OWNER},'mock-key')),
             patch.object(game,'public_store',return_value={'description':'Store description','features':['Single-player']}),
             patch.object(game,'own_stats',side_effect=account.FriendsError('Private history')),
             patch.object(game,'achievements',side_effect=account.FriendsError('Private progress'))):
            result=game.info('123')
        self.assertEqual(result['playtime_minutes'],755)
        self.assertEqual(result['achievements']['total'],58)
        self.assertEqual(result['achievements']['source'],'local_cache')
        self.assertEqual(result['description'],'Store description')
        self.assertNotIn('mock-key',json.dumps(result))
        self.fixture['favorite']=True
        with patch.object(game,'current_api',return_value=({'steamid':OWNER},'mock-key')),patch.object(game,'public_store',return_value={}):
            self.assertTrue(game.info('123')['favorite'])

    def test_friends_who_play_distinguishes_private_and_unowned(self):
        account.atomic_json(account.snapshot_path(OWNER),{'version':1,'steamid':OWNER,'friends':[{'steamid':FRIEND,'name':'A friend','avatar':'','group':'online','game':''},{'steamid':PRIVATE,'name':'Private friend','avatar':'','group':'offline','game':''}], 'updated_at':1})
        def owned(key,who,appid):
            return ({'playtime_forever':22,'rtime_last_played':1658779095},True) if who==FRIEND else (None,False)
        with patch.object(game,'current_api',return_value=({'steamid':OWNER},'mock-key')),patch.object(game,'owned_game',side_effect=owned):
            result=game.friends_who_play('123')
        self.assertTrue(result['loaded'])
        self.assertEqual(result['entries'][0]['activity'],'Played previously')
        self.assertEqual(result['entries'][0]['playtime_minutes'],22)
        self.assertEqual(result['unavailable'],1)

    def test_native_actions_mocked_no_downloads_or_launches(self):
        with patch.object(game.desktop,'dispatch',return_value={'submitted':True}) as dispatch,patch.object(game.desktop,'focus_client',return_value=True):
            game.action('123','install')
            self.assertEqual(dispatch.call_args.args[0],'steam://install/123')
            game.action('123','community')
            self.assertEqual(dispatch.call_args.args[0],'steam://openurl/https://steamcommunity.com/app/123/')
            game.action('123','achievements')
            self.assertEqual(dispatch.call_args.args[0],'steam://openurl/https://steamcommunity.com/profiles/'+OWNER+'/stats/123/?tab=achievements')
            with self.assertRaises(ValueError):game.action('123','uninstall')
            with self.assertRaises(ValueError):game.action('123;bad','install')
            self.assertEqual(dispatch.call_count,3)


if __name__=='__main__':unittest.main()
