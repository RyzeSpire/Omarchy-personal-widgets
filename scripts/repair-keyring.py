#!/usr/bin/env python3
"""Repair malformed multiline JSON in an existing GNOME text keyring.

Dry-run by default. Never creates a vault, reads a password interactively,
changes encryption settings, or prints credential values. Stop the keyring
daemon and its socket before applying to a live file.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
import tempfile

import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib

BINARY_MAGIC = b"GnomeKeyring\n\r\x00\n"


class RepairError(ValueError):
    pass


def parse_keyfile(text):
    keyfile = GLib.KeyFile()
    keyfile.load_from_data(text, len(text.encode("utf-8")), GLib.KeyFileFlags.NONE)
    return keyfile


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RepairError("Duplicate JSON properties; automatic repair refused.")
        result[key] = value
    return result


def repair_text(text):
    if not text.startswith("[keyring]"):
        raise RepairError("Not a supported GNOME text keyring.")
    try:
        keyfile = parse_keyfile(text)
        return text, 0, sum(g.isdigit() for g in keyfile.get_groups()[0])
    except GLib.Error:
        pass

    lines = text.splitlines(keepends=True)
    output = []
    repairs = 0
    group = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        header = re.fullmatch(r"\[([^\]\r\n]+)\]\s*", line)
        if header:
            group = header.group(1)
        if group.isdigit() and line.startswith("secret=") and line[7:].lstrip().startswith(("{", "[")):
            end = i + 1
            while end < len(lines):
                if re.fullmatch(r"(?:mtime|ctime)=\d+\s*", lines[end]):
                    break
                if re.fullmatch(r"\[[^\]\r\n]+\]\s*", lines[end]):
                    break
                end += 1
            if end > i + 1:
                raw = (line[7:] + "".join(lines[i + 1:end])).strip()
                try:
                    value = json.loads(raw, strict=False, object_pairs_hook=unique_object)
                    canonical = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
                    if json.loads(canonical, object_pairs_hook=unique_object) != value:
                        raise RepairError("JSON round-trip verification failed.")
                    encoder = GLib.KeyFile()
                    encoder.set_string("repair", "secret", canonical)
                    encoded = encoder.to_data()[0].splitlines()
                    if len(encoded) != 2 or not encoded[1].startswith("secret="):
                        raise RepairError("Unexpected keyfile serialization.")
                    ending = "\r\n" if line.endswith("\r\n") else "\n"
                    output.append(encoded[1] + ending)
                    repairs += 1
                    i = end
                    continue
                except (json.JSONDecodeError, UnicodeError, OverflowError):
                    pass
        output.append(line)
        i += 1

    candidate = "".join(output)
    try:
        keyfile = parse_keyfile(candidate)
    except GLib.Error:
        raise RepairError("File remains malformed; no automatic repair is safe.") from None
    headers = re.findall(r"^\[([^\]\r\n]+)\]\s*$", text, re.MULTILINE)
    if not repairs or list(keyfile.get_groups()[0]) != headers:
        raise RepairError("Section preservation could not be verified.")
    return candidate, repairs, sum(g.isdigit() for g in headers)


def checked_file(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise RepairError("Keyring must be a regular file, not a symlink.")
    if info.st_uid != os.getuid():
        raise RepairError("Keyring must belong to the current user.")
    return info, path.read_bytes()


def apply_repair(path, expected, repaired, backup_root):
    info, current = checked_file(path)
    if current != expected:
        raise RepairError("Keyring changed since inspection; nothing was replaced.")
    resolved = backup_root.resolve()
    if any((parent / ".git").exists() for parent in (resolved, *resolved.parents)):
        raise RepairError("Private backups must remain outside Git repositories.")
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if backup_root.stat().st_uid != os.getuid() or backup_root.stat().st_mode & 0o077:
        raise RepairError("Backup directory must be owned by you with mode 0700.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
    backup_dir = Path(tempfile.mkdtemp(prefix=stamp, dir=backup_root))
    backup = backup_dir / path.name
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(current)
        stream.flush()
        os.fsync(stream.fileno())
    if backup.read_bytes() != expected:
        raise RepairError("Backup verification failed; live file was not replaced.")
    fd, temporary = tempfile.mkstemp(prefix=".keyring-repair-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(repaired)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IMODE(info.st_mode) & 0o600)
        latest_info, latest = checked_file(path)
        if latest != expected or latest_info.st_ino != info.st_ino:
            raise RepairError("Keyring changed during backup; live file was not replaced.")
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return backup


def default_keyring():
    data = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    folder = data / "keyrings"
    alias = (folder / "default").read_text().strip()
    if not alias or Path(alias).name != alias or alias in {".", ".."}:
        raise RepairError("Unsafe or absent default-keyring reference.")
    return folder / (alias + ".keyring")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keyring", type=Path, help="Defaults to the current user's default keyring.")
    parser.add_argument("--apply", action="store_true", help="Back up and atomically replace the malformed file.")
    parser.add_argument("--backup-root", type=Path, help="Private 0700 backup directory outside every Git repository.")
    args = parser.parse_args()
    try:
        path = args.keyring or default_keyring()
        _, original = checked_file(path)
        if original.startswith(BINARY_MAGIC):
            print("Encrypted keyring: this text-format repair does not apply.")
            return 0
        candidate, repairs, entries = repair_text(original.decode("utf-8"))
        report = {"mode": "apply" if args.apply else "preview", "repaired_values": repairs, "credential_entries": entries}
        if args.apply and repairs:
            state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
            backup_root = args.backup_root or state / "omarchy-personal-widgets/keyring-recovery"
            backup = apply_repair(path, original, candidate.encode("utf-8"), backup_root)
            report["private_backup"] = str(backup)
        print(json.dumps(report))
        return 0
    except RepairError as error:
        print("Repair refused: " + str(error))
        return 1
    except OSError as error:
        print("File operation failed (errno " + str(error.errno) + "); credential contents are never printed.")
        return 1
    except (UnicodeError, ValueError):
        print("Unsupported encoding or JSON value; credential contents are never printed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
