# Proton widget settings and allowed countries

The personal OmaProton VPN copy retains upstream MIT attribution and its original baseline commit. The widget now pins **Connections** and **Settings** above its scrolling content. Settings contains Kill Switch, NetShield, Always On, port forwarding, split tunneling (enable, include/exclude Mode and Apps), VPN Accelerator, Moderate NAT, IPv6 and anonymous crash reports. Existing values are read from Proton and are not changed by installation. The original Protection IPC key remains compatible as `protection`; its visible tab is Settings.

Split tunneling already had an include-only list on this machine. The widget reads/writes the existing Proton settings file, since the installed CLI 1.0.5 does not expose a split-tunneling command. Kill Switch and split tunneling remain mutually exclusive in the existing integration. Selected applications need restarting after changing routing; the widget explains this. Custom DNS is available through `protonvpn config set custom-dns --help`, not edited by these widget controls.

## Brazil exclusion

The widget setting `blockedCountries` defaults to `BR`, configurable as comma-separated ISO country codes in its bar-widget settings or shell configuration. Country rows and map destinations omit blocked countries. All widget connect actions share the same guarded helper: Fastest, Random, P2P, Tor, Secure Core, direct country/server choices, profiles, recents, reconnects and Always On. Existing saved choices are retained, but blocked selections are refused before invoking Proton.

The helper selects an explicit allowed server using Proton's local logical-server cache, checking account tier, known online state, requested features/locations and both entry/exit country. It uses Proton's score for Fastest and a random allowed candidate for Random, then runs the official CLI with only that server name. Missing/invalid cache or no matching allowed route produces an error; it never falls back to an unrestricted `protonvpn connect`. Cached load/availability can become stale, so Proton may still reject an allowed server; the widget reports this and leaves retry to the user or its existing retry logic.

This is a policy for **connections made through this widget**. It does not intercept manual Proton CLI commands, another application, NetworkManager or external automation. It does not drop an existing tunnel on installation, automatically change its country, or edit Proton's authentication/cache files. Removing BR from the setting intentionally permits it again; restart/refresh the widget to rebuild the visible lists after changing the setting.

## Scrolling diagnosis

Scrolling failed outside the widget too. Touchpad scrolling worked, while a short read-only Linux input check observed no wheel events from the Logitech mouse. The user power-cycled/reconnected the mouse and confirmed its wheel worked again. No global input setting or device permission was changed. The provisional widget wheel interception change was removed; normal wheel/touchpad scrolling remains upstream behavior. The pinned Settings tab improves discoverability independently of that mouse fault.

## Restore, removal and verification

The existing widgets installer copies the modified panel/service/manifest and new `connect.py`, with original-file backups and edit-preserving removal. The helper lives alongside `servers.py` and uses the existing Python and official Proton CLI dependencies. No new application, service or background polling is installed. Plugin removal/backup restoration removes its policy; it does not disconnect the VPN, restore an earlier VPN route or erase Proton account/settings state. The independent vpn restore component still applies only the documented sanitized Proton preset when explicitly selected.

Seven isolated selection/entrypoint tests cover blocked fastest/random/direct/saved-country paths, Secure Core entry/exit, account tiers, feature/location/status filters and missing/no-match cache failures. The blocked helper entrypoint never invokes the CLI; Fastest invokes an allowed named server only. Live cache dry selections for Fastest, Random, P2P, Secure Core and Tor selected no BR route without making connections. The updated Settings panel reports a usable scroll range, accepts scroll positioning and shows the existing include-only three-app split configuration. The user confirmed Settings is visible; wheel recovery was confirmed separately after resetting the mouse. Actual VPN reconnection and changes to protection/split settings were deliberately not exercised during this update, so they remain manual validation.

Official references: [Proton Linux CLI](https://protonvpn.com/support/linux-vpn-setup), installed `protonvpn config --help`, `protonvpn config list`, and setting-specific help. The desktop module uses the installed Omarchy/Quickshell APIs.
