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

    def test_personal_addon_and_launcher_cannot_return_after_uninstall(self):
        relative='.config/omarchy/plugins/ryze.proton-vpn/ProtonWidget.qml'
        addon=self.home/relative;addon.parent.mkdir(parents=True);addon.write_bytes(b'older addon')
        launcher_relative='.local/share/applications/proton.vpn.app.gtk.desktop'
        launcher=self.home/launcher_relative;launcher.parent.mkdir(parents=True)
        original=b'[Desktop Entry]\nExec=protonvpn-app --start-minimized\n'
        launcher.write_bytes(original)
        shell=self.home/'.config/omarchy/shell.json';shell.parent.mkdir(parents=True,exist_ok=True)
        shell.write_text(json.dumps({'bar':{'layout':{'center':[{'id':'ryze.proton-vpn'},{'id':'personal.other'}]}},'plugins':['ryze.proton-vpn','personal.other']}))
        private=self.proton.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            manage.apply_files(self.home,self.state,{relative:(b'current addon',0o644),launcher_relative:(b'Exec=python3 proton_widget_app.py',0o644),'.config/omarchy/shell.json':(b'{"bar":{"layout":{}}}',0o600)})
            manage.retire_proton_widget(self.home,self.state)
            manage.retire_proton_widget(self.home,self.state)
            self.assertEqual(manage.remove_files(self.home,self.state,True),0)
        self.assertFalse(addon.exists())
        self.assertEqual(launcher.read_bytes(),original)
        restored=json.loads(shell.read_text())
        self.assertEqual(restored['plugins'],['personal.other'])
        self.assertEqual(restored['bar']['layout']['center'],[{'id':'personal.other'}])
        self.assertEqual(self.proton.read_bytes(),private)

    def test_current_payload_has_only_native_proton(self):
        plan=manage.install_plan(self.home,'DP-2',{'widgets'})
        self.assertFalse(any('ryze.proton-vpn' in key for key in plan))
        self.assertNotIn('.local/share/applications/proton.vpn.app.gtk.desktop',plan)
        self.assertFalse((manage.ROOT/'plugins/ryze.proton-vpn').exists())

    def test_unrelated_personal_launcher_is_preserved(self):
        launcher=self.home/'.local/share/applications/proton.vpn.app.gtk.desktop'
        launcher.parent.mkdir(parents=True);launcher.write_bytes(b'Exec=my-proton-launcher')
        with contextlib.redirect_stdout(io.StringIO()):manage.retire_proton_widget(self.home,self.state)
        self.assertEqual(launcher.read_bytes(),b'Exec=my-proton-launcher')

    def test_recorded_flags_restore_only_proton_tunnels(self):
        a='00000000-0000-4000-8000-000000000001'
        b='00000000-0000-4000-8000-000000000002'
        c='00000000-0000-4000-8000-000000000003'
        backup=self.home/'flags.json';backup.write_text(json.dumps({a:True,b:True,c:True}))
        calls=[]
        def command(args):
            if args[0]=='-t':return '\n'.join([a+':wireguard:no:ProtonVPN TEST#1',b+':dummy:no:pvpn-killswitch',c+':vpn:no:Office VPN'])
            calls.append(args);return ''
        self.assertEqual(manage.restore_proton_profile_flags(backup,command),1)
        self.assertEqual(calls,[['connection','modify','uuid',a,'connection.autoconnect','yes']])
        self.assertFalse(backup.exists())
