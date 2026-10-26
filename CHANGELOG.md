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
