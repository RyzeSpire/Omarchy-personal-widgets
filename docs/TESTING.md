# Verification

Run `python3 -B -m unittest discover -s tests -v` for installer, backup/rollback, path containment, merging and private/public separation. Run the Steam helper suites using `python3 -B -m unittest discover -s plugins/ryze.steam -p 'test_*.py' -v`. These use temporary fixtures/mocks; no Steam account, Spotify playback or desktop configuration is changed.

`python3 -B scripts/validate.py` parses Python/JSON, checks manifests, scans known dangerous payload patterns and runs available QML/Lua parsers without changing the desktop. QML parsing cannot validate all Omarchy runtime types. `python3 scripts/make-release.py` builds the public source tarball and checksums in ignored `dist/`. That artifact deliberately omits private state.

For a clean install use a fresh Omarchy account or separate VM with a graphical Hyprland session. Clone the repository without copying any old dotfiles. Preview/install, reboot after camera setup, and check Hyprland errors. Validate keyboard switching, theme/bar layout, Firefox URL handling, idle settings, each app shortcut and secondary-screen fallback. Authorize Spotify/Steam/Proton independently. Test Spotify background start, full-app reveal, minimize/quit confirmation, controls, playlists/queue and a local playlist already indexed by Spotify. Test Steam installed/uninstalled game views, read-only friends/achievements, explicit Play/Install actions and hidden/private error states. Confirm Vencord after its external patcher installation. Accept OBS portal prompts and select the camera in Discord.

Exercise different usernames and paths containing spaces, one/two monitors, disconnected external output, missing dependencies, revoked tokens, API failures, install twice, update, user edits then removal. Record exact Omarchy/Hyprland/Qt versions. Verify uninstall leaves account data untouched and restores originals, then reinstall. Do not claim real desktop/account feature parity from fixture tests alone. No clean VM/account session is created by the export preparation.

The keyring recovery suite uses fabricated JSON/certificate text and the distribution GLib parser through PyGObject. On Omarchy, use the system Python with `python-gobject` installed. CI installs Ubuntu `python3-gi`/`gir1.2-glib-2.0` and runs the isolated suite with `/usr/bin/python3` so its native bindings match the interpreter; Python 3.14 remains selected for source validation, Steam tests and archive building. The complete 31-test isolated suite also passed locally on the source system's Python 3.14. Live keyring/account checks are explicitly local, require authorization and are never part of CI.

## Keyboard layout chooser

Run `node --test tests/test_keyboard_layout.cjs` for XKB labels/variants, missing catalog fallback, physical-device filtering, layouts in different per-device orders, and existing indicator selection behavior. Node is a development/CI dependency only. Installer tests also verify the marked live shortcut migration, repeated installation and removal restoring the original configuration in a temporary home.

On a running desktop, use Super + middle-click on each monitor and confirm the chooser appears on the focused output with the active entry marked. Select each configured layout and verify the actual keyboards plus all bar indicators agree. Check ordinary left-click cycling, right/middle-click menu access, Up/Down/Enter, Escape, outside-click dismissal and switching to another bar popup. With three configured layouts, verify cycling reaches all three. Test a keyboard with a different layout order and one lacking the selected variant. The menu must not add layouts, change configuration, touch virtual input-method devices, or change a layout merely by opening/cancelling. Recheck `hyprctl configerrors` and Quickshell logs after hot reload.

Recorded live result on 2026-10-22: the user confirmed Super + middle-click opens the menu, selecting a layout switches it, and the indicator updates. The shortcut registry contained one matching binding and Hyprland reported no configuration errors. Source/manifests parsed; four keyboard model checks and 33 isolated Python checks passed. Menu cancellation, arrow navigation and both-monitor interaction still require broader manual coverage; they are not claimed as completed by those confirmations. The updated shell retained an old component through plugin hot reload, so `omarchy restart shell` was used once to load the implementation.

Pointer-placement regression checks (v0.1.4): the seven keyboard JavaScript checks cover all six illustrated side/vertical placements, constrained space, negative monitor origins and logical-coordinate routing. The live panel reported an anchor at (619,64) and a bounded menu at (631,76), size 312x114 on a 1280x720 logical display; this verifies the actual geometry path rather than only the helper. Check Super + middle-click near every corner and side on both monitors, ensure moving toward the menu leaves it fixed, then select a layout and dismiss with Escape/outside click. Cursor-query failure has a bounded timeout and bar-anchor fallback; that failure path is not claimed as live-tested. Inspect the plugin-owned CursorPanel.qml against upstream after Omarchy shell updates.

The pointer panel also passed installation, a repeated update, and removal in an isolated temporary home with spaces in its path. No live installer was run for that check.

## Steam desktop window policy

Run `lua tests/test_steam_workspace.lua` (CI: `lua5.4`) for six mocked compositor scenarios: client fullscreen and game exclusion, arbitrary secondary notification window and restoration after close, unrelated workspace peers, multiple secondary windows and late titles, hidden windows/coalescing/idempotence, and duplicate temporary Steam titles. The isolated Python suite now contains 35 checks including workspace rendering validation and install/update/uninstall import migration. These tests do not launch Steam or alter a desktop.

Live result on 2026-10-22: Steam became non-floating and fullscreen on workspace 6; opening only Steam Settings produced two non-floating side-by-side tiles there, then closing only the newly created test Settings window restored main-client fullscreen. Configuration errors were empty. The original automatic notification was already closed, so its exact class/managed state remains unverified; check it on its next natural appearance. See STEAM_WORKSPACE.md for scope and other manual coverage.

Steam fill-mode correction (v0.1.6): eight Lua policy scenarios pass, adding an untitled dropdown open/close check and a normal window whose title arrives later. Live X11 inspection identified the Library dropdown as a titleless POPUP_MENU. With it open, the main Steam client stayed maximized (internal mode 1), bar/margins visible, and the dropdown stayed floating. A new Settings window still produced two side-by-side tiles; closing only that test window restored mode 1. Configuration errors were empty. This supersedes v0.1.5's full-screen-alone behavior; the earlier recorded test describes that earlier version.

## Steam UI scaling and fixed-size Special Offers (2026-10-22)

31 isolated Steam helper checks passed, including child-only scale environment, unchanged GDK scaling, explicit overrides and URI preservation with/without the launch wrapper. All 35 isolated installer/Spotify/keyring tests and eight Steam Lua policy checks passed. Source/manifests/QML/Lua validation passed. `desktop-file-validate` accepts the user override with only upstream metadata notices (multiple main categories and deprecated KDE discrete-GPU key). A temporary home containing spaces verified desktop install, repeated update, all ten scaled Exec actions and restoring an existing override on removal.

Live: Special Offers is a normal Steam X11 window whose minimum and maximum size were both 1412 × 1660. A normal tile command left it floating; the Steam-only `no_max_size` rule let it tile beside Steam at 941 × 1032 each on workspace 6. After deploying through the backup ledger and an error-free Hyprland reload, Steam exited gracefully and reopened at scale 0.9 (verified in its command line and child environment), with inherited GDK_SCALE still 2. The main client alone returned to fill mode on workspace 6. No game was running during the restart. The 90% visual preference remains subject to user confirmation; 100% had already been confirmed working and the user requested a little smaller. A later automatic popup appearance and future Steam version behavior remain manual coverage.

## Sober / Roblox restore (2026-10-22)

The standalone Sober helper's install, update and uninstall previews ran with a temporary HOME containing spaces and left it empty. Removal preview preserves app data (no `--delete-data`). All 35 isolated restore/Spotify/recovery checks passed after adding Flatpak to the curated dependency list. Source/JSON/QML/Lua validation passed. Native Flatpak was installed through Omarchy; only its five newly installed package versions were added to the inventory, preserving the earlier baseline.

The public package contains installation/update/removal commands and version/source metadata only. Sober/Roblox binaries, account state and Flatpak profiles are not copied. Gameplay, account sign-in and the first-run automatic Roblox download require an interactive user session and are not asserted by the isolated tests.

Live installation completed: Sober 1.8.0, user scope, stable Flathub origin, GNOME Platform 51. Its mapped first-run window was verified after launch. Public app/ref/commit/runtime metadata is recorded in `inventory/flatpak-apps.json`; completion of the Roblox download and sign-in awaits user interaction.

The packaged helper was then applied against the installed user app: Flathub was preserved, the installed Sober ref was skipped successfully, and the command exited cleanly without launching or deleting app data.

## Sober launcher discovery (2026-10-22)

The running session's XDG_DATA_DIRS contained only system directories, so Sober's valid Flatpak export was absent from launcher search. The helper now creates standard user desktop/icon links. Four temporary-home fixtures cover repeat install and following upstream export changes, owned/dangling-link removal, preserving conflicts without partial installation, and missing export handling. All 39 isolated tests and source/manifest validation passed. The installed desktop entry passes desktop-file validation, and the standard GIO resolver finds Sober without a logout. The user confirmed Sober appears with its icon after reopening search. No shell restart, session-environment change or app restart was needed.

## Sober audio investigation (2026-10-22)

The user reported working effects with missing music/sprite assets and occasional menu audio crackling. Private local inspection found explicit Roblox asset-authorization errors for the affected content. The user later confirmed another encounter had working music and character graphics, supporting selective asset failures; the original encounter remains unverified. No renderer, graphics flags, login state or cache was changed.

Applied the documented Sober-only PipeWire environment/socket override, preserving unrelated existing permissions and saving the original override privately outside the repository. A fresh Sober shell sandbox verified SDL_AUDIO_DRIVER=pipewire and an accessible PipeWire socket. The active game was not restarted. Hearing crackling improvement requires a later full Sober restart and user feedback; current playback does not prove that improvement. The helper packages this preference with per-setting rollback, while no private log/account data is exported.

All 39 isolated restore checks and source validation passed after this helper change. All six action previews left a temporary HOME empty. Applying audio-pipewire and audio-default against a temporary XDG data directory verified actual Flatpak environment/socket changes and preservation of an unrelated filesystem permission; the live override file hash stayed unchanged during that test.

## Proton widget policy and settings (2026-10-25)

Seven synthetic server-selection/entrypoint tests exercise allowed/blocked routes, no-CLI-on-block behavior, features, tiers and missing cache. Live cache selection was dry-run only. Settings display and scroll geometry were checked without changing VPN routing or protection values. The user confirmed wheel recovery after resetting the external mouse; the touchpad remained functional. Reconnection and changes to VPN/split values remain manual coverage. Historical addon behavior is superseded by PROTON_APP.md.

The isolated public Proton checkout passed all 46 restore/policy tests. Source/manifest validation passed. The final live panel had 467 pixels of scrollable overflow with Settings pinned, BR absent from 148 allowed country rows, and the existing connected/include-three-app state intact. A VPN connection or setting-toggle test was not performed.

## Native Proton app replacement (2026-10-25)

All 42 isolated public restore tests passed after replacing the addon; source validation found five retained widgets and no retired addon payload. Three new retirement fixtures verify read-only preview, repeat upgrade, preservation of unrelated/private state and no resurrection through ledger/shell-backup restoration. The GUI package/launcher and visible native app window were verified; the addon is no longer discoverable. Retirement left the official settings hash unchanged and did not issue a connect/disconnect/logout command. Account sign-in and a new VPN connection remain interactive checks.

The user confirmed the official app recognizes the account and its Settings page is ready.

## Native Proton status companion (v0.1.14)

Nine fabricated-state/temporary-home tests cover kill-switch exclusion, unrelated VPN exclusion, connection transitions, OpenVPN authentication state, app-off/tunnel-on independence, unavailable status, exact visible/enabled menu actions, refreshed menu IDs, unavailable controls and repeated install/removal preserving private Proton settings. The complete public isolated suite passes 51 tests. Source, six manifests and QML/Lua parsing pass.

Live checks confirmed official-app ownership of the tray, an active Proton tunnel in NetworkManager, the appropriate Disconnect capability and a loaded IPC status handler. The popup and white-logo/green-closed-lock rendering were visually inspected on the desktop. No live connection, disconnection, logout, app quit or country change was issued. Red/off/transition/error states are covered by fabricated state, not by disrupting the current connection. Manual connection clicks and behavior with different app versions/locales remain user-side checks.
