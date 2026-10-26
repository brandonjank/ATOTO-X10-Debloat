"""Offline checks of the prepared clone, package isolation and its narrow patch."""
import argparse,hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--base-apk',type=Path,required=True)
p.add_argument('--apk',type=Path,required=True)
a=p.parse_args()
from loguru import logger
logger.disable('androguard')
from androguard.core.apk import APK
from androguard.core.dex import DEX
old=a.base_apk
new=a.apk
before,after=APK(str(old)),APK(str(new))
NS='{http://schemas.android.com/apk/res/android}'
assert after.get_package()=='io.atoto.home'
assert after.get_app_name()=='Lawnchair X10'
def providers(apk):return {n.get(NS+'authorities') for n in apk.get_android_manifest_xml().iter('provider')}
assert not providers(before)&providers(after)
def normalize(value):return value.replace('io.atoto.home','app.lawnchair')
assert sorted(before.get_permissions())==sorted(map(normalize,after.get_permissions()))
application=next(after.get_android_manifest_xml().iter('application'))
assert application.get(NS+'debuggable','false')=='false'
assert not after.get_android_manifest_xml().get(NS+'sharedUserId')
assert before.get_min_sdk_version()==after.get_min_sdk_version()
assert before.get_target_sdk_version()==after.get_target_sdk_version()
with zipfile.ZipFile(old) as a,zipfile.ZipFile(new) as b:
    changed=[n for n in a.namelist() if n in b.namelist() and a.read(n)!=b.read(n)]
    assert set(changed)=={'AndroidManifest.xml','resources.arsc','classes.dex','classes3.dex'},changed
    assert all(a.read(n)==b.read(n) for n in a.namelist() if n.startswith(('res/','lib/')))
    defs={}
    for name in ['classes.dex','classes2.dex','classes3.dex','classes4.dex','classes5.dex']:
        assert b.read(name)[:8]==b'dex\n038\0',('DEX version mismatch',name)
        d=DEX(b.read(name))
        for c in d.get_classes():
            assert c.get_name() not in defs
            defs[c.get_name()]=c
    assert 'Lio/atoto/home/X10Dock;' in defs
    hooks={}
    for cname,name in [('DeviceProfile','<init>'),('Hotseat','setInsets'),('BubbleTextView','applyIconAndLabel')]:
        cls=defs['Lcom/android/launcher3/'+cname+';']
        calls=[i.get_output() for m in cls.get_methods() if m.get_name()==name for i in m.get_instructions() if 'Lio/atoto/home/X10Dock;' in i.get_output()]
        assert len(calls)==1,(cname,calls)
        hooks[cname]=calls
    expected_before=set()
    for name in ['classes.dex','classes2.dex','classes3.dex','classes4.dex']:
        expected_before.update(c.get_name() for c in DEX(a.read(name)).get_classes())
    assert set(defs)==expected_before|{'Lio/atoto/home/X10Dock;'}
result={'package':after.get_package(),'label':after.get_app_name(),'sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'permissions_added':[],'provider_authorities_overlap':False,'debuggable':False,'shared_uid':False,'changed_original_zip_entries':changed,'original_resource_files_and_native_libraries_unchanged':True,'original_class_set_retained':True,'hook_calls':hooks,'installed_or_device_tested':False,'layout_plan':{'screen_width_px':1280,'side_padding_px':32,'eight_cell_width_px':152,'icon_px':80,'expected_cell_height_px':108}}
(new.parent/'offline-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
