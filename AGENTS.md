# Repository working agreements

Read `docs/PACKAGING_POLICY.md` before changing this personal Omarchy restoration bundle. The user has a standing requirement that retained Omarchy changes be packaged, verified and published here, regardless of which Codex chat performs the work.

Keep the working desktop intact, preserve unrelated edits, keep private data out of Git, and maintain installation/update/removal and migration documentation alongside the affected source. Follow the persistent global policy supplied at `config/home/.codex/AGENTS.md`. Explicit later user instructions and higher-priority instructions take precedence.

Use `python3 -B scripts/validate.py` for source/manifest parsing. Run the isolated tests appropriate to changed components; installer changes require `python3 -B -m unittest discover -s tests -v`. Steam backend changes require its helper tests. Build release artifacts with `python3 -B scripts/make-release.py`; keep `dist/` untracked. Read `docs/TESTING.md` and `docs/RESTORE.md` for validation limits and supported lifecycle.

Commit/push reviewed changes to the configured upstream without unrelated files or force pushes. Confirm the remote commit/publication result before reporting success. Never treat a pending CI run as a passed check.
