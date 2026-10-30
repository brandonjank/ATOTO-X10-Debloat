# Stock launcher audit and replacement direction

29 October 2026. Input: com.android.launcher3 version 20260327_1629,
SHA256 `dcd6c86b36294ea0dbfb0d6ee0bbba432bb4885951c7414cdbca630bde68df71`.
The live OEM APK matched the saved copy. This is static code/manifest evidence
and prior runtime observations, not a packet capture or malware verdict. The
14,436-class scan found 37 requested permissions and 26 manifest components.
Raw APKs, decompiled code and private device records are not distributed.

## Useful features

The stock launcher injects interactive map, DVR and vehicle-model views for
particular providers. Those views are not portable standard widgets. Its broader
code includes secondary-display/backlight controls, audio/EQ and volume/key
bindings, recents/gestures, notification badges and favorites/live wallpaper.
Removing the whole system package would also remove necessary integrations.

Standard radio/source, weather, Pandora and compact Audible widgets already work
in another host. Maps Nearby Traffic provides a portable map panel with different
capabilities from the OEM injected MapView. The replacement can use these widgets
and retained apps for RCAM, radio, Bluetooth, CarPlay and Torque, while preserving
camera priority, DVR, audio, MCU, phone and modem backends.

## Findings that matter

| Finding | Evidence and meaning |
| --- | --- |
| Debuggable system identity | Live SYSTEM DEBUGGABLE flags and shared android.uid.system/UID 1000. A prior real speed-compilation request ran with debuggable flags and filter verify. Debug access reaches a privileged process; the speed effect of a release build is unmeasured. |
| GPS logging | MapContainerView.handleLocationUpdate constructs INFO messages containing latitude, longitude and zoom, and can stringify Location. This is a privacy/log-hygiene defect, not proof of remote upload. Earlier per-tag WARN settings reduced output on the source unit. |
| Frequent location updates | The stock map requests high accuracy, interval 3000 ms and fastest 1200 ms; it unregisters on detach. This fits a moving map, but our widget host does not need location access itself. |
| Broad permissions | Fine/coarse location, camera, all-files, input monitoring, task management, secure-settings and display/surface control are requested. Some fit an OEM system launcher; our dashboard does not require them. Shared UID 1000 complicates permission and traffic attribution. |
| Heavy diagnostic logging | 817 OEM/Launcher3/Quickstep method bodies contain verbose/debug/info Log references. This counts methods, not runtime events or CPU cost. Filtering output does not remove eager message construction. |
| Returning taskbar | An 88-pixel OEM taskbar returned beside Lawnchair after restart. Native manual stash hides it for the current session. A static initialization-order issue may explain the lost saved state; the private patched APK remains unsigned and untested. |

## Network and exported-component checks

Google Maps/Places, Google data-transport scheduling and Firebase-related classes
are included. The CCTDestination interleaving routine decodes Google logging
hosts `firebaselogging.googleapis.com` and `firebaselogging-pa.googleapis.com`.
Its API-key-like transport constant is not copied into this report or our app.
Literal references also include Google Maps/Google APIs.

This establishes a telemetry/log-upload capability in included libraries. The
reviewed OEM/Launcher3/Quickstep method subset did not show direct URLConnection,
socket or OkHttp calls in that namespace. SDKs, reflection, generated code or
other processes can still perform network calls. Literal URL searches miss
constructed endpoints, as CCT demonstrates. No claim that the stock app is
spyware, clean or network-silent follows. UID 1000 traffic cannot automatically
be attributed to this launcher. Selected namespace scans found no Umeng, Bugly,
Baidu, AMap, JPush, Facebook or AppsFlyer classes; that does not rule out tracking.

The exported grid provider was checked beyond the manifest: its preview call
checks BIND_WALLPAPER, query exposes theme state, and the reviewed update method
returns without writing a setting. Exported alone is not evidence of an
arbitrary-write vulnerability. Normal widget receivers and system-permission
guarded services are not automatically malicious.

## Our replacement

The goal is our own source-built home, io.atoto.x10home, without Lawnchair or
OEM-derived code. It uses an ordinary dedicated UID, no requested permissions,
no network/analytics SDK and no services/boot receiver. It hosts widgets and
launches owner-selected apps through Android's normal contracts. The OEM signing
key is not needed for this independent frontend.

Keep the OEM package for Quickstep/recents and hardware integrations while parity
is established. Replacing HOME and removing its privileged backend are separate
jobs. Lawnchair is a rollback home during development, not a final dependency.
The initial frontend does not implement OEM injected map/DVR/vehicle panels,
secondary display, notification dots or hardware setters. Physical acceptance
remains necessary; see [X10 Home](X10-HOME.md).
