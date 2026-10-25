#!/usr/bin/env python3
"""Prevent NetworkManager from reviving another saved Proton tunnel.

Only connection.autoconnect is changed; no secret, route or kill-switch edits.
Original values stay private for an explicit optional rollback.
"""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid


def command(args):
    return subprocess.run(["nmcli", "--wait", "5", *args], check=True, capture_output=True,
                          text=True, timeout=8, env=dict(os.environ, LC_ALL="C")).stdout


def profiles(run=command):
    output = run(["-t", "-f", "UUID,TYPE,AUTOCONNECT,NAME", "connection", "show"])
    result = {}
    for line in output.splitlines():
        fields = line.split(":", 3)
        if len(fields) != 4:
            continue
        identifier, kind, automatic, name = fields
        if kind not in ("vpn", "wireguard") or not name.startswith("ProtonVPN "):
            continue
        uuid.UUID(identifier)
        if automatic not in ("yes", "no"):
            raise ValueError("Could not read Proton profile auto-connect state.")
        result[identifier] = dict(autoconnect=automatic == "yes", name=name)
    return result


def state_path():
    return Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "ryze-proton-widget" / "autoconnect-originals.json"


@contextmanager
def state_lock(path):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Refusing an unsafe auto-connect backup path.")
    descriptor = os.open(str(path) + ".lock", os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def save(path, entries):
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, prefix=".autoconnect-", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(entries, stream); stream.write("\n")
            stream.flush(); os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def guard(path=None, run=command):
    path = path or state_path()
    with state_lock(path):
        originals = json.loads(path.read_text()) if path.exists() else {}
        current = profiles(run)
        changes = [identifier for identifier, props in current.items() if props["autoconnect"]]
        for identifier in changes:
            # Save before mutation; repeated runs never overwrite the original flag.
            if identifier not in originals:
                originals[identifier] = True
                save(path, originals)
            run(["connection", "modify", "uuid", identifier, "connection.autoconnect", "no"])
        return len(changes)


def restore(path=None, run=command):
    path = path or state_path()
    with state_lock(path):
        originals = json.loads(path.read_text()) if path.exists() else {}
        current = profiles(run)
        restored = 0
        for identifier, automatic in list(originals.items()):
            if identifier in current and current[identifier]["autoconnect"] is False:
                run(["connection", "modify", "uuid", identifier, "connection.autoconnect", "yes" if automatic else "no"])
                restored += 1
            originals.pop(identifier)
            save(path, originals)
        return restored


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        current = profiles()
        print(json.dumps(dict(preview=True, proton_profiles=len(current), automatic=sum(p["autoconnect"] for p in current.values()), restore=args.restore)))
        return 0
    changed = restore() if args.restore else guard()
    print(json.dumps(dict(ok=True, changed=changed, restored=args.restore)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
