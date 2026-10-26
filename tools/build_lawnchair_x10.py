"""Build a separately installed, signed dock-only adaptation of the pinned APK.

Original binary XML/resources are preserved except explicit package identities.
No application is installed, removed, or granted permissions by this script.
"""
import argparse
import os
import difflib
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--tools', type=Path, required=True, help='Private SDK/JDK paths JSON')
p.add_argument('--apktool', type=Path, required=True)
p.add_argument('--base-apk', type=Path, required=True)
p.add_argument('--work', type=Path, default=ROOT/'.local/lawnchair-x10')
p.add_argument('--keystore', type=Path, required=True)
p.add_argument('--alias', default='x10-home')
p.add_argument('--generate-key', action='store_true')
args = p.parse_args()
assert os.environ.get('X10_SIGNING_PASSWORD'), 'Set X10_SIGNING_PASSWORD privately'
WORK = args.work.resolve()
DECODED = WORK/'binary-resources'
BUILD = WORK/'build'
BUILD.mkdir(parents=True, exist_ok=True)
TOOLS = json.loads(args.tools.read_text(encoding='utf8'))
APKTOOL = args.apktool.resolve()
ORIGINAL = args.base_apk.resolve()
assert hashlib.sha256(APKTOOL.read_bytes()).hexdigest() == '56d59c524fc764263ba8d345754d8daf55b1887818b15cd3b594f555d249e2db', 'Use pinned Apktool 2.11.1'
OLD, NEW = 'app.lawnchair', 'io.atoto.home'
assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() == 'd4200d0985169fd79ba1bd225d653f2a2fe7b50aa07cb0d05ca64c7623f86059'

def run(args, label):
    with (BUILD/(label+'.log')).open('w', encoding='utf8') as f:
        r = subprocess.run(list(map(str,args)), stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        print((BUILD/(label+'.log')).read_text(encoding='utf8')[-4000:])
        raise SystemExit(r.returncode)

# A clean checkout must not require someone else's decoded APK tree.
if not DECODED.exists():
    run([TOOLS['java'], '-Xmx3g', '-jar', APKTOOL, 'd', '-r', ORIGINAL, '-o', DECODED], 'decode')
    (WORK/'decoded-base.sha256').write_text(hashlib.sha256(ORIGINAL.read_bytes()).hexdigest())
assert (WORK/'decoded-base.sha256').read_text().strip() == hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()

def method_hook(text, signature, invocation, at_end=False):
    start = text.index(signature)
    end = text.index('.end method', start)
    block = text[start:end]
    if invocation in block: return text
    if at_end:
        assert block.count('return-void') == 1
        block = block.replace('    return-void', invocation+'\n\n    return-void')
    else:
        block, count = re.subn(r'(    \.locals \d+\n)', r'\1\n'+invocation+'\n', block, count=1)
        assert count == 1
    return text[:start]+block+text[end:]

def clone_literal(value):
    authorities = {
        OLD+'.fileprovider', OLD+'.search.LawnchairRecentSuggestionProvider',
        OLD+'.overview.fileprovider', OLD+'.settings', OLD+'.grid_control', OLD+'.TestInfo',
    }
    if value == OLD or value in authorities or value.startswith(OLD+'.permission.') or value == OLD+'.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION':
        return NEW+value[len(OLD):]
    if value.startswith('content://'+OLD+'.'):
        return 'content://'+NEW+value[len('content://'+OLD):]
    return value

changes = []
changed_dex = {'smali','smali_classes3'}
found=subprocess.run(['rg','-l','-g','*.smali',r'"(?:app\.lawnchair|io\.atoto\.home)(?:"|\.(?:permission\.|fileprovider|search\.LawnchairRecentSuggestionProvider|overview\.fileprovider|settings|grid_control|TestInfo|DYNAMIC_RECEIVER))|content://app\.lawnchair\.',str(DECODED)],capture_output=True,text=True,encoding='utf8',check=True)
candidates={Path(x) for x in found.stdout.splitlines()}
candidates.update(DECODED/'smali_classes3/com/android/launcher3'/name for name in ['DeviceProfile.smali','Hotseat.smali','BubbleTextView.smali'])
for file in sorted(candidates):
    text = file.read_text(encoding='utf8')
    before = text
    text = re.sub(r'(?P<head>const-string(?:/jumbo)? [^,]+, ")(?P<value>[^"\n]+)(?P<tail>")',
                  lambda m:m['head']+clone_literal(m['value'])+m['tail'], text)
    # Inlined APPLICATION_ID values are handled above; retain Java class names.
    text = text.replace('.field public static final APPLICATION_ID:Ljava/lang/String; = "'+OLD+'"',
                        '.field public static final APPLICATION_ID:Ljava/lang/String; = "'+NEW+'"')
    if file.name == 'DeviceProfile.smali' and file.parent.name == 'launcher3':
        text=text.replace('invoke-static/range {p0 .. p1}, Lio/atoto/home/X10Dock;->profile(Ljava/lang/Object;Landroid/content/Context;)V',
                          'invoke-static/range {p0 .. p0}, Lio/atoto/home/X10Dock;->profile(Ljava/lang/Object;)V')
        signature = next(x for x in text.splitlines() if x.startswith('.method public constructor <init>('))
        text = method_hook(text, signature,
            '    invoke-static/range {p0 .. p0}, Lio/atoto/home/X10Dock;->profile(Ljava/lang/Object;)V', True)
    if file.name == 'Hotseat.smali' and file.parent.name == 'launcher3':
        needle = '    iget v2, v1, Landroid/graphics/Rect;->left:I'
        call = '    invoke-static {p0, v0, v1}, Lio/atoto/home/X10Dock;->padding(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;Landroid/graphics/Rect;)V'
        if call not in text:
            assert text.count(needle) == 1
            text = text.replace(needle,call+'\n\n'+needle)
    if file.name == 'BubbleTextView.smali' and file.parent.name == 'launcher3':
        text = method_hook(text, '.method public applyIconAndLabel(Lcom/android/launcher3/model/data/ItemInfoWithIcon;)V',
            '    invoke-static {p0, p1}, Lio/atoto/home/X10Dock;->icon(Landroid/widget/TextView;Ljava/lang/Object;)V')
    if text != before:
        file.write_text(text, encoding='utf8')
        rel = file.relative_to(DECODED)
        changed_dex.add(rel.parts[0])
        changes.append(''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile=str(rel),tofile=str(rel))))
if changes:
    previous=(BUILD/'changes.patch').read_text(encoding='utf8') if (BUILD/'changes.patch').exists() else ''
    (BUILD/'changes.patch').write_text(previous+'\n'.join(changes),encoding='utf8')
else:
    # Preserve the first build's reviewed diff and rebuild its already patched trees.
    for file in DECODED.glob('smali*/**/*.smali'):
        if 'Lio/atoto/home/X10Dock;' in file.read_text(encoding='utf8'):
            changed_dex.add(file.relative_to(DECODED).parts[0])
    if (BUILD/'changed-dex.json').exists():changed_dex.update(json.loads((BUILD/'changed-dex.json').read_text()))
(BUILD/'changed-dex.json').write_text(json.dumps(sorted(changed_dex)))
reassembled=BUILD/'reassembled.apk'
configuration=DECODED/'apktool.yml'
settings=configuration.read_text(encoding='utf8')
settings=re.sub(r'sdkInfo:\n(?:  [^\n]*\n)*',"sdkInfo:\n  minSdkVersion: '26'\n  targetSdkVersion: '35'\n",settings,count=1)
configuration.write_text(settings,encoding='utf8')
run([TOOLS['java'],'-Xmx3g','-jar',APKTOOL,'b','-f',DECODED,'-o',reassembled],'assemble')
with zipfile.ZipFile(reassembled) as built:
    for folder in sorted(changed_dex):
        dex_name = 'classes.dex' if folder == 'smali' else folder.removeprefix('smali_')+'.dex'
        data=built.read(dex_name)
        assert data[:8]==b'dex\n038\0', 'Preserve the original API26 DEX interface/default-method semantics'
        (BUILD/dex_name).write_bytes(data)
        print('Assembled',dex_name,flush=True)

classes = BUILD/'helper-classes';classes.mkdir(exist_ok=True)
helper_dex = BUILD/'helper-dex';helper_dex.mkdir(exist_ok=True)
run([TOOLS['javac'],'-source','8','-target','8','-classpath',TOOLS['android_jar'],'-d',classes,ROOT/'android/lawnchair-x10/src/io/atoto/home/X10Dock.java'],'javac')
run([TOOLS['java'],'-cp',TOOLS['d8_jar'],'com.android.tools.r8.D8','--release','--min-api','26','--lib',TOOLS['android_jar'],'--output',helper_dex,*classes.rglob('*.class')],'d8')

def decode_length(data, pos, utf8):
    if utf8:
        a=data[pos];return (((a&127)<<8)|data[pos+1],2) if a&128 else (a,1)
    a=struct.unpack_from('<H',data,pos)[0]
    return (((a&32767)<<16)|struct.unpack_from('<H',data,pos+2)[0],4) if a&32768 else (a,2)

def pool_strings(pool):
    _,header,size,count,styles,flags,start,style_start=struct.unpack_from('<HH6I',pool)
    result=[]
    for i in range(count):
        pos=start+struct.unpack_from('<I',pool,header+4*i)[0]
        length,n=decode_length(pool,pos,bool(flags&256));pos+=n
        if flags&256:
            length,n=decode_length(pool,pos,True);pos+=n
            result.append(pool[pos:pos+length].decode('utf8'))
        else:result.append(pool[pos:pos+length*2].decode('utf-16le'))
    return result

def append_strings(pool, added):
    typ,header,size,count,styles,flags,start,style_start=struct.unpack_from('<HH6I',pool)
    assert header==28
    offsets=pool[header:header+count*4]
    style_offsets=pool[header+count*4:start]
    string_data=pool[start:style_start or size]
    style_data=pool[style_start:] if style_start else b''
    def length8(n):return bytes([n]) if n<128 else bytes([(n>>8)|128,n&255])
    def length16(n):return struct.pack('<H',n) if n<32768 else struct.pack('<HH',(n>>16)|32768,n&65535)
    for s in added:
        offsets+=struct.pack('<I',len(string_data))
        raw=s.encode('utf8' if flags&256 else 'utf-16le')
        string_data+=(length8(len(s.encode('utf-16le'))//2)+length8(len(raw))+raw+b'\0') if flags&256 else length16(len(raw)//2)+raw+b'\0\0'
    string_data+=b'\0'*((-len(string_data))%4)
    new_start=start+len(added)*4
    new_style_start=new_start+len(string_data) if style_start else 0
    result=struct.pack('<HH6I',typ,header,new_start+len(string_data)+len(style_data),count+len(added),styles,flags&~1,new_start,new_style_start)+offsets+style_offsets+string_data+style_data
    assert len(result)%4==0
    return result

def manifest(raw):
    chunks=[];pos=struct.unpack_from('<H',raw,2)[0]
    while pos<len(raw):
        size=struct.unpack_from('<I',raw,pos+4)[0];chunks.append(bytearray(raw[pos:pos+size]));pos+=size
    pool_index=next(i for i,c in enumerate(chunks) if struct.unpack_from('<H',c)[0]==1)
    strings=pool_strings(chunks[pool_index]);added=[]
    def index(value):
        if value in strings:return strings.index(value)
        if value not in added:added.append(value)
        return len(strings)+added.index(value)
    edits=[]
    for chunk in chunks:
        if struct.unpack_from('<H',chunk)[0]!=0x102:continue
        element=strings[struct.unpack_from('<I',chunk,20)[0]]
        attr_start,attr_size,count=struct.unpack_from('<HHH',chunk,24)
        for i in range(count):
            off=16+attr_start+i*attr_size
            ns,name_idx,raw_idx=struct.unpack_from('<III',chunk,off)
            name=strings[name_idx]
            if element=='application' and name=='label':
                new_idx=index('Lawnchair X10')
                chunk[off+15]=3
                struct.pack_into('<I',chunk,off+8,new_idx)
                struct.pack_into('<I',chunk,off+16,new_idx)
                edits.append([element,name,'original application label','Lawnchair X10'])
                continue
            if chunk[off+15]!=3:continue
            value=strings[struct.unpack_from('<I',chunk,off+16)[0]];new=value
            if element=='manifest' and name=='package':new=NEW
            elif name in ('authorities','readPermission','writePermission','permission','taskAffinity'):
                if value==OLD or value.startswith(OLD+'.'):new=NEW+value[len(OLD):]
            elif name=='name' and element in ('permission','uses-permission'):
                new=clone_literal(value)
            elif element=='application' and name=='label':new='Lawnchair X10'
            if new!=value:
                new_idx=index(new);struct.pack_into('<I',chunk,off+16,new_idx)
                if raw_idx!=0xffffffff:struct.pack_into('<I',chunk,off+8,new_idx)
                edits.append([element,name,value,new])
    chunks[pool_index]=append_strings(chunks[pool_index],added)
    result=bytearray(raw[:8])+b''.join(chunks);struct.pack_into('<I',result,4,len(result))
    (BUILD/'manifest-edits.json').write_text(json.dumps(edits,indent=2)+'\n')
    return result

def resources(raw):
    data=bytearray(raw);pos=struct.unpack_from('<H',raw,2)[0];changed=0
    while pos<len(data):
        typ,header,size=struct.unpack_from('<HHI',data,pos)
        if typ==0x200 and struct.unpack_from('<I',data,pos+8)[0]==0x7f:
            assert data[pos+12:pos+268].decode('utf-16le').rstrip('\0')==OLD
            name=NEW.encode('utf-16le');data[pos+12:pos+268]=name+b'\0'*(256-len(name));changed+=1
        pos+=size
    assert changed==1
    return data

unsigned=BUILD/'lawnchair-x10-unsigned.apk'
with zipfile.ZipFile(ORIGINAL) as source,zipfile.ZipFile(unsigned,'w') as out:
    for entry in source.infolist():
        name=entry.filename
        if re.fullmatch(r'META-INF/[^/]+\.(RSA|DSA|EC|SF|MF)',name,re.I):continue
        data=source.read(name)
        if name=='AndroidManifest.xml':data=manifest(data)
        elif name=='resources.arsc':data=resources(data)
        elif re.fullmatch(r'classes\d*\.dex',name) and (BUILD/name).exists():data=(BUILD/name).read_bytes()
        out.writestr(entry,data)
    assert 'classes5.dex' not in source.namelist()
    out.writestr('classes5.dex',(helper_dex/'classes.dex').read_bytes(),compress_type=zipfile.ZIP_DEFLATED)
aligned=BUILD/'lawnchair-x10-aligned.apk';signed=BUILD/'Lawnchair-X10-dock.apk'
run([TOOLS['zipalign'],'-f','-p','4',unsigned,aligned],'zipalign')
key=args.keystore.resolve(); key.parent.mkdir(parents=True, exist_ok=True)
if not key.exists():
    assert args.generate_key, 'Keystore missing; use --generate-key for your own new signing identity'
    run([TOOLS['keytool'],'-genkeypair','-keystore',key,'-storetype','PKCS12','-storepass:env','X10_SIGNING_PASSWORD','-keypass:env','X10_SIGNING_PASSWORD','-alias',args.alias,'-keyalg','RSA','-keysize','3072','-validity','10000','-dname','CN=X10 Local Launcher,OU=Local Build'],'keytool')
run([TOOLS['java'],'-jar',TOOLS['apksigner_jar'],'sign','--ks',key,'--ks-pass','env:X10_SIGNING_PASSWORD','--ks-key-alias',args.alias,'--out',signed,aligned],'sign')
run([TOOLS['java'],'-jar',TOOLS['apksigner_jar'],'verify','--verbose','--print-certs',signed],'verify-signature')
record={'base_sha256':hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),'package':NEW,'apk':str(signed),'sha256':hashlib.sha256(signed.read_bytes()).hexdigest(),'bytes':signed.stat().st_size,'icon_px':80,'side_padding_px':32,'cell_height_px':108,'installed':False,'resource_files':'Original binary files; only resources.arsc package name changed','code_patch':'build/changes.patch','new_helper':'src/io/atoto/home/X10Dock.java'}
(BUILD/'build-manifest.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
