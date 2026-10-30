---
name: atoto-x10-debloat
description: Audit, back up, selectively debloat, trial Lawnchair X10, optionally customize the still boot logo, and restore a supported ATOTO X10 over Wi-Fi ADB. Use for stock configuration and the explicit logo-only workflow, not replacement ROM or MCU flashing.
---

# ATOTO X10 Debloat

Work from this skill's directory; the bundled `tools/`, `profiles/`, `docs/`
and `android/` folders are relative to it. Preserve the owner's requested
features and existing authorizations. Do not assume the source owner's app
preferences apply to another driver.
Obtain the whole repository, not just this Markdown file. Read the executable
sequence and recovery branches in [AGENT-RUNBOOK.md](docs/AGENT-RUNBOOK.md) when
performing a first-device trial. No source APK or firmware download is needed
for ordinary audit, backup, disable-only cleanup or rollback.

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
Only Android owner user 0 is supported. Selected optional apps must also match
the APK hashes recorded in the profile, including any splits. An auto-updated
app is a new review case; exclude it rather than editing the guard to proceed.
If they differ, gather read-only evidence and explain the mismatch. Do not
rewrite the profile or add an override merely to pass the check.

Create `snapshot --out .local/UNIQUE_NAME --with-apks`, then
`verify --snapshot .local/UNIQUE_NAME`. Save the snapshot outside public source
or in ignored `.local/`. `--resume` is available after an interrupted capture.
A snapshot is APKs/settings evidence, not a partition or private-app-data image.
The actual original HOME APK(s) are included, even for a third-party launcher.
Run `check --snapshot PATH --out .local/before-check.json` and privately record
which required physical features work **before** cleanup. Existing failures
need to be distinguished from trial regressions. Packages being enabled does
not prove a camera, microphone, SIM or phone connection works.
Export the current home through its native backup UI before launcher changes;
copy the export to the PC and use `attach-export --snapshot PATH --file FILE`,
then verify again. Original Lawnchair needs its native export before a HOME
switch. For an OEM launcher without an export, preserve its data in place and
privately photograph the layout, audio/EQ and vehicle settings; record that the
snapshot cannot restore all private settings after a reset.
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
Use a fresh snapshot per batch; keep earlier snapshots intact. Only one cleanup
journal and one launcher trial are allowed per snapshot. `--apk-cache` can reuse
verified APKs from an earlier private snapshot to reduce Wi-Fi transfer time.
Run `check` and the physical tests after each batch, and again after any parked,
owner-controlled reboot. Stop expanding the trial on a regression or warning
that has not been explained. Do not force-stop an entire shared system UID.

Never disable the protected packages, delete shared-UID services, apply generic
background-process limits, alter CPU/MCU/USB/DVR shutdown timing, or change SIM
policy to chase performance. The original hardware ordering is intentionally
preserved. A registered boot receiver or active DVR process is not proof of
unnecessary work. Existing animations are already disabled on the source unit;
no global logging or additional performance tweaks are part of this installer.

## Launcher trial

For the owner's own open-source launcher, use [X10-HOME.md](docs/X10-HOME.md)
and the [stock audit](docs/STOCK-LAUNCHER-AUDIT.md). X10 Home is an independent
source-built app, `io.atoto.x10home`, with no Lawnchair/OEM code, shared UID or
requested permissions. Preview it explicitly before choosing HOME and retain the
working launcher as rollback. Its standard widgets do not reproduce OEM-injected
map/DVR/vehicle views. Complete the physical checks before retiring Lawnchair.
The legacy `x10.py home x10` choice below still means the Lawnchair adaptation;
it does not select this new app. Use the new app's normal Android Home-role flow
and record the exact original component for rollback.

Read [BUILDING.md](docs/BUILDING.md) only when a custom APK is needed. The
Lawnchair adaptation uses a pinned official APK and separate package
`io.atoto.home`, retains original launchers, and adds only dock layout hooks.
Use separate local signing material and verify the output before proposing an
install. New device installs require the owner's authorization. Do not copy
the source owner's private launcher backup, account data or widget IDs.

Install the trial alongside the existing home. Launch its explicit MAIN /
LAUNCHER activity first; keep the working default until it is stable. Add
widgets with Android's normal binding flow. Then switch HOME only within the
authorized trial. `home x10 --snapshot PATH` previews the change and preserves
the snapshot's original HOME in a separate journal. Add `--execute` only after
the explicit MAIN / LAUNCHER test. `home original --snapshot PATH --execute`
returns to the actual original HOME, including a third-party launcher. Native
ATOTO taskbar visibility is separate. Do not disable OEM Quickstep to hide it. This release does not
automate the source unit's temporary debugger-based taskbar customization.

## Optional still boot logo

Only when requested, read [BOOT-LOGO.md](docs/BOOT-LOGO.md) and use
`tools/boot_logo.py`. This is a separate, explicit **splash partition write**;
the OEM updater automatically restarts Android. Ordinary cleanup authorization
does not include it. Preserve existing owner authorization when it covers the
reviewed image and update, and confirm current parked readiness for the restart.
Do not confuse a still logo with Android's boot animation or the FactoryTools
hardware-configuration selector.

Prepare and show that owner's image, capture/verify the complete original splash,
then preview/stage only the generated marker and BMP. Use the narrower logo
profile; no hash overrides or cross-model assumptions. The already installed
stock direct-command reader is used without installing a root manager or helper.
Keep the ordinary APK/settings snapshot as well; it does not contain splash.
Install only the logo component, reconnect after its automatic reboot, verify
the full partition and repeat physical checks. Do not replay an attempted install
after a lost link. Restore the owner's original splash through the separate
previewed restoration command when authorized. Raw restoration has not been
physically trialed; unknown/partial state stops for recovery inspection.
Keep all artwork, images and identity-bound journals private.

## Verify, recover and report

Check the cameras/reverse priority, DVR recording/playback, all speaker outputs,
EQ/radio, microphone/Bluetooth calls, CarPlay, navigation and physical-SIM data.
Capture software state; have the parked owner perform physical tests and ignition
cycles. Do not trigger an unattended reboot or power cycle. Keep the distinction
between user-reported behavior, software checks and measured timing.

On a failed trial, stop further changes and use the saved journal's
`restore --snapshot PATH` preview, then `--execute` within the authorized rollback.
This restores any journaled HOME first, then attempted package/settings changes;
it also handles an interrupted apply or a HOME-only trial. A changed connection
port does not change the device identity; reconnect to the new Wi-Fi endpoint.
Keep journals and the original snapshot; do not start a new apply to repair an
interrupted trial. If a guard prevents recovery, follow the inspected, limited
manual recovery branch in RESTORE.md rather than weakening the check.
Switch to the retained working HOME first if the trial launcher fails. Never
use a factory reset or partition write as routine cleanup/launcher rollback.
The explicitly requested boot-logo workflow has its own splash-only restoration
and does not alter OS, boot, MCU or modem partitions.

Report the actual changes, snapshot path, compatibility, physical test results,
unresolved issues and exact restore command. No claim that all spyware is
removed, that recovery flashing is proven, or that one X10 validates every X10.
Keep device identifiers, raw dumps, APKs, signing keys and native backups private.
