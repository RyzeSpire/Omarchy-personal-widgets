# Official Proton VPN app only

The retained VPN interface is the unmodified native `proton-vpn-gtk-app` package (observed 4.18.7-1), installed from Arch extra as recommended by [Proton's guide](https://protonvpn.com/support/linux-vpn-arch). Search **Proton VPN** in the launcher, or run `protonvpn-app`. Its system desktop entry is `proton.vpn.app.gtk.desktop`.

Both custom Proton addons are retired: `io.github.grichard99.omaproton-vpn` and `ryze.proton-vpn`. The current package contains no custom Proton widget, server browser, app wrapper, country filter or custom desktop launcher. Proton settings, sign-in, server selection, tray and connection recovery belong to the official app. The custom Brazil exclusion is removed with the adapter.

## Reinstall and upgrade

The curated dependencies retain `proton-vpn-gtk-app`; install independently with `omarchy pkg add proton-vpn-gtk-app`. No binaries, accounts, profiles or keyrings are redistributed. Sign in privately if needed.

Applying the widgets component removes both retired IDs from bar/plugin preferences, retires old active code/state outside plugin discovery and drops obsolete ledger entries. An owned wrapper launcher is removed or replaced by its recorded original. Unrelated widgets and custom launchers are preserved. Original shell backups are sanitized on bundle removal so they cannot resurrect either addon. If upgrading an older bundle while its custom app process is running, close it and reopen the official app once; the live cleanup already performed that restart.

When the old private auto-connect backup exists in the live home, migration restores only recorded Proton tunnel flags. Kill-switch, WiFi, routes, secrets and unrelated VPN profiles are untouched. The migration helper remains only to reverse old installations; it adds no runtime policy or background process. The optional sanitized native VPN preset is separate from addon removal and is not applied by this cleanup.

Account credentials, native app configuration and shared settings are preserved. Inactive installer history and historical Git commits/releases remain history; use this current package to restore the native-only setup. Removing the restore bundle does not uninstall Proton or erase its account. To remove the app itself later, use `omarchy pkg drop proton-vpn-gtk-app` and review shared dependencies.
