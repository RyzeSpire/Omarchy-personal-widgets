# Export verification — 2026-10-19

Completed against the separate package without installing it over the working desktop:

- 23 isolated packaging/Spotify regression tests passed.
- 30 exported Steam helper tests passed.
- All six plugin manifests passed installed Omarchy schema validation.
- All 23 QML components parsed successfully; nine Lua configuration files parsed with luac.
- Python and JSON parsed successfully.
- The public tree was checked against seven known private values (OAuth credentials/client identity, Steam account configuration and OBS portal grants); zero matches. Values were not printed or saved into the repository.
- Source provenance records compare 70 source files with their exported copies. Only one plugin source file differs: SpotifyWidget.qml resolves its three helpers relative to itself in the exported copy. The live source file is untouched.
- Public archive checksums verified after extraction. The extracted installer previewed, installed twice and uninstalled in a temporary home containing spaces, using a different username/monitor connector.
- Camera system-file install/remove passed against an isolated fake root; no host module was loaded.
- GPG encrypted/decrypted a fake private-state fixture in an isolated temporary GPG home. No real personal backup or production keyring was created/modified by that test.

Not claimed: a fresh graphical Omarchy installation, new-machine OAuth, native app sign-ins, real OBS permission dialogs, or end-to-end playback on new hardware. Follow TESTING.md to validate those. Dependency installation, live configuration application and private account export have not been run on the source machine. Current working widget files and services remain unchanged.
