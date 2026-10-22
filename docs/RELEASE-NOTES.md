v0.1.4 — Pointer-positioned keyboard menu

- The keyboard chooser now opens next to the mouse on its monitor, flipping left near the right edge and above near the bottom. Mid-screen placement centers vertically beside the pointer; coordinates stay fixed after opening.
- Supports logical display scaling, monitor offsets and negative origins, with bounded placement and a bar-anchor fallback if pointer lookup fails.
- Added a local MIT adaptation of Omarchy's keyboard panel for placement while preserving its focus/dismissal/theme behavior; shared shell source and global configuration remain untouched.
- Seven keyboard model checks pass, covering all six illustrated placements, tight bounds and monitor routing. Live pointer/menu coordinates were checked on the running desktop; manual confirmation is recorded separately.

v0.1.3 — Keyboard layout chooser

- Added a themed menu for configured keyboard layouts, opened anywhere with Super + middle-click, or by right/middle-clicking the indicator. Left-click still cycles; the chooser supports arrow keys, Enter and Escape.
- Layout choices and variants come from the user's current Hyprland/XKB configuration. Matching physical keyboards switch together by layout identity rather than assuming identical per-device ordering. Virtual input-method devices are excluded.
- Added focused-monitor popup routing, explicit switch error feedback, portable shortcut packaging and migration preventing a duplicate pre-bundle binding. Existing backup and edit-preserving removal remain in use.
- Added isolated keyboard model checks, shortcut installation/update/removal coverage and CI execution. Live desktop checks and their limits are recorded in docs/TESTING.md.

v0.1.2 — Native download manager and keyring recovery

- Added Persepolis from Arch's official repository to the restore profile, with Firefox extension setup, updates, removal instructions and affected package inventories.
- Recorded FDM package removal and cleanup of its obsolete integrations while preserving personal downloads/settings.
- Added an optional, preview-by-default repair for malformed multiline JSON in an existing GNOME text keyring. It preserves the credential entries and protection mode, backs up outside Git and replaces the file atomically. Actual vaults, tokens and private backups are excluded.
- Added five fabricated-data recovery tests and distribution GLib support to CI. All 31 isolated packaging/Spotify/recovery checks passed locally; source/manifests/QML/Lua validation passed.
- Existing widget implementation files are unchanged. The repair helper is not run automatically by the installer.

v0.1.1 — Persistent packaging policy

Persistent packaging policy for future Codex-assisted Omarchy changes.

- Global working instruction installed in Codex home and supplied in the desktop restore payload.
- Repository AGENTS.md and docs/PACKAGING_POLICY.md define the packaging, verification, privacy and publication completion workflow.
- Installer merges the managed block without replacing unrelated instructions, supports active global override files, and restores originals on removal.
- Policy files are included in the source archive; both global instruction files can also migrate through the private encrypted export.
- 26 isolated packaging/Spotify regression checks passed; QML/Lua/Python/JSON and all six manifests validated. Existing widget playback code is unchanged.

Restart other already-open Codex sessions to load the guidance. This is a Codex working rule; changes made outside Codex still need an explicit audit/export. No credentials or chat history are published.
