"""Regression fixtures for native-Spotify local playlist support; no real audio/API."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/ryze.spotify'))
import spotify_playback as p
import spotify_desktop as d

LOCAL = 'spotify:local:Artist:Album:Song:226'
PLAYLIST = 'spotify:playlist:' + 'P' * 22
REMOTE = 'spotify:track:' + 'R' * 22


class PlaybackTests(unittest.TestCase):
    def test_local_and_remote_availability(self):
        self.assertTrue(p.track({'uri': LOCAL, 'is_local': True, 'is_playable': False})['playable'])
        self.assertTrue(p.track({'uri': LOCAL})['is_local'])
        self.assertFalse(p.track({'uri': REMOTE, 'is_playable': False})['playable'])
        self.assertTrue(p.track({'uri': REMOTE})['playable'])

    def test_only_spotify_track_identities(self):
        self.assertEqual(p.spotify_track_uri('https://open.spotify.com/local/Artist/Album/Song/226'), LOCAL)
        for value in ('file:///home/example/Music/song.mp3', '/home/example/song.mp3', 'https://evil.example/local/A/B/C/1', 'spotify:local:broken'):
            self.assertEqual(p.spotify_track_uri(value), '')
            self.assertFalse(p.track({'uri': value, 'is_local': True})['playable'])

    def test_old_cache_invalidated_and_positions_preserved(self):
        old = {'fetched_at': p.time.time(), 'playlist': {'name': 'Old'}}
        responses = [{'name': 'Jazz'}, {'items': [None, {'is_local': True, 'track': {'uri': LOCAL, 'duration_ms': 226000}}], 'total': 2, 'next': None}]
        with patch.object(p.api, 'read_state', return_value=old), patch.object(p.api, 'write_state') as save, patch.object(p.api, 'api_get', side_effect=responses):
            result = p.playlist(PLAYLIST)
            self.assertEqual(result['local_count'], 1)
            self.assertEqual(result['items'][0]['position'], 1)
            self.assertEqual(save.call_args.args[1]['format'], 2)

    def test_local_queue_does_not_claim_empty(self):
        state = {'item': {'uri': LOCAL, 'is_local': True}, 'context': {'uri': PLAYLIST}}
        with patch.object(p.api, 'status', return_value={'playback_connected': True}), patch.object(p.api, 'api_get', side_effect=[state, {}]), patch.object(p.api, 'read_state', return_value={}):
            result = p.queue()
            self.assertEqual(result['current']['uri'], LOCAL)
            self.assertTrue(result['local_queue_unavailable'])

    def test_queue_error_fallback_only_for_local(self):
        for uri, fallback in [(LOCAL, True), (REMOTE, False)]:
            with self.subTest(uri=uri), patch.object(p.api, 'status', return_value={'playback_connected': True}), patch.object(p.api, 'api_get', side_effect=[{'item': {'uri': uri}}, p.api.ApiError('Unavailable')]), patch.object(p.api, 'read_state', return_value={}):
                if fallback:
                    self.assertTrue(p.queue()['local_queue_unavailable'])
                else:
                    with self.assertRaises(p.api.ApiError): p.queue()

    def test_native_local_metadata(self):
        result = type('Result', (), {'stdout': json.dumps({'data': {'xesam:url': {'data': 'https://open.spotify.com/local/Artist/Album/Song/226'}}})})()
        with patch.object(d, 'run', return_value=result):
            self.assertEqual(p.local_track_uri(), LOCAL)

    def test_selection_keeps_spotify_context(self):
        with patch.object(p.api, 'status', return_value={'playback_connected': True}), patch.object(p, 'local_device', return_value={'id': 'device'}), patch.object(p.api, 'api_request') as request:
            p.play(PLAYLIST, 12)
            self.assertEqual(request.call_args.kwargs['body'], {'context_uri': PLAYLIST, 'position_ms': 0, 'offset': {'position': 12}})

    def test_queue_jump_uses_native_next_and_play(self):
        state = {'device': {'id': 'device'}}
        queue = {'currently_playing': {'uri': REMOTE}, 'queue': [{'uri': LOCAL}]}
        with patch.object(p.api, 'status', return_value={'playback_connected': True}), patch.object(p, 'local_device', return_value={'id': 'device'}), patch.object(p.api, 'api_get', side_effect=[state, queue]), patch.object(p, 'local_track_uri', side_effect=[REMOTE, LOCAL]), patch.object(d, 'run') as run, patch.object(p.time, 'sleep'):
            p.play_queue(LOCAL, 0)
            self.assertEqual([call.args[0][-1] for call in run.call_args_list], ['Next', 'Play'])
