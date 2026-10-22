# Roblox through Sober

Sober is installed as the normal desktop user's Flatpak `org.vinegarhq.Sober` from official Flathub. The Arch `flatpak` package is included in the curated native dependencies. Sober itself is restored separately; the general widget installer does not install Flatpak applications automatically.

## Install, update and remove

Run these from the repository as your normal user:

```bash
python3 -B scripts/sober.py                  # preview
python3 -B scripts/sober.py install --apply  # install Flatpak if absent, add user Flathub, install Sober
python3 -B scripts/sober.py update --apply
python3 -B scripts/sober.py uninstall --apply
python3 -B scripts/sober.py launcher --apply # repair launcher/icon discovery without reinstalling
```

If Flatpak is missing, installation uses `omarchy pkg add flatpak` and may ask for a password in the terminal. It adds the standard Flathub remote only when absent and preserves an existing remote configuration. If the name flathub already refers to another service, review `flatpak remotes --user --show-details` before applying. No root-owned Sober installation is created. Install pulls the latest stable app and required runtimes; versions/commits captured in `inventory/flatpak-apps.json` record the source installation rather than pinning old clients that may stop working with Roblox.

Launch **Sober** from the application menu or run:

```bash
flatpak run org.vinegarhq.Sober
```

On first launch leave **Automatic** installation selected to download Roblox, then sign in privately. The helper never signs in or copies another account. Roblox web links use the handlers exported by Sober where supported. Install and update also create two user-owned symbolic links: the exported Sober desktop entry under `~/.local/share/applications/` and its scalable icon under `~/.local/share/icons/hicolor/scalable/apps/`. This makes Sober discoverable even when the current session started before Flatpak was installed and lacks its export directory in `XDG_DATA_DIRS`. The links keep following Flatpak-managed updates; no entry or icon binary is copied into the repository. Use `python3 -B scripts/sober.py launcher --apply` to repair discovery for an existing installation, then reopen the launcher and search Sober or Roblox. No logout is needed.

Sober and its runtimes update through Flatpak (`flatpak update --user`), independently of Arch's pacman packages. Uninstalling the widget bundle does not uninstall Sober or Flatpak. The explicit Sober uninstall removes only these helper-owned symbolic links and preserves `~/.var/app/org.vinegarhq.Sober`, other applications, Flathub and shared runtimes. Account data deletion is a separate manual choice; no `--delete-data` operation is performed. Remove the native Flatpak package only after reviewing whether other apps need it.

## Scope and verification

The source machine meets Sober's x86-64/SSE4.2 CPU and Linux-kernel requirements. Actual game performance and account access require a signed-in session. No custom graphics/environment overrides, window rules or network settings are applied. Account data, Roblox APKs, proprietary Sober binaries, runtimes, caches and logs are excluded from this repository; only reproducible setup and public version metadata are packaged.

Official references: [Sober](https://sober.vinegarhq.org/), [installation and first run](https://vinegarhq.org/Sober/Installation.html), [Flathub listing](https://flathub.org/apps/org.vinegarhq.Sober).

The helper validates both installed exports and any destination conflicts before creating links. Existing custom desktop/icon files or links are preserved and reported for review; no original is overwritten, so no backup is needed for this operation. Removal deletes only links still pointing at the expected export paths, including dangling links after Flatpak has removed its exports. Replacing a managed link with a custom entry leaves that entry untouched on helper removal. A direct `flatpak uninstall` bypasses this helper cleanup; remove any remaining helper-owned links manually or use the documented helper for uninstall.
