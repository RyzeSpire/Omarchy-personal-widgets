# Steam workspace and secondary windows

The desktop component installs `hypr/steam-workspace.lua`, loaded by the managed personal integrations. It overrides Omarchy's default floating rule for titled windows of the exact native Steam client class. Newly mapped managed client windows open tiled on workspace 6. Games with `steam_app_*` classes and unrelated applications are outside this rule.

When the main window titled Steam is alone on that workspace, Hyprland uses maximized fill mode (internal state 1), matching Omarchy's Full width action: the bar, margins and borders remain visible. A second real window removes that mode so the normal tiling layout can show both; closing it restores fill mode. Unrelated visible windows placed on that workspace also prevent Steam from covering them. The source machine's dwindle layout was verified to arrange the two Steam windows side by side; other user-selected layouts determine their own split orientation. The policy does not override the user's global tiling layout or bind the workspace to a specific monitor.

All separate titled Steam client windows are included regardless of their secondary title, so startup announcements/news are covered when they expose the same native class. The automatic Special Offers window was subsequently inspected live: it is a normal titled Steam X11 client whose equal minimum/maximum size hints prevented tiling. The Steam-only `no_max_size` rule releases that restriction; both it and Steam were verified as 941 × 1032 non-floating tiles on workspace 6. Unmanaged X11 menus/toasts, Steam's in-game overlay and shell notifications are not normal Hyprland client windows and cannot be converted into tiled clients by this policy. No Steam notification or account preferences were changed.

The event handlers react to window map/close/workspace changes and Steam title/class changes, coalesced into one short native Lua timer. There is no background polling, extra process, package installation, or authentication. Fill mode is compositor-side; Steam retains its normal interface state. Existing mapped Steam windows are reconciled after configuration reload. Moving Steam elsewhere is intentionally reversed to the configured workspace.

## Configuration and lifecycle

Set `profile.json` → `workspaces.steam` to an integer from 1 to 99 before applying the desktop restore component. The default is 6; the installer renders the placeholder in the Lua template. Existing live imports in the owned marked block are migrated to the managed integration so installation/update does not register the policy twice. Originals are backed up using the existing installer ledger; uninstall restores them when installed files have not subsequently been edited.

For a standalone installation, render `@STEAM_WORKSPACE@` in the template to the intended number, put the file in `~/.config/hypr/steam-workspace.lua`, and require it after Omarchy defaults. Remove that import to disable the policy, then reload Hyprland and check `hyprctl configerrors`. Disabling does not move existing windows back, restore their prior floating geometry or close Steam. Future windows return to the remaining applicable rules. Do not remove the module while an active require remains in configuration.

## Verification

`lua tests/test_steam_workspace.lua` runs eight synthetic policy checks with a mocked compositor. CI uses `lua5.4`; Lua is a development test runtime, while the desktop runs its existing embedded Lua. Installer tests cover configurable workspace rendering, duplicate-import migration, repeated update and restoration of originals in temporary homes.

Live verification on Omarchy 4.0.6 / Hyprland 0.56.2: the client uses maximized fill on workspace 6. With its untitled Library dropdown open, the main client remained in mode 1 and the menu stayed floating. A newly opened Steam Settings window joined it in two side-by-side non-floating tiles. Only that newly created test window was closed; the main client returned to mode 1. Hyprland reported no configuration errors. Other tiling layouts and behavior after future Steam updates remain manual coverage.

The policy uses the official [window rules](https://wiki.hypr.land/Configuring/Basics/Window-Rules/), [0.56 dispatcher API](https://wiki.hypr.land/0.56.0/Configuring/Basics/Dispatchers/) and [Lua events/timers](https://wiki.hypr.land/0.56.0/Configuring/Advanced-and-Cool/Expanding-functionality/), checked against the installed Lua API metadata.

## Transient menu handling

Steam's Library dropdown was inspected live: X11 identifies it as `_NET_WM_WINDOW_TYPE_POPUP_MENU`, with no title. Hyprland's Lua window metadata exposes its empty title but not that X11 type. The policy therefore excludes untitled Steam surfaces from static tiling, window moves and peer counting. Ordinary dropdowns stay popups and no longer toggle the main window between modes. A normal client window that initially lacks a title becomes managed when a title arrives. A permanently untitled Steam auxiliary window is also excluded; if the automatic notification uses that shape, inspect it separately before extending the match. No X11 inspection command is added as a runtime dependency.

## Steam interface scale

The source machine prefers 90% (`0.9`) Steam desktop UI scale. The widget passes Valve's `-forcedesktopscaling` argument and a child-only `STEAM_FORCE_DESKTOPUI_SCALING` environment variable on every native-client action. An explicitly supplied environment value overrides the widget default. Global monitor/GDK scaling is preserved. Steam must fully exit and reopen to change its existing UI scale; opening another URI in an already-running client does not reliably apply a new scale.

The desktop component also installs `~/.local/share/applications/steam.desktop`, copied from the package's public desktop metadata with all ten launch actions set to `0.9`. This covers the app launcher and Steam URI handling when that desktop entry is used. The widget component supplies its own scale arguments, so either component works independently. Direct manual `/usr/bin/steam` calls bypass the desktop override; use `STEAM_FORCE_DESKTOPUI_SCALING=0.9 /usr/bin/steam -forcedesktopscaling 0.9` for the same behavior.

To choose a different retained default, change both occurrences of `0.9` in each desktop entry Exec line and the widget backend's default value before reapplying those components. Updates use the existing backup ledger; uninstall restores a previous user desktop override or removes the newly installed one, preserving later manual edits. The system desktop entry, Steam profile/account files and game files are never modified. No additional runtime dependency is needed. The desktop metadata was taken from Arch Steam 1.0.0.87-3; review it against upstream when updating Steam integrations.

Valve documents these scale controls in its [Steam desktop update notes](https://store.steampowered.com/news/posts/?enddate=1687195871&feed=steam_blog). The fixed-size override uses Hyprland's documented [no_max_size rule](https://wiki.hypr.land/Configuring/Basics/Window-Rules/).
