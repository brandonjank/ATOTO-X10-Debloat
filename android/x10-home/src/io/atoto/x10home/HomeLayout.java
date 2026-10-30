// SPDX-License-Identifier: Apache-2.0
package io.atoto.x10home;

/** Pure geometry in dp; intentionally independent of Android for host tests. */
public final class HomeLayout {
    public static final int SLOTS = 5, DOCK_ITEMS = 8;
    public static final class Box {
        public final int x, y, width, height;
        Box(int x, int y, int width, int height) {
            this.x=x; this.y=y; this.width=width; this.height=height;
        }
    }
    public final Box toolbar;
    public final Box[] panels = new Box[SLOTS], dock = new Box[DOCK_ITEMS];
    public HomeLayout(int width, int height) {
        if (width < 600 || height < 300) throw new IllegalArgumentException("Landscape area too small");
        int side=24, gap=12, verticalGap=8, top=56, dockHeight=Math.min(112,height/4);
        int dockY=height-dockHeight-8;
        int bodyHeight=dockY-verticalGap-top;
        int column=(width-side*2-gap*2)/3;
        toolbar=new Box(side,0,width-side*2,48);
        panels[0]=new Box(side,top,column,bodyHeight);
        panels[1]=new Box(side+column+gap,top,column,bodyHeight);
        int right=side+(column+gap)*2;
        // At 1280x638: 242 weather + 8 + 100 Pandora + 8 + 96 Audible = 454.
        // Give forecast rows space before expanding already-usable media controls.
        int remaining=bodyHeight-verticalGap*2;
        int media=remaining>=436?100:remaining/4;
        int audible=remaining>=436?96:remaining/4;
        int weather=remaining-media-audible;
        panels[2]=new Box(right,top,column,weather);
        panels[3]=new Box(right,top+weather+verticalGap,column,media);
        panels[4]=new Box(right,top+weather+media+verticalGap*2,column,audible);
        int dockSide=32;
        for(int i=0;i<DOCK_ITEMS;i++) {
            int left=dockSide+(width-dockSide*2)*i/DOCK_ITEMS;
            int end=dockSide+(width-dockSide*2)*(i+1)/DOCK_ITEMS;
            dock[i]=new Box(left,dockY,end-left,dockHeight);
        }
    }
}
