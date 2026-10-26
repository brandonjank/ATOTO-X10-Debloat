"""Create a reviewed source ZIP plus per-file manifest and ZIP checksum."""
import argparse, hashlib, json, zipfile
from pathlib import Path
from check_release import main as check, release_files

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
check()
if a.out.exists(): p.error('Output already exists; choose a new release filename')
a.out.parent.mkdir(parents=True, exist_ok=True)
manifest = {'version': json.loads((Path(__file__).resolve().parents[1]/'release-files.json').read_text())['version'], 'kind': 'source-only', 'files': []}
with zipfile.ZipFile(a.out, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, path in release_files():
        # Source exports use LF on every host, matching .gitattributes.
        data = path.read_text(encoding='utf8').encode('utf8')
        # Fixed ZIP timestamp and sorted allowlist make repeated source exports stable.
        entry = zipfile.ZipInfo('ATOTO-X10-Debloat/' + name, date_time=(2026, 10, 25, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(entry, data)
        manifest['files'].append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    z.writestr(zipfile.ZipInfo('ATOTO-X10-Debloat/RELEASE-MANIFEST.json', date_time=(2026, 10, 25, 0, 0, 0)), json.dumps(manifest, indent=2)+'\n')
sha = hashlib.sha256(a.out.read_bytes()).hexdigest()
a.out.with_suffix('.sha256').write_text(sha+'  '+a.out.name+'\n', encoding='ascii')
print(json.dumps({'archive': str(a.out), 'sha256': sha, 'files': len(manifest['files']), 'published': False}, indent=2))
