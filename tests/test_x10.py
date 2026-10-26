"""Exercise mutation boundaries and rollback behavior without a real device."""
import contextlib, copy, io, json
from pathlib import Path
import sys, tempfile, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import x10

PKG = 'com.atoto.log.uploader'

class FakeDevice:
    def __init__(self):
        self.i = dict(x10.PROFILE['identity'], device_id_sha256='device-one')
        self.g = dict(x10.PROFILE['guard_apks'])
        self.state = {PKG: 0}
        self.settings = {k: '1' for k in x10.SETTINGS['secure'][:3]}
        self.writes = []
        self.fail_after_write = False
    def identity(self): return self.i
    def guards(self): return self.g
    compatible = x10.Device.compatible
    def package(self, name): return {'present': True, 'installed': True, 'enabled': self.state[name]}
    def shell(self, *args):
        if args[:2] == ('settings', 'get'): return self.settings[args[3]]
        self.writes.append(args)
        if args[0] == 'pm':
            self.state[args[-1]] = {v: k for k, v in x10.RESTORE.items()}[args[1]]
        elif args[:2] == ('settings', 'put'): self.settings[args[3]] = args[4]
        elif args[:2] == ('settings', 'delete'): self.settings[args[3]] = 'null'
        else: raise AssertionError(args)
        if self.fail_after_write: raise RuntimeError('Lost connection after device write')
        return ''

class TrialTests(unittest.TestCase):
    def setUp(self):
        temp_root = Path(__file__).resolve().parents[1]/'.local/tests'
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        # TemporaryDirectory cleanup is restricted to this newly allocated workspace child.
        self.assertTrue(Path(self.temp.name).resolve().is_relative_to(temp_root.resolve()))
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder/'app.apk').write_bytes(b'test-apk')
        self.d = FakeDevice()
        self.data = {'schema': 1, 'complete': True, 'identity': copy.deepcopy(self.d.i),
                     'guard_apks': dict(self.d.g), 'packages': {PKG: {'present': True, 'installed': True,
                     'enabled': 0, 'files': [{'local': 'app.apk', 'sha256': x10.digest(self.folder/'app.apk')}]}},
                     'settings': {'secure': dict(self.d.settings)}}
    def quiet(self, func, *args):
        with contextlib.redirect_stdout(io.StringIO()): return func(*args)
    def actions(self): return x10.plan(self.data, [PKG], True)
    def test_real_package_dump_states(self):
        self.assertEqual(x10.parse_package('  User 0: installed=false hidden=false stopped=true enabled=0 instant=false'),
                         {'installed': False, 'enabled': 0})
        self.assertIsNone(x10.parse_package('Unable to find package: missing'))
    def test_preview_has_no_device_writes_or_journal(self):
        self.quiet(x10.apply, self.d, self.folder, self.data, self.actions(), False)
        self.assertEqual(self.d.writes, [])
        self.assertFalse((self.folder/'trial-journal.json').exists())
    def test_apply_and_restore_original_values(self):
        self.quiet(x10.apply, self.d, self.folder, self.data, self.actions(), True)
        self.assertEqual(self.d.state[PKG], 3)
        self.assertEqual(set(self.d.settings.values()), {'0'})
        self.quiet(x10.restore, self.d, self.folder, self.data, True)
        self.assertEqual(self.d.state[PKG], 0)
        self.assertEqual(set(self.d.settings.values()), {'1'})
    def test_foreign_device_blocked_before_any_write(self):
        self.d.i['device_id_sha256'] = 'another-device'
        with self.assertRaises(RuntimeError): x10.apply(self.d, self.folder, self.data, self.actions(), True)
        self.assertEqual(self.d.writes, [])
    def test_changed_firmware_blocked_before_any_write(self):
        self.d.g[next(iter(self.d.g))] = 'changed'
        with self.assertRaises(RuntimeError): x10.apply(self.d, self.folder, self.data, self.actions(), True)
        self.assertEqual(self.d.writes, [])
    def test_corrupt_backup_blocked_before_any_write(self):
        (self.folder/'app.apk').write_bytes(b'corrupt')
        with self.assertRaises(RuntimeError): x10.apply(self.d, self.folder, self.data, self.actions(), True)
        self.assertEqual(self.d.writes, [])
    def test_snapshot_path_escape_rejected(self):
        self.data['packages'][PKG]['files'][0]['local'] = '../secret.apk'
        with self.assertRaises(RuntimeError): x10.verify_files(self.folder, self.data)
    def test_unselected_or_protected_package_rejected(self):
        with self.assertRaises(RuntimeError): x10.plan(self.data, ['com.zh.zhpower'], False)
        with self.assertRaises(RuntimeError): x10.plan(self.data, ['com.android.phone'], False)
    def test_drift_stops_entire_apply_before_writes(self):
        self.d.settings['screensaver_activate_on_sleep'] = 'null'
        with self.assertRaises(RuntimeError): x10.apply(self.d, self.folder, self.data, self.actions(), True)
        self.assertEqual(self.d.writes, [])
    def test_lost_connection_keeps_rollback_intent(self):
        self.d.fail_after_write = True
        with self.assertRaises(RuntimeError): self.quiet(x10.apply, self.d, self.folder, self.data, self.actions(), True)
        journal = json.loads((self.folder/'trial-journal.json').read_text())
        self.assertTrue(journal['actions'][0]['attempted'])
        self.assertNotIn('verified', journal['actions'][0])
        self.d.fail_after_write = False
        self.quiet(x10.restore, self.d, self.folder, self.data, True)
        self.assertEqual(self.d.state[PKG], 0)
    def test_restore_refuses_unexplained_state(self):
        self.quiet(x10.apply, self.d, self.folder, self.data, self.actions(), True)
        self.d.state[PKG] = 2
        self.d.writes.clear()
        with self.assertRaises(RuntimeError): x10.restore(self.d, self.folder, self.data, True)
        self.assertEqual(self.d.writes, [])
    def test_tampered_restore_cannot_target_core_package(self):
        self.quiet(x10.apply, self.d, self.folder, self.data, self.actions(), True)
        path = self.folder/'trial-journal.json'; j = json.loads(path.read_text())
        j['actions'][0]['package'] = 'com.android.phone'; x10.save(path, j)
        self.d.writes.clear()
        with self.assertRaises(RuntimeError): x10.restore(self.d, self.folder, self.data, True)
        self.assertEqual(self.d.writes, [])

if __name__ == '__main__': unittest.main()
