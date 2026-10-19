# Omarchy personal widgets and setup

Ryze's retained Omarchy Quattro desktop setup, packaged for reviewable reinstallation. Includes Spotify, Steam, Discord, Codex and keyboard widgets, plus the surrounding workspace, keyboard, browser, idle, audio, VPN and OBS camera configuration needed to recreate their behavior.

```bash
git clone https://github.com/RyzeSpire/Omarchy-personal-widgets.git
cd Omarchy-personal-widgets
./install.sh                          # preview only
./install.sh --apply --packages --theme --reload
```

Read **[installation, accounts, migration and removal](docs/RESTORE.md)** first. Requires an existing compatible Omarchy installation; this is not an OS/disk image. Package installation and camera-driver setup are explicit operations. No credentials, personal playlists, music, browser sessions or chat history are included. Each user authenticates independently. Original working files were not changed to prepare this repository.

| Path | Purpose |
|---|---|
| `plugins/` | Five personal QML/Python widgets, preserved from the working installation |
| `vendor/` | Pinned OmaProton VPN source with its original MIT license |
| `config/` | Audited, sanitized presets, home templates and optional system camera files |
| `profile.json` | Captured platform baseline, preferences and curated dependencies |
| `inventory/` | Package versions, explicit/foreign package lists and upstream provenance |
| `docs/ANALYSIS.md` | Inspection findings, scope, portability and known limitations |
| `scripts/manage.py` | Dry-run installer, file backups, updates and account-preserving removal |
| `scripts/private-data.py` | Optional encrypted private migration outside Git |
| `scripts/camera-system.py` | Separate system-driver setup/removal for the OBS camera |
| `scripts/make-release.py` | Public source tarball and SHA-256 checksum builder |
| `tests/` | Isolated packaging tests; Steam helper tests are next to its plugin |

The public source includes the full working widget feature set, including Spotify local-playlist selection through Spotify itself. Known limits remain: Spotify's API can omit local-file queues; Smart Shuffle is deferred; Steam privacy/API restrictions still apply; the older general Codex wrapper has a previously reported intermittent routing issue. See the analysis and plugin READMEs.

Create an export artifact with `python3 scripts/make-release.py`. Recreate accounts through the UI, or use the separately encrypted migration helper for your own data. A whole-machine migration also needs your normal personal-file/disk backup; this repository must never contain browser profiles, tokens, keyrings, old configuration backups or media archives.

[Validation guide](docs/TESTING.md) · [Third-party notices](THIRD_PARTY_NOTICES.md)

Persistent Codex instructions require future retained Omarchy changes to be packaged and published here. See [the packaging policy](docs/PACKAGING_POLICY.md). The desktop installer restores this global policy while preserving existing unrelated guidance. Restart existing Codex sessions to load new global instructions.
