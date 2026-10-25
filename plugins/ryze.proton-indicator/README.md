# Proton VPN status and app opener

A small read-only bar indicator. It shows whether the official app is running and whether Proton reports a connection. Clicking opens/focuses the unmodified official app. It has no popup, server list, connect/disconnect command, account integration, app wrapper, launcher override or country policy.

- Dim grayscale logo: app off; full-color logo: app on, including when hidden in the tray.
- Green closed lock: connected. Red open lock: not connected. Amber: network transition. Gray question mark: status unavailable.
- App and tunnel state are independent: closing the GUI does not necessarily disconnect a tunnel.

The compact 12-unit logo is loaded from the installed official app. Artwork is not redistributed. Status polls local session/system D-Bus every five seconds. When available, the official tray's connection state takes precedence over a merely activated interface; NetworkManager is the fallback when the app/tray is absent. Only Proton WireGuard/OpenVPN tunnels count; dummy kill-switch devices and other VPNs do not. An activated tunnel is not a guarantee that every app uses it or that an external website is reachable.

Opening first focuses an existing native window by its verified app PID. A hidden running app uses its native tray Show entry, with owner-PID and menu-revision/property checks; ordinary desktop activation is the fallback. A closed app starts the ordinary `protonvpn-app` executable without custom flags. No new controller is started while the app is running. The native app keeps its startup/minimize preferences and sign-in prompts. If a future app release no longer exposes a recognizable Show entry, use its native tray; localized Show labels use the installed app's translation catalog. The helper never imports Proton account code or uses VPN-changing APIs, profile changes or state backups.

Requires the official `proton-vpn-gtk-app`, NetworkManager, Python with `python-dbus`, and Omarchy's Quickshell/Qt Quick Effects runtime, already covered by the restore dependencies. Verified against app 4.18.7-1. The new ID `ryze.proton-indicator` is separate from retired adapters, which remain removed.

The widgets component installs/updates the indicator and bar entry with standard file backups. Bundle removal restores originals/removes owned indicator files and keeps the official app, launcher, account and network settings. Reinstall/migration tests ensure retirement of the old adapters does not remove this indicator. There is no widget account setup or private state to export.

Read-only check: `python3 -B proton_indicator.py status`. App opening: `python3 -B proton_indicator.py open`. All other commands are rejected. Tests use fabricated app/bus/window data and temporary homes.
