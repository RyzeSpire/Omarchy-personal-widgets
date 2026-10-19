# Codex global working agreements

<!-- BEGIN OMARCHY-PACKAGING-POLICY -->
## Standing rule: package and publish retained Omarchy changes

For every new or changed item retained on this personal Omarchy installation, completing the requested work includes packaging it for reinstallation and publishing the sanitized result to https://github.com/RyzeSpire/Omarchy-personal-widgets. This applies across Codex chats and working directories, including widgets, applications/dependencies, scripts, desktop settings, keybindings, workspace rules, services, integrations, and removals of previously packaged items.

- Inspect the current implementation and repository before editing. Preserve the working setup and unrelated user changes. Use the required Omarchy skill for desktop/system customization.
- Maintain the repository checkout at ~/Work/Omarchy-personal-widgets (discover an existing checkout or clone the exact upstream if absent). Treat it as the maintained restore package; live changes must be reflected there before finishing.
- Include reusable source/configuration, dependency/version metadata, portable paths, installation/update/removal behavior, documentation and appropriate verification. Keep machine preferences configurable and user/account state separate. Add migrations or backup/rollback handling when needed. Record unavoidable manual setup accurately.
- For installed applications whose binaries are not suitable for distribution, record their package/source, relevant configuration and reproducible installation steps instead of committing the binaries. Update relevant inventories after installs, updates and removals; never blindly export the whole home or /etc.
- Verify the affected behavior and packaging using appropriate checks. Preview/test installers in temporary homes when changed. Rebuild the public archive/checksums when its contents change. Review staged files for private data before committing.
- Never publish credentials, tokens, API keys, personal Client IDs, account identifiers, chat history, browser/application profiles, keyrings, caches, logs, old backups, copyrighted media, or unrelated project source. Use sanitized templates, independent sign-in and the separate encrypted private-migration workflow.
- The user gives standing authorization to commit and push reviewed, relevant setup changes to that repository as part of the task; do not repeatedly request publication permission. Preserve repository history, avoid force pushes, and do not commit unrelated work. Publish versioned artifacts when appropriate; do not replace existing release assets silently.
- If authentication, network access or another real blocker prevents publication, retain the prepared local work and report exactly what is pending. Do not claim it was published. Research-only tasks and explicit instructions not to change/publish remain read-only; later user instructions take precedence.
- In the final response, briefly state what was packaged, what was verified, the publication result, and any remaining manual steps. Do not leave a retained machine change unrecorded without explicitly reporting the gap.

The detailed maintained workflow is docs/PACKAGING_POLICY.md in that repository. This is a Codex working rule, not a background watcher for changes made outside Codex. Global guidance is loaded at session startup; restart existing sessions after changing it. Other machines/custom CODEX_HOME profiles require installing the same guidance there.
<!-- END OMARCHY-PACKAGING-POLICY -->
