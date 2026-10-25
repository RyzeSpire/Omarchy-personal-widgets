# Export analysis — 2026-10-19

The working desktop was inspected before packaging. The installed setup is not changed by preparing this repository. The package targets Omarchy Quattro 4.0.4 with Hyprland Lua, Quickshell 0.3.1 and Qt 6.11; it is not an OS image or a universal dotfiles distribution.

## Confirmed retained configuration

| Area | Current implementation | Export treatment |
|---|---|---|
| Spotify | QML popup and icon, Python PKCE/Web API helpers, native Spotify/MPRIS engine; volume, shuffle/repeat, playlists, queue, local-playlist selection, confirm quit | Full plugin source; helper resolution made relative only in the exported copy; private tokens/caches excluded |
| Spotify lifecycle | Hidden special workspace; reveal on tenth workspace (key 0); Super+W/Alt+F4/Ctrl+Q confirmation | Managed Hyprland module and bindings included |
| Steam | Installed/cached collection browser, independent widget pins, search, friends API, game-detail popups, achievements and friends-who-play | Full source and existing isolated tests; API key, account caches and pins separate |
| Discord | Native launcher on workspace 8; background-running indicator | Full plugin source; official app dependency; separate desktop shortcut retained |
| Codex | Bar button opens fresh resume picker on workspace 7 on secondary display; older terminal wrapper routes other interactive sessions to workspace 9 | Both retained; the older wrapper previously had an intermittent placement report and is not represented as universally reliable |
| Keyboard | US/Brazilian ABNT2; Alt+Alt toggle; compose Caps; custom keyboard widget | Plugin and input settings |
| Bar/idle | Existing layout, clock format, tray pins; idle screensaver/lock 3600 seconds | Merge the saved bar/idle values, preserve unrelated top-level settings |
| Firefox | Default web URL/HTML associations; Wayland environment | Merge selected MIME defaults and install environment file |
| VPN | Native Proton VPN GTK app from Arch extra; existing split-tunneling/account settings preserved | Reproducible native package install, sanitized optional settings preset, retired-addon upgrade cleanup |
| Both screens in Discord | OBS collection/profile, 3840x1080 canvas, 2560x720 30fps camera, video42 loopback driver and launcher | Scene/profile sanitized, driver config supplied as separate root setup; portal choices must be renewed |
| Audio | Bluetooth A2DP WirePlumber rule; saved device choices in WirePlumber state | Rule public; hardware-specific defaults/routing kept in optional encrypted migration |
| Discord/Vencord | Patched client with enabled plugins/preferences | Sanitized preferences; preserve full account-linked settings only in encrypted backup; patcher must be installed separately |
| Terminal/theme/tools | Foot preferences, ethereal theme/background choice, default agent Codex, mise tool selections | Files and declarative preferences; use packaged theme rather than copying its binaries/artwork |
| Software/system | All explicitly installed packages and versions, foreign packages, enabled service names | Inventory, plus curated dependencies; never blindly restore kernel, GPU, bootloader, disks or networking |

## Portability findings

The source is mainly user-independent already. Remaining assumptions are the Omarchy shell interfaces, Hyprland Lua version, Foot/mise availability, workspace numbers, preferred HDMI output and native Spotify executable/device name. A fresh install supplies the same integration and permits a monitor override. The native Spotify device is matched to the current hostname dynamically. Spotify OAuth uses each user's own Client ID and loopback callback http://127.0.0.1:8765/callback. Steam needs that user's own API key. No personal developer app or account identifiers are embedded in this package.

OBS portal restore tokens were removed from the exported scene. Recording paths use @HOME@ templates, and the OBS browser cookie identifier was removed. Full Vencord configuration contains Discord user/channel references; those and cloud settings are omitted from the public preset. The current Proton settings contain application paths, not login data. No local MP3s or archives are published. The local jazz playlist remains a Spotify feature; the widget does not play files itself.

## Scope and limits

Only the five personal widget directories and pinned VPN source participate in the public source bundle. Old backups, caches, logs, compiled bytecode, notifications, clipboard history, browser/Discord/Steam profiles, Spotify user databases, tokens, keyrings, and Codex chats are excluded. Optional encrypted migration can carry personal state; signing in again remains the preferred authentication path. Full application profiles are optional because they may contain credentials and locks; close applications before exporting them.

No persistent microphone-specific rule was found in the user audio configuration. Device defaults are hardware state, not a portable microphone fix. The OBS workflow still requires actual desktop permission dialogs and matching displays. Old ALVR/SteamVR experiments are not reintroduced. A clean Omarchy desktop installation remains a prerequisite, and real clean-machine playback, OAuth and portal acceptance require human validation. Installer tests use isolated home directories and cannot establish those desktop outcomes.

## Packaging decisions

Retain the existing QML/Python implementation. This is a restoration package, not a rewrite or a new playback backend. Use a separate managed Hyprland module, reversible file journals, dependency checks, explicit system-driver setup and a private-data export utility. Installation defaults to a plan; --apply writes files. Package and system-level operations require separate explicit flags. Publishing contains only reviewed source and sanitized presets. Private-data deletion is never part of uninstall.
