# Keyboard layout widget

Left-click cycles the layouts already configured on the current physical keyboard. Right-click or middle-click the widget to choose a layout from its themed popup. **Super + middle mouse button**, anywhere on the desktop, opens the same chooser on the focused monitor. The current layout is marked; click a row or use Up/Down and Enter. Escape or clicking outside dismisses it without changing the layout.

The menu reads Hyprland keyboard configuration and XKB descriptions (`xkbcli list --load-exotic`); it does not add languages or change input configuration. Configured variants are retained. Matching physical keyboards switch together, even when they list layouts in different orders. Devices without the selected layout/variant are left alone; virtual input-method keyboards and power/lid buttons are excluded. A failed switch shows an error; successful devices are not rolled back automatically.

Requires Omarchy's shell/Quickshell, Hyprland and `xkbcli` (libxkbcommon); no new application dependency. Tested on Omarchy 4.0.6, Hyprland 0.56.2, Quickshell 0.3.2.r7 and Qt 6.12.0. UI follows the active Omarchy theme.

The bundle's `desktop` component installs the Super + mouse:274 binding in `hypr/personal-widgets.lua`; `widgets` supplies the QML and JavaScript. Standalone installs must add `o.bind("SUPER + mouse:274", "Choose keyboard layout", "omarchy-shell ryze.keyboard-layout choose")` to their own Hyprland bindings after checking for conflicts. A live binding created before bundle installation is migrated out of its marked block to prevent duplication. Installer backups and edit-preserving removal cover these files.

Disable the widget through the bar editor. To disable just the shortcut, remove that binding from the managed module; uninstalling the bundle restores the previous configuration when it has not been subsequently edited. Removing the plugin alone also requires removing its shortcut. No account data or persistent layout state is stored by this widget.

Read-only diagnostics: `omarchy-shell ryze.keyboard-layout status`. `choose` opens the menu; `close` dismisses it. `select <zero-based menu index>` applies the corresponding configured layout.

After updating, use `omarchy restart shell` if the old component remains cached and the new IPC target is absent; the source system required this after hot reload. Before applying the desktop component on another machine, check Super + mouse:274 in its existing keybindings and choose a different shortcut if it is already used. The installer does not resolve unrelated shortcut conflicts automatically.
