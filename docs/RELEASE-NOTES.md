v0.1.18 — Hide and block Brazil VPN routes

- Default the configurable country policy to BR; hide routes with Brazil entry, exit or declared host-country metadata, including Secure Core paths.
- Apply the filtered catalog to native fastest/country/startup/pinned selections and recheck cached DTOs at the SDK connection boundary so reconnection cannot bypass the block.
- Refuse unadapted-tray connection fallback; provide a read-only native fastest-candidate preview. Preserve the saved-profile auto-connect guard and native account/cache state.
- All 90 isolated checks and source validation pass. Live Brazil searches return zero, blocked validation is refused, and the native fastest preview selects an allowed route without changing the active tunnel.

v0.1.17 — Search and select Proton servers in the widget

- Add debounced country/city/server search, a scrollable 50-result page, cached loads and location/feature labels. Selecting a row does not connect; an explicit Connect button submits that exact server.
- Keep all connection controls in the official app process through a small local adapter. Honor native account/plan checks and revalidate availability; no separate CLI, VPN engine, credential export or pinned-server edits.
- Add a reversible user launcher, native-compatible startup handling and full reinstall/removal documentation. Retain the compact full-color logo and lock badge.
- Prevent NetworkManager from reviving older saved Proton tunnels during switches, using scoped manual-connect flags, private original-value backups and explicit rollback; kill-switch profiles remain unchanged.
- All 74 isolated checks and source validation pass. Live search, native GUI/tray and read-only selection validation checked. The user confirmed search/selection and a switch without the Brazil detour.

v0.1.16 — Restore the full Proton logo and compact badge

- Keep the official logo's original purple/teal gradients and inner shape when the app runs; use grayscale when it is off. Artwork comes from the installed app, with no image binary redistributed.
- Reduce the combined bar icon to a 12 logical pixel canvas and a smaller corner lock. Expose the live icon size in IPC status and reload the shell so stale components cannot hide the change.
- Validate QML/source and inspect live status/rendering without changing the VPN connection.

v0.1.15 — Match Proton icon size to the bar

- Use Omarchy's standard icon canvas and status slot for the Proton icon and lock badge, reducing the bar artwork from 23 to 16 logical pixels at the default theme scale.
- Keep the popup artwork and VPN controls unchanged. QML/source validation and live status/rendering checked; no VPN connection change.

v0.1.14 — Native Proton VPN status companion

- Add an original bar widget beside the other app widgets, using the installed Proton logo with a separate connection-lock badge: gray/white for app off/on, red open/green closed for disconnected/connected, amber transitions and unknown-status fallback.
- Add a compact popup with status/server, guarded Quick connect/Disconnect via the official app tray, and Open Proton VPN / Settings. No account import, CLI polling, network status service or automatic VPN changes.
- Keep the old addon retired and native app settings intact. Package dependencies and temporary-home install/update/removal coverage; 51 isolated tests and six-plugin source validation pass. Live connected rendering/status verified; real connect/disconnect clicks were not automated.

v0.1.13 — Replace Proton addon with the native app

- Remove the retired VPN addon source, assets, tests and bar entry from the current restore payload.
- Install Proton's native GTK application through Arch's recommended proton-vpn-gtk-app package; preserve official account and connection settings.
- Add safe upgrade retirement: preserve unrelated widgets, archive only retired active code/state privately, and prevent old ledger/shell backups from resurrecting it on uninstall.
- The former widget's Always On, profiles and Brazil block are removed; use the native app's own settings. Historical commits/releases remain historical.

v0.1.12 — Proton settings access and Brazil exclusion

- Pin Connections / Settings above the scrolling content and expose supported VPN Accelerator, Moderate NAT, IPv6 and crash-report controls alongside split tunneling and existing protection settings.
- Default blockedCountries to BR and enforce it for every widget connection path, including quick/automatic/saved selections and both Secure Core hops. Cache/no-match failures refuse unrestricted fallback.
- Diagnose the universal scroll failure as missing external-mouse wheel events; the user confirmed recovery after resetting the mouse. No global input changes were needed.
- Add isolated country-policy tests, portable helper packaging, original-file backups and documentation. No VPN reconnection or existing preference change is performed during installation.

v0.1.10 — Sober PipeWire audio preference

- Retain Sober's documented PipeWire workaround for occasional audio crackling, scoped to this app and preserving other permissions.
- Install applies the preference; separate preview/apply actions enable it or restore the default driver without resetting all overrides. A restart between games is required.
- Verified the audio setting/socket inside the Flatpak sandbox. Selective music/sprite authorization failures were investigated separately; another encounter's audio/graphics worked, but the original encounter and crackling improvement remain unverified.

v0.1.9 — Sober launcher discovery

- Expose the official Sober Flatpak desktop entry and icon in standard user XDG directories so launcher search works in the current session without logging out.
- Install/update maintain export links; a standalone launcher action repairs existing installations. Removal deletes only owned links and preserves custom replacements.
- Four isolated link lifecycle fixtures added; all 39 restore checks pass. Desktop-file validation and live discovery passed, and the user confirmed the search result and icon.

v0.1.8 — Roblox through Sober

- Added user-scoped Sober installation from official Flathub, with Flatpak as a curated native dependency.
- Added a standalone preview-first install/update/uninstall helper and first-run, maintenance and removal instructions. Uninstall preserves account data and shared runtimes.
- Recorded relevant native packages and public Flatpak version metadata. Proprietary binaries, Roblox APKs and account state are excluded from the restore archive.
- Validated helper previews in a temporary home and passed all 35 isolated restore checks; actual sign-in/gameplay remain interactive.

v0.1.7 — Smaller Steam UI and Special Offers tiling

- Steam launches from the widget and user desktop entry default to 90% UI scale, preserving global display scaling and all launch actions. Existing explicit widget environment overrides remain supported.
- Fixed the real Special Offers popup refusing tiling because of fixed-size X11 hints. A Steam-only size-limit override lets it split with the main client; ordinary untitled menus remain excluded.
- Added child-environment/URI regression coverage, validated the desktop metadata and retained the existing backup/update/removal lifecycle. Live and isolated verification details are in docs/TESTING.md.

v0.1.6 — Steam fill mode and dropdown stability

- Steam now uses Omarchy's maximized Full width/fill mode while alone on workspace 6, keeping the bar, borders and margins visible.
- Fixed ordinary Steam dropdowns being counted as secondary client windows: the verified untitled popup surface is excluded from tiling and peer counting. Named secondary windows still split with Steam and restore fill mode when closed.
- Added dropdown open/close and late-title regression cases. Eight Lua policy checks pass; live dropdown stability plus Settings split/fill restoration were verified without configuration errors.
- Permanently untitled Steam auxiliary windows remain excluded; the automatic notification still needs inspection on its next appearance.

v0.1.5 — Steam workspace and tiled secondary windows

- Added a user-owned native Steam client policy overriding Omarchy's floating default. Steam opens on configurable workspace 6 and fills it while alone.
- Secondary managed Steam windows join the tiling layout; main-client fullscreen is removed while sharing, then restored after they close. Unrelated peers prevent fullscreen, and game classes are excluded.
- Added portable module rendering, owned-import migration, backup/edit-preserving removal documentation, six isolated Lua scenarios and 35 Python installer/backend checks.
- Live Steam Settings verified the side-by-side transition and fullscreen restoration. The already-dismissed automatic notification remains unverified until its next appearance; unmanaged toasts and menus cannot be tiled as client windows.

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
