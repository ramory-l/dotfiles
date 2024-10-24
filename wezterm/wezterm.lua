-- Pull in the wezterm API
local wezterm = require("wezterm")

-- This will hold the configuration.
local config = wezterm.config_builder()

-- This is where you actually apply your config choices

-- config.font = wezterm.font("MesloLGS Nerd Font Mono")
config.font_size = 19

config.enable_tab_bar = false

config.window_decorations = "RESIZE"

-- config.window_background_opacity = 0.8
config.macos_window_background_blur = 10

function scheme_for_appearance(appearance)
	-- if appearance:find("Dark") then
	-- 	return "Catppuccin Mocha"
	-- else
	-- 	return "Catppuccin Latte"
	-- end
	return "Catppuccin Macchiato"
end

config.color_scheme = scheme_for_appearance(wezterm.gui.get_appearance())

-- and finally, return the configuration to wezterm
return config
