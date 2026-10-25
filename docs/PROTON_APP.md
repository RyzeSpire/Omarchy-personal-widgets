# Native Proton VPN app

The retained VPN interface is Proton's own Linux GTK application, installed from Arch extra as `proton-vpn-gtk-app` (observed version 4.18.7-1). This is the native package recommended by [Proton's Arch guide](https://protonvpn.com/support/linux-vpn-arch); Arch packaging is community-maintained. No application binary or account data is redistributed in this repository.

## Install and open

The curated dependency list now includes the GUI package, so `./install.sh --apply --packages` installs it along with the chosen restore components. Independently:

```bash
omarchy pkg add proton-vpn-gtk-app
protonvpn-app
```

Search **Proton VPN** in the launcher. Its desktop ID is `proton.vpn.app.gtk.desktop`. A native tray item is provided by the app; closing the window may leave it running in the tray. To show an already-running app through the standard desktop activation interface:

```bash
gdbus call --session --dest proton.vpn.app.gtk --object-path /proton/vpn/app/gtk --method org.freedesktop.Application.Activate '{}'
```

Sign in privately if prompted. Use the app's Settings for split tunneling, Kill Switch, NetShield and other native features. The existing Proton settings and credentials are not reset. The older official CLI may remain installed as an optional native utility; it is not required by this restore profile and the status widget does not invoke it in the background. Updates come from normal Omarchy/Arch updates.

## Retired addon and upgrade behavior

The former third-party Omarchy VPN widget is removed from the active desktop and current restore payload. Its sources, artwork, tests and bar entry are no longer shipped. Applying the widgets component cleans only that retired ID from existing bar/plugin preferences, removes its active code/state into private installer history, and drops its obsolete restoration-ledger entries. Preview remains read-only. Other widgets and official Proton settings/account files are preserved.

The private retirement archive lives under `~/.local/state/omarchy-personal-widgets/history/retire-proton-widget-*`, outside active plugin discovery and outside Git. Uninstalling the restore bundle cannot resurrect the old addon through its ledger or an original shell backup. Existing historical Git commits/release assets remain historical; use the current release for reinstallation.

The addon's Always On reconnection, profiles, recent-server list and Brazil block are removed with it. They are not native app preferences and are not migrated as if the app supported them. The shared Proton settings preset remains available in the optional vpn restore component; applying that preset is separate from retiring the addon. Review native routing/startup settings yourself before a new connection. No connection, disconnection, logout or new-country selection is issued by this migration.

## Remove

Close the native app and run `omarchy pkg drop proton-vpn-gtk-app` if you want to uninstall it later. Review dependency removals; the official CLI or other apps may share Proton libraries. App account/settings data is preserved unless you explicitly remove it separately. The widget-bundle uninstall does not uninstall applications or erase VPN accounts.

## Verification

The native package and launcher metadata were verified, systemd-resolved was active, the app registered its native tray/session interfaces, and a visible Proton VPN window mapped on workspace 5 after desktop activation. The retired addon was absent from shell plugin discovery and active code/state paths. The official Proton settings hash was unchanged by retirement. Isolated tests cover plan-only behavior, repeated upgrade, preserving other widgets/private settings and preventing addon resurrection during bundle uninstall. The user confirmed the official app recognizes the account and its Settings page is ready. A new VPN connection or native settings changes were not performed automatically.

## Personal status widget (v0.1.14)

The native app now has a small original bar companion, `ryze.proton-vpn`. See its [appearance, controls and lifecycle](../plugins/ryze.proton-vpn/README.md). The app stays the VPN controller; this widget reads local NetworkManager state and delegates explicit clicks to its official tray menu. It does not restore the retired addon, its background reconnection or its settings interface. The lock badge reflects the tunnel separately from whether the app process is running. No VPN connection was changed to install or test it.

## Searchable widget adapter (v0.1.17)

The [widget server picker](../plugins/ryze.proton-vpn/README.md) searches the native app's server model by country, city or name and submits explicit selections to that same app's controller. The widgets component now owns a reversible user launcher for **Proton VPN**, which starts the installed official UI with a small session-bus adapter. Use the launcher or widget after reboot. A bare `protonvpn-app` start while closed uses the original entry point; restart via the launcher/widget if server browsing is unavailable.

Normal startup retains native auto-connect preferences. The live migration used an internal resume flag and checked that tunnel identity/state stayed unchanged after the native UI settled. No server selection, connection or disconnection was automatically exercised. The native window, tray, search, account restrictions and read-only selection validation were checked; a real change to another server remains a manual user action. The adapter uses native Python interfaces verified with 4.18.7; see its compatibility/rollback notes before removing it or after incompatible upstream updates.

The server-switch investigation found an older saved Proton tunnel still allowed to auto-connect in NetworkManager. The packaged guard marks saved Proton tunnel profiles manual before startup and widget requests; the current/older profiles were corrected without disconnecting the active tunnel. Kill-switch profiles remain automatic. Private original-value backups and an explicit optional restore command are documented in the widget README. This prevents competing saved-profile activation; it is not a country blacklist or a replacement for native connection recovery.

## Country exclusion (v0.1.18)

The personal adapter now defaults to blocking Brazil through its [country policy](../plugins/ryze.proton-vpn/README.md#blocked-country-policy). Search and native catalog views omit routes entering, exiting or hosted in Brazil. Native fastest/country/startup/pinned selection and the SDK connection/reconnection boundary apply the same checks; blocked or unknown routes fail without fallback. Original package files, credentials and server caches are unchanged. Use the provided launcher/widget for enforcement; independent clients and raw manual profiles are outside this adapter's scope.
