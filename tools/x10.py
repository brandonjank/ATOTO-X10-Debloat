#!/usr/bin/env python3
"""X10 stock-Android trial tools. No root, flashing, app-data erase or reboot."""
import argparse
import datetime as dt
import hashlib
import json
import os
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
BACKUP_APPS = ['io.atoto.home', 'app.lawnchair', 'io.atoto.tools.audiblewidget']
IDENTITY_KEYS = ['model', 'sdk', 'platform', 'product_version', 'fingerprint', 'device_id_sha256']

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
    with temporary.open('w', encoding='utf8') as f:
        f.write(json.dumps(value, indent=2) + '\n')
        f.flush()
        os.fsync(f.fileno())
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
    return {'installed': installed[1] == 'true', 'enabled': int(enabled[1]),
            'hidden': bool(re.search(r'\bhidden=true\b', state[0])),
            'suspended': bool(re.search(r'\bsuspended=true\b', state[0]))}

def component(value):
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*/[A-Za-z0-9_.$]+', value),
            'No usable default HOME component; select a working default home before taking the snapshot')
    package, activity = value.split('/')
    if activity.startswith('.'): activity = package + activity
    return package + '/' + activity

def available(entry):
    return entry.get('present') and entry.get('installed') and entry.get('enabled') in (0, 1) and not entry.get('hidden') and not entry.get('suspended')

def apk_hashes(entry):
    return sorted(f['sha256'] for f in entry.get('files', []))

def metadata_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

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

    def owner(self):
        require(self.shell('am', 'get-current-user') == '0', 'Only Android owner user 0 is supported; no changes made')

    def home(self):
        text = self.shell('cmd', 'package', 'resolve-activity', '--brief', '-a',
                          'android.intent.action.MAIN', '-c', 'android.intent.category.HOME')
        require(text, 'Cannot resolve default HOME')
        return component(text.splitlines()[-1])

    def homes(self):
        text = self.shell('cmd', 'package', 'query-activities', '--brief', '--components', '--user', '0',
                          '-a', 'android.intent.action.MAIN', '-c', 'android.intent.category.HOME')
        return {component(line.strip()) for line in text.splitlines() if '/' in line and ' ' not in line.strip()}

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
            require(bool(re.search(r'Unable to find package|Unknown package|Package .* not found', text, re.I)),
                    'Unrecognized package dump; refusing to treat a failed query as absence: ' + name)
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

def validate_snapshot(data):
    require(data.get('schema') == 1 and data.get('complete') is True, 'Incomplete or unsupported snapshot')
    require(all(isinstance(data.get('identity', {}).get(k), str) and data['identity'][k] for k in IDENTITY_KEYS),
            'Missing snapshot identity')
    require(set(data.get('guard_apks', {})) == set(PROFILE['guard_apks']), 'Missing hardware APK records')
    original = component(data.get('home'))
    names = set(PROFILE['optional_packages']) | set(PROFILE['protected_packages']) | set(BACKUP_APPS) | {original.split('/')[0]}
    require(names <= set(data.get('packages', {})), 'Snapshot package inventory is incomplete; take a fresh snapshot')
    for name in names:
        entry = data['packages'][name]
        require(type(entry.get('present')) is bool and isinstance(entry.get('files'), list), 'Invalid package record: ' + name)
        if not entry['present']: continue
        require(type(entry.get('installed')) is bool and type(entry.get('enabled')) is int and entry['enabled'] in RESTORE,
                'Invalid installed/enabled state: ' + name)
        require(entry['files'] and all(re.fullmatch(r'[0-9a-f]{64}', f.get('sha256', '')) for f in entry['files']),
                'Missing/invalid APK hashes: ' + name)
    require(available(data['packages'][original.split('/')[0]]), 'Original HOME was not usable at snapshot time')
    require(all(k in data.get('settings', {}).get('secure', {}) and data['settings']['secure'][k] in ('0', '1', 'null')
                for k in SETTINGS['secure'][:3]), 'Incomplete or invalid screensaver settings')

def verify_snapshot(folder, data):
    validate_snapshot(data)
    require(data.get('apks_copied') is True, 'Metadata-only snapshot; take a snapshot --with-apks before applying changes')
    selected = set(PROFILE['optional_packages']) | set(BACKUP_APPS) | {component(data['home']).split('/')[0]}
    verify_files(folder, data, selected)
    artifacts = list(data.get('evidence', {}).values())
    if data.get('launcher_export'): artifacts.append(data['launcher_export'])
    for artifact in artifacts:
        path = file_in(folder, artifact['local'])
        require(path.is_file() and digest(path) == artifact['sha256'], 'Missing/corrupt evidence or launcher export: ' + str(path))

def health(device, data=None):
    device.owner()
    identity, guards = device.identity(), device.guards()
    packages = {name: device.package(name) for name in PROFILE['protected_packages']}
    issues = []
    if not device.compatible(identity, guards): issues.append('Firmware does not match the tested profile')
    for name, now in packages.items():
        before = data['packages'].get(name, {}) if data else {}
        if name in PROFILE['required_packages'] or available(before):
            if not available(now): issues.append(name + ': missing, disabled, hidden or suspended')
        if available(before) and apk_hashes(before) != apk_hashes(now):
            issues.append(name + ': APKs changed since snapshot; review the update before further cleanup')
    current_home = device.home()
    sim = device.shell('getprop', 'gsm.sim.state')
    warnings = []
    if data and data.get('sim_state') and sim != data['sim_state']:
        warnings.append('SIM state changed since snapshot; verify physical-SIM service manually')
    return {'checked_utc': utc(), 'packages': packages, 'home': current_home, 'sim_state': sim,
            'issues': issues, 'warnings': warnings, 'software_checks_passed': not issues,
            'physical_feature_tests_passed': None}

def attach_export(folder, data, source):
    validate_snapshot(data)
    require(not any((folder/name).exists() for name in ('trial-journal.json', 'home-journal.json')),
            'Export the original HOME before starting a trial; use a fresh snapshot')
    require(not data.get('launcher_export'), 'An original-home export is already recorded')
    require(source.is_file() and source.stat().st_size > 0, 'Launcher export is missing or empty')
    suffix = source.suffix if re.fullmatch(r'\.[A-Za-z0-9_-]+', source.suffix) else '.backup'
    relative = 'exports/original-home' + suffix
    dest = file_in(folder, relative)
    require(not dest.exists(), 'Export destination already exists; inspect it before retrying')
    dest.parent.mkdir(exist_ok=True)
    shutil.copy2(source, dest)
    require(digest(dest) == digest(source), 'Launcher export copy failed verification')
    data['launcher_export'] = {'local': relative, 'sha256': digest(dest), 'source_filename': source.name,
                               'home': component(data['home']), 'format': 'Owner-supplied native export; use the original app to import'}
    save(folder/'snapshot.json', data)
    print('Original-home export copied and hash recorded; app ownership and export contents require human/agent verification.')

def snapshot(device, folder, with_apks=False, caches=(), resume=False):
    device.owner()
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
    original_home = ensure_home(device, device.home())
    data = {'schema': 1, 'created_utc': utc(), 'identity': identity, 'guard_apks': guards,
            'compatible': device.compatible(identity, guards), 'packages': {}, 'settings': {},
            'home': original_home, 'sim_state': device.shell('getprop', 'gsm.sim.state'),
            'limits': 'APK/settings snapshot only. No private app data, accounts, pairing, modem calibration or partition backup.',
            'complete': False}
    save(folder / 'snapshot.json', data)
    cache = {}
    if with_apks:
        for root in caches:
            for path in Path(root).rglob('*.apk'):
                cache.setdefault(digest(path), path)
    home_package = component(data['home']).split('/')[0]
    names = list(PROFILE['optional_packages']) + PROFILE['protected_packages'] + BACKUP_APPS + ['app.lawnchair.lawnicons.play'] + DEPENDENCIES + [home_package]
    for name in dict.fromkeys(names):
        entry = device.package(name)
        # Include the actual original HOME even if it is neither Lawnchair nor ATOTO.
        should_copy = name in PROFILE['optional_packages'] or name in BACKUP_APPS or name == home_package
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
    data['evidence'] = {}
    for label, command in {'dexopt': ['dumpsys', 'package', 'dexopt'],
                            'widgets': ['dumpsys', 'appwidget'], 'power': ['dumpsys', 'power'],
                            'settings-system': ['settings', 'list', 'system'],
                            'settings-secure': ['settings', 'list', 'secure'],
                            'settings-global': ['settings', 'list', 'global'],
                            'original-home-package': ['dumpsys', 'package', home_package],
                            'installed-versions': ['pm', 'list', 'packages', '-u', '--show-versioncode']}.items():
        path = folder / (label + '.txt')
        path.write_text(device.shell(*command) + '\n', encoding='utf8')
        data['evidence'][label] = {'local': path.name, 'sha256': digest(path)}
    require(device.identity() == identity and device.guards() == guards, 'Device/firmware changed during capture; snapshot remains incomplete')
    data.update(complete=True, apks_copied=with_apks, finished_utc=utc())
    validate_snapshot(data)
    if with_apks: verify_snapshot(folder, data)
    save(folder / 'snapshot.json', data)
    return data

def validate_binding(device, data):
    validate_snapshot(data)
    device.owner()
    current = device.identity()
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

def validate_action(data, action):
    if action.get('kind') == 'package':
        name = action['package']
        require(name in PROFILE['optional_packages'] and name not in PROFILE['protected_packages'], 'Invalid package action')
        entry = data['packages'][name]
        require(available(entry) and action['before'] == entry['enabled'] and action['after'] == 3,
                'Package action does not match its original snapshot')
    else:
        require(action.get('kind') == 'setting' and action.get('namespace') == 'secure'
                and action.get('key') in SETTINGS['secure'][:3]
                and action['before'] == data['settings']['secure'][action['key']] and action['after'] == '0', 'Invalid setting action')

def validate_target(device, data, name):
    now = device.package(name)
    before = data['packages'][name]
    require(now.get('present') and now.get('installed') == before['installed'] and not now.get('hidden') and not now.get('suspended'),
            'Package installation/visibility changed since snapshot: ' + name)
    require(apk_hashes(now) == apk_hashes(before), 'Package APKs changed since snapshot: ' + name)
    require(apk_hashes(now) == sorted(PROFILE['optional_apk_sha256'][name]),
            'Package version is outside the audited optional-app profile: ' + name)

def journal_binding(journal, data):
    require(journal.get('schema') == 1 and journal['identity'] == data['identity'], 'Invalid trial journal')
    if 'snapshot_sha256' in journal:
        require(journal['snapshot_sha256'] == metadata_hash(data), 'Snapshot metadata changed after the trial began')

def new_journal(path, value):
    # Exclusive creation prevents two concurrent invocations from overwriting rollback intent.
    with path.open('x', encoding='utf8') as f:
        f.write(json.dumps(value, indent=2) + '\n')
        f.flush()
        os.fsync(f.fileno())

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
    verify_snapshot(folder, data)
    check = health(device, data)
    require(check['software_checks_passed'], 'Protected feature stack needs review: ' + '; '.join(check['issues']))
    # Preflight the entire plan before the first write.
    for action in actions:
        validate_action(data, action)
        if action['kind'] == 'package':
            require(action['package'] != check['home'].split('/')[0], 'Refusing to disable the current HOME')
            validate_target(device, data, action['package'])
        require(state_now(device, action) == action['before'], 'Device state changed since snapshot')
    print(json.dumps(actions, indent=2))
    if not execute:
        print('Preview only. Add --execute to apply the displayed plan.')
        return
    if not actions:
        print('Nothing to change; no trial journal created.')
        return
    path = folder / 'trial-journal.json'
    require(not path.exists(), 'A trial journal already exists; restore or take a fresh snapshot')
    journal = {'schema': 1, 'identity': data['identity'], 'snapshot_sha256': metadata_hash(data), 'created_utc': utc(), 'actions': actions}
    new_journal(path, journal)
    for action in actions:
        if action['kind'] == 'package': validate_target(device, data, action['package'])
        require(state_now(device, action) == action['before'], 'State changed during apply; use the journal to restore attempted changes')
        action['attempted'] = True
        save(path, journal)
        write_action(device, action, action['after'])
        action['verified'] = True
        save(path, journal)
    after = health(device, data)
    save(folder/'after-apply.json', after)
    require(after['software_checks_passed'], 'Protected stack changed; inspect after-apply.json and restore the trial')
    print('Applied and verified. No reboot performed; see docs/RESTORE.md.')

def restore(device, folder, data, execute):
    validate_binding(device, data)
    path = folder / 'trial-journal.json'
    journal = json.loads(path.read_text(encoding='utf8')) if path.exists() else {'schema': 1, 'identity': data['identity'], 'actions': []}
    journal_binding(journal, data)
    home_record = home_rollback(device, folder, data)
    require(path.exists() or (folder/'home-journal.json').exists(), 'No cleanup or HOME trial journal found in this snapshot')
    actions = [a for a in reversed(journal['actions']) if a.get('attempted') and not a.get('restored')]
    # Validate journal entries against the saved snapshot before any device writes.
    for action in actions:
        validate_action(data, action)
        if action['kind'] == 'package': validate_target(device, data, action['package'])
        require(state_now(device, action) in (action['before'], action['after']), 'State diverged; inspect before restore')
    print(json.dumps({'home': home_record['original'] if home_record else None, 'actions': actions}, indent=2))
    if not execute:
        print('Preview only. Add --execute to restore these original values.')
        return
    if home_record: restore_home(device, folder, home_record)
    for action in actions:
        if action['kind'] == 'package': validate_target(device, data, action['package'])
        require(state_now(device, action) in (action['before'], action['after']), 'State changed during restore; inspect the journal')
        action['restore_attempted'] = True
        save(path, journal)
        write_action(device, action, action['before'])
        action['restored'] = True
        save(path, journal)
    after = health(device, data)
    save(folder/'after-restore.json', after)
    require(after['software_checks_passed'], 'Journal rollback finished, but protected stack still needs review; see after-restore.json')
    print('Restored journaled values. App data retained.')

def ensure_home(device, target):
    target = component(target)
    require(available(device.package(target.split('/')[0])), 'Selected HOME is missing, disabled, hidden or suspended')
    require(target in device.homes(), 'Selected activity is not an available HOME handler')
    return target

def launch_home(device, target):
    target = ensure_home(device, target)
    result = device.shell('cmd', 'package', 'set-home-activity', '--user', '0', target)
    require('Success' in result, 'Default HOME change failed: ' + result)
    require(device.home() == target, 'Default HOME did not match request')
    result = device.shell('am', 'start', '-W', '-a', 'android.intent.action.MAIN', '-c', 'android.intent.category.HOME', '-n', target)
    require(not re.search(r'(^|\n)(?:Error|Exception)|Permission Denial|SecurityException', result), 'HOME launch failed: ' + result)
    require(device.home() == target, 'Default HOME changed during launch; restore the original')

def home_rollback(device, folder, data):
    path = folder/'home-journal.json'
    if not path.exists(): return None
    record = json.loads(path.read_text(encoding='utf8'))
    journal_binding(record, data)
    require(record['original'] == component(data['home']) and record['target'] in {component(x) for x in HOMES.values()}
            and record['original'] != record['target'], 'Invalid HOME journal')
    if record.get('restored') or not record.get('attempted'): return None
    require(device.home() in (record['original'], record['target']), 'Default HOME diverged; inspect the journal and choose the original manually')
    ensure_home(device, record['original'])
    return record

def restore_home(device, folder, record):
    # Keep rollback intent even if launch or reconnection fails after set-home-activity.
    require(device.home() in (record['original'], record['target']), 'HOME changed during restore')
    record['restore_attempted'] = True
    save(folder/'home-journal.json', record)
    launch_home(device, record['original'])
    record['restored'] = True
    save(folder/'home-journal.json', record)

def switch_home(device, folder, data, choice, execute):
    validate_binding(device, data)
    if choice == 'original':
        target = ensure_home(device, data['home'])
        record = home_rollback(device, folder, data)
        print('Restore original HOME: ' + target)
        if not execute:
            print('Preview only. Add --execute to restore the original HOME.')
            return
        if record:
            restore_home(device, folder, record)
        elif device.home() != target:
            recovery = {'schema': 1, 'identity': data['identity'], 'before': device.home(), 'target': target,
                        'attempted': True, 'created_utc': utc()}
            new_journal(folder/'home-recovery.json', recovery)
            launch_home(device, target)
            recovery['verified'] = True; save(folder/'home-recovery.json', recovery)
        return
    verify_snapshot(folder, data)
    target = ensure_home(device, HOMES[choice])
    original = component(data['home'])
    require(device.home() == original, 'HOME changed since snapshot; inspect it before a new trial')
    if target == original:
        print('Requested HOME is already the original default; no changes made.')
        return
    if original.split('/')[0] in ('app.lawnchair', 'io.atoto.home'):
        require(data.get('launcher_export'), 'Attach the original Lawnchair native export before switching HOME')
    before = health(device, data)
    require(before['software_checks_passed'], 'Protected stack needs review before a launcher trial: ' + '; '.join(before['issues']))
    print('Set HOME to ' + target + '; original: ' + original)
    if not execute:
        print('Preview only. Add --execute after testing MAIN / LAUNCHER and backing up the original layout.')
        return
    record = {'schema': 1, 'identity': data['identity'], 'snapshot_sha256': metadata_hash(data),
              'original': original, 'target': target, 'created_utc': utc(), 'attempted': True}
    new_journal(folder/'home-journal.json', record)
    launch_home(device, target)
    record['verified'] = True; save(folder/'home-journal.json', record)
    print('HOME switched; recovery: home original --snapshot ' + str(folder) + ' --execute')

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
    attach = sub.add_parser('attach-export'); attach.add_argument('--snapshot', type=Path, required=True); attach.add_argument('--file', type=Path, required=True)
    check = sub.add_parser('check'); check.add_argument('--snapshot', type=Path, required=True); check.add_argument('--out', type=Path)
    home = sub.add_parser('home'); home.add_argument('choice', choices=['original', *HOMES]); home.add_argument('--snapshot', type=Path, required=True); home.add_argument('--execute', action='store_true')
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
        switch_home(d, a.snapshot, load_snapshot(a.snapshot), a.choice, a.execute)
    else:
        data = load_snapshot(a.snapshot)
        if a.command == 'verify':
            verify_snapshot(a.snapshot, data)
            print('Saved APK hashes verified offline; this does not verify private app data or firmware restoration.')
        elif a.command == 'attach-export':
            attach_export(a.snapshot, data, a.file)
        elif a.command == 'check':
            validate_binding(d, data)
            if a.out: require(not a.out.exists(), 'Report path already exists; choose a new output path')
            report = health(d, data)
            if a.out: save(a.out, report)
            print(json.dumps(report, indent=2))
            require(report['software_checks_passed'], 'Protected stack checks need review; do not make further cleanup changes')
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
