# Persistent packaging and publication policy

The user requires every retained new item or modification to the personal Omarchy setup to remain reinstallable from **https://github.com/RyzeSpire/Omarchy-personal-widgets**, across Codex chats. This includes additions, updates, settings changes and removals. The user has authorized publication of the reviewed, sanitized setup changes as a standing part of the work.

## Persistence and scope

`~/.codex/AGENTS.md` carries the global policy on this machine. `AGENTS.md` at the repository root reinforces it for project work. The restore payload `config/home/.codex/AGENTS.md` reinstalls it with the desktop component. The installer merges the marked policy block into existing global instructions, preserving other content; if a nonempty `AGENTS.override.md` is active, it merges into that effective file instead. A custom CODEX_HOME must receive the same block in its own global instruction file. Both global instruction filenames are eligible for optional encrypted migration.

Codex discovers guidance at session startup. Restart an already-open session to reliably load a newly added/updated policy. Guidance files express a durable working requirement; they are not a daemon, package-manager hook or guarantee that every running AI client has loaded them. Manual changes outside Codex require a later audit/export. Other coding agents do not automatically inherit Codex's global file. Explicit research-only/do-not-change/do-not-publish instructions take precedence for that task.

## Completion workflow

1. **Inspect.** Identify the live files, external integration, dependency source/version, private state and current repository status. Keep unrelated work intact. Use Omarchy's skill and installed interfaces for desktop configuration.
2. **Package the retained result.** Preserve functional source and appearance. Add reusable configuration/templates and installation/update/removal handling. Keep usernames and home paths dynamic; expose machine preferences rather than silently assuming this laptop. Add dependency metadata and update relevant software inventories after installs/upgrades/removals. Keep proprietary application installers and media out of the source tree; describe reproducible installation instead.
3. **Separate private state.** Use per-user authentication and sanitized presets. Credentials, personal account/profile/history data, old backups and caches never go into Git. Private migration remains optional, encrypted and outside the repository. Inspect copied configuration rather than assuming an innocent filename is safe.
4. **Verify proportionately.** Validate changed source/manifests, test affected helpers, and exercise installer changes against temporary homes including update/removal. Avoid playback changes, service restarts or destructive tests unless needed and authorized. State which desktop/account outcomes remain unverified.
5. **Refresh artifacts and documentation.** Update setup/cleanup/manual steps, provenance or relevant inventory, and build the source tarball/checksums when the payload changes. Test that any new required top-level files are included by the archive allowlist. This policy itself must travel with the package.
6. **Publish.** Review the staged diff for scope and secrets, commit and push to the repository, then verify the remote result. No repeated publication permission question is needed within this authorization. Use a new release version when distributing changed release artifacts; do not silently change an existing tagged release. Preserve existing history and others' work; never force-push to resolve a routine conflict.
7. **Report.** Briefly explain the result, validation, repository/release link and any required manual steps. If publication is blocked, say so clearly and preserve the prepared local changes. A local commit is not a successful remote publication.

## Sources

- [Codex global and project AGENTS.md discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- Local restore and verification rules: [RESTORE.md](RESTORE.md), [TESTING.md](TESTING.md).
