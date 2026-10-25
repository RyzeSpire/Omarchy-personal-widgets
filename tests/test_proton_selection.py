"""Synthetic server fixtures; never connects or reads the real account cache."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import contextlib
import io

ROOT = Path(__file__).resolve().parents[1] / 'vendor/io.github.grichard99.omaproton-vpn'
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('proton_selection', ROOT / 'connect.py')
selection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selection)


def server(name, code, score=2, features=0, tier=0, entry=None, status=1):
    return dict(Name=name, ExitCountry=code, EntryCountry=entry or code, Score=score,
                Features=features, Tier=tier, Status=status, City='Fixture')


class ProtonSelection(unittest.TestCase):
    def data(self, *rows, tier=2):
        return dict(MaxTier=tier, LogicalServers=list(rows))

    def test_fastest_and_repeated_random_never_choose_brazil(self):
        data = self.data(server('BR#1','BR',0), server('US#1','US',1), server('NL#1','NL',3))
        self.assertEqual(selection.select_server(data, [], {'BR'}), 'US#1')
        for _ in range(100):
            self.assertNotEqual(selection.select_server(data, ['--random'], {'BR'}), 'BR#1')

    def test_explicit_country_server_and_saved_args_rejected(self):
        data = self.data(server('BR#1','BR'), server('US#1','US'))
        for args in (['--country','BR'], ['BR#1'], ['--country','br','--p2p']):
            with self.subTest(args=args), self.assertRaises(ValueError):
                selection.select_server(data, args, {'BR'})

    def test_secure_core_entry_and_exit_are_both_checked(self):
        data = self.data(server('CH-BR#1','BR',0,1,entry='CH'),server('BR-US#1','US',0,1,entry='BR'),server('CH-US#1','US',2,1,entry='CH'))
        self.assertEqual(selection.select_server(data, ['--securecore'], {'BR'}), 'CH-US#1')
        for name in ('CH-BR#1','BR-US#1'):
            with self.assertRaises(ValueError): selection.select_server(data,[name],{'BR'})

    def test_feature_tier_status_and_location_constraints(self):
        data=self.data(server('US#1','US',0,tier=2),server('US#2','US',1,4),server('NL#1','NL',0,4,status=0),tier=0)
        self.assertEqual(selection.select_server(data,['--p2p','--country','US'],{'BR'}),'US#2')
        for args in (['--tor'],['--country','NL'],['US#1'],['--city','Missing']):
            with self.assertRaises(ValueError): selection.select_server(data,args,{'BR'})

    def test_missing_invalid_or_blocked_only_cache_fails_closed(self):
        for data in (None,{},self.data(server('BR#1','BR')),self.data(server('US#1','US',status=0))):
            with self.assertRaises(ValueError): selection.select_server(data,[],{'BR'})
        with self.assertRaises(ValueError): selection.select_server(self.data(server('US#1','US')),['--unsupported'],{'BR'})

    def test_blocked_main_never_invokes_cli(self):
        with patch.object(selection, 'read_cache', return_value=self.data(server('BR#1','BR'))), patch.object(sys, 'argv', ['connect.py','--blocked','BR','--','BR#1']), patch.object(selection.subprocess,'run') as run, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(selection.main(), 2)
            run.assert_not_called()

    def test_fastest_invokes_only_the_selected_allowed_name(self):
        data=self.data(server('BR#1','BR',0),server('US#1','US',1))
        with patch.object(selection, 'read_cache', return_value=data), patch.object(sys, 'argv', ['connect.py','--blocked','BR','--']), patch.object(selection.subprocess,'run') as run:
            run.return_value.returncode=0
            self.assertEqual(selection.main(),0)
            run.assert_called_once_with(['protonvpn','connect','US#1'],check=False)
