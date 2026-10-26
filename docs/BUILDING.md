# Build the optional apps locally

Audit/debloat/restore uses only Python's standard library and ADB. This page is
needed only for the optional custom home or Audible widget. These build tools
write PC files; they never install an app or change a device.

## Inputs

- Python 3.11+, JDK 17+, Android SDK platform 33 and build-tools 35.0.0.
- `rg` on PATH for the launcher patcher.
- [Apktool 2.11.1](https://github.com/iBotPeaches/Apktool/releases/tag/v2.11.1),
  JAR SHA256 `56d59c524fc764263ba8d345754d8daf55b1887818b15cd3b594f555d249e2db`.
- [Official Lawnchair 15 Beta 3](https://github.com/LawnchairLauncher/lawnchair/releases/tag/v15.0.0-beta3.0),
  asset `Lawnchair.15.0.0.Beta.3.0.apk`, SHA256
  `d4200d0985169fd79ba1bd225d653f2a2fe7b50aa07cb0d05ca64c7623f86059`.
- For offline launcher verification: `python -m pip install -r requirements-dev.txt`.

Download inputs on the PC from the publishers, not over the head unit's SIM.
Copy `tools/android-tools.example.json` to `.local/tools.json` and replace SDK
paths with absolute paths. On Windows include `.exe` for the relevant SDK tools.
Supply your own private signing keystore and `X10_SIGNING_PASSWORD` environment
variable. `--generate-key` creates a new identity if the specified file is absent.
The password is read by the Java signing tools from the environment, not passed
as a literal command-line password. Keep the keystore and password private.

## Lawnchair X10

```powershell
python tools/build_lawnchair_x10.py --tools .local/tools.json --apktool .local/apktool_2.11.1.jar --base-apk .local/Lawnchair.15.0.0.Beta.3.0.apk --keystore .local/signing/home.p12 --generate-key
python tools/verify_lawnchair_x10.py --base-apk .local/Lawnchair.15.0.0.Beta.3.0.apk --apk .local/lawnchair-x10/build/Lawnchair-X10-dock.apk
```

The builder decodes the pinned APK without rebuilding resources, patches three
layout call sites and package/provider identities, adds `X10Dock.java`, aligns
and signs the result. This is a binary adaptation, not a full upstream source
build. It preserves original resource files, native libraries and the original
class set. The verifier checks these invariants, namespace isolation, absence
of added permissions, and all DEX headers as format 038 (API 26+).

The DEX version matters: older format 035 broke interface default-method
dispatch during an early local trial. The DeviceProfile hook must pass only
`p0`; `p1` has been reused by R8 at that point. Do not move the hook or change
registers without repeating class-linking/device launch checks.

The adaptation is for the tested 1280×720 landscape display. Its helper checks
model/orientation, but another X10 screen geometry still needs review. Runtime
head-unit validation is separate from the offline verifier. Preserve the
original home, install only with owner authorization, and initially launch:

```powershell
adb -s SERIAL install .local/lawnchair-x10/build/Lawnchair-X10-dock.apk
adb -s SERIAL shell am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n io.atoto.home/app.lawnchair.LawnchairLauncher
```

Recreate the 9×8 home and eight-item dock using the owner's apps. Add each widget
through the standard widget picker. Android assigns fresh widget IDs. Only
after a stable trial, select the new default home with
`tools/x10.py --serial SERIAL home x10 --snapshot .local/before --execute`.
Keep a verified snapshot and the original launcher's native export where available;
the original default HOME is journaled before the switch. Recovery is
`home original --snapshot .local/before --execute`, or a full `restore` preview.
No OEM launcher disable, widget database injection or debugger attachment is
part of the public installer. Native taskbar hiding is a separate customization.

## Compact Audible controls

```powershell
python tools/build_audible_widget.py --tools .local/tools.json --keystore .local/signing/widget.p12 --generate-key
```

Output: `.local/audible-widget/x10-audible-controls.apk`. It requests no
permissions and has no service, timer, Internet access, boot receiver or
notification listener. It sends ordinary media-key intents to Audible's exported
AndroidX MediaButtonReceiver. That receiver and behavior can change with Audible
versions; verify play/pause and backward/forward on the target installation.
The controls have no book-title/artwork readback or dynamic playback-state icon.

Install only after review/authorization, then add **Audible Compact Controls**
below Pandora. Remove its widget before uninstalling the helper if reverting.
Audible and Pandora themselves are not modified or included.

## Signing and public binaries

Your new key will differ from the source owner's key. That is expected for a
fresh device install; it cannot update an existing same-package app signed by
another key. Preserve the working APK and native launcher export before any
future key migration. Never uninstall a working home just to bypass a signature
error without a deliberate backup/restore plan.

The preview export is source-only. Do not bundle OEM/Google/Pandora/Audible apps,
private configuration, or signing material. For a future custom binary release,
retain the applicable upstream and dependency notices and identify the modified
files and base release. See THIRD_PARTY.md.
