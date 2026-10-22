# Steam library widget

A local Omarchy/Quickshell game picker. Click the Steam icon to browse installed games, search titles, star favorites, or launch a game. The bar icon is gray when Steam is closed and blue when a Steam client/background web helper is running. Opening the dropdown does not start Steam.

The panel reads native Steam library indexes and installed-game manifests, including external library locations, and uses cached game artwork. Games are sorted by last played; Proton, Steam runtimes and shared redistributables are excluded. Favorites are independent of Steam's own favorites/categories. Play delegates to Steam's `steam://rungameid/` protocol, and opens Steam as needed. Library, Friends, Store, Settings and Big Picture shortcuts open the official client. No account credentials, OAuth or API key are used. Live friend details, achievements and download controls are not implemented. Cached collection browsing is described below.

## Requirements

Omarchy 4's native shell, Quickshell, Python 3 (standard library only), and the native `steam` executable on PATH. Tested against Omarchy 4.0.4 / Quickshell 0.3.1. Flatpak Steam is not currently supported. Native discovery searches `~/.local/share/Steam`, `~/.steam/steam`, and `~/.steam/root`; `STEAM_DIR` can override/add a root. Library data remains read-only.

## Files

- `SteamWidget.qml`: bar icon, popup lifecycle and backend process coordination.
- `SteamPanel.qml`: search, filters, scrolling library and client shortcuts.
- `GameCard.qml`: artwork, game title, size, favorite and Play actions.
- `steam_backend.py`: VDF parsing, local library/artwork discovery, background status, validated client launches and atomic favorites storage.
- `test_backend.py`: isolated helper tests, with process launching mocked. Run `python3 -B test_backend.py`; no installed game is started.

Favorites are created only when changed, in `$XDG_STATE_HOME/omarchy/steam-widget/favorites.json` (default `~/.local/state/omarchy/steam-widget/favorites.json`). The directory is created with mode 0700, files with mode 0600. An advisory lock and atomic replacement serialize writes. Unreadable or unrecognized favorites files are left untouched. No credentials are stored.

## Bar placement / removal

Validate with `omarchy plugin validate ~/.config/omarchy/plugins/ryze.steam`. Add with `omarchy bar put ryze.steam --section center --after ryze.discord-launcher` (choose a placement appropriate to your own bar). Disable/remove the widget using the Omarchy bar editor before removing its plugin directory. Removing it does not terminate Steam or delete favorites; deleting the separate favorites directory is an explicit optional cleanup step. No Hyprland rules or keyboard bindings are installed.

## Limits

An accepted launch means the command was submitted to Steam, not that the game successfully started. Login, Steam updates, first-run prerequisites and Proton compatibility remain Steam's responsibility. The picker displays fully installed games whose local installation directory is present; offline/unmounted libraries disappear until mounted and refreshed. Refresh occurs when opening, manually, and every 15 seconds while visible; process status updates every 3 seconds. Artwork falls back to a Steam glyph if absent. Runtime/tool filtering is name-based and may need extension for third-party compatibility tools. The widget does not currently show which game is running or manage Steam shutdown.


## Button dropdowns (1.1.0)

Library now opens an in-widget Steam-style collection browser. Favorites and custom collections (such as My games) come from the selected Steam profile's local cloudstorage collection records. Pending modified records and deletion markers are respected. Categories expand/collapse and support search, alphabetical/recent ordering, installed-only filtering, and Games/Games & software filtering. Compact rows use locally cached icons; installed titles have Play, other titles have View (opens that title's Steam library page without starting an installation). Hidden titles are excluded.

Steam collections are read-only. They are separate from the widget's own favorite pins on the main installed-game view; pinning there does not change Steam Favorites. Collection members without cached Game/Application metadata cannot currently be listed. Dynamic collection filter rules are not evaluated; only saved explicit membership is shown. Uncategorized is computed from titles known through this profile's collections, local app history, per-title library cache and installed manifests. `appinfo.vdf` alone is deliberately not treated as owned-library data. Accordingly, Uncategorized and filtered counts can differ from the full Steam client; this is a partial local view, not a full ownership synchronization. No Web API keys or Steam login credentials are used. If multiple local profiles exist, only the one marked MostRecent is selected; profiles are not merged. Account IDs are used internally for local profile discovery and are not returned in the helper's JSON.

Friends opens a dropdown with a Friends & chat client action; live friends/chat remain in Steam. Store opens a dropdown with a search field; results and the full store open in Steam. Settings offers current-session library display options, Refresh, and an explicit Open Steam settings action. Big Picture offers an explicit Enter Big Picture action. These buttons no longer immediately open Steam when clicked.

Additional source files: `LibraryDropdown.qml` (collection list), `ClientDropdown.qml` (other menus), and `steam_collections.py` (bounded binary appinfo reader, profile selection and read-only collection parsing). Appinfo formats 39, 40 and 41 are recognized; an unsupported format falls back to the installed-game picker with a notice. Local-cache parsing follows the format documented by [SteamDatabase/SteamAppInfo](https://github.com/SteamDatabase/SteamAppInfo); cloudstorage record shape is also used by [Steam ROM Manager](https://github.com/SteamGridDB/steam-rom-manager/blob/master/src/lib/category-manager.ts). No code from those projects is bundled and no dependencies were added.


## Built-in Friends (1.2.0)

Friends now renders a native QML profile card and searchable, collapsible In Game, Online, Offline and Status unavailable sections, with avatars, visible game names and Steam chat buttons. The list polls the official Steam Web API while the Friends page is open, with a shared private cache and 30-second refresh interval. The official Steam application can be closed while viewing friends; chat opens a conversation in the Steam application. No message is sent by the widget. Group chats and Steam rich-presence text beyond the game name are not implemented.

Choose Friends, create a user key at <https://steamcommunity.com/dev/apikey> (a local-use domain can be `localhost`), paste it into the masked API key field, and choose Connect. Current Steam profile identity is discovered locally. This uses `ISteamUser/GetFriendList/v1` and `GetPlayerSummaries/v2` at `api.steampowered.com`; Steam profile/friends privacy restrictions still apply. The API can report a friend offline when their status is hidden; the widget does not guess otherwise. A failed refresh retains previous data labeled Last known status; unavailable status is distinct from offline.

The credential lives in `$XDG_CONFIG_HOME/omarchy/steam-widget/friends.json` (default `~/.config/omarchy/steam-widget/friends.json`), written atomically with mode 0600 in a directory created with mode 0700. It is local plaintext protected by file permissions, not an encrypted keyring. The key is sent to the Python helper over stdin, never process arguments, shell.json or logs; Steam receives it via the HTTPS `x-webapi-key` header, not the request URL. Redirects are refused. Returned JSON includes profile/friend identifiers and names needed for UI actions but never the key. Credential replacement is validated first, and an invalid replacement preserves working credentials.

Private friend snapshots are stored separately in `$XDG_CACHE_HOME/omarchy/steam-widget/` (default `~/.cache/omarchy/steam-widget/`) with mode 0600. These contain personal profile/friend data and must not be distributed or committed. API calls are serialized between monitors, lists are batched in groups of at most 100 profiles, and rapid refreshes are bounded. Configuration and cache are scoped to the selected Steam account; switching accounts clears the visible previous list and requires configuring the newly selected account. Avatar requests are restricted to Steam CDN hosts.

The Friends account menu supports changing the key or explicitly disconnecting. Confirming Disconnect removes this widget's saved key and friends snapshots; it does not revoke the key at Steam or log the desktop client out. Uninstallation should keep credential/cache deletion an explicit choice. New files: `FriendsDropdown.qml`, `steam_friends.py`, `test_friends.py`. Run `python3 -B test_friends.py` for isolated HTTP/credential/cache/privacy/chat checks; real HTTP and launches are mocked.

For keyboard bindings or diagnostics, `omarchy-shell ryze.steam menu friends` opens the specified menu on the focused monitor (also library/store/settings/bigpicture). `omarchy-shell ryze.steam status` returns redacted UI state and popup geometry, without keys or friend names/IDs. `omarchy-shell ryze.steam refreshFriends` refreshes monitor instances using the shared cache. These IPC controls never configure credentials.


## Game information popup (1.3.0)

View now opens a compact native popup within the Steam widget, rather than opening the Steam desktop window. It is available for installed and cached uninstalled titles, including from the main game cards. The original library search, expanded collections and scroll position remain mounted behind the details page; Back restores that view. Popup height follows visible content and longer sections scroll internally.

The popup shows cached hero/logo art, installed size or public store minimum storage, playtime and last-played date. The information button expands the short description, developer/publisher, release date, supported platforms and store feature tags. Achievement progress and previews expand separately. Steam-specific Properties, Store, Community and full achievements links are explicit client actions under the gear menu. The heart pins the title to the widget's own favorites, and pinned cached titles appear in the separate Widget pins section; Steam Favorites and collections are not edited.

Play keeps the existing installed-game launch path. Install in Steam requires an explicit Continue in Steam confirmation and delegates to the official client's install protocol. The helper never downloads or installs games itself; the Steam client handles licenses, platform requirements and its installation flow. Tests never execute install/play/native actions.

Local history comes from this profile's localconfig.vdf; achievement/association/description summaries use complete records from the per-title library cache. Some Steam cache files on this installation have an appended description record outside the first JSON array. The read-only parser recovers complete records and ignores an unreadable remainder; it never rewrites Steam's cache. Missing history or achievement data is displayed as unavailable, not inferred as zero.

Public store metadata uses the Steam Store appdetails endpoint, cached for 24 hours. This is an undocumented store endpoint and may change; failure falls back to local details. Personal playtime and achievements use the already configured Steam user key through the existing HTTPS/header-only API helper: IPlayerService/GetOwnedGames/v1 (input_json with appids_filter), ISteamUserStats/GetSchemaForGame/v2 and GetPlayerAchievements/v1. Schema/store data is cached separately from private per-account history; personal details cache for 10 minutes. Hidden locked achievements retain hidden names/descriptions. Legacy achievement CDN paths are normalized to the current Steam community-assets CDN. No API key is returned to QML.

Friends who play loads on explicit expansion. It checks visible owned-game/play-history data of up to 200 friends from this account's existing friends snapshot, with four concurrent requests, per-request timeouts and a deadline. It distinguishes playing now, played recently, played previously, and owns with no recorded playtime. Private/unavailable friend game details are counted separately. Friend wishlist matches are not implemented. This information is cached privately for 10 minutes; disconnecting Friends deletes these personal game caches as well as the friends cache. Favorites and the public store/schema caches are preserved.

New components are GameDetails.qml, GameInfoController.qml and steam_game_info.py. The controller delivers local details first, enriches asynchronously, ignores responses from previously selected games, and preserves favorite changes across responses. `python3 -B test_game_info.py` uses isolated fixtures and mocked API/native actions. `omarchy-shell ryze.steam game 284160` opens a known title's widget popup for keyboard bindings or inspection; it does not launch the game or official client.

`omarchy-shell ryze.steam gameSection about|achievements|friends|actions` expands an information section of the selected game, for keyboard-driven navigation. This interface never activates Play/Install. Backend replies include a request tag to reject cancelled or previous requests when games are reopened or switched.

## Desktop placement

The restore bundle's desktop component now supplies a separate [Steam workspace policy](../../docs/STEAM_WORKSPACE.md): native client windows use workspace 6, maximized fill while alone and tiled together while a secondary managed Steam window is open. This is optional desktop integration, not a requirement of the widget itself. Disabling the widget does not remove those desktop rules. Games and unmanaged notification surfaces remain outside that policy.

## Interface size

Native Steam launches default to 90% desktop UI scale through Valve's `-forcedesktopscaling` option and child-only `STEAM_FORCE_DESKTOPUI_SCALING`. An explicit value already present in the environment overrides the widget default. Restart Steam fully to apply a changed scale. The desktop restore component supplies a matching user desktop entry for app/URI launches. See [scale configuration and removal](../../docs/STEAM_WORKSPACE.md#steam-interface-scale); no Steam profiles or global desktop scale settings are changed.
