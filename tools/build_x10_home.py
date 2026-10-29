"""Build our source-only, ordinary-UID X10 Home dashboard. Does not install it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tools',type=Path,required=True)
parser.add_argument('--keystore',type=Path,required=True)
parser.add_argument('--alias',default='x10-home')
parser.add_argument('--generate-key',action='store_true')
parser.add_argument('--out',type=Path,default=ROOT/'.local/x10-home')
args=parser.parse_args()
if not os.environ.get('X10_SIGNING_PASSWORD'):parser.error('Set X10_SIGNING_PASSWORD privately')
tools=json.loads(args.tools.read_text(encoding='utf8'))
project=ROOT/'android/x10-home'
out=args.out.resolve()
if out.exists():parser.error('Output exists; preserve it and choose a new build folder')
if out.is_relative_to(ROOT) and not out.is_relative_to(ROOT/'.local'):
    parser.error('Build outputs belong in ignored .local/ or outside source')
out.mkdir(parents=True)
for directory in ('generated','classes','dex'):(out/directory).mkdir()

def run(command):
    result=subprocess.run(list(map(str,command)),capture_output=True,text=True,encoding='utf8',errors='replace',timeout=120)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return result.stdout

run([tools['aapt2'],'compile','--dir',project/'res','-o',out/'resources.zip'])
run([tools['aapt2'],'link','-I',tools['android_jar'],'--manifest',project/'AndroidManifest.xml',
     '--java',out/'generated','-o',out/'unsigned.apk',out/'resources.zip'])
sources=sorted((project/'src').rglob('*.java'))+sorted((out/'generated').rglob('*.java'))
run([tools['javac'],'-encoding','UTF-8','-source','8','-target','8','-classpath',tools['android_jar'],
     '-d',out/'classes',*sources])
run([tools['java'],'-cp',tools['d8_jar'],'com.android.tools.r8.D8','--release','--min-api','26',
     '--lib',tools['android_jar'],'--output',out/'dex',*sorted((out/'classes').rglob('*.class'))])
with zipfile.ZipFile(out/'unsigned.apk','a') as archive:
    archive.write(out/'dex/classes.dex','classes.dex',compress_type=zipfile.ZIP_STORED)
run([tools['zipalign'],'-p','4',out/'unsigned.apk',out/'aligned.apk'])
key=args.keystore.resolve()
key.parent.mkdir(parents=True,exist_ok=True)
if not key.exists():
    if not args.generate_key:parser.error('Key is missing; use --generate-key for a dedicated development identity')
    run([tools['keytool'],'-genkeypair','-keystore',key,'-storetype','PKCS12','-storepass:env','X10_SIGNING_PASSWORD',
         '-keypass:env','X10_SIGNING_PASSWORD','-alias',args.alias,'-keyalg','RSA','-keysize','3072',
         '-validity','10000','-dname','CN=X10 Home Local Development'])
apk=out/'X10-Home-0.1.0-preview.apk'
run([tools['java'],'-jar',tools['apksigner_jar'],'sign','--ks',key,'--ks-pass','env:X10_SIGNING_PASSWORD',
     '--ks-key-alias',args.alias,'--out',apk,out/'aligned.apk'])
verification=run([tools['java'],'-jar',tools['apksigner_jar'],'verify','--verbose','--print-certs',apk])
permissions=run([tools['aapt2'],'dump','permissions',apk])
if 'uses-permission' in permissions:raise RuntimeError('Unexpected requested permission')
with zipfile.ZipFile(apk) as archive:
    if archive.getinfo('resources.arsc').compress_type!=zipfile.ZIP_STORED:
        raise RuntimeError('Resource table must be stored for ordinary Android installation')
source_hashes={str(p.relative_to(project).as_posix()):hashlib.sha256(p.read_bytes()).hexdigest()
               for p in project.rglob('*') if p.is_file()}
report={'package':'io.atoto.x10home','apk':apk.name,'bytes':apk.stat().st_size,
        'sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'permissions':[],
        'source_hashes':source_hashes,'signature_verification':verification,'installed':False,
        'default_home_changed':False,'physical_features_tested':False}
(out/'build.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ('source_hashes','signature_verification')},indent=2))
