"""Host/transport simulations; no real head-unit writes or reboot in this suite."""
import contextlib
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import boot_logo as logo
from PIL import Image


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class FakeDevice:
    def __init__(self):
        self.raw = bytes(logo.PREFIX) + logo.bmp_bytes(3, 2, bytes(range(18)))
        self.raw += bytes(4 * 1024 * 1024 - len(self.raw))
        self.original = self.raw
        self.s = {'identity': dict(logo.x10.PROFILE['identity'], device_id_sha256='a' * 64),
                  'guards': dict(logo.x10.PROFILE['guard_apks']), 'hardware_config': '0400000000000000',
                  'rotated_panel': '12,', 'node': '/dev/block/sdz1', 'bytes': len(self.raw),
                  'enabled_packages': sorted(logo.x10.PROFILE['required_packages']),
                  'home': 'org.example.home/org.example.home.Home', 'boot_id': 'first-boot', 'sim_state': 'LOADED,ABSENT'}
        self.dirs, self.files, self.writes = set(), {}, []
        self.selected, self.bad_dialog, self.disconnect_after_confirm = False, False, False
        self.push_failure, self.read_failure = False, False

    def state(self): return copy.deepcopy(self.s)
    def partition_hash(self): return sha(self.raw)
    def read_partition(self, size):
        if self.read_failure: return self.raw[:-1]
        return self.raw
    def exists(self, remote): return remote in self.dirs or remote in self.files
    def listing(self, remote):
        prefix = remote + '/'
        return {p[len(prefix):].split('/')[0] for p in self.dirs | self.files.keys() if p.startswith(prefix)}
    def push(self, local, remote):
        self.writes.append(('push', remote))
        self.files[remote] = Path(local).read_bytes()
        if self.push_failure:
            self.files[remote] = b'incomplete'
            self.push_failure = False
            raise RuntimeError('Simulated Wi-Fi loss')
    def inflate(self, source, dest):
        self.writes.append(('inflate', dest))
        self.files[dest] = gzip.decompress(self.files[source])
    def ui(self, remote):
        extra = '<node package="com.zhonghong.update" resource-id="com.zhonghong.update:id/tip_info" enabled="true" text="Upgrade OS"/>' if self.bad_dialog else ''
        return ('<hierarchy><node package="com.zhonghong.update" resource-id="com.zhonghong.update:id/tip_info" enabled="true" text="Upgrade LOGO"/>'
                '<node package="com.zhonghong.update" resource-id="com.zhonghong.update:id/check_view" enabled="true" selected="' + str(self.selected).lower() + '" bounds="[10,10][20,20]"/>'
                '<node package="com.zhonghong.update" resource-id="com.zhonghong.update:id/update_confirm" enabled="true" bounds="[10,300][20,320]"/>' + extra + '</hierarchy>')
    def flash(self):
        path = next(k for k in self.files if k.endswith('/Upgrade/zh_logo.bmp'))
        # Independent Pillow encoding, checked against the public byte encoder.
        image = Image.open(io.BytesIO(self.files[path])).transpose(Image.Transpose.ROTATE_270)
        output = io.BytesIO(); image.save(output, format='BMP')
        bmp = bytearray(output.getvalue()); bmp[34:54] = bytes(20)
        payload = bytes(16384) + bmp
        self.raw = payload + self.raw[len(payload):]
        self.s['boot_id'] = 'second-boot'
        self.writes.append(('OEM_FLASH', logo.PROFILE['partition']))
    def root(self, *args):
        if args[0] == 'dd':
            self.writes.append(('RESTORE', args))
            source = next(x[3:] for x in args if x.startswith('if='))
            self.raw = self.files[source]
            return ''
        raise AssertionError(args)
    def shell(self, *args):
        args = tuple(map(str, args))
        if args[0] == 'sha256sum': return sha(self.files[args[1]]) + '  ' + args[1]
        self.writes.append(args)
        if args[0] == 'mkdir': self.dirs.add(args[1])
        elif args[0] == 'mv': self.files[args[2]] = self.files.pop(args[1])
        elif args[:2] == ('am', 'startservice'): pass
        elif args[:2] == ('input', 'tap'):
            if int(args[3]) < 200: self.selected = not self.selected
            else:
                self.flash()
                if self.disconnect_after_confirm: raise RuntimeError('Link closed during reboot')
        elif args == ('sync',): pass
        else: raise AssertionError(args)
        return ''


class LogoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.image, self.kit, self.folder = self.root/'own.png', self.root/'kit', self.root/'backup'
        Image.new('RGB', (8, 4), (190, 70, 20)).save(self.image)
        logo.prepare(self.image, self.kit, (16, 10))
        self.d = FakeDevice()
        logo.backup(self.d, self.folder)

    def stage(self): return logo.stage(self.d, self.folder, self.kit, True)
    def install(self): return logo.install(self.d, self.folder, True, True, True)
    def quiet_main(self, argv):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            logo.main(argv)
        return json.loads(out.getvalue())

    def test_bmp_padding_rotation_and_rgb_match_independent_decoder(self):
        pixels = bytes(range(18))
        raw = logo.bmp_bytes(3, 2, pixels)
        image = Image.open(io.BytesIO(raw))
        self.assertEqual(image.tobytes(), pixels)
        self.assertEqual(logo.read_bmp(raw), (3, 2, pixels))
        w, h, rotated = logo.rotate_clockwise(3, 2, pixels)
        self.assertEqual((w, h), (2, 3))
        self.assertEqual(rotated, image.transpose(Image.Transpose.ROTATE_270).tobytes())
    def test_prepare_letterboxes_and_flattens_transparency(self):
        image = self.root/'alpha.png'
        Image.new('RGBA', (8, 4), (255, 0, 0, 128)).save(image)
        out = self.root/'alpha-kit'; logo.prepare(image, out, (16, 16))
        preview = Image.open(out/'preview.png')
        self.assertEqual(preview.getpixel((0, 0)), (0, 0, 0))
        self.assertEqual(preview.getpixel((8, 8)), (128, 0, 0))
        with logo.zipfile.ZipFile(out/'logo-usb.zip') as archive:
            self.assertEqual(set(archive.namelist()), {'Upgrade/qcm6125_T10.txt', 'Upgrade/zh_logo.bmp'})
    def test_prepare_refuses_overwrite_invalid_size_and_animation(self):
        with self.assertRaises(RuntimeError): logo.prepare(self.image, self.kit)
        with self.assertRaises(RuntimeError): logo.prepare(self.image, self.root/'bad', (1281, 720))
        animated = self.root/'animated.webp'
        Image.new('RGB',(4,4),'red').save(animated, save_all=True, append_images=[Image.new('RGB',(4,4),'blue')], duration=100)
        with self.assertRaises(RuntimeError): logo.prepare(animated, self.root/'animated-kit')
    def test_malformed_bmp_headers_are_rejected(self):
        raw = bytearray((self.kit/'usb-root/Upgrade/zh_logo.bmp').read_bytes())
        for offset, value in [(28, 32), (30, 1), (10, 55)]:
            broken = raw.copy(); broken[offset] = value
            with self.assertRaises(RuntimeError): logo.read_bmp(broken)
        with self.assertRaises(RuntimeError): logo.read_bmp(raw[:-1])
    def test_backup_full_image_verified_without_device_writes(self):
        data = logo.verify_backup(self.folder)
        self.assertEqual(data['sha256'], sha(self.d.raw))
        self.assertEqual(self.d.writes, [])
    def test_incomplete_or_corrupt_backup_rejected(self):
        (self.folder/'splash.img').write_bytes(b'partial')
        with self.assertRaises(RuntimeError): self.stage()
        self.assertEqual(self.d.writes, [])
    def test_truncated_capture_never_becomes_a_verified_backup(self):
        self.d.read_failure = True
        out = self.root/'broken-backup'
        with self.assertRaises(RuntimeError): logo.backup(self.d, out)
        self.assertFalse((out/'backup.json').exists())
        self.assertFalse(json.loads((out/'capture-status.json').read_text())['complete'])
    def test_device_changes_during_backup_rejected(self):
        original = self.d.read_partition
        def changed(size):
            raw = original(size); self.d.s['boot_id'] = 'changed'; return raw
        self.d.read_partition = changed
        with self.assertRaises(RuntimeError): logo.backup(self.d, self.root/'changed-backup')
        self.assertEqual(self.d.writes, [])
    def test_compressed_image_limits_and_crc(self):
        with self.assertRaises(RuntimeError): logo.decompress(gzip.compress(bytes(100)), 99)
        with self.assertRaises((OSError, EOFError)): logo.decompress(gzip.compress(bytes(100))[:-2], 100)
    def test_corrupt_metadata_and_wrong_device_stop_before_staging(self):
        self.d.s['identity']['device_id_sha256'] = 'b'*64
        with self.assertRaises(RuntimeError): self.stage()
        self.assertEqual(self.d.writes, [])
        data = json.loads((self.folder/'backup.json').read_text()); data['state']['identity']['device_id_sha256'] = 'b'*64
        (self.folder/'backup.json').write_text(json.dumps(data))
        with self.assertRaises(RuntimeError): self.stage()
    def test_extra_firmware_file_in_kit_rejected(self):
        (self.kit/'usb-root/Upgrade/update.zip').write_bytes(b'not allowed')
        with self.assertRaises(RuntimeError): self.stage()
        self.assertEqual(self.d.writes, [])
    def test_stage_preview_never_writes_or_creates_journal(self):
        logo.stage(self.d, self.folder, self.kit)
        self.assertEqual(self.d.writes, [])
        self.assertFalse((self.folder/'logo-journal.json').exists())
    def test_interrupted_staging_resumes_same_owned_directory(self):
        self.d.push_failure = True
        with self.assertRaises(RuntimeError): self.stage()
        first = logo.trial(self.folder, logo.verify_backup(self.folder))
        self.stage()
        second = logo.trial(self.folder, logo.verify_backup(self.folder))
        self.assertEqual(first['remote'], second['remote'])
        self.assertTrue(second['staged'])
        self.assertEqual(self.d.raw, self.d.original)
        self.assertFalse(any(w[0] in ('am','OEM_FLASH','RESTORE') for w in self.d.writes))
    def test_unrecognized_remote_component_not_overwritten(self):
        self.stage(); r = logo.trial(self.folder, logo.verify_backup(self.folder))
        self.d.files[r['remote']+'/Upgrade/bt.bin'] = b'unknown'
        self.d.writes.clear()
        with self.assertRaises(RuntimeError): self.stage()
        self.assertEqual(self.d.writes, [])
    def test_install_preview_and_missing_reboot_authorization_do_not_write(self):
        self.stage(); self.d.writes.clear()
        logo.install(self.d, self.folder)
        for parked, restart in [(False,False),(True,False),(False,True)]:
            with self.assertRaises(RuntimeError): logo.install(self.d, self.folder, True, parked, restart)
        self.assertEqual(self.d.writes, [])
    def test_staged_file_tampering_blocks_install(self):
        self.stage(); r = logo.trial(self.folder, logo.verify_backup(self.folder))
        self.d.files[r['remote']+'/Upgrade/zh_logo.bmp'] = b'changed'
        self.d.writes.clear()
        with self.assertRaises(RuntimeError): self.install()
        self.assertEqual(self.d.writes, [])
    def test_other_update_component_in_ui_is_not_confirmed(self):
        self.stage(); self.d.bad_dialog = True
        with self.assertRaises(RuntimeError): self.install()
        self.assertEqual(self.d.raw, self.d.original)
        self.assertFalse(any(w[0]=='input' for w in self.d.writes))
        with self.assertRaises(RuntimeError): self.install()
    def test_install_verify_and_restore_full_image(self):
        self.stage(); self.install()
        result = logo.verify(self.d, self.folder)
        self.assertTrue(result['splash_verified'])
        self.assertIsNone(result['physical_confirmation'])
        self.assertNotEqual(self.d.raw, self.d.original)
        before = len(self.d.writes); logo.restore(self.d, self.folder)
        self.assertEqual(len(self.d.writes), before)
        with self.assertRaises(RuntimeError): logo.restore(self.d, self.folder, True, False)
        logo.restore(self.d, self.folder, True, True)
        self.assertEqual(self.d.raw, self.d.original)
        before = len(self.d.writes); logo.restore(self.d, self.folder, True, True)
        self.assertEqual(len(self.d.writes), before)
        writes = [w for w in self.d.writes if w[0]=='RESTORE']
        self.assertEqual(len(writes),1)
        self.assertIn('of=/dev/block/by-name/splash', writes[0][1])
    def test_lost_confirmation_ack_is_verified_without_replay(self):
        self.stage(); self.d.disconnect_after_confirm = True
        with self.assertRaises(RuntimeError): self.install()
        self.assertTrue(logo.verify(self.d,self.folder)['splash_verified'])
        before = len(self.d.writes)
        with self.assertRaises(RuntimeError): self.install()
        self.assertEqual(len(self.d.writes), before)
    def test_unknown_partition_blocks_automatic_restore(self):
        self.stage(); self.install(); self.d.raw = b'corrupt' + self.d.raw[7:]
        self.d.writes.clear()
        with self.assertRaises(RuntimeError): logo.restore(self.d, self.folder, True, True)
        self.assertEqual(self.d.writes, [])
    def test_home_regression_is_reported_without_resetting_home(self):
        self.stage(); self.install(); self.d.s['home'] = 'org.example.other/.Home'
        self.d.writes.clear()
        with self.assertRaises(RuntimeError): logo.verify(self.d, self.folder)
        self.assertEqual(self.d.writes, [])
        r = logo.trial(self.folder, logo.verify_backup(self.folder))
        self.assertIn('Default HOME changed', r['verification']['issues'])
    def test_backup_node_drift_blocks_restore(self):
        self.stage(); self.install(); self.d.s['node'] = '/dev/block/sdz2'; self.d.writes.clear()
        with self.assertRaises(RuntimeError): logo.restore(self.d, self.folder, True, True)
        self.assertEqual(self.d.writes, [])
    def test_full_cli_simulation_and_offline_verification(self):
        with mock.patch.object(logo, 'LogoDevice', return_value=self.d):
            prefix = ['--serial','explicit-unit']
            self.quiet_main(prefix+['stage','--backup',str(self.folder),'--kit',str(self.kit),'--execute'])
            self.quiet_main(prefix+['install','--backup',str(self.folder),'--execute','--parked','--allow-reboot'])
            result=self.quiet_main(prefix+['verify','--backup',str(self.folder)])
            self.assertTrue(result['restart_verified'])
            self.quiet_main(prefix+['restore','--backup',str(self.folder),'--execute','--parked'])
        with mock.patch.object(logo,'LogoDevice',side_effect=AssertionError('Offline command used ADB')):
            self.assertTrue(self.quiet_main(['verify-backup','--backup',str(self.folder)])['verified'])
        with self.assertRaises(RuntimeError): logo.main(['backup','--out',str(self.root/'no-serial')])


class LiveGuardTests(unittest.TestCase):
    def make(self):
        device = logo.LogoDevice('adb','explicit-unit')
        device.owner = lambda: None
        device.identity = lambda: dict(logo.x10.PROFILE['identity'],device_id_sha256='a'*64)
        device.guards = lambda: dict(logo.x10.PROFILE['guard_apks'])
        device.home = lambda: 'org.example.home/org.example.home.Home'
        values = {
            ('getprop','sys.boot_completed'):'1', ('getprop','ro.boot.mcuconfig'):'0400000000000000',
            ('getprop','persist.zh.logo.rotated_panel'):'12,', ('getprop','gsm.sim.state'):'LOADED',
            ('sha256sum',logo.PROFILE['stock_su']):logo.PROFILE['stock_su_sha256']+'  su',
            ('sha256sum',logo.PROFILE['updater']):logo.PROFILE['updater_sha256']+'  updater',
            ('pm','path','com.zhonghong.update'):'package:'+logo.PROFILE['updater'],
            ('readlink','-f',logo.PROFILE['partition']):'/dev/block/sdz1',
            ('cat','/sys/class/block/sdz1/size'):'8192',
            ('cat','/proc/sys/kernel/random/boot_id'):'first-boot',
            ('pm','list','packages','-e','--user','0'):'\n'.join('package:'+p for p in logo.x10.PROFILE['required_packages'])}
        device.shell = lambda *args: values[tuple(args)]
        return device,values
    def test_live_guard_accepts_only_reviewed_code_panel_and_core_stack(self):
        d,v=self.make(); self.assertEqual(d.state()['bytes'],4194304)
        for key,value in [(('getprop','ro.boot.mcuconfig'),'0500000000000000'),
                          (('getprop','persist.zh.logo.rotated_panel'),'4,'),
                          (('sha256sum',logo.PROFILE['updater']),'b'*64+'  updater'),
                          (('pm','path','com.zhonghong.update'),'package:/data/app/changed/base.apk'),
                          (('pm','list','packages','-e','--user','0'),'package:org.example.only')]:
            d,v=self.make();v[key]=value
            with self.assertRaises(RuntimeError): d.state()
        d,v=self.make();d.identity=lambda:{'model':'S8'}
        with self.assertRaises(RuntimeError):d.state()


if __name__ == '__main__': unittest.main()
