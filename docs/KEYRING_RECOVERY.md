# GNOME Keyring text-format recovery

This optional utility repairs one specific format defect: an existing unencrypted GNOME text keyring containing a multiline JSON credential with raw line breaks. Those line breaks can make the whole file unreadable, causing clients such as the Proton VPN CLI to request a new collection repeatedly. A failed GitHub CLI lookup can also result from an unreadable vault; authentication must be checked separately after repair.

The helper is `scripts/repair-keyring.py`. It uses Python and the distribution's `python-gobject`/GLib bindings, with the existing `gnome-keyring` and `libsecret` installation. No additional packages were required on the source system. [GNOME's reader supports encrypted and text formats](https://github.com/GNOME/gnome-keyring/blob/master/pkcs11/secret-store/gkm-secret-collection.c); [the text-format implementation](https://github.com/GNOME/gnome-keyring/blob/master/pkcs11/secret-store/gkm-secret-textual.c) uses GLib key-file escaping for saved values.

## Scope and privacy

- Preview is the default; valid text files are left unchanged.
- JSON is parsed locally, checked for duplicate properties and round-trip equivalence, then serialized with GLib escaping. Section order and credential-item count are verified.
- Only the malformed value's representation is replaced. Account/password resets and encryption changes are outside this utility's scope. A text-format vault retains its existing unencrypted protection mode.
- An existing encrypted file is recognized as outside this repair's scope; its health is not validated or decrypted.
- Applying creates an exact mode-0600 backup in a mode-0700 directory before atomic replacement. The source must be a regular file owned by the current user; concurrent source changes and Git-contained backup locations are refused.
- Credential values, JSON properties, certificates and tokens are never printed or included in this repository. Tests use fabricated values only. The helper has no startup hook and is never invoked by the restoration installer.

## Preview and backup location

Run as the normal desktop user:

```bash
python3 -B scripts/repair-keyring.py
```

The default keyring is discovered through the user's XDG data directory and its `keyrings/default` reference. `--keyring PATH` selects another owned text keyring explicitly.

The default backup root is under the user's XDG state directory at `omarchy-personal-widgets/keyring-recovery`. If any ancestor is a Git repository, choose a private location outside Git. This matters when the user's home directory is itself a repository. For a persistent alternative:

```bash
keyring_backup_dir="/var/lib/omarchy-keyring-recovery-$(id -u)"
sudo install -d -m 700 -o "$(id -u)" -g "$(id -g)" "$keyring_backup_dir"
```

Do not put this directory in the public source archive. It is private recovery data, and requires the same care as the original vault. The helper never creates a new vault or weakens an encrypted one.

## Apply and reload

Close the VPN widget's panel and finish credential operations first. This briefly stops the user keyring service; credential clients may need to retry. It does not explicitly disconnect a VPN or restart the desktop shell.

With the selected `keyring_backup_dir` variable still set:

```bash
(
    trap 'systemctl --user start gnome-keyring-daemon.socket gnome-keyring-daemon.service' EXIT
    systemctl --user stop gnome-keyring-daemon.socket gnome-keyring-daemon.service
    python3 -B scripts/repair-keyring.py --apply --backup-root "$keyring_backup_dir"
)
```

If using the ordinary state-directory backup outside Git, omit `--backup-root`. Keep the returned backup path private. A refused repair leaves the original file in place; if a filesystem operation fails after replacement, inspect the live file and preserved backup before taking further action.

## Verify and recover

Run preview again: it should report zero repaired values with the original credential-item count. Inspect fresh daemon messages for format errors, then check ordinary client operations such as `protonvpn status` and `gh auth status`. Logs and account output stay local. A repaired format does not guarantee that an independently expired token will become valid.

On the source system, the default collection loaded and unlocked, Proton status and GitHub authentication succeeded, and no password prompt remained after repair. Future encrypted vaults may still require their legitimate password; this utility is not an unlock bypass or PAM configuration change.

To undo the file replacement, stop the keyring service and socket, preserve the current file separately, copy the exact private backup to the matching original keyring path with owner-only permissions, and restart the service/socket. Restoring the original also restores its original syntax defect. Investigate or recover individual credentials from that private backup only through an explicitly authorized local process.

## Disabling or removing this support

The helper and this document are optional source files. Deleting them does not change the repaired keyring. Original backup removal is a separate informed user choice. Leave unrelated keyrings, browser profiles, account stores and the system's GNOME Keyring packages alone.
