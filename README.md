# ATOTO X10 Debloat

Experimental, reversible stock-Android cleanup and a Lawnchair X10 home-screen
trial for the ATOTO X10G2A7E. This is the working baseline before a separate
clean-Android project. **This repository does not contain a flashable ROM.**

Tested on one X10G2A7E, Android 13/API 33, Snapdragon 6125/trinket,
ATOTO application version `20260403.140715`, MCU `2026-04-02-101021_C`,
1280×720 landscape. An X10 model name alone does not establish compatibility.

## Start with your agent

Give your agent [SKILL.md](SKILL.md) and say:

> Follow this skill to audit my X10 over Wi-Fi and back it up. Show me the
> optional changes that fit the features I use, then apply those I authorize.
> Preserve the cameras, audio, Bluetooth, CarPlay and physical SIM.

The skill and tools work directly from this folder. Installing the skill into
an agent's skill directory is optional; copy the **whole folder** if doing so.
The [agent runbook](docs/AGENT-RUNBOOK.md) provides the connection, backup,
physical baseline, batch cleanup and interrupted-recovery sequence.

## Manual quick start

Install Python 3.11+ and Android Platform Tools on the PC. Connect through
Wireless debugging over a trusted Wi-Fi network. Use the **connection port**;
the pairing port is a separate, temporary endpoint. No permanent ADB listener
or Android privileged-settings grant is installed by this project.

Run from this folder (replace the example address and port):

```powershell
adb connect HEADUNIT_IP:CONNECTION_PORT
python tools/x10.py --serial HEADUNIT_IP:CONNECTION_PORT audit
python tools/x10.py --serial HEADUNIT_IP:CONNECTION_PORT snapshot --out .local/before --with-apks
python tools/x10.py --serial HEADUNIT_IP:CONNECTION_PORT verify --snapshot .local/before
python tools/x10.py --serial HEADUNIT_IP:CONNECTION_PORT check --snapshot .local/before --out .local/before-check.json
```

`--adb` accepts an explicit executable path if ADB is not on PATH. All device
commands require an explicit `--serial`; the tool never chooses a device.
Snapshots contain private identifiers and device state: keep `.local/` private.
Interrupted snapshots can be retried with `--resume` and the same arguments.
Verification rejects incomplete inventories and metadata-only captures. The
original HOME APK(s) and hashed settings/widget evidence are included. Export
your original launcher layout through its native UI where supported; use
`attach-export --snapshot .local/before --file LOCAL_EXPORT` to keep it with the
backup, then verify again. A backup does not include private app data or accounts.

Choose packages by reading [the profile](profiles/stock-20260403.json). The
following example disables log upload and remote tracking, plus the screensaver:

```powershell
python tools/x10.py --serial HEADUNIT_IP:CONNECTION_PORT apply --snapshot .local/before --packages com.atoto.log.uploader org.atoto.gps --screensaver
```

That command previews the plan. Add `--execute` to apply it. A compatible
firmware, unchanged device, verified APK backup and unchanged original state
are required. The tool records intent **before** each write and verifies each
result. It never uninstalls packages, clears app data, changes MCU/power delays,
installs a ROM, roots the unit, or reboots automatically.
Selected app APKs must also match the audited hashes in the profile. Core
package checks run before and after cleanup; repeat the physical feature tests
after every batch. Use a fresh snapshot for the next batch. Preview
`restore --snapshot .local/before` to undo a partial or completed trial.

## What is included

- `tools/x10.py`: audit, private snapshot, backup verification, selected cleanup,
  protected-stack checks, native-export attachment, journal restore, and
  snapshot-bound switching among already installed home apps.
- `profiles/`: fourteen optional packages and twenty-eight protected packages.
  Optional means the original owner chose not to use the corresponding feature;
  it does not establish that an app is malware.
- `android/` and build tools: compact Audible widget source and the narrow
  Lawnchair dock adaptation. See [building](docs/BUILDING.md).
- Optional [custom boot logo workflow](docs/BOOT-LOGO.md): prepare your own
  image and USB kit, back up the complete original splash, stage/install the
  logo alone over Wi-Fi, verify and restore. **This separate opt-in workflow
  writes splash and the OEM updater automatically restarts Android.**
- [Restore guide](docs/RESTORE.md), [friend trial](docs/FRIEND-TRIAL.md),
  [baseline](docs/BASELINE.md), and [release notes](CHANGELOG.md).

The launcher configuration uses a 9×8 grid, with radio, nearby traffic, weather,
Pandora and Audible panels. Its eight-item dock has larger, wider touch targets.
Widgets must be added/bound on each device; accounts, widget IDs and another
owner's launcher database are not copied into the release.

## Current evidence and limits

The original owner reports that the required head-unit features work and that
return after a short ignition-off interval takes about one second. The measured
cycle did not enter full Android sleep. Overnight wake, cold boot, parked
current and another vehicle's integration remain unverified.

The OEM launcher, power stack, camera/DVR, audio, Bluetooth, CarPlay and physical
SIM stack remain installed. Package/process checks do not replace physical tests.
The existing stock firmware's ADB authentication weakness is unresolved; using
Wireless debugging on that firmware is a deliberate owner decision. This kit
does not fix or enable persistent ADB. See [SECURITY.md](SECURITY.md).

Private APKs, firmware images, account data, screenshots, signing keys and
launcher backups are excluded from source exports. Obtain third-party apps
from their publishers; no Google, Audible, Pandora or OEM binaries are bundled.

## Development and release

```powershell
python -m pip install -r requirements-logo.txt
python -m unittest discover -s tests -v
python tools/check_release.py
python tools/package_release.py --out ../releases/ATOTO-X10-Debloat-0.2.0-preview.zip
```

The packager uses an explicit reviewed file list and produces a checksum and
manifest. It does not publish anything to GitHub. Copying the entire parent
workspace into a Git repository would expose private research and backups.

Project-authored source uses Apache-2.0. Lawnchair and its dependencies retain
their own notices; see [NOTICE](NOTICE) and [THIRD_PARTY.md](THIRD_PARTY.md).
