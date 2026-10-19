# Codex resume launcher

A terminal icon beside the other app widgets. Clicking opens a new Codex resume picker showing chats from all directories, on workspace 7.

Requires Foot, Hyprland with the installed Lua dispatch API, Python 3, and Codex managed by mise. Resolves the installed CLI directly to avoid the personal workspace-9 wrapper. Existing Codex sessions are left alone. Uses the existing Foot theme; no global Hyprland rules are changed. Multiple simultaneous clicks are locked while a window starts.

Files: `CodexWidget.qml` (button), `launch_codex.py` (launch and placement), `manifest.json` (Omarchy discovery).

Disable/remove using Omarchy plugin management. To remove manually, remove `ryze.codex-launcher` from the bar and then delete this plugin directory. Existing terminals remain open. No authentication or chat data is stored by this plugin.

On every launch, workspace 7 is moved to the secondary monitor if available (prefers HDMI-A-1, otherwise a non-laptop display). With one display, normal workspace placement is retained. All windows already sharing workspace 7 follow that workspace. No permanent monitor or workspace rule is installed.
