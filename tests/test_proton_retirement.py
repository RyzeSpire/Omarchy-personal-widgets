"""Retired widget migration: temporary homes, no app/network/session calls."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import manage


class ProtonRetirement(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='proton retirement ')
        self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)/'home with spaces';self.home.mkdir()
        self.state=self.home/'.local/state/omarchy-personal-widgets'
        self.relative='.config/omarchy/plugins/'+manage.RETIRED_PROTON_WIDGET+'/Panel.qml'
        self.old=self.home/self.relative;self.old.parent.mkdir(parents=True);self.old.write_bytes(b'original widget')
        self.proton=self.home/'.config/Proton/VPN/settings.json';self.proton.parent.mkdir(parents=True);self.proton.write_bytes(b'{"account_state":"private fixture","features":{"split_tunneling":{}}}')
        self.widget_state=self.home/'.local/state/omarchy-protonvpn/state.json';self.widget_state.parent.mkdir(parents=True);self.widget_state.write_text('{"autoConnect":true}')

    def test_plan_is_read_only_and_omits_old_widget(self):
        plan=manage.install_plan(self.home,'DP-2',{'widgets'})
        self.assertFalse(any(manage.RETIRED_PROTON_WIDGET in key for key in plan))
        self.assertTrue(self.old.exists())
        self.assertTrue(self.widget_state.exists())

    def test_upgrade_repeat_and_uninstall_never_resurrect_widget(self):
        saved=json.loads((manage.ROOT/'config/shell.json').read_text())
        original={'plugins':[manage.RETIRED_PROTON_WIDGET,'personal.other'], 'bar':{'layout':{'right':[{'id':manage.RETIRED_PROTON_WIDGET},{'id':'personal.other'}]}}}
        shell=self.home/'.config/omarchy/shell.json';shell.parent.mkdir(parents=True,exist_ok=True);shell.write_text(json.dumps(original))
        private=self.proton.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            manage.apply_files(self.home,self.state,{self.relative:(b'previous installation',0o644)})
            for _ in range(2):
                manage.apply_files(self.home,self.state,{'.config/omarchy/shell.json':(manage.json_bytes(manage.merge_shell(original,saved)),0o600)})
                manage.retire_proton_widget(self.home,self.state)
            self.assertEqual(manage.remove_files(self.home,self.state,True),0)
        self.assertFalse(self.old.exists())
        self.assertFalse(self.widget_state.exists())
        restored=json.loads(shell.read_text())
        self.assertEqual(restored['plugins'],['personal.other'])
        self.assertEqual(restored['bar']['layout']['right'],[{'id':'personal.other'}])
        self.assertEqual(self.proton.read_bytes(),private)
        self.assertTrue(list((self.state/'history').glob('retire-proton-widget-*/plugin/Panel.qml')))

    def test_dictionary_preferences_preserve_unrelated_entries(self):
        data={'plugins':{manage.RETIRED_PROTON_WIDGET:False,'personal.other':{'enabled':True}},'bar':{'layout':{'left':[]}}}
        self.assertEqual(manage.strip_retired_widgets(data)['plugins'],{'personal.other':{'enabled':True}})
