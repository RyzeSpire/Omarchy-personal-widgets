-- Managed personal integrations; loaded after Omarchy defaults.
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

hl.config({ input = { kb_layout = "us,br", kb_variant = ",abnt2",
  kb_options = "compose:caps,shift:both_capslock_cancel,grp:alts_toggle" } })
-- Ask before closing Spotify so playback survives until a choice is made.
-- SUPER+W previously closed the active window immediately.
hl.unbind("SUPER + W")
hl.unbind("ALT + F4")
hl.unbind("CTRL + Q")
local spotify_close_command = "python " .. o.shell_quote(os.getenv("HOME") .. "/.config/omarchy/plugins/ryze.spotify/spotify_desktop.py") .. " request-close"
function ryze_spotify_close(default_close)
  local window = hl.get_active_window()
  if window ~= nil and string.lower(window.class or "") == "spotify" then
    return hl.dsp.exec_cmd(spotify_close_command)
  elseif default_close then
    return hl.dsp.window.close()
  else
    -- Preserve application handling of Alt+F4 and Ctrl+Q outside Spotify.
    return hl.dsp.pass({ window = window })
  end
end
o.bind("SUPER + W", "Close window (confirm for Spotify)", function() hl.dispatch(ryze_spotify_close(true)) end)
o.bind("ALT + F4", "Close app (confirm for Spotify)", function() hl.dispatch(ryze_spotify_close(false)) end)
o.bind("CTRL + Q", "Quit app (confirm for Spotify)", function() hl.dispatch(ryze_spotify_close(false)) end)
