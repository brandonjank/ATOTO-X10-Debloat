# Trial on another X10

1. Park the vehicle. Record the retail model, application, MCU and Bluetooth
   versions. Photograph vehicle-integration and audio settings privately.
2. Run the audit and create a private APK snapshot. A mismatch permits evidence
   gathering, but not automated writes. Another SKU or firmware needs review.
3. Export the current launcher's layout. Make a second off-device copy of the
   snapshot and native export. Keep accounts and credentials on that device.
4. Select optional packages according to the driver's preferences. The original
   owner does not use ATOTO tracking, DriveChat or the OEM store. Another owner
   may use them. Cloud-SIM/shared networking components stay outside the trial.
5. Preview/apply a small selected group. Record software state and verify actual
   behavior before expanding the selection. No generic optimizer or cache
   cleaner is needed.
6. If requested, trial the custom home alongside the retained original launcher.
   Follow BUILDING.md, verify its package/signature, install with authorization,
   and launch MAIN / LAUNCHER explicitly before selecting it as default HOME.
   Recreate widgets with that owner's apps and accounts.
7. Check every required feature below. Revert the last group on a regression.

| Feature | Check |
| --- | --- |
| Rear camera | Correct image and reverse priority from home and other apps |
| Dashcam | Current image, recording, saved clip playback after ignition cycle |
| Audio | Each speaker, volume, mute, EQ, AM/FM and no new wake pops |
| Bluetooth | Reconnect, microphone call audio and media |
| CarPlay/Android Auto | Phone reconnect and audio/navigation handoff as used |
| Physical SIM | Mobile data with Wi-Fi disconnected by the owner; restore Wi-Fi before agent transfers |
| GPS | Correct position and normal navigation |
| Vehicle integration | Steering controls/CAN functions as fitted |
| Power | Short stop, overnight return, cold boot and any unexpected battery drain |

Record firmware versions, chosen packages, before/after observations and failure
conditions. Redact serials, SIM identifiers, network names, locations and account
information before sharing results. Do not attach raw snapshots or launcher exports
to public GitHub issues.
