# Installation and migration

This is a multi-plugin personal setup bundle. Use `install.sh`; do not pass the repository root to `omarchy plugin add`, which expects one plugin manifest at its root. Source targets x86-64 Omarchy Quattro 4.0.4 / Hyprland Lua 0.56 / Quickshell 0.3.1. Test newer versions before applying. Standard `~/.config`, `~/.local/share` and `~/.local/state` directories are assumed; custom XDG roots are explicitly rejected rather than silently installing into the wrong location.

## Fresh Omarchy installation

```bash
git clone https://github.com/RyzeSpire/Omarchy-personal-widgets.git
cd Omarchy-personal-widgets
./install.sh check
./install.sh                         # inspect the plan
./install.sh --apply --packages --theme --reload
```

Run as your normal desktop user, not root. The optional `--packages` action uses Omarchy package management and may ask for your password. It installs only the curated dependencies in `profile.json`; a full historical package inventory is supplied for review, not blindly replayed. In particular, don't reinstall another machine's kernel/GPU/bootloader packages. No packages are installed merely by cloning or previewing. Verify the package name `ffmpeg4.4` remains available: the captured Spotify release uses its libraries for local MP3s.

Close OBS, Vencord/Discord and Proton before applying their configuration. No app is stopped or started automatically. Applying the Hyprland module can move matching windows as window rules take effect. The saved bar layout takes effect automatically. `--reload` restarts the desktop shell; Spotify/Steam/Discord themselves remain running. `--theme` applies the packaged ethereal theme and recorded background; user custom themes are not downloaded.

For a different external connector use `--monitor DP-2`. `auto` detects connected external screens at installation time, preferring HDMI-A-1. When no session/output is available it keeps the recorded HDMI preference, which falls back to available outputs; rerun with the correct connector after connecting the new display. Workspace preferences remain 7=Codex widget, 8=Discord, 9=legacy Codex wrapper, 10/key 0=full Spotify. Change `profile.json` and corresponding rules/helpers for a different workspace scheme; these are your preferences, not universally reserved IDs.

Choose a subset using `--components widgets,desktop` or `--components widgets` (the latter installs bar widgets but intentionally omits window/binding/keyboard integration). Default is `widgets,desktop,obs,vpn,vencord`. `--home /tmp/test-home --apply` performs an isolated file-only installation; it never installs packages, changes the live session or loads kernel modules. Do not treat that as a real desktop validation.

## Account and client setup

- **Spotify:** install/sign in to native Spotify. In the widget connect your own Spotify developer application's Client ID, registered loopback redirect `http://127.0.0.1:8765/callback`. Approve the PKCE scopes. No shared Client ID/token is bundled. Spotify's API features depend on Premium, development-mode account rules and endpoint availability. Existing playlist shortcuts/caches can migrate privately, otherwise the library is fetched again. For local music, copy your own files and enable the folder in Spotify's Local Files settings; the native client must index it. The widget never decodes music files.
- **Steam:** install/sign in to Steam. Its libraries/collections are read from that installation. Enter your own Steam Web API key privately under the widget's Friends tab. Library folders/game files, account caches and widget pins are not public assets. Some friend/achievement data remains inaccessible due to privacy settings.
- **Proton:** sign in with the official CLI/widget. The preset enables include-only split tunneling for native Discord and Chromium, leaves Firefox outside that list, uses WireGuard and has kill switch off. Review this before connecting. The installer only writes settings; it does not activate a VPN, move a connection or log in. If Proton resets preferences during first sign-in, reapply `./install.sh --components vpn --apply` while its apps are closed/disconnected.
- **Codex and GitHub:** the launcher resolves the mise-managed executable directly. Install tools explicitly after Omarchy's agent setup, e.g. `mise use -g codex@latest gh@latest node@26.8.2`, then authenticate each separately. `~/.config/omarchy/defaults/agent` is set to Codex. The older interactive `~/.local/bin/codex` wrapper is retained for workspace 9; commands that bypass it retain their own placement. The new button uses workspace 7 independently.
- **Discord/Vencord:** native Discord is a package dependency. The Vencord preset contains sanitized plugin preferences, not Discord itself or its patcher. Apply the official [Vencord installer](https://docs.vencord.dev/installing/) to your current Discord version separately, then start Discord. No proprietary Discord payload or Vencord build binaries are republished. Cloud tokens, pinned conversations and account-specific plugin lists require private migration/reconfiguration.

## Both screens camera

```bash
python3 scripts/camera-system.py                 # preview
sudo python3 scripts/camera-system.py --apply --load
```

This separate, explicit root step installs only `/etc/modprobe.d/ryze-obs-camera.conf` and `/etc/modules-load.d/ryze-obs-camera.conf`, with a reversible system journal. It requires `v4l2loopback-dkms` and headers matching the running kernel. The recorded machine uses linux-omarchy-headers; choose the headers for the new machine rather than copying that assumption. If video42 is already in use, adjust `config/system/etc/modprobe.d/ryze-obs-camera.conf` before applying. It does not unload a camera currently in use. A reboot may be needed if an existing loaded module has different parameters.

Open **Discord Both Screens**, select the two monitors again when the portal prompts, then select **OBS Both Screens** under Discord's camera settings. Layout is laptop left/external right, 3840x1080 canvas, 2560x720 at 30fps output. Output is a camera feed, not desktop-audio screen sharing. Renew audio-device choices in the new session; the Bluetooth A2DP rule is portable, saved microphone/route choices are not. There is no bundled persistent hardware-specific microphone fix.

## Private data, optional

Do not put private backups in this repository, even if it becomes private. Encryption is not a reason to publish account backups. Close the affected apps before a consistent profile export.

```bash
python3 scripts/private-data.py export                    # sizes only
python3 scripts/private-data.py export --apply            # private widget state/preferences
# To also migrate all ~/.config preferences/profiles, Firefox/Steam profiles, local music and keyrings:
python3 scripts/private-data.py export --profiles --media --keyrings --apply \
  --output "$HOME/omarchy-full-private.tar.gz.gpg"
```

GPG asks for a passphrase in your terminal. Plaintext is streamed into encryption and is not written to a temporary archive. The encrypted destination is mode 0600 outside the repository; existing files are never overwritten. Keyrings may still require the old login password. OAuth sessions may expire or be bound to another device; signing in again is normal. File contents are private even if their directory names look harmless.

On the new machine:

```bash
python3 scripts/private-data.py restore --archive "$HOME/omarchy-full-private.tar.gz.gpg"
python3 scripts/private-data.py restore --archive "$HOME/omarchy-full-private.tar.gz.gpg" --apply
```

Decryption goes into an empty `~/omarchy-migration-review` directory. Inspect it and selectively copy data back with apps closed. It never extracts directly over your live home. Browser profiles, keyrings, audio names and Spotify's local index may need manual adjustment. With --profiles, all ~/.config files are included (including additional retained application preferences such as CurseForge/Vortex), excluding cache/log/backup directories. The encrypted helper is not a whole-disk backup: game binaries, general documents, SSH/GPG keys, Wi-Fi/system NetworkManager secrets, bootloader files and disk partitions need your normal backup process. It includes only the documented allowlist; account backups and all local music are optional flags. Original working-machine backups remain untouched.

## Updates and removal

```bash
git pull --ff-only
./install.sh                         # review the next version
./install.sh --apply --reload
./install.sh uninstall               # preview restoration
./install.sh uninstall --apply --reload
sudo python3 scripts/camera-system.py uninstall --apply   # only if you installed the camera step
```

Before-files and original metadata live in `~/.local/state/omarchy-personal-widgets`; camera originals live in `/var/lib/omarchy-personal-widgets/camera`. Originals survive package updates. Uninstall restores original files only if the installed file has not been edited since; edited files are kept and reported. Retain the local backups until satisfied. Empty plugin directories may remain; unrelated files in those directories are never deleted. Authentication data, music, downloaded games, packages, running apps and backup history are not deleted. Uninstall never unloads an active camera or disconnects a VPN. OBS permission grants are renewed rather than imported.

## Persistent Codex workflow

The desktop component restores the marked global packaging policy into `~/.codex/AGENTS.md`, preserving unrelated instructions. If a nonempty `AGENTS.override.md` is active, the block is merged into that file instead. Restart Codex afterward. For a custom `CODEX_HOME`, install the block in that profile manually. This makes packaging/publishing the expected completion workflow for future Codex-assisted Omarchy changes; it does not monitor manual changes. See [PACKAGING_POLICY.md](PACKAGING_POLICY.md).


## Recorded application removals

See `inventory/software-changes.json` for changes after the original package snapshot. Those records explain removals; the restore installer does not automatically uninstall applications from another machine.

Free Download Manager (`freedownloadmanager` and `freedownloadmanager-debug`, version `6.35.1.7021-1`) was removed on 2026-10-19 at the user's request. The package manager also removed `libtorrent 0.16.22-1`, which was installed solely for FDM. None of these packages is in the curated restore dependencies or original inventories.

To remove the package-managed copy on another Omarchy installation, close FDM and run `omarchy pkg drop freedownloadmanager freedownloadmanager-debug`. Review the dependency transaction before applying removal on a different machine; unrelated applications may now use those dependencies.

FDM-created per-user integrations may outlive package removal. If their executable still points to `/opt/freedownloadmanager/`, remove `.config/autostart/FDM.desktop`, the three `.local/share/applications/freedownloadmanager_{torrent,magnet_up,fdm_up}.desktop` launchers, and `.mozilla/native-messaging-hosts/org.freedownloadmanager.fdm5.cnh.json`, all relative to the user's home. In `.config/mimeapps.list`, remove only the FDM desktop IDs from association values, preserving other handlers. Run `update-desktop-database "$HOME/.local/share/applications"` afterward. Do not apply this cleanup after reinstalling FDM at that same path.

Downloads, partial transfers, FDM settings/history and Firefox profiles/extensions are preserved. No replacement application is installed automatically. If reinstalling later, review the vendor's current Linux instructions and Firefox native-messaging integration; the reason for removing this copy does not establish that an AUR build cannot support the extension. Do not restore another user's browser profile or download history from this public bundle.


## Persepolis Download Manager

The retained native download manager is `persepolis` from Arch's official `extra` repository (recorded version `5.2.0-3`). It is included in `profile.json`, so `./install.sh --apply --packages` installs it. For installation independently of the widget bundle, run `omarchy pkg add persepolis`. Normal Omarchy/Arch package updates maintain the application. The incremental inventory records this application and the six packages installed for it; it does not capture unrelated software changes made outside this task.

Launch **Persepolis Download Manager** from the application menu, or run `persepolis`, once as the normal desktop user. First launch generates the user's settings, wrapper and browser native-messaging manifests; these files contain per-user paths and must be generated independently rather than copied from the source machine.

For Firefox, install the [official Persepolis Download Manager Integration extension](https://addons.mozilla.org/en-US/firefox/addon/persepolis-dlm-integration/) interactively. Enable **Interrupt downloads** and **Context menu** in its popup, following the [upstream integration guide](https://github.com/persepolisdm/persepolis/wiki/How-to-use-persepolis-browser-extension-en). If the browser cannot find the host, restart Persepolis and, after preserving current transfers, Firefox. Check that `~/.mozilla/native-messaging-hosts/com.persepolis.pdmchromewrapper.json` points to an executable locally generated wrapper. Installing the desktop package alone does not establish end-to-end browser capture.

A signed-in OneDrive page may need to pass cookies or a current download URL through the browser extension. Authentication, server resume support and delivery speed are server-dependent; application installation does not prove those transfers work. Existing Firefox partial files are not imported automatically. Preserve existing downloads, and compare the final archive against its independently supplied SHA256 checksum before importing it.

To uninstall, close Persepolis and run `omarchy pkg drop persepolis`; inspect dependencies before applying removal on another machine. User preferences and download history are preserved by default. To disable Firefox capture, turn off **Interrupt downloads** or disable the extension. After uninstalling, remove only `com.persepolis.pdmchromewrapper.json` native-messaging registrations whose path belongs to that removed installation; first-run initialization can create these for Firefox and other supported browsers. Preserve unrelated browser connectors and personal downloads. Removal of settings/history remains a separate explicit user choice.

The public bundle contains package names, versions and these setup instructions, not application binaries, browser profiles, cookies, download URLs, manifests containing personal paths or download history. Desktop startup, version reporting and the Firefox native-host manifest were verified on the source system; extension installation, actual browser capture, and clean-machine graphical behavior still require interactive verification.


## Keyring recovery

For the specific malformed multiline-JSON credential defect, see [GNOME Keyring text-format recovery](KEYRING_RECOVERY.md). The optional preview-by-default helper preserves an exact private backup outside Git and retains the existing credential entries and protection mode. It is never run by the installer. Private vaults and recovery backups remain excluded from the public package.

## Keyboard chooser shortcut

The keyboard widget now supports a configured-layout menu. Install both `widgets` and `desktop` components for Super + middle-click to open it beside the pointer on its monitor. Standalone setup and removal are documented in [the keyboard widget README](../plugins/ryze.keyboard-layout/README.md). The `desktop` component places its shortcut in the managed Hyprland integration, migrates the marked pre-bundle live binding to avoid duplicates, and uses the existing backup/edit-preserving uninstall behavior. An incomplete marked block is refused for manual review.

## Steam client workspace

The desktop component also restores [Steam's workspace/fill and split-window policy](STEAM_WORKSPACE.md). Its workspace is configurable through `profile.json` (`workspaces.steam`, default 6). Managed native Steam secondary windows tile alongside the client; the automatic notification still needs confirmation when it next appears. No game placement or notification preferences are changed.
