-- Learn how to configure Hyprland: https://wiki.hypr.land/Configuring/Start/

-- Omarchy's bootstrap keeps path setup out of this user config.
dofile((os.getenv("OMARCHY_PATH") or "/usr/share/omarchy") .. "/default/hypr/bootstrap.lua")

-- Disable all Omarchy default bindings. Add your own in hypr/bindings.lua.
-- omarchy_default_bindings = false
--
-- Or disable only bindings for Omarchy's preinstalled apps/web apps while
-- keeping core window-manager bindings:
-- omarchy_preinstalled_bindings = false

-- Load Omarchy defaults.
require("default.hypr.omarchy")

-- Put your personal overrides in these files. They're loaded after Omarchy's
-- defaults so package updates can improve the defaults without rewriting your
-- ~/.config/hypr files.
require("hypr.monitors")
require("hypr.input")
require("hypr.bindings")
require("hypr.looknfeel")
require("hypr.autostart")

-- Toggle config flags dynamically.
require("default.hypr.toggles")

-- Add any other personal Hyprland configuration below.
-- o.window("qemu", { workspace = "5" })

-- Keep Spotify's audio engine out of numbered workspaces; the widget can reveal it.
o.window("[Ss]potify", { workspace = "special:spotify silent", no_initial_focus = true })

-- Discord and Codex prefer the external screen; disconnected outputs fall back normally.
hl.workspace_rule({ workspace = "8", monitor = "HDMI-A-1" })
hl.workspace_rule({ workspace = "9", monitor = "HDMI-A-1" })
o.window("chrome-discord\\.com__channels_@me-Default", { workspace = "8" })
o.window("[Dd]iscord", { workspace = "8" })

-- Move these workspaces back to the external screen when it is reconnected.
hl.on("monitor.added", function(monitor)
  if monitor ~= nil and monitor.name == "HDMI-A-1" then
    for _, id in ipairs({ "8", "9" }) do
      if hl.get_workspace(id) ~= nil then
        hl.dispatch(hl.dsp.workspace.move({ workspace = id, monitor = monitor }))
      end
    end
  end
end)
