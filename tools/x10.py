#!/usr/bin/env python3
"""X10 stock-Android trial tools. No root, flashing, app-data erase or reboot."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROFILE = json.loads((ROOT / 'profiles/stock-20260403.json').read_text(encoding='utf8'))
RESTORE = {0: 'default-state', 1: 'enable', 2: 'disable', 3: 'disable-user', 4: 'disable-until-used'}
HOMES = {'x10': 'io.atoto.home/app.lawnchair.LawnchairLauncher',
         'lawnchair': 'app.lawnchair/app.lawnchair.LawnchairLauncher',
         'oem': 'com.android.launcher3/.uioverrides.QuickstepLauncher'}
SETTINGS = {'secure': ['screensaver_enabled', 'screensaver_activate_on_dock',
                       'screensaver_activate_on_sleep', 'notification_badging'],
            'global': ['window_animation_scale', 'transition_animation_scale', 'animator_duration_scale']}
DEPENDENCIES = ['com.google.android.apps.maps', 'com.pandora.android', 'com.audible.application',
                'org.prowl.torque', 'com.google.android.inputmethod.latin']

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')
    temporary.replace(path)

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def parse_package(text):
    state = re.search(r'^\s*User 0:.*$', text, re.M)
    if not state:
        return None
    enabled = re.search(r'\benabled=(\d+)\b', state[0])
    installed = re.search(r'\binstalled=(true|false)\b', state[0])
    require(enabled and installed and int(enabled[1]) in RESTORE, 'Unrecognized package state')
    return {'installed': installed[1] == 'true', 'enabled': int(enabled[1])}

class Device:
    def __init__(self, adb, serial):
        self.adb, self.serial = adb, serial

    def run(self, *args, timeout=40, check=True):
        r = subprocess.run([self.adb, '-s', self.serial, *map(str, args)],
                           capture_output=True, text=True, encoding='utf8', errors='replace', timeout=timeout)
        if check:
            require(r.returncode == 0, 'ADB failed: ' + (r.stderr or r.stdout)[-1600:])
        return r

    def shell(self, *args, **kw):
        return self.run('shell', shlex.join(list(map(str, args))), **kw).stdout.strip()

    def identity(self):
        # Raw serial never enters the portable public profile. Snapshot identity stays private.
        props = dict(re.findall(r'^\[([^\]]+)\]: \[(.*)\]$', self.shell('getprop'), re.M))
        serial = props.get('ro.serialno') or props.get('ro.boot.serialno')
        require(serial, 'Cannot establish a stable device identity')
        return {'model': props.get('ro.product.model'), 'sdk': props.get('ro.build.version.sdk'),
                'platform': props.get('ro.board.platform'), 'product_version': props.get('ro.product.version'),
                'fingerprint': props.get('ro.build.fingerprint'),
                'device_id_sha256': hashlib.sha256(serial.encode()).hexdigest()}

    def guards(self):
        result = {}
        for path in PROFILE['guard_apks']:
            r = self.run('shell', shlex.join(['sha256sum', path]), check=False)
            tokens = r.stdout.split()
            result[path] = tokens[0] if r.returncode == 0 and tokens and re.fullmatch(r'[0-9a-f]{64}', tokens[0]) else None
        return result

    def compatible(self, identity, guards):
        return all(identity.get(k) == v for k, v in PROFILE['identity'].items()) and guards == PROFILE['guard_apks']

    def package(self, name):
        require(re.fullmatch(r'[A-Za-z0-9_.]+', name), 'Invalid package name')
        text = self.shell('dumpsys', 'package', name)
        state = parse_package(text)
        if state is None:
            return {'present': False, 'files': []}
        path_result = self.run('shell', shlex.join(['pm', 'path', name]), check=False)
        require(path_result.returncode in (0, 1) and not path_result.stderr.strip(), 'Package path query failed: ' + name)
        paths = [x[8:] for x in path_result.stdout.splitlines() if x.startswith('package:')]
        if not paths:
            # User-removed system packages can still have registered dexopt paths.
            paths = re.findall(r'^\s*path: (/[^\r\n]+\.apk)\s*$', text, re.M)
        require(paths, 'Cannot locate APKs for ' + name)
        require(all(p.startswith('/') and p.endswith('.apk') and '\n' not in p for p in paths), 'Invalid APK path')
        version = re.search(r'\bversionName=([^\r\n]*)', text)
        return dict(state, present=True, version=version[1] if version else None,
                    files=[{'remote': p, 'sha256': self.shell('sha256sum', p).split()[0]} for p in dict.fromkeys(paths)])

def file_in(folder, relative):
    result = (folder / relative).resolve()
    require(result.is_relative_to(folder.resolve()), 'Backup path escapes its folder')
    return result

def verify_files(folder, snapshot, selected=None):
    for name, entry in snapshot['packages'].items():
        if selected is not None and name not in selected:
            continue
        if not entry.get('present'):
            continue
        require(entry.get('files'), 'Missing APK records: ' + name)
        for item in entry['files']:
            require(item.get('local'), 'No APK backup for ' + name + '; use snapshot --with-apks')
            path = file_in(folder, item['local'])
            require(path.is_file() and digest(path) == item['sha256'], 'APK backup missing or corrupt: ' + str(path))

def snapshot(device, folder, with_apks=False, caches=(), resume=False):
    if folder.exists():
        require(resume, 'Snapshot folder already exists; use --resume only for an interrupted capture')
        old = load_snapshot(folder)
        require(not old.get('complete') and old['identity'] == device.identity() and old['guard_apks'] == device.guards(),
                'Only an incomplete snapshot from this unchanged device can be resumed')
    else:
        require(not resume, 'No interrupted snapshot to resume')
        folder.mkdir(parents=True)
    identity = device.identity()
    guards = device.guards()
    data = {'schema': 1, 'created_utc': utc(), 'identity': identity, 'guard_apks': guards,
            'compatible': device.compatible(identity, guards), 'packages': {}, 'settings': {},
            'home': device.shell('cmd', 'package', 'resolve-activity', '--brief', '-a',
                                 'android.intent.action.MAIN', '-c', 'android.intent.category.HOME').splitlines()[-1],
            'limits': 'APK/settings snapshot only. No private app data, accounts, pairing, modem calibration or partition backup.',
            'complete': False}
    save(folder / 'snapshot.json', data)
    cache = {}
    if with_apks:
        for root in caches:
            for path in Path(root).rglob('*.apk'):
                cache.setdefault(digest(path), path)
    names = list(PROFILE['optional_packages']) + PROFILE['protected_packages'] + ['io.atoto.home', 'app.lawnchair', 'io.atoto.tools.audiblewidget', 'app.lawnchair.lawnicons.play'] + DEPENDENCIES
    for name in dict.fromkeys(names):
        entry = device.package(name)
        # Pull only optional apps and our home/widget; core APKs get hashes without large redundant copies.
        should_copy = name in PROFILE['optional_packages'] or name in ('io.atoto.home', 'app.lawnchair', 'io.atoto.tools.audiblewidget')
        if with_apks and should_copy:
            for index, item in enumerate(entry['files']):
                relative = 'apks/' + name + '/' + str(index) + '.apk'
                dest = folder / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                cached = cache.get(item['sha256'])
                if cached and cached.resolve() == dest.resolve():
                    pass
                elif cached:
                    shutil.copy2(cached, dest)
                else:
                    device.run('pull', item['remote'], dest, timeout=300)
                require(digest(dest) == item['sha256'], 'Transferred APK hash mismatch: ' + name)
                item['local'] = relative
        data['packages'][name] = entry
        save(folder / 'snapshot.json', data)
        print('Captured ' + name, flush=True)
    for ns, keys in SETTINGS.items():
        data['settings'][ns] = {k: device.shell('settings', 'get', ns, k) for k in keys}
    # Status evidence only, never replayed as settings or commands.
    for label, command in {'dexopt': ['dumpsys', 'package', 'dexopt'],
                            'widgets': ['dumpsys', 'appwidget'], 'power': ['dumpsys', 'power']}.items():
        (folder / (label + '.txt')).write_text(device.shell(*command) + '\n', encoding='utf8')
    data.update(complete=True, apks_copied=with_apks, finished_utc=utc())
    save(folder / 'snapshot.json', data)
    return data

def validate_binding(device, data):
    current = device.identity()
    require(data.get('schema') == 1 and data.get('complete'), 'Incomplete or unsupported snapshot')
    require(current == data['identity'], 'Snapshot belongs to another device or firmware')
    guards = device.guards()
    require(guards == data['guard_apks'], 'Hardware-stack APKs changed since snapshot')
    require(device.compatible(current, guards), 'Firmware is outside the tested profile; read-only capture remains available')

def load_snapshot(folder):
    return json.loads((folder / 'snapshot.json').read_text(encoding='utf8'))

def plan(data, packages, screensaver):
    require(set(packages) <= set(PROFILE['optional_packages']), 'Package outside optional allowlist')
    require(not (set(packages) & set(PROFILE['protected_packages'])), 'Protected package requested')
    actions = []
    for name in dict.fromkeys(packages):
        entry = data['packages'].get(name)
        require(entry is not None, 'Package missing from snapshot: ' + name)
        if entry.get('present') and entry['installed'] and entry['enabled'] not in (2, 3, 4):
            actions.append({'kind': 'package', 'package': name, 'before': entry['enabled'], 'after': 3})
    if screensaver:
        for key in SETTINGS['secure'][:3]:
            old = data['settings']['secure'][key]
            if old != '0':
                actions.append({'kind': 'setting', 'namespace': 'secure', 'key': key, 'before': old, 'after': '0'})
    return actions

def state_now(device, action):
    if action['kind'] == 'package':
        entry = device.package(action['package'])
        require(entry.get('present') and entry['installed'], 'Package installation state changed')
        return entry['enabled']
    return device.shell('settings', 'get', action['namespace'], action['key'])

def write_action(device, action, value):
    if action['kind'] == 'package':
        require(action['package'] in PROFILE['optional_packages'], 'Package outside allowlist')
        device.shell('pm', RESTORE[value], '--user', '0', action['package'])
    else:
        require(action.get('namespace') == 'secure' and action['key'] in SETTINGS['secure'][:3], 'Setting outside allowlist')
        if value == 'null':
            device.shell('settings', 'delete', 'secure', action['key'])
        else:
            require(value in ('0', '1'), 'Unexpected screensaver value')
            device.shell('settings', 'put', 'secure', action['key'], value)
    require(state_now(device, action) == value, 'State verification failed')

def apply(device, folder, data, actions, execute):
    validate_binding(device, data)
    selected = [a['package'] for a in actions if a['kind'] == 'package']
    verify_files(folder, data, selected)
    # Preflight the entire plan before the first write.
    for action in actions:
        require(state_now(device, action) == action['before'], 'Device state changed since snapshot')
    print(json.dumps(actions, indent=2))
    if not execute:
        print('Preview only. Add --execute to apply the displayed plan.')
        return
    path = folder / 'trial-journal.json'
    require(not path.exists(), 'A trial journal already exists; restore or take a fresh snapshot')
    journal = {'schema': 1, 'identity': data['identity'], 'created_utc': utc(), 'actions': actions}
    save(path, journal)
    for action in actions:
        action['attempted'] = True
        save(path, journal)
        write_action(device, action, action['after'])
        action['verified'] = True
        save(path, journal)
    print('Applied and verified. No reboot performed; see docs/RESTORE.md.')

def restore(device, folder, data, execute):
    validate_binding(device, data)
    path = folder / 'trial-journal.json'
    journal = json.loads(path.read_text(encoding='utf8'))
    require(journal.get('schema') == 1 and journal['identity'] == data['identity'], 'Invalid trial journal')
    actions = [a for a in reversed(journal['actions']) if a.get('attempted') and not a.get('restored')]
    # Validate journal entries against the saved snapshot before any device writes.
    for action in actions:
        if action['kind'] == 'package':
            name = action['package']
            require(name in PROFILE['optional_packages'] and action['before'] == data['packages'][name]['enabled'] and action['after'] == 3, 'Invalid package action')
        else:
            require(action['kind'] == 'setting' and action['namespace'] == 'secure' and action['key'] in SETTINGS['secure'][:3]
                    and action['before'] == data['settings']['secure'][action['key']] and action['after'] == '0', 'Invalid setting action')
        require(state_now(device, action) in (action['before'], action['after']), 'State diverged; inspect before restore')
    print(json.dumps(actions, indent=2))
    if not execute:
        print('Preview only. Add --execute to restore these original values.')
        return
    for action in actions:
        write_action(device, action, action['before'])
        action['restored'] = True
        save(path, journal)
    print('Restored journaled values. App data retained.')

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adb', default='adb', help='ADB executable on PATH, or an explicit path')
    p.add_argument('--serial', required=True, help='Explicit Wi-Fi ADB serial/address; no automatic device selection')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('audit')
    snap = sub.add_parser('snapshot'); snap.add_argument('--out', type=Path, required=True)
    snap.add_argument('--with-apks', action='store_true'); snap.add_argument('--resume', action='store_true')
    snap.add_argument('--apk-cache', type=Path, action='append', default=[], help='Private local APK cache; hash checked before reuse')
    change = sub.add_parser('apply'); change.add_argument('--snapshot', type=Path, required=True)
    change.add_argument('--packages', nargs='*', default=[])
    change.add_argument('--screensaver', action='store_true'); change.add_argument('--execute', action='store_true')
    undo = sub.add_parser('restore'); undo.add_argument('--snapshot', type=Path, required=True); undo.add_argument('--execute', action='store_true')
    verify = sub.add_parser('verify'); verify.add_argument('--snapshot', type=Path, required=True)
    home = sub.add_parser('home'); home.add_argument('choice', choices=HOMES); home.add_argument('--execute', action='store_true')
    a = p.parse_args(argv)
    d = Device(a.adb, a.serial)
    if a.command == 'audit':
        i = d.identity(); g = d.guards()
        print(json.dumps({'identity': {k: v for k, v in i.items() if k != 'device_id_sha256'},
                          'compatible': d.compatible(i, g), 'guard_apks': g}, indent=2))
    elif a.command == 'snapshot':
        s = snapshot(d, a.out, a.with_apks, a.apk_cache, a.resume)
        print(json.dumps({'snapshot': str(a.out), 'compatible': s['compatible'], 'complete': s['complete']}, indent=2))
    elif a.command == 'home':
        i = d.identity(); require(d.compatible(i, d.guards()), 'Untested firmware; use Android default-app settings manually')
        component = HOMES[a.choice]
        entry = d.package(component.split('/')[0])
        require(entry.get('present') and entry['installed'] and entry['enabled'] in (0, 1), 'Selected home is not enabled/installed')
        print('Set HOME to ' + component)
        if a.execute:
            d.shell('cmd', 'package', 'set-home-activity', '--user', '0', component)
            d.shell('am', 'start', '-a', 'android.intent.action.MAIN', '-c', 'android.intent.category.HOME', '-n', component)
            actual = d.shell('cmd', 'package', 'resolve-activity', '--brief', '-a', 'android.intent.action.MAIN', '-c', 'android.intent.category.HOME').splitlines()[-1]
            package, activity = actual.split('/')
            if activity.startswith('.'): activity = package + activity
            expected_package, expected_activity = component.split('/')
            if expected_activity.startswith('.'): expected_activity = expected_package + expected_activity
            require((package, activity) == (expected_package, expected_activity), 'Default home did not match request')
        else: print('Preview only. Add --execute to switch. Layouts are retained; taskbar visibility is separate.')
    else:
        data = load_snapshot(a.snapshot)
        if a.command == 'verify':
            verify_files(a.snapshot, data, list(PROFILE['optional_packages']) + ['io.atoto.home', 'app.lawnchair', 'io.atoto.tools.audiblewidget'])
            print('Saved APK hashes verified offline; this does not verify private app data or firmware restoration.')
        elif a.command == 'apply':
            apply(d, a.snapshot, data, plan(data, a.packages, a.screensaver), a.execute)
        else:
            restore(d, a.snapshot, data, a.execute)

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.SubprocessError, OSError, ValueError, KeyError) as exc:
        print('Stopped: ' + str(exc), file=sys.stderr)
        sys.exit(1)
