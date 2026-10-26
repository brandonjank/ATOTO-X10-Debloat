"""Build the compact, no-permission Audible widget with local Android tools."""
import argparse, hashlib, json, os, subprocess, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--tools', type=Path, required=True)
p.add_argument('--keystore', type=Path, required=True)
p.add_argument('--alias', default='x10-widget')
p.add_argument('--generate-key', action='store_true')
p.add_argument('--out', type=Path, default=ROOT/'.local/audible-widget')
a = p.parse_args()
if not os.environ.get('X10_SIGNING_PASSWORD'):
    p.error('Set X10_SIGNING_PASSWORD privately')
t = json.loads(a.tools.read_text(encoding='utf8'))
project = ROOT/'android/audible-widget'; b = a.out.resolve()
for directory in ('classes', 'dex', 'generated'): (b/directory).mkdir(parents=True, exist_ok=True)
def run(args):
    r = subprocess.run(list(map(str, args)), capture_output=True, text=True, encoding='utf8', errors='replace', timeout=120)
    if r.returncode: raise RuntimeError(r.stdout + r.stderr)
    return r.stdout
resources = b/'resources.zip'
run([t['aapt2'], 'compile', '--dir', project/'res', '-o', resources])
unsigned = b/'unsigned.apk'
run([t['aapt2'], 'link', '-I', t['android_jar'], '--manifest', project/'AndroidManifest.xml', '--java', b/'generated', '-o', unsigned, resources])
sources = list((project/'src').rglob('*.java')) + list((b/'generated').rglob('*.java'))
run([t['javac'], '-encoding', 'UTF-8', '-source', '8', '-target', '8', '-classpath', t['android_jar'], '-d', b/'classes', *sources])
run([t['java'], '-cp', t['d8_jar'], 'com.android.tools.r8.D8', '--release', '--min-api', '26', '--lib', t['android_jar'], '--output', b/'dex', *list((b/'classes').rglob('*.class'))])
with zipfile.ZipFile(unsigned, 'a') as z: z.write(b/'dex/classes.dex', 'classes.dex', compress_type=zipfile.ZIP_STORED)
aligned = b/'aligned.apk'; run([t['zipalign'], '-f', '4', unsigned, aligned])
key = a.keystore.resolve(); key.parent.mkdir(parents=True, exist_ok=True)
if not key.exists():
    if not a.generate_key: p.error('Keystore missing; use --generate-key for a new private signing identity')
    run([t['keytool'], '-genkeypair', '-keystore', key, '-storetype', 'PKCS12', '-storepass:env', 'X10_SIGNING_PASSWORD',
         '-keypass:env', 'X10_SIGNING_PASSWORD', '-alias', a.alias, '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000', '-dname', 'CN=X10 Audible Controls Local Build'])
apk = b/'x10-audible-controls.apk'
run([t['java'], '-jar', t['apksigner_jar'], 'sign', '--ks', key, '--ks-pass', 'env:X10_SIGNING_PASSWORD', '--ks-key-alias', a.alias, '--out', apk, aligned])
signature = run([t['java'], '-jar', t['apksigner_jar'], 'verify', '--verbose', '--print-certs', apk])
permissions = run([t['aapt2'], 'dump', 'permissions', apk])
if 'uses-permission' in permissions: raise RuntimeError('Unexpected requested permission')
result = {'apk': apk.name, 'sha256': hashlib.sha256(apk.read_bytes()).hexdigest(), 'requested_permissions': [],
          'signature': signature, 'device_tested': False}
(b/'build-manifest.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
print(json.dumps(result, indent=2))
