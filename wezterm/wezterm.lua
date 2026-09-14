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

return config
