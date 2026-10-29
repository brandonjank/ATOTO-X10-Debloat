# Third-party inputs and attribution

| Input | Pinned reference | Release treatment |
| --- | --- | --- |
| Lawnchair | [v15.0.0-beta3.0](https://github.com/LawnchairLauncher/lawnchair/releases/tag/v15.0.0-beta3.0), commit 505dbc4 | Download separately; base APK is not bundled |
| Lawnchair license | [LICENSE.txt at the pinned tag](https://github.com/LawnchairLauncher/lawnchair/blob/v15.0.0-beta3.0/LICENSE.txt), Apache-2.0 | Preserve upstream and dependency notices in derived binaries |
| Android Launcher3 | Included by upstream Lawnchair | Original code/resources remain in locally built APK |
| Apktool | [2.11.1](https://github.com/iBotPeaches/Apktool/releases/tag/v2.11.1), Apache-2.0 | Download separately, hash checked |
| Androguard | 4.1.3, Apache-2.0 | Optional host verification dependency, not vendored |
| Pillow | [12.3.0](https://pypi.org/project/pillow/12.3.0/), MIT-CMU | Optional PC image preparation dependency; not vendored |
| Android SDK / Platform Tools / JDK | Obtain from their publishers | Not bundled; publisher terms apply |
| ATOTO firmware and apps | Matching vendor build 20260403.140715 | Private recovery reference; not redistributed |
| Google apps, Pandora, Audible, Torque, Lawnicons | Owner-installed publisher releases | Not bundled or patched |

The toolkit and authored helper/widget source use Apache-2.0 (LICENSE). This is
not a relicensing of upstream components or their dependencies. A new binary
release needs its own notices review; the initial preview packages source only.
Owners supply their own logo artwork and must have permission for its intended
use. No Chevrolet, ATOTO or other logo artwork is included in this source release.
