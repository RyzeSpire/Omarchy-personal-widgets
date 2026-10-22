# Steam workspace and secondary windows

The desktop component installs `hypr/steam-workspace.lua`, loaded by the managed personal integrations. It overrides Omarchy's default floating rule for the exact native Steam client class. Newly mapped managed client windows open tiled on workspace 6. Games with `steam_app_*` classes and unrelated applications are outside this rule.

When the main window titled Steam is alone on that workspace, Hyprland makes it fullscreen. A second managed window removes fullscreen so the normal tiling layout can show both; closing the secondary window restores fullscreen. Unrelated visible windows placed on that workspace also prevent Steam from covering them. The source machine's dwindle layout was verified to arrange the two Steam windows side by side; other user-selected layouts determine their own split orientation. The policy does not override the user's global tiling layout or bind the workspace to a specific monitor.

All separate managed Steam client windows are included regardless of secondary title, so startup announcements/news are covered when they expose the same native class. The actual automatic notification had already been closed and was not reproduced during validation. Unmanaged X11 menus/toasts, Steam's in-game overlay and shell notifications are not normal Hyprland client windows and cannot be converted into tiled clients by this policy. No Steam notification or account preferences were changed.

The event handlers react to window map/close/workspace changes and Steam title/class changes, coalesced into one short native Lua timer. There is no background polling, extra process, package installation, or authentication. Fullscreen is compositor-side; Steam retains its normal interface state. Existing mapped Steam windows are reconciled after configuration reload. Moving Steam elsewhere is intentionally reversed to the configured workspace.

## Configuration and lifecycle

Set `profile.json` → `workspaces.steam` to an integer from 1 to 99 before applying the desktop restore component. The default is 6; the installer renders the placeholder in the Lua template. Existing live imports in the owned marked block are migrated to the managed integration so installation/update does not register the policy twice. Originals are backed up using the existing installer ledger; uninstall restores them when installed files have not subsequently been edited.

For a standalone installation, render `@STEAM_WORKSPACE@` in the template to the intended number, put the file in `~/.config/hypr/steam-workspace.lua`, and require it after Omarchy defaults. Remove that import to disable the policy, then reload Hyprland and check `hyprctl configerrors`. Disabling does not move existing windows back, restore their prior floating geometry or close Steam. Future windows return to the remaining applicable rules. Do not remove the module while an active require remains in configuration.

## Verification

`lua tests/test_steam_workspace.lua` runs six synthetic policy checks with a mocked compositor. CI uses `lua5.4`; Lua is a development test runtime, while the desktop runs its existing embedded Lua. Installer tests cover configurable workspace rendering, duplicate-import migration, repeated update and restoration of originals in temporary homes.

Live verification on Omarchy 4.0.6 / Hyprland 0.56.2: the existing client became tiled/fullscreen on workspace 6. A newly opened Steam Settings window joined it in two side-by-side non-floating tiles. Only that newly created test window was closed; the main client returned to fullscreen. Hyprland reported no configuration errors. The automatic notification, startup from a fully closed client, other tiling layouts and close/reopen after future Steam updates remain manual coverage.

The policy uses the official [window rules](https://wiki.hypr.land/Configuring/Basics/Window-Rules/), [0.56 dispatcher API](https://wiki.hypr.land/0.56.0/Configuring/Basics/Dispatchers/) and [Lua events/timers](https://wiki.hypr.land/0.56.0/Configuring/Advanced-and-Cool/Expanding-functionality/), checked against the installed Lua API metadata.
