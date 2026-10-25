# Proton VPN status widget

An original Omarchy widget around the official Proton VPN GTK app; it does not restore OmaProton.

- Gray Proton logo: official app is not running. White: app is running, including in the tray.
- Green closed lock: NetworkManager reports an activated Proton tunnel. Red open lock: no active Proton tunnel.
- Amber open lock: connecting or disconnecting. Gray question mark: connection status is unavailable.
- App status and tunnel status are independent. Closing/quitting the app does not by itself prove that the tunnel disconnected. A connected tunnel also does not imply every application uses it when split tunneling is configured.

Left-click opens a compact status popup with the connected server name, Quick connect/Disconnect and Open Proton VPN / Settings. Right-click opens the official app directly. Escape/outside click dismisses the popup; Tab/Enter operates its buttons. Starting the app does not itself issue a connect command. Proton's own startup preferences still apply.

Quick connect and Disconnect invoke the current official app tray-menu action only after a user click. No separate CLI/account session is started, no credentials are read, and no settings are rewritten. Controls are disabled when absent, hidden, disabled, ambiguous or unavailable; open the official app and sign in privately if needed. Quick connect uses Proton's own fastest-server selection and settings, with no custom country blacklist. Countries, split tunneling and advanced settings remain in the official app; the button opens its main window, where Settings is available.

Requires `proton-vpn-gtk-app`, `networkmanager`, `python-dbus` and Omarchy's Quickshell/Qt Quick Effects runtime. The logo is loaded from the installed official package (`proton-vpn-sign`), not redistributed here. Status polls local D-Bus every five seconds, every two seconds with the popup open. It never imports Proton account libraries or calls external status/IP APIs. The official GTK app's tray-menu interface is version-dependent (verified with 4.18.7); if it changes, status can still work while controls fall back to the official app.

The widgets restore component installs/updates this folder and merges `ryze.proton-vpn` into the bar. Preview remains read-only, updates retain backups, and bundle uninstall removes owned files while preserving official app settings/accounts. To hide it independently use Omarchy's bar editor or remove its layout entry. Keep the native app installed for VPN use. The older addon retirement migration remains in place.

Development: `python3 -B -m unittest discover -s tests -p 'test_proton_status.py' -v` uses fabricated state and temporary homes. Read-only live inspection: `python3 -B plugins/ryze.proton-vpn/proton_status.py status`. Never exercise real connect/disconnect as part of automatic tests.
