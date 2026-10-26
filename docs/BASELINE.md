# Source baseline, 2026-10-25

This document contains device-type facts and observations without the source
owner's identifiers, location, accounts, network details or raw captures.

| Item | Recorded baseline |
| --- | --- |
| Head unit | X10G2A7E, Android 13/API 33, Snapdragon 6125/trinket, 8 GB/128 GB |
| ATOTO UI/application | AICE UI 13.0 / 20260403.140715 |
| MCU | 2026-04-02-101021_C |
| Bluetooth build | CQ131.20250606_20250709 |
| Default home | io.atoto.home/app.lawnchair.LawnchairLauncher |
| Home base | Official Lawnchair 15 Beta 3, separate local adaptation |
| Display/grid | 1280×720 landscape, 9×8 |
| Dock | Maps, Pandora, Audible, rear camera, Torque, ZLINK, radio, Bluetooth |
| Dock geometry | Eight 152-pixel touch cells, 80-pixel icons, 14sp labels |
| Panels | Radio 3×8, nearby traffic 3×8, weather 3×4, Pandora 3×2, Audible 3×2 |
| Keyboard | Gboard retained; Automotive Keyboard was incompatible in Play |
| Core policy | Keep OEM launcher/Quickstep, MCU, power, audio, camera/DVR, Bluetooth, CarPlay, SIM |

The fourteen optional packages in the profile are inactive on the source unit.
Three were removed only for user 0 with data retained: photo screensaver, QCC
and ATOTO keep-alive. The public trial uses disabling rather than repeating
those removals. GlocalMe/Cloud SIM components are not part of this cleanup
allowlist; shared networking dependencies still need investigation.

Screensaver activation and notification badging are off. Animation scales are
zero. Twenty-one named OEM launcher UI log tags were set to WARN using separate
historical journals; no global log suppression was applied. The public installer
does not reproduce the logging/badging/animation changes automatically.

Generated ART code for Lawnchair X10, ZLINK and Bluetooth was verified as `speed`.
The launcher stayed loaded through the observed short ignition cycle. The
owner reported about one second for return and subsequently reported the main
features working. This is a broad owner report, not individual instrumented
certification of each feature. No full Android suspend occurred in that cycle.
Cold boot, overnight return and parked battery consumption remain open checks.

One warm launcher sample measured median 18 ms and p95 31 ms over 137 frames.
There were zero frames in a three-second idle sample. These small samples do
not establish universal speed improvement. The OEM weather widget can show
placeholders after a forced launcher restart.

The matching stock OTA and recovery were archived and verified locally. Actual
firmware restoration and an unbrick route remain untested. No root, MCU flash,
partition modification or replacement ROM was applied to create this baseline.
