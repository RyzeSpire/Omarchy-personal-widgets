-- Native Steam client windows share one tiled workspace. Games (steam_app_*)
-- and untitled transient Steam menu surfaces are outside this policy.
local workspace_name = "@STEAM_WORKSPACE@"
local class_pattern = "^[Ss]team$"

o.window({ class = class_pattern, title = ".+" }, {
  workspace = workspace_name,
  float = false,
  tile = true,
  suppress_event = "fullscreen maximize",
})

local scheduled = false

local function is_steam(window)
  return window ~= nil and string.lower(window.class or "") == "steam"
end

-- Steam's dropdown was verified as an untitled X11 POPUP_MENU. The Lua
-- window API exposes its empty title, but not its X11 window-type atom.
-- A real window that initially has no title is handled once its title arrives.
local function is_steam_menu(window)
  return is_steam(window) and (window.title or "") == ""
end

local function on_workspace(window)
  return window.workspace ~= nil and tostring(window.workspace.name) == workspace_name
end

local function set_mode(window, mode)
  if window.fullscreen ~= mode or window.fullscreen_client ~= 0 then
    -- Client stays in normal UI mode; internal 1 fills the work area with the bar visible.
    hl.dispatch(hl.dsp.window.fullscreen_state({ window = window,
      internal = mode, client = 0, action = "set" }))
  end
end

local function reconcile()
  local main = nil
  for _, window in ipairs(hl.get_windows({ mapped = true })) do
    if is_steam(window) and not is_steam_menu(window) and not window.hidden then
      if not on_workspace(window) then
        hl.dispatch(hl.dsp.window.move({ window = window,
          workspace = workspace_name, follow = false }))
      end
      if window.floating then
        hl.dispatch(hl.dsp.window.float({ window = window, action = "unset" }))
      end
      if window.title == "Steam" and main == nil then
        main = window
      else
        set_mode(window, 0)
      end
    end
  end
  if main == nil then return end

  local peers = 0
  for _, window in ipairs(hl.get_windows({ mapped = true })) do
    if not window.hidden and not is_steam_menu(window) and on_workspace(window) then peers = peers + 1 end
  end
  -- A second managed window needs the ordinary tiling layout to remain visible.
  -- Counting unrelated windows too prevents Steam from covering a user's work.
  set_mode(main, peers == 1 and 1 or 0)
end

local function schedule()
  if scheduled then return end
  scheduled = true
  hl.timer(function()
    scheduled = false
    reconcile()
  end, { timeout = 40, type = "oneshot" })
end

-- Defer until close/map processing has settled, with no background polling.
for _, event in ipairs({ "window.open", "window.close", "window.destroy", "window.move_to_workspace" }) do
  hl.on(event, schedule)
end
for _, event in ipairs({ "window.title", "window.class" }) do
  hl.on(event, function(window) if is_steam(window) then schedule() end end)
end
hl.on("config.reloaded", schedule)
schedule()
