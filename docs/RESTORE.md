# Restore a trial without erasing the unit

Keep the private snapshot and any native launcher export on another storage
device. Verify the APK hashes before relying on them. A hash proves integrity,
not that a restoration path has been physically demonstrated.

Custom still boot logos use a separate complete splash backup and journal.
See [BOOT-LOGO.md](BOOT-LOGO.md) for the splash-only restoration helper and its
limits. `x10.py restore` does not restore a boot logo or Android animation.

## Recover the home screen first

With Wi-Fi ADB connected, preview one of:

```powershell
python tools/x10.py --serial SERIAL home original --snapshot .local/before
```

Add `--execute` to return to the actual original HOME saved for this device,
including a third-party launcher. Its installed activity must remain an available
HOME handler. This retains app data and both layouts; native taskbar
visibility is a separate preference. If firmware compatibility changed, use
Android Settings → default apps → Home app instead of bypassing the tool's gate.
`home oem`, `home lawnchair`, and `home x10` also require `--snapshot`; they are
explicit choices, not assumptions about what the friend's original home was.

For a freshly installed unverified launcher, use the explicit MAIN / LAUNCHER
activity first. Choosing an unstable app as default HOME can create a relaunch
loop. Retain the original launcher and a known working alternative throughout.

## Undo changes made by this toolkit

```powershell
python tools/x10.py --serial SERIAL restore --snapshot .local/before
```

Inspect the plan; add `--execute` to restore a journaled HOME first, then original
enabled states and the three journaled screensaver values. A HOME-only trial
can also be restored. Intent is persisted before each write, including home
switches and restore attempts. Repeating restore after a dropped link handles
already restored values without replaying unattempted actions.
The snapshot must belong to this device and
firmware. If a third party changed the same state after the trial, the tool
stops for inspection rather than overwriting an unexplained value.
Keep the same snapshot and journals. Reconnect to the current Wi-Fi connection
port on the same physical unit. Do not make a new apply journal to fix a partial
apply. If several batches were performed, restore the newest batch first.

`after-apply.json` and `after-restore.json` contain protected-package checks.
An explicit `check --snapshot .local/before --out .local/restored-check.json`
can save a new report without changing the unit. A software pass does not prove
the camera, microphone, sound path or phone connection works: repeat the parked
physical test matrix and record any remaining failure.

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
An export attached with `attach-export` is under `exports/` with its native file
extension retained and checksum verified by `verify`. The raw package/settings
evidence is a reference, not a replacement for that export or private app data.
Obtain third-party apps from their legitimate publishers and sign in yourself.

## If automatic rollback refuses

Do not change hashes, delete journals or force a downgrade to make it proceed.
First inspect the saved identity and original values, the journal's attempted
actions, current APK versions and current default home. A firmware update or
manual app change can legitimately invalidate an older automated plan.

With the owner's recovery authorization, use Android's default-app settings to
select the **saved original** launcher if it is still installed. For a journaled
package still installed but disabled, restore only its saved enabled state:
`default-state`, `enable`, `disable`, `disable-user` or `disable-until-used`
correspond to Android enabled values 0 through 4. An agent can inspect the exact
saved entry and use `adb -s SERIAL shell pm STATE --user 0 PACKAGE` for that
package. Do not enable unrelated packages or bulk-change a shared UID. These
manual commands bypass toolkit checks, so verify the device, package and intent
first, record the action and repeat the physical tests.

If a journaled stock package was actually removed outside this toolkit,
`install-existing` may re-add its ROM copy as described above. Reinstalling a
saved APK is a separate recovery choice, not an automatic rollback step. A
signature mismatch or changed firmware requires review; do not clear app data,
force-install an incompatible old system APK, or factory reset to work around it.

## What a snapshot does not restore

- Google/Pandora/Audible accounts or tokens, Bluetooth pairing and Wi-Fi passwords.
- Private app databases not included in an application's own export.
- MCU configuration, modem NV/calibration, radio provisioning or partitions.
- A failed firmware flash or an electrically damaged unit.

The source owner's archived stock firmware is not bundled with this kit and
does not establish a recovery path for the friend's device.
Do not run fastboot/EDL/MCU flash commands from this guide. A future ROM release
must establish its own compatible recovery route before any partition writes.
