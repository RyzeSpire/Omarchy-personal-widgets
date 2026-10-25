# Proton VPN status and server picker

An original Omarchy widget around the installed official Proton VPN GTK app. The native app still owns its account, settings, VPN protocols and connection lifecycle. The old OmaProton addon remains retired.

## Icon and controls

- Grayscale Proton logo: app off. Full purple/teal logo: app running, including in the tray.
- Green closed lock: NetworkManager reports an activated Proton tunnel. Red open lock: no active tunnel. Amber open lock: a transition. Gray question mark: status unavailable.
- App status and tunnel status are independent. Split tunneling can also mean some apps bypass a connected tunnel.

The combined bar artwork uses a compact 12-unit canvas and Omarchy's standard status slot; theme scaling applies. The popup keeps a larger logo. Restart the shell if an old component stays cached; IPC status reports the actual icon size.

Left-click opens the popup; right-click opens the official app. Escape/outside click dismisses it. Tab/Enter operates the search and buttons. The wheel or scrollbar scrolls the server list.

Search by country, city, code or server name. Search folds accents/case, shows 50 results per page, and includes location, cached load and applicable Free/Secure Core/Tor labels. Results are ordered by Proton's own cached server score. Refresh rereads the app's in-memory catalog (up to five seconds of picker caching), not a new third-party API. Load figures can therefore lag behind actual load. Offline and higher-tier servers are omitted. The live native controller checks the server again when connecting, including account, plan and availability restrictions. No unrestricted fallback is used if the selected server becomes unavailable.

Click a row to select it, then **Connect to …** to connect. Typing, browsing, paging and selecting rows never change the VPN connection. Quick connect and Disconnect use the same official app controller. Quick connect uses Proton's own fastest-server selection within the permitted country list. Brazil is hidden and blocked by the bundled country policy. Automatic widget reconnection is not added. Countries, split tunneling and other advanced settings remain available in the native app.

## Native app adapter

`proton_widget_app.py` launches the installed official `App` and `Controller`, adding a small session-bus server picker inside that same process. It does not patch package files, copy the client, run the CLI alongside the GUI, create another account session, rewrite native settings, or export credentials. The bar helper verifies that the adapter and canonical app belong to the same process. Only display fields are returned: names, locations, load, feature labels and availability. Account IDs, IPs, physical server data, keys and tokens are not returned.

Requires `proton-vpn-gtk-app`, `networkmanager`, `python-dbus`, `python-gobject` and Omarchy's Quickshell/Qt Quick Effects runtime. The official logo is loaded from the installed app (`proton-vpn-sign`), not redistributed. Tested with app 4.18.7. The adapter uses version-dependent native Python interfaces; after incompatible app updates, check the official app and update this adapter. `python3 -B proton_widget_app.py --check` checks installed interface compatibility without constructing a controller or connecting.

The widgets restore component installs a user desktop launcher with the same **Proton VPN** name, pointing to the adapter. It backs up/restores an existing personal launcher. Use this launcher or the widget to start the app after reboot. Running bare `protonvpn-app` while it is closed starts the unadapted official entry point: exit it and start through the launcher/widget to restore server browsing. Repeated launcher invocations activate the existing app and do not create a second controller. Normal app startup keeps its existing auto-connect preference. Internal migration restarts can use `--widget-resume --start-minimized` to suppress startup auto-connect for that process and retain the active tunnel.

Saved Proton WireGuard/OpenVPN profiles are marked **manual connect** before app startup and each explicit widget request. This prevents NetworkManager from reviving an older server between switches; only `connection.autoconnect` is changed. Kill-switch dummy profiles, other VPNs, WiFi, routes and secrets are untouched. The native app's own reconnection/startup preferences still apply. A failed guard refuses the widget request instead of connecting through another profile.

Original flags are backed up privately under `$XDG_STATE_HOME/ryze-proton-widget/autoconnect-originals.json` (default `~/.local/state`). They are machine-specific and excluded from this package. Preview with `python3 -B plugins/ryze.proton-vpn/proton_autoconnect.py`; apply with `--apply`. To deliberately restore original flags, run that repository helper with `--restore --apply` (which may reenable an old server's automatic activation). Bundle removal preserves the manual-connect flags; this explicit rollback remains available from the checkout.

The adapter reads the official app's existing server model; no separate cache, credentials, settings or pinned-server entries are written. Regular status polling reads local D-Bus every five seconds, every two seconds while open. Server requests are debounced and bounded; stale replies cannot overwrite a newer query. Search text is not saved.

## Reinstall and removal

The widgets installer previews by default. Apply it to install/update the widget and its user launcher together. Temporary-home tests cover repeat install, paths with spaces/quotes, preserving native settings, and restoring an existing personal launcher on bundle uninstall. Removal does not remove the native package or account data. Close the adapter app and start the system `protonvpn-app` after removing this widget to return to the unadapted native entry point. Shared native settings, profiles and keyrings remain outside this bundle.

Development: `python3 -B -m unittest discover -s tests -p 'test_proton*.py' -v`. Tests use fabricated controllers/servers and temporary homes; no real connect/disconnect is issued. Read-only live checks: `proton_status.py status`, `proton_status.py search Netherlands 0`, and `proton_status.py validate <server-name>`. Validate checks the native live model but never connects.

## Blocked-country policy

`country-policy.json` defaults to `BR`. Brazil entry, exit and declared host-country routes are hidden from widget search and the adapted native app's catalog. The same guard checks direct selections and revalidates every SDK connection, including cached reconnect requests. Native fastest-server selection, startup targets, countries and pinned choices use the filtered catalog. A blocked/unknown route is refused without an unrestricted fallback. Secure Core paths involving Brazil and virtual routes with a declared Brazil host are excluded too. The original account/server cache remains unchanged.

The adapted app disconnects an existing route when its native current-server metadata identifies it as blocked; it does not automatically choose a replacement. The widget also refuses to connect through an unadapted native tray because that path cannot enforce the policy. Keep using the provided Proton launcher/widget. Independently launched CLI clients, raw NetworkManager profiles and the original system entry point are outside this in-process policy; it is not an operating-system country firewall.

The app's installed package files are untouched. To deliberately change the blocked countries, edit the packaged JSON and restart the adapted app. Invalid policy data fails closed; a missing policy file retains the Brazil default. Read-only verification: `proton_status.py search Brazil 0`, `proton_status.py validate <blocked-server>` (must refuse), and `proton_status.py preview-fastest` (returns an allowed native candidate without connecting).
