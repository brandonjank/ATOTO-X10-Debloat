# First X10 trial: agent execution guide

Use the owner's authorization and feature preferences from the conversation.
This sequence supplies missing operational details; it does not authorize all
optional removals or promise that physical hardware has passed testing.

## Get the complete kit and connect

Clone/download `brandonjank/ATOTO-X10-Debloat` to the PC and work from its root.
Read SKILL.md. Python 3.11+ and Android Platform Tools are the only dependencies
for stock cleanup; no SDK build, firmware image or paid app is needed.

```powershell
git clone https://github.com/brandonjank/ATOTO-X10-Debloat.git
cd ATOTO-X10-Debloat
python tools/x10.py --help
adb devices -l
```

Use the owner's exact Wi-Fi device. If needed, enable Developer options and
Wireless debugging through Android settings. If a pairing screen exists:

```powershell
adb pair HEADUNIT_IP:PAIRING_PORT
adb connect HEADUNIT_IP:CONNECTION_PORT
```

Enter the current pairing code interactively. Pairing and connection ports are
different; after reboot the connection port may change and debugging may turn
off. Re-enable/reconnect normally. Do not enable persistent TCP ADB, install a
relay, bypass pairing, use another device, or upload pairing/device credentials.
The tested firmware has a known authentication weakness; see SECURITY.md.
If pairing UI is absent, inspect the existing connection/developer screen with
the owner; do not guess an undocumented factory code or expose more ports.

## Capture and verify the original setup

The commands below use an explicit endpoint; an mDNS serial works as well.
Add global `--adb PATH` before the command if the executable is not on PATH.

```powershell
python tools/x10.py --serial SERIAL audit
python tools/x10.py --serial SERIAL snapshot --out .local/before-batch1 --with-apks
python tools/x10.py --serial SERIAL verify --snapshot .local/before-batch1
python tools/x10.py --serial SERIAL check --snapshot .local/before-batch1 --out .local/before-check.json
```

`audit` checks firmware identity and three core APKs. `apply` additionally checks
each selected optional app against its reviewed hashes. A different MCU, retail
SKU, display or vehicle adapter still needs review even if Android's common
properties match. Record the About screen versions privately. Only owner user
0 is supported; leave another Android user's configuration untouched.

The snapshot saves the actual original HOME APKs (including splits), optional
apps, selected settings, original-home package evidence, all settings as private
reference dumps, widget state, installed versions and hardware-stack hashes.
It does not capture private application data, Bluetooth pairing, accounts,
modem calibration, MCU configuration or partitions. Do not replay raw dumps.

If interrupted, repeat the snapshot command with `--resume`; completion and
all copied hashes must verify. A metadata-only or partial capture is not an
adequate trial backup. Copy the private snapshot to a second storage location.

Before a launcher trial, export the original layout through that launcher's
own menu. For Lawnchair, Settings → three-dot menu → Create backup → Create →
save to Downloads. Copy the actual newly created filename to the PC using
`adb -s SERIAL pull`, keeping filenames with spaces as one quoted argument.
For example, after saving the local export in `.local/original.lawnchairbackup`:

```powershell
python tools/x10.py --serial SERIAL attach-export --snapshot .local/before-batch1 --file .local/original.lawnchairbackup
python tools/x10.py --serial SERIAL verify --snapshot .local/before-batch1
```

Attach the **original**, not the replacement launcher's export, before any
trial journals exist. Preserve the original file too. For a launcher lacking
an export, photograph the layout and audio/EQ/vehicle settings privately and
retain the installed app and data. Record the recovery limitation explicitly.
Existing Lawnchair must have its export attached before a HOME switch.

Have the parked owner check the feature matrix in FRIEND-TRIAL.md before any
changes; record `working`, `failed before trial`, `not tested`, or `not fitted`
for each item. Identify which cloud/remote/store functions the owner actually
uses. No package list or process presence proves the feature works.

## Apply one selected batch

Example only: the owner has chosen to stop remote tracking and log upload:

```powershell
python tools/x10.py --serial SERIAL apply --snapshot .local/before-batch1 --packages org.atoto.gps com.atoto.log.uploader --screensaver
```

Review the plan and authorized feature tradeoffs; add `--execute` to apply it.
Screensaver changes are optional too. No package is uninstalled and no private
app data is erased. A changed package, incomplete backup, unhealthy protected
stack or unexpected original state stops the operation. Do not change the
profile to silence a refusal. Exclude an unreviewed app and investigate it.

The tool persists intent before each write and checks protected packages before
and after. Its `after-apply.json` records software results; read any warnings.
Run a separate explicit check and repeat the physical tests:

```powershell
python tools/x10.py --serial SERIAL check --snapshot .local/before-batch1 --out .local/after-check.json
```

Use a fresh snapshot for a later batch. `snapshot ... --apk-cache
.local/before-batch1` reuses matching files by hash. Restore batches in reverse
order. Never delete a journal or overwrite an original snapshot to continue.
Some factory persistent processes remain until a parked, owner-controlled
restart. Reconnect and repeat checks afterward; do not kill a shared system UID.

## Optional launcher work

Only if requested, follow BUILDING.md for source inputs and private signing.
Installing a trial, widget or granting Maps background location is a separate
owner choice; preserve existing permissions unless that feature is requested.
Keep the original home installed/enabled. Test explicit MAIN / LAUNCHER first,
then recreate widgets using normal binding and the owner's apps/accounts.

```powershell
python tools/x10.py --serial SERIAL home x10 --snapshot .local/before-batch1
```

Add `--execute` after the stable trial. The original home is journaled before
switching. Its package and data remain intact. This is a launcher replacement,
not a taskbar/Quickstep/service replacement. No debugger or database injection
is required. Repeat camera reverse priority and all feature checks after it.

## Recover, including after a connection failure

Read RESTORE.md before a write. If only the home is failing:

```powershell
python tools/x10.py --serial SERIAL home original --snapshot .local/before-batch1
```

Add `--execute` to return to that unit's actual original home. To undo the whole
journaled trial, preview `restore --snapshot .local/before-batch1`, then execute
it. HOME is restored first. Already restored actions and unattempted actions
are not replayed. If the link drops, reconnect to the same physical unit and
repeat the restore preview; keep all journal files.

If an update, manual change or missing package makes a guard refuse rollback,
inspect the saved identity, journal and current state. Follow only the relevant
manual branch in RESTORE.md with the owner's recovery authorization. Do not
force-install old system APKs onto a new firmware, clear app data, factory reset
or flash anything. Record unfinished recovery instead of declaring success.

Finish with snapshot locations, selected changes, precise rollback commands,
software reports, original/after physical test results and open questions.
Keep snapshots and exports private. Cold boot, overnight wake and parked
current remain separate tests; the source unit's short return does not prove them.
