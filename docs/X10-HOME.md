# X10 Home: our open-source launcher

X10 Home is source-built, not a Lawnchair fork or repackaged OEM APK. Application
ID: io.atoto.x10home. Code is in android/x10-home under this repository's
Apache-2.0 license. It is an experimental preview; hardware and boot/wake
acceptance must be established on each unit. Native layout export/import is not
implemented yet; a preview reset requires rebinding its own panels and shortcuts.
Keep the working launcher's native export and data as the rollback baseline.

## Initial capabilities and limits

Three columns hold radio/source, Google Maps Nearby Traffic, and weather above
Pandora/Audible controls. Eight large dock targets span the bottom. Long-press a
dock item to choose another app. Apps, Panels, Home app and Previous home buttons
provide setup/navigation; a TextClock shows the date/time. Launching the preview
does not itself select default HOME.

The app requests no permissions: no INTERNET, location, camera, microphone,
telephony, all-files, secure-settings or notification-listener access. It has no
shared system UID, service, boot receiver, network/analytics SDK or redraw loop.
The apps-list worker runs on request; widget-host updates stop onStop. Providers
and launched apps retain their own permissions/network behavior, so this does
not make the dashboard or head unit offline.

The [stock audit](STOCK-LAUNCHER-AUDIT.md) explains feature gaps. OEM injected
map/DVR/vehicle views, secondary displays, notifications and hardware setters are
not implemented. Retain Quickstep, vehicle logic and all hardware backends during
testing. The final goal is to stop using Lawnchair after our own home passes.

## Build

Use the local SDK/JDK configuration in [BUILDING.md](BUILDING.md). No external
app APK, OEM resource, Google SDK, artwork or third-party runtime is a build input.
Set X10_SIGNING_PASSWORD privately and keep your dedicated key outside public
source, as for the other builders:

```powershell
python tools/build_x10_home.py --tools .local/android-tools.json --keystore .local/signing/x10-home.p12 --alias x10-home --generate-key --out .local/x10-home-build
```

Omit --generate-key when reusing the key. Preserve previous build folders. The
builder verifies signing, no requested permissions and stored resource-table
format, and records source/APK hashes. It never installs or selects HOME.

## Preview and configure

1. Keep the current launcher snapshot, native export and exact HOME component.
   Preserve the working default and original launchers throughout the trial.
2. With the owner parked/ready, normally install the reviewed new APK and launch
   io.atoto.x10home/.HomeActivity explicitly. Verify default HOME stayed unchanged.
3. Choose Panels, Set up missing panels. Approve Android's binding/configuration
   dialogs for the five wanted providers. Widget IDs are allocated to this host;
   never copy another host's IDs or private launcher database.
4. Panels can choose other widgets. A canceled replacement preserves the previous
   working panel; Cancel pending setup deletes only the newly allocated incomplete
   ID. Long-press dock items to choose another app. Accounts stay in their apps.
5. Test map zoom, real radio/media controls and every shortcut. Repeat the full
   [physical matrix](FRIEND-TRIAL.md), especially reverse priority, DVR recording,
   calls/CarPlay, all speakers and physical-SIM data. Software checks do not prove
   those features work.
6. Only after preview checks pass, use Home app and Android's normal role dialog
   for a default-home trial. Record the previous HOME first; keep OEM Quickstep
   and hardware services. Test hardware Home/recents, reboot and sleep/wake.

The initial panels use installed standard widgets. Replace unavailable providers
through Panels. Maps retains its own location permission choice. The separate
ATOTO taskbar can still return after a restart; its persistence is an OEM issue,
not another bar drawn by X10 Home. Do not disable the OEM launcher to hide it.
The source unit's native-stash workaround is not automated in this preview.

## Rollback

Previous home opens the recorded working home. Android Settings, Default apps,
Home app selects it again. With the exact saved component and owner authorization,
an agent can use `adb -s SERIAL shell cmd package set-home-activity --user 0
ORIGINAL_COMPONENT`, then launch it and verify. Keep its data and layout.

Switch and verify the old HOME before removing only io.atoto.x10home. Do not
remove Lawnchair until our replacement passes acceptance and its export/rollback
are preserved. A raw APK/settings snapshot is not every app's private-state backup.
