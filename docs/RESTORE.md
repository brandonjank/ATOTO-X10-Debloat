# Restore a trial without erasing the unit

Keep the private snapshot and any native launcher export on another storage
device. Verify the APK hashes before relying on them. A hash proves integrity,
not that a restoration path has been physically demonstrated.

## Recover the home screen first

With Wi-Fi ADB connected, preview one of:

```powershell
python tools/x10.py --serial SERIAL home oem
python tools/x10.py --serial SERIAL home lawnchair
python tools/x10.py --serial SERIAL home x10
```

Add `--execute` to switch to that installed, enabled home. This retains app data
and both layouts. `oem` restores the original default HOME; native taskbar
visibility is a separate preference. If firmware compatibility changed, use
Android Settings → default apps → Home app instead of bypassing the tool's gate.

For a freshly installed unverified launcher, use the explicit MAIN / LAUNCHER
activity first. Choosing an unstable app as default HOME can create a relaunch
loop. Retain the original launcher and a known working alternative throughout.

## Undo changes made by this toolkit

```powershell
python tools/x10.py --serial SERIAL restore --snapshot .local/before
```

Inspect the plan; add `--execute` to restore original enabled states and the
three journaled screensaver values. The snapshot must belong to this device and
firmware. If a third party changed the same state after the trial, the tool
stops for inspection rather than overwriting an unexplained value.

No APK uninstall or app-data deletion is used by the toolkit. Some factory
persistent apps can remain in memory until an owner-controlled reboot; a
disabled flag is not proof that the process has already stopped. Plan any
restart while parked and account for camera/audio interruption.

## Rebuild after an app was accidentally removed

For a stock system app still registered in the ROM, inspect its package first.
Android can re-add it for user 0 with `cmd package install-existing --user 0
PACKAGE`, followed by its recorded enabled state. Do not use this command on
unrelated package names. It is not necessary for a normal toolkit rollback.

For the custom home or Audible widget, reinstall the saved exact signed APK(s),
then use the application's native import flow. Split APKs must be installed
together. A different signing key cannot update an existing app under the same
package name. Preserve your own private build key; never upload it to GitHub.

Lawnchair: open its Settings, use the three-dot menu → Restore backup, choose
your native `.lawnchairbackup`, and rebind missing widgets through Android.
The source owner's old widget IDs and app sessions are not transferable.
Obtain third-party apps from their legitimate publishers and sign in yourself.

## What a snapshot does not restore

- Google/Pandora/Audible accounts or tokens, Bluetooth pairing and Wi-Fi passwords.
- Private app databases not included in an application's own export.
- MCU configuration, modem NV/calibration, radio provisioning or partitions.
- A failed firmware flash or an electrically damaged unit.

The archived stock firmware is a reference, not a tested full-device backup.
Do not run fastboot/EDL/MCU flash commands from this guide. A future ROM release
must establish its own compatible recovery route before any partition writes.
