// Copyright 2026 ATOTO X10 Debloat contributors. SPDX-License-Identifier: Apache-2.0
package io.atoto.home;

import android.content.Context;
import android.content.res.Configuration;
import android.graphics.Rect;
import android.os.Build;
import android.util.Log;
import android.util.TypedValue;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import java.lang.reflect.Field;

/** Layout-only adaptation for this X10. No permissions, network, service or timer. */
public final class X10Dock {
    public static final int ICON_PX = 80;
    public static final int SIDE_PX = 32;
    public static final int BOTTOM_PX = 12;
    public static final int CELL_HEIGHT_PX = 108;
    private static boolean active(Context context) {
        return "io.atoto.home".equals(context.getPackageName())
                && "X10".equals(Build.MODEL)
                && context.getResources().getConfiguration().orientation
                   == Configuration.ORIENTATION_LANDSCAPE;
    }
    public static void profile(Object profile) {
        if (!"X10".equals(Build.MODEL)) return;
        try {
            if (!profile.getClass().getField("isLandscape").getBoolean(profile)) return;
            // Keep hotseatBarSizePx and all workspace/widget geometry unchanged.
            profile.getClass().getField("hotseatCellHeightPx").setInt(profile, CELL_HEIGHT_PX);
        } catch (ReflectiveOperationException e) {
            Log.e("X10Dock", "Stock profile retained", e);
        }
    }
    public static void padding(View hotseat, ViewGroup.LayoutParams params, Rect padding) {
        if (!active(hotseat.getContext()) || params.height < 100) return;
        // CellLayout divides this whole width into equal, clickable dock cells.
        padding.set(SIDE_PX, 0, SIDE_PX, BOTTOM_PX);
    }
    public static void icon(TextView view, Object item) {
        if (!active(view.getContext()) || item == null) return;
        try {
            if (((Number) item.getClass().getField("container").get(item)).longValue() != -101)
                return;
            Field size = findField(view.getClass(), "mIconSize");
            size.setAccessible(true);
            size.setInt(view, ICON_PX);
            Field center = findField(view.getClass(), "mCenterVertically");
            center.setAccessible(true);
            center.setBoolean(view, true);
            view.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
            view.setCompoundDrawablePadding(4);
        } catch (ReflectiveOperationException e) {
            Log.e("X10Dock", "Stock icon retained", e);
        }
    }
    private static Field findField(Class<?> type, String name) throws NoSuchFieldException {
        for (Class<?> current = type; current != null; current = current.getSuperclass()) {
            try { return current.getDeclaredField(name); }
            catch (NoSuchFieldException ignored) { }
        }
        throw new NoSuchFieldException(name);
    }
    private X10Dock() {}
}
