-- Pull in the wezterm API
local wezterm = require("wezterm")

-- This will hold the configuration.
local config = wezterm.config_builder()

-- This is where you actually apply your config choices

-- config.font = wezterm.font("MesloLGS Nerd Font Mono")
config.font_size = 20

-- config.disable_default_key_bindings = true

config.use_dead_keys = false

config.send_composed_key_when_left_alt_is_pressed = false
config.send_composed_key_when_right_alt_is_pressed = false

config.enable_tab_bar = false

config.window_decorations = "RESIZE"
config.window_background_opacity = 0.8
config.macos_window_background_blur = 10

local function scheme_for_appearance(appearance)
	return "Catppuccin Mocha"
	-- if appearance:find("Dark") then
	-- 	return "Catppuccin Mocha"
	-- else
	-- 	return "Catppuccin Latte"
	-- end
end

config.color_scheme = scheme_for_appearance(wezterm.gui.get_appearance())

config.keys = {
	{
		key = "Enter",
		mods = "ALT",
		action = wezterm.action.DisableDefaultAssignment,
	},
	{
		key = "=",
		mods = "CTRL",
		action = wezterm.action.DisableDefaultAssignment,
	},
	{
		key = "-",
		mods = "CTRL",
		action = wezterm.action.DisableDefaultAssignment,
	},
	-- Shift+Enter -> ESC+CR (= Option/Meta+Enter), which Claude Code treats as a newline.
	{
		key = "Enter",
		mods = "SHIFT",
		action = wezterm.action.SendString("\x1b\r"),
	},
}

-- Layout-independent hotkeys. With a non-Latin input source (e.g. Russian) active,
-- Alt/Ctrl combos still send the US character of the physical key, so zellij, helix,
-- yazi and readline hotkeys work in any layout. These combos leave the input source
-- alone, so editing a line (Alt+b, Ctrl+w, ...) doesn't interrupt typing in it.

-- Physical key -> US character, unshifted and shifted.
local us_keys = {
	Grave = { "`", "~" },
	Minus = { "-", "_" },
	Equal = { "=", "+" },
	LeftBracket = { "[", "{" },
	RightBracket = { "]", "}" },
	Backslash = { "\\", "|" },
	Semicolon = { ";", ":" },
	Quote = { "'", '"' },
	Comma = { ",", "<" },
	Period = { ".", ">" },
	Slash = { "/", "?" },
}
-- The same keys in a fixed order. action_callback names its events by creation order
-- and WezTerm evaluates the config more than once, so the bindings must come out in
-- the same order every time (pairs() doesn't guarantee one) or a combo fires another
-- combo's callback.
local phys_keys = {
	"Grave",
	"Minus",
	"Equal",
	"LeftBracket",
	"RightBracket",
	"Backslash",
	"Semicolon",
	"Quote",
	"Comma",
	"Period",
	"Slash",
}
-- Ctrl combos that terminals encode as control characters. Ctrl+- and Ctrl+= are
-- left out on purpose: they stay disabled above.
local ctrl_keys = { LeftBracket = true, RightBracket = true, Backslash = true, Slash = true }
for letter in ("abcdefghijklmnopqrstuvwxyz"):gmatch(".") do
	us_keys[letter:upper()] = { letter, letter:upper() }
	table.insert(phys_keys, letter:upper())
	ctrl_keys[letter:upper()] = true
end

-- Combos that enter a command mode also switch macOS to the English input source, so
-- the plain letters typed next are Latin: Ctrl+[ leaves helix insert mode, Alt+g is the
-- zellij prefix (zellij/config.kdl). macism is installed by install.sh.
local macism = wezterm.home_dir .. "/.local/bin/macism"
local english_input_source = "com.apple.keylayout.ABC"
local english_triggers = { ["CTRL LeftBracket"] = true, ["ALT G"] = true }

-- WezTerm resolves physical-key bindings before the bindings of an active key table, so
-- the combos the copy/search modes use must hand over to the mode while it's active.
local key_table_actions = {}
for name, entries in pairs(wezterm.gui.default_key_tables()) do
	key_table_actions[name] = {}
	for _, entry in ipairs(entries) do
		local key = entry.key:gsub("^mapped:", "")
		key_table_actions[name][entry.mods .. " " .. key] = entry.action
	end
end

local function used_by_key_table(combo)
	for _, actions in pairs(key_table_actions) do
		if actions[combo] then
			return true
		end
	end
	return false
end

local function us_key_action(phys, mods)
	local key, key_mods = us_keys[phys][1], mods
	if mods == "ALT|SHIFT" then
		key, key_mods = us_keys[phys][2], "ALT"
	end
	local send = wezterm.action.SendKey({ key = key, mods = key_mods })
	local combo = key_mods .. " " .. key
	local switches_to_english = english_triggers[mods .. " " .. phys]
	if not switches_to_english and not used_by_key_table(combo) then
		return send
	end
	return wezterm.action_callback(function(window, pane)
		local mode = key_table_actions[window:active_key_table() or ""] or {}
		window:perform_action(mode[combo] or send, pane)
		if switches_to_english then
			wezterm.background_child_process({ macism, english_input_source })
		end
	end)
end

local function bind_us_key(phys, mods)
	table.insert(config.keys, { key = "phys:" .. phys, mods = mods, action = us_key_action(phys, mods) })
end

for _, phys in ipairs(phys_keys) do
	bind_us_key(phys, "ALT")
	bind_us_key(phys, "ALT|SHIFT")
	if ctrl_keys[phys] then
		bind_us_key(phys, "CTRL")
	end
end

return config
