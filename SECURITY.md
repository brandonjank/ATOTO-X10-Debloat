# Device access and private data

The tested stock firmware accepted a never-paired ADB TLS client during a
separate controlled test. Its ADB authentication issue is unresolved. This
project does not claim that the Wireless debugging toggle guarantees pairing
enforcement on that firmware. Keep access on a trusted Wi-Fi network and turn
debugging off when no longer needed if that matches the owner's preference.

The project does not add a fixed-port ADB relay, boot listener, privileged helper
or authentication workaround. The earlier experimental relay is not included.

Keep `.local/`, snapshots, accounts, private signing material and OEM firmware
outside public releases. `check_release.py` checks the reviewed source list for
common accidental leaks; it is not proof that arbitrary imported files are safe.
Use the allowlist packager instead of zipping the parent research workspace.

For an issue, share the tool version, sanitized audit and exact failed step.
Avoid raw logcat, screenshots of addresses, Wi-Fi credentials, IMEI/ICCID/IMSI,
serials or application exports. Never send your signing keystore to a tester.
