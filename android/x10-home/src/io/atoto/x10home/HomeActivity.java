// SPDX-License-Identifier: Apache-2.0
package io.atoto.x10home;

import android.app.*;
import android.app.role.RoleManager;
import android.appwidget.*;
import android.content.*;
import android.content.pm.*;
import android.graphics.Color;
import android.graphics.drawable.*;
import android.os.Bundle;
import android.provider.Settings;
import android.view.*;
import android.widget.*;
import java.util.*;
import java.util.concurrent.*;

/** Ordinary-UID dashboard. Widgets and apps retain their own hardware/network ownership. */
public final class HomeActivity extends Activity {
    private static final int HOST=1010, BIND=100, CONFIG=102;
    private static final String[] TITLES={"Radio","Nearby traffic","Weather","Pandora","Audible"};
    private static final String[] DEFAULT_WIDGETS={
        "com.zhonghong.appwidgets/com.zhonghong.appwidgets.appwidget.SourceAppWidget3x4",
        "com.google.android.apps.maps/com.google.android.apps.gmm.widget.traffic.TrafficWidgetProvider",
        "com.zhonghong.weatherwidget/com.zhonghong.weatherwidget.widget.WeatherAppWidgetProvider3x2",
        "com.pandora.android/com.pandora.android.widget.Widget",
        "io.atoto.tools.audiblewidget/io.atoto.tools.audiblewidget.AudibleWidget"};
    private static final String[] LABELS={"Maps","Pandora","Audible","RCAM","Torque","ZLINK","Radio","Bluetooth"};
    private static final String[] DEFAULT_APPS={
        "com.google.android.apps.maps/com.google.android.maps.MapsActivity",
        "com.pandora.android/.LauncherActivity", "com.audible.application/.MainLauncher",
        "com.zhonghong.rearvideo/.MainActivity", "org.prowl.torque/.landing.FrontPage",
        "com.zjinnova.zlink/com.zjinnova.android.zlink.features.main.MainActivity",
        "com.zhonghong.radio/.MainActivity", "com.zhonghong.bluetooth/.MainActivity"};
    private AppWidgetHost host;
    private AppWidgetManager manager;
    private SharedPreferences prefs;
    private Dashboard dashboard;
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private boolean setupAll;
    private int pendingSlot=-1, pendingId=-1;

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        prefs=getSharedPreferences("home",MODE_PRIVATE);
        host=new AppWidgetHost(this,HOST);
        manager=AppWidgetManager.getInstance(this);
        pendingSlot=prefs.getInt("pending_slot",-1); pendingId=prefs.getInt("pending_id",-1);
        if(saved!=null) setupAll=saved.getBoolean("setup_all",false);
        rememberPreviousHome();
        render();
    }
    @Override protected void onStart(){super.onStart();host.startListening();}
    @Override protected void onStop(){host.stopListening();super.onStop();}
    @Override protected void onDestroy(){worker.shutdownNow();super.onDestroy();}
    @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);}
    @Override protected void onSaveInstanceState(Bundle out){out.putBoolean("setup_all",setupAll);super.onSaveInstanceState(out);}
    private int dp(float value){return Math.round(value*getResources().getDisplayMetrics().density);}
    private void say(String text){Toast.makeText(this,text,Toast.LENGTH_LONG).show();}
    private GradientDrawable background(int color,int radius){
        GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));return d;
    }
    private Button button(String title,Runnable action){
        Button b=new Button(this);b.setText(title);b.setAllCaps(false);b.setTextColor(0xffeaf2f5);
        b.setTextSize(16);b.setMinHeight(dp(48));b.setOnClickListener(v->action.run());return b;
    }
    private Button toolbarButton(String title,Runnable action){
        Button b=button(title,action);b.setBackground(new RippleDrawable(
            android.content.res.ColorStateList.valueOf(0x40ffffff),background(0xff282c30,8),null));
        b.setPadding(dp(16),0,dp(16),0);return b;
    }
    private void setupMenu(){
        new AlertDialog.Builder(this).setTitle("X10 Home")
            .setItems(new String[]{"Panels","Choose default home","Previous home"},(dialog,which)->{
                if(which==0)panelMenu();else if(which==1)chooseHome();else previousHome();
            }).setNegativeButton("Close",null).show();
    }
    private void render(){
        dashboard=new Dashboard();
        dashboard.setBackgroundColor(0xff101214);
        LinearLayout bar=new LinearLayout(this);bar.setGravity(Gravity.CENTER_VERTICAL);
        TextView brand=new TextView(this);brand.setText("X10 Home");brand.setTextColor(Color.WHITE);
        brand.setTextSize(20);brand.setTypeface(null,android.graphics.Typeface.BOLD);
        bar.addView(brand,new LinearLayout.LayoutParams(dp(144),-2));
        TextClock clock=new TextClock(this);clock.setFormat12Hour("EEE, MMM d  •  h:mm a");
        clock.setFormat24Hour("EEE, MMM d  •  HH:mm");clock.setTextColor(0xffedf5f7);clock.setTextSize(20);
        clock.setGravity(Gravity.CENTER_VERTICAL);clock.setSingleLine(true);
        clock.setEllipsize(android.text.TextUtils.TruncateAt.END);
        bar.addView(clock,new LinearLayout.LayoutParams(0,-1,1));
        LinearLayout.LayoutParams appsParams=new LinearLayout.LayoutParams(dp(96),dp(48));
        bar.addView(toolbarButton("Apps",()->appPicker(-1)),appsParams);
        LinearLayout.LayoutParams setupParams=new LinearLayout.LayoutParams(dp(112),dp(48));setupParams.leftMargin=dp(8);
        bar.addView(toolbarButton("Setup",()->setupMenu()),setupParams);
        dashboard.addView(bar);
        for(int i=0;i<5;i++){
            final int slot=i;
            FrameLayout panel=new FrameLayout(this);panel.setBackground(background(0xff1c2024,12));
            panel.setContentDescription(TITLES[i]+" panel");
            int id=prefs.getInt("widget_"+slot,-1);
            AppWidgetProviderInfo info=id<0?null:manager.getAppWidgetInfo(id);
            if(info!=null){
                try {
                    AppWidgetHostView view=host.createView(this,id,info);
                    view.setPadding(0,0,0,0);
                    panel.addView(view,new FrameLayout.LayoutParams(-1,-1));
                    panel.setTag(view);
                }catch(RuntimeException failure){
                    panel.addView(button("Re-add "+TITLES[i],()->requestWidget(slot,false)));
                }
            }else{
                Button add=button("Add "+TITLES[i],()->requestWidget(slot,false));
                panel.addView(add,new FrameLayout.LayoutParams(-1,-1));
            }
            dashboard.addView(panel);
        }
        for(int i=0;i<8;i++){
            final int index=i;
            LinearLayout cell=new LinearLayout(this);cell.setOrientation(LinearLayout.VERTICAL);
            cell.setGravity(Gravity.CENTER);cell.setFocusable(true);cell.setClickable(true);
            cell.setBackground(new RippleDrawable(android.content.res.ColorStateList.valueOf(0x40ffffff),
                new InsetDrawable(background(0xff1c2024,10),dp(3),0,dp(3),0),null));
            String target=prefs.getString("dock_"+i,DEFAULT_APPS[i]);
            String label=prefs.getString("dock_label_"+i,LABELS[i]);
            ImageView icon=new ImageView(this);icon.setScaleType(ImageView.ScaleType.FIT_CENTER);
            try {icon.setImageDrawable(getPackageManager().getActivityIcon(ComponentName.unflattenFromString(target)));}
            catch(Exception missing){icon.setImageResource(android.R.drawable.ic_menu_view);}
            cell.addView(icon,new LinearLayout.LayoutParams(dp(80),dp(80)));
            TextView title=new TextView(this);title.setText(label);title.setGravity(Gravity.CENTER);
            title.setTextColor(Color.WHITE);title.setTextSize(14);title.setSingleLine(true);
            cell.addView(title,new LinearLayout.LayoutParams(-1,dp(24)));
            cell.setContentDescription(label);cell.setOnClickListener(v->open(target));
            cell.setOnLongClickListener(v->{appPicker(index);return true;});
            dashboard.addView(cell);
        }
        setContentView(dashboard);
    }
    private void rememberPreviousHome(){
        ResolveInfo previous=getPackageManager().resolveActivity(new Intent(Intent.ACTION_MAIN)
            .addCategory(Intent.CATEGORY_HOME),PackageManager.MATCH_DEFAULT_ONLY);
        if(previous!=null && previous.activityInfo!=null && !previous.activityInfo.packageName.equals(getPackageName())
            && !previous.activityInfo.name.contains("ResolverActivity")){
            prefs.edit().putString("previous_home",new ComponentName(previous.activityInfo.packageName,
                previous.activityInfo.name).flattenToString()).apply();
        }
    }
    private void previousHome(){
        String previous=prefs.getString("previous_home",null);
        if(previous==null){say("Choose a home app in Android Settings");startActivity(new Intent(Settings.ACTION_HOME_SETTINGS));}
        else {
            try{startActivity(new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
                .setComponent(ComponentName.unflattenFromString(previous)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));}
            catch(RuntimeException unavailable){say("Previous home is unavailable; choose a home app in Settings");}
        }
    }
    @Override public void onBackPressed(){
        ResolveInfo home=getPackageManager().resolveActivity(new Intent(Intent.ACTION_MAIN)
            .addCategory(Intent.CATEGORY_HOME),PackageManager.MATCH_DEFAULT_ONLY);
        if(home!=null&&home.activityInfo!=null&&home.activityInfo.packageName.equals(getPackageName()))return;
        finish();
    }
    private void chooseHome(){
        if(android.os.Build.VERSION.SDK_INT>=29){
            RoleManager roles=getSystemService(RoleManager.class);
            if(roles!=null&&roles.isRoleAvailable(RoleManager.ROLE_HOME)){
                startActivityForResult(roles.createRequestRoleIntent(RoleManager.ROLE_HOME),103);return;
            }
        }
        startActivity(new Intent(Settings.ACTION_HOME_SETTINGS));
    }
    private void open(String flat){
        ComponentName component=ComponentName.unflattenFromString(flat);
        if(component==null){say("App shortcut is unavailable");return;}
        try{startActivity(new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
            .setComponent(component).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED));}
        catch(ActivityNotFoundException|SecurityException error){say("This app is unavailable; long-press to choose another");}
    }
    private void appPicker(int dock){
        worker.execute(()->{
            List<ResolveInfo> apps=getPackageManager().queryIntentActivities(new Intent(Intent.ACTION_MAIN)
                .addCategory(Intent.CATEGORY_LAUNCHER),0);
            Collections.sort(apps,new ResolveInfo.DisplayNameComparator(getPackageManager()));
            String[] names=new String[apps.size()];
            for(int i=0;i<apps.size();i++)names[i]=apps.get(i).loadLabel(getPackageManager()).toString();
            runOnUiThread(()->{
                if(isFinishing()||isDestroyed())return;
                new AlertDialog.Builder(this).setTitle(dock<0?"Apps":"Choose dock app")
                    .setItems(names,(dialog,which)->{
                        ActivityInfo app=apps.get(which).activityInfo;
                        String component=new ComponentName(app.packageName,app.name).flattenToString();
                        if(dock<0)open(component);
                        else{prefs.edit().putString("dock_"+dock,component).putString("dock_label_"+dock,names[which]).apply();render();}
                    }).setNegativeButton("Cancel",null).show();
            });
        });
    }
    private void panelMenu(){
        String[] choices={"Set up missing panels","Change Radio","Change Nearby traffic","Change Weather",
            "Change Pandora","Change Audible","Cancel pending setup"};
        new AlertDialog.Builder(this).setTitle("Panels").setItems(choices,(dialog,which)->{
            if(which==0){setupAll=true;setupNext(0);}
            else if(which==6){cancelPending();render();}
            else {setupAll=false;requestWidget(which-1,true);}
        }).setNegativeButton("Close",null).show();
    }
    private void setupNext(int from){
        for(int i=from;i<5;i++){
            int id=prefs.getInt("widget_"+i,-1);
            if(id<0||manager.getAppWidgetInfo(id)==null){requestWidget(i,false);return;}
        }
        setupAll=false;render();
    }
    private void requestWidget(int slot,boolean pick){
        if(pendingId>=0){say("Finish or cancel the pending panel setup first");return;}
        if(pick){
            List<AppWidgetProviderInfo> providers=manager.getInstalledProviders();
            Collections.sort(providers,(a,b)->a.loadLabel(getPackageManager()).compareToIgnoreCase(b.loadLabel(getPackageManager())));
            String[] names=new String[providers.size()];
            for(int i=0;i<providers.size();i++)names[i]=providers.get(i).loadLabel(getPackageManager());
            new AlertDialog.Builder(this).setTitle("Choose "+TITLES[slot]+" widget")
                .setItems(names,(dialog,which)->bindProvider(slot,providers.get(which).provider))
                .setNegativeButton("Cancel",null).show();return;
        }
        bindProvider(slot,ComponentName.unflattenFromString(DEFAULT_WIDGETS[slot]));
    }
    private void bindProvider(int slot,ComponentName provider){
        if(pendingId>=0){say("Finish or cancel the pending panel setup first");return;}
        pendingSlot=slot;pendingId=host.allocateAppWidgetId();
        prefs.edit().putInt("pending_id",pendingId).putInt("pending_slot",slot).commit();
        try{
            Bundle options=new Bundle();options.putInt(AppWidgetManager.OPTION_APPWIDGET_HOST_CATEGORY,AppWidgetProviderInfo.WIDGET_CATEGORY_HOME_SCREEN);
            if(manager.bindAppWidgetIdIfAllowed(pendingId,provider,options))configuredOrCommit();
            else startActivityForResult(new Intent(AppWidgetManager.ACTION_APPWIDGET_BIND)
                .putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID,pendingId)
                .putExtra(AppWidgetManager.EXTRA_APPWIDGET_PROVIDER,provider)
                .putExtra(AppWidgetManager.EXTRA_APPWIDGET_OPTIONS,options),BIND);
        }catch(RuntimeException error){cancelPending();say("This widget is unavailable; use Panels to choose another");}
    }
    private void configuredOrCommit(){
        AppWidgetProviderInfo info=manager.getAppWidgetInfo(pendingId);
        if(info==null){cancelPending();say("Widget was not added");return;}
        if(info.configure!=null){
            try{host.startAppWidgetConfigureActivityForResult(this,pendingId,0,CONFIG,null);}
            catch(RuntimeException error){cancelPending();say("Widget setup could not open");}
        }else commitPending();
    }
    private void commitPending(){
        int slot=pendingSlot,old=prefs.getInt("widget_"+slot,-1);
        prefs.edit().putInt("widget_"+slot,pendingId).remove("pending_id").remove("pending_slot").commit();
        pendingId=-1;pendingSlot=-1;
        if(old>=0)host.deleteAppWidgetId(old);
        render();if(setupAll)setupNext(slot+1);
    }
    private void cancelPending(){
        if(pendingId>=0)host.deleteAppWidgetId(pendingId);
        pendingId=-1;pendingSlot=-1;setupAll=false;
        prefs.edit().remove("pending_id").remove("pending_slot").commit();
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request!=BIND&&request!=CONFIG)return;
        if(pendingId<0||pendingSlot<0)return;
        if(result!=RESULT_OK){cancelPending();render();return;}
        if(request==CONFIG)commitPending();else configuredOrCommit();
    }
    private final class Dashboard extends ViewGroup {
        private final HashMap<Integer,String> sizes=new HashMap<>();
        Dashboard(){super(HomeActivity.this);}
        @Override protected void onMeasure(int widthSpec,int heightSpec){
            int width=MeasureSpec.getSize(widthSpec),height=MeasureSpec.getSize(heightSpec);
            setMeasuredDimension(width,height);
            if(width<dp(600)||height<dp(300))return;
            HomeLayout layout=new HomeLayout(Math.round(width/getResources().getDisplayMetrics().density),
                Math.round(height/getResources().getDisplayMetrics().density));
            for(int i=0;i<getChildCount();i++){
                HomeLayout.Box box=i==0?layout.toolbar:(i<=5?layout.panels[i-1]:layout.dock[i-6]);
                getChildAt(i).measure(MeasureSpec.makeMeasureSpec(dp(box.width),MeasureSpec.EXACTLY),
                    MeasureSpec.makeMeasureSpec(dp(box.height),MeasureSpec.EXACTLY));
            }
        }
        @Override protected void onLayout(boolean changed,int left,int top,int right,int bottom){
            int width=right-left,height=bottom-top;
            if(width<dp(600)||height<dp(300))return;
            HomeLayout layout=new HomeLayout(Math.round(width/getResources().getDisplayMetrics().density),
                Math.round(height/getResources().getDisplayMetrics().density));
            for(int i=0;i<getChildCount();i++){
                HomeLayout.Box b=i==0?layout.toolbar:(i<=5?layout.panels[i-1]:layout.dock[i-6]);
                View view=getChildAt(i);view.layout(dp(b.x),dp(b.y),dp(b.x+b.width),dp(b.y+b.height));
                if(i>=1&&i<=5&&view.getTag() instanceof AppWidgetHostView){
                    AppWidgetHostView widget=(AppWidgetHostView)view.getTag();
                    String size=b.width+"x"+b.height;
                    if(!size.equals(sizes.get(widget.getAppWidgetId()))){
                        sizes.put(widget.getAppWidgetId(),size);
                        widget.post(()->widget.updateAppWidgetSize(null,b.width,b.height,b.width,b.height));
                    }
                }
            }
        }
    }
}
