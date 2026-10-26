"""Regression tests for the friend-agent backup and recovery workflow."""
import copy, json, unittest
from unittest import mock
import test_x10 as fixtures
from test_x10 import x10

PKG, OEM, OTHER_HOME = fixtures.PKG, fixtures.OEM, fixtures.OTHER_HOME

class ReviewTests(unittest.TestCase):
    setUp = fixtures.TrialTests.setUp
    quiet = fixtures.TrialTests.quiet
    actions = fixtures.TrialTests.actions
    def apply(self): return self.quiet(x10.apply, self.d, self.folder, self.data, self.actions(), True)
    def restore(self): return self.quiet(x10.restore, self.d, self.folder, self.data, True)
    def assert_blocked(self, operation):
        with self.assertRaises(RuntimeError): operation()
        self.assertEqual(self.d.writes, [])
    def test_non_owner_android_user_blocked(self):
        self.d.user = '10'; self.assert_blocked(self.apply)
    def test_updated_target_blocked_before_any_write(self):
        self.d.hashes[PKG] = 'b'*64; self.assert_blocked(self.apply)
    def test_unreviewed_target_version_with_valid_backup_blocked(self):
        mock.patch.dict(x10.PROFILE['optional_apk_sha256'], {PKG: ['b'*64]}).start()
        self.assert_blocked(self.apply)
    def test_disabled_core_blocks_cleanup(self):
        self.d.state['com.zh.zhpower'] = 3; self.assert_blocked(self.apply)
    def test_hidden_or_suspended_core_blocks_cleanup(self):
        for field in (self.d.hidden, self.d.suspended):
            field['com.zhonghong.camera'] = True
            self.assert_blocked(self.apply)
            field.clear()
    def test_missing_required_core_blocks_cleanup(self):
        del self.d.state['com.android.phone']; self.assert_blocked(self.apply)
    def test_post_apply_regression_retains_journal_for_rollback(self):
        self.d.after_write = lambda: self.d.state.update({'com.zhonghong.camera': 3 if self.d.state[PKG] == 3 else 0})
        with self.assertRaises(RuntimeError): self.apply()
        report = json.loads((self.folder/'after-apply.json').read_text())
        self.assertFalse(report['software_checks_passed'])
        self.restore()
        self.assertEqual(self.d.state['com.zhonghong.camera'], 0)
    def test_modified_snapshot_rejected_by_existing_journal(self):
        self.apply(); self.data['home'] = x10.component(x10.HOMES['lawnchair'])
        self.d.writes.clear(); self.assert_blocked(self.restore)
    def test_incomplete_snapshot_cannot_verify(self):
        self.data['complete'] = False
        with self.assertRaises(RuntimeError): x10.verify_snapshot(self.folder, self.data)
    def test_missing_package_inventory_cannot_verify(self):
        del self.data['packages']['com.android.phone']
        with self.assertRaises(RuntimeError): x10.verify_snapshot(self.folder, self.data)
    def test_metadata_only_snapshot_cannot_verify_or_apply(self):
        self.data['apks_copied'] = False
        self.assert_blocked(self.apply)
        with self.assertRaises(RuntimeError): x10.verify_snapshot(self.folder, self.data)
    def test_missing_original_home_apk_cannot_verify(self):
        self.data['packages']['com.android.launcher3']['files'][0].pop('local')
        with self.assertRaises(RuntimeError): x10.verify_snapshot(self.folder, self.data)
    def test_corrupt_evidence_cannot_verify(self):
        self.data['evidence'] = {'power': {'local': 'missing.txt', 'sha256': 'b'*64}}
        with self.assertRaises(RuntimeError): x10.verify_snapshot(self.folder, self.data)
    def test_null_setting_is_deleted_on_restore(self):
        self.data['settings']['secure']['screensaver_enabled'] = 'null'
        self.d.settings['screensaver_enabled'] = 'null'
        self.apply(); self.restore()
        self.assertEqual(self.d.settings['screensaver_enabled'], 'null')
    def test_empty_plan_does_not_consume_snapshot(self):
        self.quiet(x10.apply, self.d, self.folder, self.data, [], True)
        self.assertFalse((self.folder/'trial-journal.json').exists())
    def test_home_switch_and_restore_keep_actual_original(self):
        self.data['home'] = OTHER_HOME; self.d.current_home = OTHER_HOME
        self.data['packages']['org.example.home'] = self.d.package('org.example.home')
        self.data['packages']['org.example.home']['files'][0]['local'] = 'app.apk'
        self.quiet(x10.switch_home, self.d, self.folder, self.data, 'x10', True)
        self.assertEqual(self.d.home(), x10.component(x10.HOMES['x10']))
        self.restore()
        self.assertEqual(self.d.home(), OTHER_HOME)
    def test_home_launch_failure_is_recoverable(self):
        self.d.launch_error = True
        with self.assertRaises(RuntimeError): self.quiet(x10.switch_home, self.d, self.folder, self.data, 'x10', True)
        record = json.loads((self.folder/'home-journal.json').read_text())
        self.assertTrue(record['attempted']); self.assertNotIn('verified', record)
        self.d.launch_error = False
        self.quiet(x10.switch_home, self.d, self.folder, self.data, 'original', True)
        self.assertEqual(self.d.home(), OEM)
    def test_home_preview_does_not_write_or_create_journal(self):
        self.quiet(x10.switch_home, self.d, self.folder, self.data, 'x10', False)
        self.assertEqual(self.d.writes, [])
        self.assertFalse((self.folder/'home-journal.json').exists())
    def test_non_home_activity_rejected_before_home_change(self):
        self.d.homes = lambda: {OEM}
        self.assert_blocked(lambda: self.quiet(x10.switch_home, self.d, self.folder, self.data, 'x10', True))
    def test_home_restore_stops_on_manual_home_drift(self):
        self.quiet(x10.switch_home, self.d, self.folder, self.data, 'x10', True)
        self.d.current_home = OTHER_HOME; self.d.writes.clear(); self.assert_blocked(self.restore)
    def test_lawnchair_export_required_before_switch(self):
        self.data['home'] = x10.component(x10.HOMES['lawnchair']); self.d.current_home = self.data['home']
        self.assert_blocked(lambda: self.quiet(x10.switch_home, self.d, self.folder, self.data, 'x10', True))
    def test_export_hash_and_native_extension_preserved(self):
        source = self.folder/'native.lawnchairbackup'; source.write_bytes(b'owner export')
        self.quiet(x10.attach_export, self.folder, self.data, source)
        self.assertTrue(self.data['launcher_export']['local'].endswith('.lawnchairbackup'))
        x10.verify_snapshot(self.folder, self.data)
        (self.folder/self.data['launcher_export']['local']).write_bytes(b'bad')
        with self.assertRaises(RuntimeError): x10.verify_snapshot(self.folder, self.data)
    def test_export_cannot_be_overwritten_or_added_after_trial(self):
        source = self.folder/'native.backup'; source.write_bytes(b'owner export')
        self.quiet(x10.attach_export, self.folder, self.data, source)
        with self.assertRaises(RuntimeError): x10.attach_export(self.folder, self.data, source)
        self.data.pop('launcher_export'); self.apply()
        with self.assertRaises(RuntimeError): x10.attach_export(self.folder, self.data, source)
    def test_snapshot_pulls_original_third_party_home_and_verifies(self):
        self.d.current_home = OTHER_HOME
        dest = self.folder/'new'
        data = self.quiet(x10.snapshot, self.d, dest, True)
        self.assertTrue(data['complete']); self.assertEqual(data['home'], OTHER_HOME)
        self.assertTrue(data['packages']['org.example.home']['files'][0].get('local'))
        x10.verify_snapshot(dest, data)
        self.assertEqual(self.d.writes, [])
    def test_snapshot_failure_remains_unusable_then_resumes(self):
        dest = self.folder/'partial'; original = self.d.run
        self.d.run = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError('transfer failed'))
        with self.assertRaises(RuntimeError): self.quiet(x10.snapshot, self.d, dest, True)
        self.assertFalse(x10.load_snapshot(dest)['complete'])
        self.d.run = original
        data = self.quiet(x10.snapshot, self.d, dest, True, (), True)
        x10.verify_snapshot(dest, data)
    def test_sim_warning_does_not_claim_physical_feature_success(self):
        self.d.sim = 'ABSENT,ABSENT'
        report = x10.health(self.d, self.data)
        self.assertTrue(report['warnings']); self.assertIsNone(report['physical_feature_tests_passed'])
    def test_package_query_error_is_not_treated_as_app_absence(self):
        real = x10.Device('unused-adb', 'unused-serial')
        real.shell = lambda *a: 'Permission Denial: cannot dump package state'
        with self.assertRaises(RuntimeError): real.package(PKG)
    def test_package_query_recognizes_real_absence(self):
        real = x10.Device('unused-adb', 'unused-serial')
        real.shell = lambda *a: 'Unable to find package: '+PKG
        self.assertFalse(real.package(PKG)['present'])
    def test_home_only_restore_can_be_repeated(self):
        self.quiet(x10.switch_home, self.d, self.folder, self.data, 'x10', True)
        self.restore(); self.d.writes.clear(); self.restore()
        self.assertEqual(self.d.home(), OEM)
        self.assertEqual(self.d.writes, [])
    def test_snapshot_rejects_resolver_instead_of_real_home(self):
        self.d.current_home = 'android/com.android.internal.app.ResolverActivity'
        with self.assertRaises(RuntimeError): self.quiet(x10.snapshot, self.d, self.folder/'resolver', True)
        self.assertEqual(self.d.writes, [])
    def test_split_apks_are_all_saved_and_verified(self):
        original = self.d.package
        def package(name):
            entry = original(name)
            if name == PKG:
                split = copy.deepcopy(entry['files'][0]); split['remote'] = '/apps/split_config.en.apk'
                entry['files'].append(split)
            return entry
        self.d.package = package
        dest = self.folder/'split-snapshot'
        data = self.quiet(x10.snapshot, self.d, dest, True)
        self.assertEqual(len(data['packages'][PKG]['files']), 2)
        x10.verify_snapshot(dest, data)
    def test_complete_agent_cli_sequence_with_fake_adb(self):
        dest = self.folder/'agent-sequence'
        export = self.folder/'original.lawnchairbackup'; export.write_bytes(b'original native export')
        def cli(*args):
            return self.quiet(x10.main, ['--serial', 'test-device', *map(str, args)])
        with mock.patch.object(x10, 'Device', return_value=self.d):
            cli('audit')
            cli('snapshot', '--out', dest, '--with-apks')
            cli('attach-export', '--snapshot', dest, '--file', export)
            cli('verify', '--snapshot', dest)
            cli('check', '--snapshot', dest, '--out', self.folder/'before.json')
            cli('apply', '--snapshot', dest, '--packages', PKG, '--screensaver')
            self.assertEqual(self.d.writes, [])
            cli('apply', '--snapshot', dest, '--packages', PKG, '--screensaver', '--execute')
            cli('home', 'x10', '--snapshot', dest, '--execute')
            cli('restore', '--snapshot', dest)
            cli('restore', '--snapshot', dest, '--execute')
            cli('check', '--snapshot', dest, '--out', self.folder/'after.json')
        self.assertEqual(self.d.home(), OEM)
        self.assertEqual(self.d.state[PKG], 0)
        self.assertEqual(set(self.d.settings.values()), {'1'})
    def test_target_update_between_preflight_and_write_is_blocked(self):
        original = self.d.package
        calls = 0
        def package(name):
            nonlocal calls
            entry = original(name)
            if name == PKG:
                calls += 1
                if calls >= 3: entry['files'][0]['sha256'] = 'b'*64
            return entry
        self.d.package = package
        self.assert_blocked(self.apply)
        journal = json.loads((self.folder/'trial-journal.json').read_text())
        self.assertFalse(any(a.get('attempted') for a in journal['actions']))
    def test_check_cannot_overwrite_snapshot_or_existing_report(self):
        path = self.folder/'snapshot.json'; before = path.read_bytes()
        with mock.patch.object(x10, 'Device', return_value=self.d):
            self.assert_blocked(lambda: self.quiet(x10.main, ['--serial', 'test-device', 'check', '--snapshot', str(self.folder), '--out', str(path)]))
        self.assertEqual(path.read_bytes(), before)

if __name__ == '__main__': unittest.main()
