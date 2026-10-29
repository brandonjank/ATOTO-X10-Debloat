#!/usr/bin/env python3
"""Optional X10 still-logo workflow. Explicit splash writes; separate from x10.py."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import struct
import subprocess
import sys
import uuid
import warnings
import xml.etree.ElementTree as ET
import zipfile

import x10

ROOT = Path(__file__).resolve().parents[1]
PROFILE = json.loads((ROOT / 'profiles/boot-logo-20260403.json').read_text(encoding='utf8'))
MARKER = b'X10 logo-only update; no OS, MCU or Bluetooth firmware.\n'
PREFIX = 16384
require, save, utc, digest = x10.require, x10.save, x10.utc, x10.digest


def seal(data):
    return dict(data, seal=x10.metadata_hash(data))


def load_sealed(path, kind):
    data = json.loads(Path(path).read_text(encoding='utf8'))
    signature = data.pop('seal', None)
    require(signature == x10.metadata_hash(data), 'Metadata changed or is incomplete: ' + str(path))
    require(data.get('schema') == 1 and data.get('kind') == kind, 'Unsupported metadata')
    return data


def private_path(path):
    path = Path(path).resolve()
    require(not path.is_relative_to(ROOT) or path.is_relative_to(ROOT / '.local'),
            'Generated images/backups belong outside source or in ignored .local/')
    return path


def bmp_bytes(width, height, pixels):
    """Match the saved OEM 24-bit bottom-up BMP encoder, including zero DPI fields."""
    require(0 < width <= 1280 and 0 < height <= 1280 and len(pixels) == width * height * 3, 'Invalid pixels')
    stride = (width * 3 + 3) & ~3
    header = bytearray(54)
    struct.pack_into('<2sI', header, 0, b'BM', 54 + stride * height)
    struct.pack_into('<I', header, 10, 54)
    struct.pack_into('<IiiHH', header, 14, 40, width, height, 1, 24)
    rows = bytearray()
    for y in range(height - 1, -1, -1):
        row = pixels[y * width * 3:(y + 1) * width * 3]
        for x in range(width):
            rows.extend(row[x * 3:x * 3 + 3][::-1])
        rows.extend(bytes(stride - width * 3))
    return bytes(header + rows)


def read_bmp(raw):
    require(len(raw) >= 54 and raw[:2] == b'BM', 'Not a BMP image')
    size, offset, dib = struct.unpack_from('<I4xII', raw, 2)
    width, height, planes, bpp, compression = struct.unpack_from('<iiHHI', raw, 18)
    require(dib == 40 and offset == 54 and planes == 1 and bpp == 24 and compression == 0,
            'Expected uncompressed 24-bit BMP from prepare')
    require(0 < width <= 1280 and 0 < height <= 1280, 'Unsupported BMP dimensions')
    stride = (width * 3 + 3) & ~3
    require(size == len(raw) == 54 + stride * height, 'Truncated or oversized BMP')
    pixels = bytearray()
    for y in range(height - 1, -1, -1):
        row = raw[54 + y * stride:54 + y * stride + width * 3]
        for x in range(width):
            pixels.extend(row[x * 3:x * 3 + 3][::-1])
    return width, height, bytes(pixels)


def rotate_clockwise(width, height, pixels):
    result = bytearray(len(pixels))
    for y in range(height):
        for x in range(width):
            start = (y * width + x) * 3
            dest = (x * height + height - 1 - y) * 3
            result[dest:dest + 3] = pixels[start:start + 3]
    return height, width, bytes(result)


def prepare(image, out, size=(1280, 720)):
    try:
        from PIL import Image, ImageOps
    except ImportError as error:
        raise RuntimeError('Image preparation needs: python -m pip install -r requirements-logo.txt') from error
    width, height = size
    require(0 < width <= 1280 and 0 < height <= 720, 'Output must be at most 1280 x 720')
    image, out = Path(image), private_path(out)
    require(image.is_file() and image.stat().st_size <= 32 * 1024 * 1024, 'Image missing or over 32 MiB')
    require(not out.exists(), 'Output already exists; choose a new folder')
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(image) as source:
            require(source.format in ('PNG', 'JPEG', 'BMP', 'WEBP'), 'Use PNG, JPEG, BMP or WebP')
            require(getattr(source, 'n_frames', 1) == 1, 'Use a single still image')
            require(source.width * source.height <= 16_000_000, 'Source exceeds 16 million pixels')
            source = ImageOps.exif_transpose(source).convert('RGBA')
            fitted = ImageOps.contain(source, size, Image.Resampling.LANCZOS)
            canvas = Image.new('RGBA', size, (0, 0, 0, 255))
            canvas.alpha_composite(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))
            canvas = canvas.convert('RGB')
    raw = bmp_bytes(width, height, canvas.tobytes())
    out.mkdir(parents=True)
    upgrade = out / 'usb-root/Upgrade'
    upgrade.mkdir(parents=True)
    (upgrade / PROFILE['marker']).write_bytes(MARKER)
    (upgrade / 'zh_logo.bmp').write_bytes(raw)
    canvas.save(out / 'preview.png')
    names = [PROFILE['marker'], 'zh_logo.bmp']
    with zipfile.ZipFile(out / 'logo-usb.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            archive.writestr('Upgrade/' + name, (upgrade / name).read_bytes())
    data = {'schema': 1, 'kind': 'x10-logo-kit', 'dimensions': [width, height],
            'files': {name: digest(upgrade / name) for name in names},
            'preview_sha256': digest(out / 'preview.png'), 'zip_sha256': digest(out / 'logo-usb.zip')}
    save(out / 'kit.json', seal(data))
    verify_kit(out)
    return {'kit': str(out), 'dimensions': [width, height], 'device_commands': 0}


def verify_kit(folder):
    folder = private_path(folder)
    data = load_sealed(folder / 'kit.json', 'x10-logo-kit')
    upgrade = folder / 'usb-root/Upgrade'
    expected = {PROFILE['marker'], 'zh_logo.bmp'}
    require(set(data['files']) == expected and {p.name for p in upgrade.iterdir()} == expected,
            'Upgrade folder must contain only the X10 marker and zh_logo.bmp')
    for name, sha in data['files'].items():
        require(digest(upgrade / name) == sha, 'Kit file changed: ' + name)
    require((upgrade / PROFILE['marker']).read_bytes() == MARKER, 'Unexpected marker')
    width, height, _ = read_bmp((upgrade / 'zh_logo.bmp').read_bytes())
    require([width, height] == data['dimensions'] and height <= 720, 'Kit image dimensions changed')
    require(digest(folder / 'preview.png') == data['preview_sha256'], 'Preview changed')
    require(digest(folder / 'logo-usb.zip') == data['zip_sha256'], 'USB ZIP changed')
    with zipfile.ZipFile(folder / 'logo-usb.zip') as archive:
        require(len(archive.infolist()) == 2 and set(archive.namelist()) == {'Upgrade/' + n for n in expected},
                'Unexpected USB ZIP entries')
        for name in expected:
            require(archive.read('Upgrade/' + name) == (upgrade / name).read_bytes(), 'USB ZIP content changed')
    return data


def decompress(raw, size):
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        data = stream.read(size + 1)
        require(len(data) == size and stream.read(1) == b'', 'Incomplete/oversized compressed image')
    return data


class LogoDevice(x10.Device):
    def root(self, *args):
        # The existing su directly execs the reader/writer; an intermediate sh drops its UID.
        return self.shell(PROFILE['stock_su'], '0,2000', '/system/bin/toybox', *args)

    def partition_hash(self):
        result = self.root('sha256sum', PROFILE['partition']).split()
        require(len(result) == 2 and re.fullmatch(r'[0-9a-f]{64}', result[0]), 'Invalid partition checksum')
        return result[0]

    def state(self):
        self.owner()
        identity, guards = self.identity(), self.guards()
        require(self.compatible(identity, guards), 'Stock firmware/hardware APK mismatch; stop for review')
        require(self.shell('getprop', 'sys.boot_completed') == '1', 'Android has not finished booting')
        for path, sha in ((PROFILE['stock_su'], PROFILE['stock_su_sha256']),
                          (PROFILE['updater'], PROFILE['updater_sha256'])):
            require(self.shell('sha256sum', path).split()[0] == sha, 'Logo command/updater code changed')
        require(self.shell('pm', 'path', 'com.zhonghong.update').splitlines() == ['package:' + PROFILE['updater']],
                'A different/updated updater APK is active; stop for review')
        config = self.shell('getprop', 'ro.boot.mcuconfig')
        require(re.fullmatch(r'[0-9a-fA-F]{16}', config), 'Unrecognized hardware configuration')
        require(int(config[:2], 16) & 15 in PROFILE['panel_configs'], 'Panel not reviewed for logo updates')
        rotated = self.shell('getprop', 'persist.zh.logo.rotated_panel')
        require(rotated == PROFILE['rotated_panel_property'], 'Panel rotation policy changed')
        node = self.shell('readlink', '-f', PROFILE['partition'])
        require(re.fullmatch(r'/dev/block/sd[a-z]+\d+', node), 'Unexpected splash mapping')
        size = int(self.shell('cat', '/sys/class/block/' + node.rsplit('/', 1)[1] + '/size')) * 512
        require(PREFIX + 1280 * 720 * 3 + 54 <= size <= PROFILE['maximum_partition_bytes'], 'Unexpected splash size')
        enabled = sorted(line[8:] for line in self.shell('pm', 'list', 'packages', '-e', '--user', '0').splitlines()
                         if line.startswith('package:'))
        require(set(x10.PROFILE['required_packages']) <= set(enabled), 'Required core package is not enabled')
        return {'identity': identity, 'guards': guards, 'hardware_config': config, 'rotated_panel': rotated,
                'node': node, 'bytes': size, 'enabled_packages': enabled, 'home': self.home(),
                'boot_id': self.shell('cat', '/proc/sys/kernel/random/boot_id'),
                'sim_state': self.shell('getprop', 'gsm.sim.state')}

    def read_partition(self, size):
        command = shlex.join([PROFILE['stock_su'], '0,2000', '/system/bin/toybox', 'cat', PROFILE['partition']])
        command += ' 2>/dev/null | /system/bin/toybox gzip -c'
        result = subprocess.run([self.adb, '-s', self.serial, 'exec-out', command],
                                capture_output=True, timeout=180, check=True)
        return decompress(result.stdout, size)

    def exists(self, remote):
        result = self.run('shell', shlex.join(['test', '-e', remote]), check=False)
        require(result.returncode in (0, 1) and not result.stderr.strip(), 'Cannot check remote path')
        return result.returncode == 0

    def listing(self, remote):
        return set(self.shell('ls', '-1A', remote).splitlines())

    def push(self, local, remote):
        self.run('push', str(local), remote, timeout=120)

    def inflate(self, source, dest):
        command = shlex.join(['/system/bin/toybox', 'gzip', '-dc', source]) + ' > ' + shlex.quote(dest)
        self.run('shell', command, timeout=60)

    def ui(self, remote):
        self.shell('uiautomator', 'dump', remote)
        return self.shell('cat', remote)


def same_device(before, now, stable=True):
    keys = ['identity', 'guards', 'node', 'bytes', 'hardware_config', 'rotated_panel']
    if stable:
        keys += ['home', 'enabled_packages']
    require(all(before[k] == now[k] for k in keys), 'Device, firmware, layout or protected state changed; stop for review')


def backup(device, out):
    out = private_path(out)
    require(not out.exists(), 'Backup exists; keep it and choose a new folder')
    before = device.state()
    out.mkdir(parents=True)
    save(out / 'capture-status.json', {'complete': False, 'started_utc': utc()})
    first = device.partition_hash()
    raw = device.read_partition(before['bytes'])
    partial = out / 'splash.img.partial'
    with partial.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        x10.os.fsync(stream.fileno())
    require(digest(partial) == first == device.partition_hash(), 'Splash backup checksum mismatch')
    after = device.state()
    same_device(before, after)
    require(before['boot_id'] == after['boot_id'], 'Device restarted during capture')
    partial.rename(out / 'splash.img')
    (out / 'splash.img.gz').write_bytes(gzip.compress(raw, mtime=0))
    save(out / 'backup.json', seal({'schema': 1, 'kind': 'x10-splash-backup', 'created_utc': utc(),
                                  'state': before, 'sha256': first, 'gzip_sha256': digest(out / 'splash.img.gz')}))
    save(out / 'capture-status.json', {'complete': True, 'finished_utc': utc()})
    verify_backup(out)
    return {'backup': str(out), 'bytes': len(raw), 'sha256': first, 'device_writes': 0}


def verify_backup(folder):
    folder = private_path(folder)
    data = load_sealed(folder / 'backup.json', 'x10-splash-backup')
    require(json.loads((folder / 'capture-status.json').read_text(encoding='utf8')).get('complete') is True,
            'Capture is incomplete')
    require(data['state']['identity'].keys() >= x10.PROFILE['identity'].keys(), 'Missing device identity')
    require(all(data['state']['identity'][k] == v for k, v in x10.PROFILE['identity'].items()), 'Wrong backup firmware')
    require(data['state']['guards'] == x10.PROFILE['guard_apks'], 'Backup hardware hashes changed')
    require(0 < data['state']['bytes'] <= PROFILE['maximum_partition_bytes'], 'Invalid backup size')
    require((folder / 'splash.img').stat().st_size == data['state']['bytes'] and digest(folder / 'splash.img') == data['sha256'],
            'Original splash is missing/corrupt')
    require(digest(folder / 'splash.img.gz') == data['gzip_sha256'], 'Compressed backup changed')
    require(hashlib.sha256(decompress((folder / 'splash.img.gz').read_bytes(), data['state']['bytes'])).hexdigest() == data['sha256'],
            'Compressed backup differs from full image')
    return data


def expected_partition(original, bmp):
    width, height, pixels = read_bmp(bmp)
    # This release supports the tested panel-4 policy, which rotates 90 degrees.
    width, height, pixels = rotate_clockwise(width, height, pixels)
    payload = bytes(PREFIX) + bmp_bytes(width, height, pixels)
    require(len(payload) <= len(original), 'Logo exceeds splash partition')
    return payload + original[len(payload):]


def trial(folder, data):
    record = load_sealed(folder / 'logo-journal.json', 'x10-logo-trial')
    require(record['backup_sha256'] == data['sha256'] and record['backup_seal'] == digest(folder / 'backup.json'),
            'Journal does not match this backup')
    require(re.fullmatch(r'/sdcard/x10-logo-[0-9a-f]{32}', record['remote']), 'Unexpected staging path')
    return record


def save_trial(folder, record):
    save(folder / 'logo-journal.json', seal(record))


def stage(device, folder, kit, execute=False):
    folder, kit = Path(folder), Path(kit)
    data, artwork = verify_backup(folder), verify_kit(kit)
    now = device.state()
    same_device(data['state'], now)
    require(device.partition_hash() == data['sha256'], 'Current splash differs from original backup')
    original = (folder / 'splash.img').read_bytes()
    expected = expected_partition(original, (kit / 'usb-root/Upgrade/zh_logo.bmp').read_bytes())
    require(hashlib.sha256(expected).hexdigest() != data['sha256'], 'New logo already matches original')
    journal_path = folder / 'logo-journal.json'
    record = trial(folder, data) if journal_path.exists() else None
    if record:
        require(record['kit_hash'] == digest(kit / 'kit.json'), 'Use the original kit for this journal')
        require(not record.get('install_attempted_utc') and not record.get('restore_attempted_utc'),
                'Install/restore was attempted; verify it instead of staging again')
    if not execute:
        return {'mode': 'PREVIEW', 'action': 'stage only; no updater launch or reboot', 'dimensions': artwork['dimensions']}
    if record is None:
        record = {'schema': 1, 'kind': 'x10-logo-trial', 'backup_sha256': data['sha256'],
                  'backup_seal': digest(folder / 'backup.json'), 'kit_hash': digest(kit / 'kit.json'),
                  'bmp_sha256': artwork['files']['zh_logo.bmp'], 'expected_sha256': hashlib.sha256(expected).hexdigest(),
                  'remote': '/sdcard/x10-logo-' + uuid.uuid4().hex, 'staged': False,
                  'physical_confirmation': None}
        x10.new_journal(journal_path, seal(record))
    remote = record['remote']
    if not device.exists(remote):
        device.shell('mkdir', remote)
    require(device.listing(remote) <= {'Upgrade', 'logo.bmp.gz'}, 'Unrecognized file in staging folder')
    if not device.exists(remote + '/Upgrade'):
        device.shell('mkdir', remote + '/Upgrade')
    require(device.listing(remote + '/Upgrade') <= {PROFILE['marker'], 'zh_logo.bmp', 'zh_logo.bmp.partial'},
            'Unexpected update component; leave it untouched')
    compressed = folder / 'new-logo.bmp.gz'
    compressed.write_bytes(gzip.compress((kit / 'usb-root/Upgrade/zh_logo.bmp').read_bytes(), mtime=0))
    device.push(compressed, remote + '/logo.bmp.gz')
    device.inflate(remote + '/logo.bmp.gz', remote + '/Upgrade/zh_logo.bmp.partial')
    require(device.shell('sha256sum', remote + '/Upgrade/zh_logo.bmp.partial').split()[0] == record['bmp_sha256'],
            'Staged BMP checksum mismatch')
    device.shell('mv', remote + '/Upgrade/zh_logo.bmp.partial', remote + '/Upgrade/zh_logo.bmp')
    device.push(kit / 'usb-root/Upgrade' / PROFILE['marker'], remote + '/Upgrade/' + PROFILE['marker'])
    check_staged(device, record)
    record['staged'] = True
    save_trial(folder, record)
    return {'mode': 'STAGED', 'remote': remote, 'updater_started': False, 'reboot': False}


def check_staged(device, record):
    upgrade = record['remote'] + '/Upgrade'
    require(device.listing(upgrade) == {PROFILE['marker'], 'zh_logo.bmp'}, 'Unexpected/missing update components')
    for name, sha in ((PROFILE['marker'], hashlib.sha256(MARKER).hexdigest()), ('zh_logo.bmp', record['bmp_sha256'])):
        require(device.shell('sha256sum', upgrade + '/' + name).split()[0] == sha, 'Staged file changed')


def logo_dialog(xml):
    nodes = list(ET.fromstring(xml).iter('node'))
    require(all(n.get('package') == 'com.zhonghong.update' for n in nodes), 'Not the OEM updater dialog')
    def field(name):
        found = [n for n in nodes if n.get('resource-id') == 'com.zhonghong.update:id/' + name]
        require(len(found) == 1 and found[0].get('enabled') == 'true', 'Unexpected updater controls')
        return found[0]
    require(field('tip_info').get('text') == 'Upgrade LOGO', 'Updater is not logo-only')
    return field('check_view'), field('update_confirm')


def tap(device, node):
    match = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.get('bounds', ''))
    require(match, 'Missing control geometry')
    x1, y1, x2, y2 = map(int, match.groups())
    require(0 <= x1 < x2 <= 1920 and 0 <= y1 < y2 <= 1280, 'Invalid control geometry')
    device.shell('input', 'tap', (x1 + x2) // 2, (y1 + y2) // 2)


def install(device, folder, execute=False, parked=False, allow_reboot=False):
    folder = Path(folder)
    data = verify_backup(folder)
    record = trial(folder, data)
    same_device(data['state'], device.state())
    require(record['staged'], 'Stage and verify the logo first')
    require(not record.get('install_attempted_utc') and not record.get('restore_attempted_utc'),
            'Update was already attempted; reconnect and verify, do not replay it')
    check_staged(device, record)
    require(device.partition_hash() == data['sha256'], 'Splash changed since backup')
    if not execute:
        return {'mode': 'PREVIEW', 'action': 'OEM logo-only update', 'automatic_reboot': True}
    require(parked and allow_reboot, 'Installation needs --parked --allow-reboot and current owner authorization')
    current_state = device.state()
    same_device(data['state'], current_state)
    record['boot_before_install'] = current_state['boot_id']
    record['install_attempted_utc'] = utc()
    save_trial(folder, record)  # The service can retain a prior auto-update preference.
    device.shell('am', 'startservice', '-n', 'com.zhonghong.update/.service.UpdateService',
                 '--ei', '_cmd', '2', '--es', '_value', record['remote'])
    remote_xml = record['remote'] + '/selection.xml'
    xml = device.ui(remote_xml)
    (folder / 'selection.xml').write_text(xml, encoding='utf8')
    check, button = logo_dialog(xml)
    if check.get('selected') != 'true':
        tap(device, check)
        check, button = logo_dialog(device.ui(remote_xml))
    require(check.get('selected') == 'true', 'Logo selection did not stick')
    check_staged(device, record)
    require(device.partition_hash() == data['sha256'], 'Logo update may already have started; reconnect and verify')
    current_state = device.state()
    same_device(data['state'], current_state)
    require(current_state['boot_id'] == record['boot_before_install'], 'Device restarted; verify before any further confirmation')
    record['confirm_attempted_utc'] = utc()
    save_trial(folder, record)
    tap(device, button)
    record['confirm_sent'] = True
    save_trial(folder, record)
    return {'mode': 'UPDATE_REQUESTED', 'automatic_reboot': True, 'verification_pending': True}


def verify(device, folder):
    folder = Path(folder)
    data = verify_backup(folder)
    record = trial(folder, data)
    now = device.state()
    same_device(data['state'], now, stable=False)
    current = device.partition_hash()
    require(current in (data['sha256'], record['expected_sha256']), 'Unrecognized/partial splash; stop for recovery inspection')
    require(current == record['expected_sha256'], 'Original splash remains; no custom logo installation verified')
    require(record.get('boot_before_install') and now['boot_id'] != record['boot_before_install'], 'No post-update restart observed')
    issues = []
    if now['home'] != data['state']['home']:
        issues.append('Default HOME changed')
    missing = set(data['state']['enabled_packages']) - set(now['enabled_packages'])
    issues += ['Previously enabled package missing: ' + name for name in sorted(missing & set(x10.PROFILE['protected_packages']))]
    result = {'checked_utc': utc(), 'splash_verified': True, 'restart_verified': True,
              'home': now['home'], 'sim_state': now['sim_state'], 'issues': issues,
              'sim_state_changed': now['sim_state'] != data['state']['sim_state'],
              'physical_confirmation': record.get('physical_confirmation')}
    record['verification'] = result
    save_trial(folder, record)
    require(not issues, 'Logo matches, but software checks require review: ' + '; '.join(issues))
    return result


def restore(device, folder, execute=False, parked=False):
    folder = Path(folder)
    data, record = verify_backup(folder), None
    if (folder / 'logo-journal.json').exists():
        record = trial(folder, data)
    now = device.state()
    same_device(data['state'], now, stable=False)
    current = device.partition_hash()
    if current == data['sha256']:
        if execute and record and record.get('restore_attempted_utc'):
            record['restore_verified_utc'] = utc()
            save_trial(folder, record)
        return {'mode': 'ALREADY_ORIGINAL', 'device_writes': 0, 'reboot': False}
    require(record and current == record['expected_sha256'], 'Unknown/partial splash; inspect before manual recovery')
    if not execute:
        return {'mode': 'PREVIEW', 'action': 'Restore only the complete original splash', 'reboot': False,
                'restore_physically_trialed': False}
    require(parked, 'Restoration needs --parked and explicit owner restoration authorization')
    record['restore_attempted_utc'] = utc()
    save_trial(folder, record)
    remote = record['remote'] + '/restore'
    require(device.exists(record['remote']), 'Original staging folder is missing; inspect before recovery')
    if not device.exists(remote):
        device.shell('mkdir', remote)
    require(device.listing(remote) <= {'splash.img', 'splash.img.gz'}, 'Unrecognized restore file')
    device.push(folder / 'splash.img.gz', remote + '/splash.img.gz')
    device.inflate(remote + '/splash.img.gz', remote + '/splash.img')
    require(device.shell('sha256sum', remote + '/splash.img').split()[0] == data['sha256'], 'Restore transfer failed')
    same_device(data['state'], device.state(), stable=False)
    require(device.partition_hash() == current, 'Splash changed during restore preparation')
    # The sole direct partition writer in this toolkit. No arbitrary target is accepted.
    device.root('dd', 'if=' + remote + '/splash.img', 'of=' + PROFILE['partition'], 'bs=1048576')
    device.shell('sync')
    require(device.partition_hash() == data['sha256'], 'Original splash restoration did not verify')
    record['restore_verified_utc'] = utc()
    save_trial(folder, record)
    return {'mode': 'ORIGINAL_RESTORED', 'sha256': data['sha256'], 'reboot': False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adb', default='adb')
    p.add_argument('--serial')
    commands = p.add_subparsers(dest='command', required=True)
    q = commands.add_parser('prepare')
    q.add_argument('--image', required=True, type=Path)
    q.add_argument('--out', required=True, type=Path)
    q.add_argument('--size', default='1280x720')
    q = commands.add_parser('backup')
    q.add_argument('--out', required=True, type=Path)
    q = commands.add_parser('verify-backup')
    q.add_argument('--backup', required=True, type=Path)
    for name in ('stage', 'install', 'verify', 'restore'):
        q = commands.add_parser(name)
        q.add_argument('--backup', required=True, type=Path)
        if name == 'stage':
            q.add_argument('--kit', required=True, type=Path)
        if name != 'verify':
            q.add_argument('--execute', action='store_true')
        if name in ('install', 'restore'):
            q.add_argument('--parked', action='store_true')
        if name == 'install':
            q.add_argument('--allow-reboot', action='store_true')
    a = p.parse_args(argv)
    if a.command == 'prepare':
        require(re.fullmatch(r'\d{1,4}x\d{1,4}', a.size), 'Use WIDTHxHEIGHT')
        result = prepare(a.image, a.out, tuple(map(int, a.size.split('x'))))
    elif a.command == 'verify-backup':
        data = verify_backup(a.backup)
        result = {'verified': True, 'bytes': data['state']['bytes'], 'device_commands': 0}
    else:
        require(a.serial, 'Device commands require explicit --serial; no automatic target selection')
        device = LogoDevice(a.adb, a.serial)
        if a.command == 'backup': result = backup(device, a.out)
        elif a.command == 'stage': result = stage(device, a.backup, a.kit, a.execute)
        elif a.command == 'install': result = install(device, a.backup, a.execute, a.parked, a.allow_reboot)
        elif a.command == 'verify': result = verify(device, a.backup)
        else: result = restore(device, a.backup, a.execute, a.parked)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.SubprocessError, ET.ParseError) as error:
        print('Stopped: ' + str(error), file=sys.stderr)
        sys.exit(1)
