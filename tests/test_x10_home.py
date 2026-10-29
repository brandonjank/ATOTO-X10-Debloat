"""Source boundary and pure-JVM layout checks for our new dashboard."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'android/x10-home'
NS='{http://schemas.android.com/apk/res/android}'


class HomeSourceTests(unittest.TestCase):
    def test_manifest_is_an_ordinary_home_with_no_requested_permissions(self):
        xml=ET.parse(PROJECT/'AndroidManifest.xml').getroot()
        self.assertEqual(xml.get('package'),'io.atoto.x10home')
        self.assertIsNone(xml.get(NS+'sharedUserId'))
        self.assertEqual(list(xml.iter('uses-permission')),[])
        app=xml.find('application')
        self.assertEqual(app.get(NS+'debuggable'),'false')
        self.assertEqual(list(app.iter('service')),[])
        self.assertEqual(list(app.iter('receiver')),[])
        self.assertEqual(list(app.iter('provider')),[])
        self.assertEqual(len(app.findall('activity')),1)
        categories={v.get(NS+'name') for v in app.iter('category')}
        self.assertTrue({'android.intent.category.HOME','android.intent.category.LAUNCHER'}<=categories)

    def test_generated_apks_and_signing_are_not_source_inputs(self):
        self.assertFalse(any(p.suffix in {'.apk','.dex','.jar','.p12','.jks','.so'} for p in PROJECT.rglob('*')))
        for source in (PROJECT/'src').rglob('*.java'):
            self.assertIn('SPDX-License-Identifier: Apache-2.0',source.read_text())

    def test_layout_bounds_and_touch_geometry_on_jvm(self):
        javac=os.environ.get('X10_TEST_JAVAC') or shutil.which('javac')
        java=os.environ.get('X10_TEST_JAVA') or shutil.which('java')
        if not javac or not java:self.skipTest('A JDK is needed for pure-JVM geometry verification')
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            source=out/'LayoutCheck.java'
            source.write_text('''
import io.atoto.x10home.HomeLayout;
public class LayoutCheck {
 static void require(boolean value){if(!value)throw new AssertionError();}
 static boolean overlaps(HomeLayout.Box a,HomeLayout.Box b){
  return a.x<b.x+b.width&&b.x<a.x+a.width&&a.y<b.y+b.height&&b.y<a.y+a.height;
 }
 public static void main(String[] args){
  int cases=0;
  for(int w=600;w<=2560;w+=73)for(int h=300;h<=1440;h+=41){
   HomeLayout l=new HomeLayout(w,h);
   HomeLayout.Box[] all=new HomeLayout.Box[14];all[0]=l.toolbar;
   System.arraycopy(l.panels,0,all,1,5);System.arraycopy(l.dock,0,all,6,8);
   for(int i=0;i<all.length;i++){
    HomeLayout.Box b=all[i];require(b.width>0&&b.height>0&&b.x>=0&&b.y>=0&&b.x+b.width<=w&&b.y+b.height<=h);
    for(int j=0;j<i;j++)require(!overlaps(b,all[j]));
   }
   require(l.dock[0].x==32&&l.dock[7].x+l.dock[7].width==w-32);cases++;
  }
  HomeLayout nativeLayout=new HomeLayout(1280,662);
  require(nativeLayout.dock[0].width==152&&nativeLayout.dock[0].height>=104);
  boolean rejected=false;try{new HomeLayout(500,200);}catch(IllegalArgumentException expected){rejected=true;}
  require(rejected);System.out.println(cases+" layouts checked");
 }
}
''',encoding='utf8')
            subprocess.run([javac,'-d',str(out),str(PROJECT/'src/io/atoto/x10home/HomeLayout.java'),str(source)],check=True,capture_output=True)
            result=subprocess.run([java,'-cp',str(out),'LayoutCheck'],check=True,capture_output=True,text=True)
            self.assertIn('layouts checked',result.stdout)


if __name__=='__main__':unittest.main()
