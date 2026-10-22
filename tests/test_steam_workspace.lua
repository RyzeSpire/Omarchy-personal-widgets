-- Synthetic compositor fixtures only; no Hyprland session or Steam is used.
local source_file = assert(io.open("config/hypr/steam-workspace.lua", "r"))
local source = source_file:read("*a"):gsub("@STEAM_WORKSPACE@", "6")
source_file:close()

local function fixture(windows)
  local callbacks, timers, actions, rules = {}, {}, {}, {}
  local function dispatcher(kind)
    return function(args) return { kind = kind, args = args } end
  end
  _G.o = { window = function(class, rule) rules[#rules + 1] = { class = class, rule = rule } end }
  _G.hl = {
    get_windows = function() return windows end,
    on = function(event, callback) callbacks[event] = callback end,
    timer = function(callback) timers[#timers + 1] = callback end,
    dsp = { window = {
      move = dispatcher("move"), float = dispatcher("float"), fullscreen_state = dispatcher("fullscreen") } },
    dispatch = function(action)
      actions[#actions + 1] = action
      local args, window = action.args, action.args.window
      if action.kind == "move" then
        assert(args.follow == false)
        window.workspace = { name = args.workspace }
      elseif action.kind == "float" then window.floating = false
      else window.fullscreen = args.internal; window.fullscreen_client = args.client end
    end,
  }
  assert(load(source, "@steam-workspace.lua"))()
  local function flush()
    local batch = timers; timers = {}
    for _, callback in ipairs(batch) do callback() end
  end
  return { flush = flush, events = callbacks, actions = actions, rules = rules }
end

local function window(class, title, workspace)
  return { class = class, title = title, workspace = { name = workspace or "3" },
    floating = true, mapped = true, hidden = false, fullscreen = 0, fullscreen_client = 0 }
end

local checks = 0
local function test(name, callback)
  callback(); checks = checks + 1; print("ok - " .. name)
end

test("native client moves and tiles fullscreen, while games remain untouched", function()
  local main, game = window("steam", "Steam"), window("steam_app_123", "Game")
  local f = fixture({ main, game }); f.flush()
  assert(main.workspace.name == "6" and not main.floating and main.fullscreen == 2)
  assert(game.workspace.name == "3" and game.floating and game.fullscreen == 0)
  assert(f.rules[1].class == "^[Ss]team$" and f.rules[1].rule.tile == true)
  assert(f.rules[1].rule.suppress_event == "fullscreen maximize")
end)

test("arbitrary managed Steam notification window joins split, then fullscreen returns", function()
  local main, notice = window("steam", "Steam", "6"), window("steam", "Automatic announcement")
  local windows = { main }; local f = fixture(windows); f.flush()
  windows[2] = notice; f.events["window.open"](notice); f.flush()
  assert(not notice.floating and notice.workspace.name == "6")
  assert(main.fullscreen == 0 and notice.fullscreen == 0)
  windows[2] = nil; f.events["window.close"](notice); f.flush()
  assert(main.fullscreen == 2)
end)

test("unrelated workspace peer prevents fullscreen without being moved or retiled", function()
  local main, editor = window("Steam", "Steam", "6"), window("foot", "Work", "6")
  local f = fixture({ main, editor }); f.flush()
  assert(main.fullscreen == 0 and editor.floating and editor.workspace.name == "6")
end)

test("multiple popups, late main title and class changes reconcile safely", function()
  local main, first, second = window("steam", ""), window("steam", "Friends"), window("steam", "News")
  local f = fixture({ main, first, second }); f.flush()
  main.title = "Steam"; f.events["window.title"](main); f.flush()
  assert(main.fullscreen == 0 and first.workspace.name == "6" and second.workspace.name == "6")
  for _, action in ipairs(f.actions) do assert(action.args.window.class:lower() == "steam") end
end)

test("hidden windows do not split the main client; events are coalesced", function()
  local main, hidden = window("steam", "Steam"), window("steam", "Hidden helper")
  hidden.hidden = true
  local f = fixture({ main, hidden })
  for i = 1, 20 do f.events["window.open"](main) end
  f.flush(); assert(main.fullscreen == 2 and hidden.workspace.name == "3")
  local before = #f.actions
  f.events["config.reloaded"](); f.flush(); assert(#f.actions == before)
end)

test("a secondary window temporarily titled Steam cannot leave the main fullscreen", function()
  local main, duplicate = window("steam", "Steam", "6"), window("steam", "Steam", "6")
  main.fullscreen = 2
  local f = fixture({ main, duplicate }); f.flush()
  assert(main.fullscreen == 0 and duplicate.fullscreen == 0)
end)

print(tostring(checks) .. " Steam workspace policy checks passed")
