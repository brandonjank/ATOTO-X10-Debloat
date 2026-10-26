// Copyright 2026 ATOTO X10 Debloat contributors. SPDX-License-Identifier: Apache-2.0
package io.atoto.tools.audiblewidget;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.view.KeyEvent;
import android.widget.RemoteViews;

/** Static, event-driven widget; media buttons go directly to Audible's public receiver. */
public final class AudibleWidget extends AppWidgetProvider {
    private static final String AUDIBLE = "com.audible.application";

    private static PendingIntent button(Context context, int keyCode) {
        Intent intent = new Intent(Intent.ACTION_MEDIA_BUTTON);
        intent.setComponent(new ComponentName(AUDIBLE, "androidx.media.session.MediaButtonReceiver"));
        intent.putExtra(Intent.EXTRA_KEY_EVENT, new KeyEvent(KeyEvent.ACTION_DOWN, keyCode));
        intent.addFlags(Intent.FLAG_RECEIVER_FOREGROUND);
        return PendingIntent.getBroadcast(context, keyCode, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    private static void update(Context context, AppWidgetManager manager, int id) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.audible_widget);
        views.setOnClickPendingIntent(R.id.back, button(context, KeyEvent.KEYCODE_MEDIA_REWIND));
        views.setOnClickPendingIntent(R.id.toggle, button(context, KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE));
        views.setOnClickPendingIntent(R.id.forward, button(context, KeyEvent.KEYCODE_MEDIA_FAST_FORWARD));
        Intent launch = context.getPackageManager().getLaunchIntentForPackage(AUDIBLE);
        if (launch != null) {
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            views.setOnClickPendingIntent(R.id.open, PendingIntent.getActivity(context, 1, launch,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE));
        }
        manager.updateAppWidget(id, views);
    }

    @Override public void onUpdate(Context context, AppWidgetManager manager, int[] ids) {
        for (int id : ids) update(context, manager, id);
    }
    @Override public void onAppWidgetOptionsChanged(Context context, AppWidgetManager manager,
            int id, Bundle options) { update(context, manager, id); }
}
