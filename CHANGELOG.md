# 0.3.0-preview

Introduce our own open-source X10 Home dashboard, independent of Lawnchair and
OEM launcher code. It hosts the five standard radio/map/weather/media widgets,
provides eight wide dock targets, an apps list, widget binding/configuration and
Android HOME-role selection. No requested permissions, network/analytics SDK,
shared UID, services or boot receiver. Build with an owner-controlled local key.

Add the exact-stock launcher audit, privacy/logging findings, feature gaps and
ordinary-UID replacement plan. Preserve Quickstep/hardware backends and the
previous HOME during preview; hardware/reboot acceptance is not implied by
source, APK or geometry validation. Native layout export/import and the OEM
injected map/DVR/vehicle panels are not implemented in the first preview.

# 0.2.0-preview

Optional custom still boot logos:

- Prepare an owner's PNG/JPEG/BMP/still WebP as a reviewed 24-bit BMP and
  logo-only USB kit. Preserve aspect ratio and flatten transparency on black.
- Capture and checksum-verify the full original splash over Wi-Fi; bind the
  update journal to that unit, backup, artwork and reviewed updater/panel code.
- Preview/stage without starting the updater. Explicit parked/restart flags
  permit a sole-logo OEM update; interrupted install confirmation is not replayed.
- Verify the complete resulting partition and normal software state after reboot;
  provide a separate guarded original-splash restore, without automatic reboot.
- Add agent instructions, failure branches, source-only packaging and simulated
  transport tests. Other firmware/panels and S8 remain outside the logo profile.

Evidence: one source-unit logo installed through the OEM route; full partition
checksum matched and the owner confirmed appearance and home/audio return.
The generalized workflow is host-tested; raw restoration was not physically
trialed. Ordinary debloat remains disable-only and does not use root commands,
write partitions or restart automatically. No personal artwork/backups are shipped.

# 0.1.1-preview

Friend-agent backup/recovery review:

- Reject incomplete/metadata-only backups and incomplete package inventories.
- Back up the actual original HOME, including third-party launchers and splits;
  hash private evidence and optionally attach a native layout export.
- Gate writes on owner user 0, audited optional-app APK hashes, unchanged live
  target APKs and protected-package checks before/after cleanup.
- Require a snapshot for HOME changes, journal before switching and return to
  the actual original HOME during rollback, including interrupted/HOME-only trials.
- Add `check`, `attach-export`, an executable agent runbook and manual recovery
  branches. Native Lawnchair export is required before replacing an existing
  Lawnchair HOME. Physical vehicle tests remain separate from software checks.

Compatibility: existing version-1 snapshots can still be inspected/restored when
their recorded inventory and identity are complete. Older captures that did not
save their original HOME APK cannot pass full backup verification; take a fresh
capture before a new trial. Use the same snapshot/journals after an interruption.

# 0.1.0-preview

Initial friend-trial source package, 2026-10-25.

- Explicit-device, firmware-gated audit and private snapshot.
- Hash-verified optional APK backup, selected disable-only cleanup and rollback.
- Screensaver plan, existing-home switching and recovery instructions.
- Portable agent skill, compact Audible widget source and Lawnchair dock patch.
- Public/private export boundary and allowlist release packaging.

Evidence: tested source configuration on one X10G2A7E. The owner reports required
features working and approximately one-second return after a short stop. A new
friend-device trial, overnight wake, cold boot and firmware recovery are pending.

This is a preview toolkit, not a universal X10 debloater or a flashable image.
