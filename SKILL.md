---
name: atoto-x10-debloat
description: Audit, back up, selectively debloat, trial the Lawnchair X10 home screen, and restore a supported ATOTO X10 head unit over Wi-Fi ADB while preserving its hardware features. Use for stock Android configuration work, not firmware flashing.
---

# ATOTO X10 Debloat

Work from this skill's directory; the bundled `tools/`, `profiles/`, `docs/`
and `android/` folders are relative to it. Preserve the owner's requested
features and existing authorizations. Do not assume the source owner's app
preferences apply to another driver.

## Audit and backup

Use an installed Python 3.11+ and Android Platform Tools. Discover the actual
ADB executable and ask for a Wi-Fi connection endpoint only if not available
in the conversation or current ADB device inventory. Always pass `--serial`;
never operate on an arbitrary connected device. Keep transfers over Wi-Fi.
Pair/connect with Android's normal workflow as needed. Do not install the old
ADB persistence helper or alter authentication.

Run `python tools/x10.py --serial SERIAL audit`. `--adb PATH` may precede the
command. Read [the compatibility profile](profiles/stock-20260403.json).
Model `X10` alone is insufficient: application version, Android/platform,
fingerprint and three stock hardware APK hashes must match for automated writes.
If they differ, gather read-only evidence and explain the mismatch. Do not
rewrite the profile or add an override merely to pass the check.

Create `snapshot --out .local/UNIQUE_NAME --with-apks`, then
`verify --snapshot .local/UNIQUE_NAME`. Save the snapshot outside public source
or in ignored `.local/`. `--resume` is available after an interrupted capture.
A snapshot is APKs/settings evidence, not a partition or private-app-data image.
Export the current home through its native backup UI before launcher changes.
Use [RESTORE.md](docs/RESTORE.md) to distinguish returning to the existing home,
restoring this trial's changes, and rebuilding a lost device configuration.

## Select and apply

Read [FRIEND-TRIAL.md](docs/FRIEND-TRIAL.md). Determine which optional features
the owner uses; ask only about choices that remain relevant and unknown.
Remote tracking, cloud speech, OEM store and remote wake are optional features,
not automatically expendable. Preserve cloud-SIM networking components unless
separately investigated; they can share hardware dependencies with physical SIM
or hotspot functions.

Preview `apply --snapshot PATH --packages PACKAGE ... --screensaver` with only
the selected options. Applying is opt-in via `--execute`. Use the owner's
existing explicit cleanup authorization if it covers the displayed choices;
otherwise obtain authorization for that concrete plan before executing it.
This skill's invocation alone does not authorize unrelated removals or all
fourteen optional packages. The tool records rollback values and verifies writes.

Never disable the protected packages, delete shared-UID services, apply generic
background-process limits, alter CPU/MCU/USB/DVR shutdown timing, or change SIM
policy to chase performance. The original hardware ordering is intentionally
preserved. A registered boot receiver or active DVR process is not proof of
unnecessary work. Existing animations are already disabled on the source unit;
no global logging or additional performance tweaks are part of this installer.

## Launcher trial

Read [BUILDING.md](docs/BUILDING.md) only when a custom APK is needed. The
Lawnchair adaptation uses a pinned official APK and separate package
`io.atoto.home`, retains original launchers, and adds only dock layout hooks.
Use separate local signing material and verify the output before proposing an
install. New device installs require the owner's authorization. Do not copy
the source owner's private launcher backup, account data or widget IDs.

Install the trial alongside the existing home. Launch its explicit MAIN /
LAUNCHER activity first; keep the working default until it is stable. Add
widgets with Android's normal binding flow. Then switch HOME only within the
authorized trial. `home oem`, `home lawnchair`, and `home x10` preview a switch;
add `--execute` for an installed, enabled home. Native ATOTO taskbar visibility
is separate. Do not disable OEM Quickstep to hide it. This release does not
automate the source unit's temporary debugger-based taskbar customization.

## Verify, recover and report

Check the cameras/reverse priority, DVR recording/playback, all speaker outputs,
EQ/radio, microphone/Bluetooth calls, CarPlay, navigation and physical-SIM data.
Capture software state; have the parked owner perform physical tests and ignition
cycles. Do not trigger an unattended reboot or power cycle. Keep the distinction
between user-reported behavior, software checks and measured timing.

On a failed trial, stop further changes and use the saved journal's
`restore --snapshot PATH` preview, then `--execute` within the authorized rollback.
Switch to the retained working HOME first if the trial launcher fails. Never
use a factory reset or partition write as routine rollback.

Report the actual changes, snapshot path, compatibility, physical test results,
unresolved issues and exact restore command. No claim that all spyware is
removed, that recovery flashing is proven, or that one X10 validates every X10.
Keep device identifiers, raw dumps, APKs, signing keys and native backups private.
