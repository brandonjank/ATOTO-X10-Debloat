"""Validate the reviewed export allowlist and look for common private data."""
import hashlib, json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = {'.apk', '.img', '.bin', '.jks', '.keystore', '.p12', '.pfx', '.pem', '.key', '.lawnchairbackup', '.zip', '.gz', '.log'}
PATTERNS = {
    'private IPv4': r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b',
    'ADB device identity': r'adb-[0-9a-f]{8}-[A-Za-z0-9]+\._adb',
    'private key': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'personal Windows path': r'[A-Za-z]:[\\/](?:Users|Projects)[\\/]',
    'GitHub token': r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b',
}

def release_files():
    names = json.loads((ROOT/'release-files.json').read_text(encoding='utf8'))['files']
    if len(names) != len(set(names)): raise RuntimeError('Duplicate export entry')
    files = []
    for name in names:
        pure = PurePosixPath(name)
        if pure.is_absolute() or '..' in pure.parts or '\\' in name: raise RuntimeError('Unsafe export path')
        path = ROOT.joinpath(*pure.parts)
        if not path.resolve().is_relative_to(ROOT.resolve()) or path.is_symlink(): raise RuntimeError('External export path')
        if path.suffix.lower() in BLOCKED: raise RuntimeError('Binary/private file in source export: ' + name)
        if not path.is_file(): raise RuntimeError('Missing export file: ' + name)
        text = path.read_text(encoding='utf8')
        for label, pattern in PATTERNS.items():
            if re.search(pattern, text): raise RuntimeError(label + ' in ' + name)
        files.append((name, path))
    return files

def main():
    files = release_files()
    reviewed = {name for name, _ in files}
    generated = {'.git', '.local', '.tools', 'out', 'downloads', 'build', 'binary-resources', '__pycache__'}
    unexpected = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
                  if p.is_file() and not (set(p.relative_to(ROOT).parts) & generated)
                  and p.relative_to(ROOT).as_posix() not in reviewed
                  and p != ROOT/'RELEASE-MANIFEST.json']
    if unexpected: raise RuntimeError('Files outside reviewed source list: ' + ', '.join(unexpected))
    manifest = ROOT/'RELEASE-MANIFEST.json'
    if manifest.exists():
        entries = json.loads(manifest.read_text(encoding='utf8'))['files']
        if len(entries) != len(files) or {e['path'] for e in entries} != reviewed:
            raise RuntimeError('Release manifest does not match reviewed files')
        for entry in entries:
            data = (ROOT/entry['path']).read_bytes()
            if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise RuntimeError('Release source changed: ' + entry['path'])
    # Follow local Markdown links in reviewed source, excluding external URLs and fragments.
    known = {p.resolve() for _, p in files}
    for name, path in files:
        if path.suffix != '.md': continue
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf8')):
            if '://' in target or target.startswith('#'): continue
            dest = (path.parent/target.split('#')[0]).resolve()
            if dest not in known: raise RuntimeError('Unexported/broken document link in ' + name + ': ' + target)
    print(f'Checked {len(files)} reviewed source files; no blocked files or common private-data patterns.')

if __name__ == '__main__': main()
