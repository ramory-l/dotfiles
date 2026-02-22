-- Pull in the wezterm API
local wezterm = require("wezterm")

-- This will hold the configuration.
local config = wezterm.config_builder()

-- This is where you actually apply your config choices

-- config.font = wezterm.font("MesloLGS Nerd Font Mono")
config.font_size = 18

config.enable_tab_bar = true

config.window_decorations = "RESIZE"

config.window_background_opacity = 0.8
config.macos_window_background_blur = 10

function scheme_for_appearance(appearance)
	if appearance:find("Dark") then
		return "Catppuccin Mocha"
	else
		return "Catppuccin Latte"
	end
end

config.color_scheme = scheme_for_appearance(wezterm.gui.get_appearance())

-- Vim-like keybindings
config.keys = {
  -- Existing keybindings
  {key="Enter", mods="SHIFT", action=wezterm.action.SendString("\x1b\r")},

  -- Pane splitting (like tmux)
  {key="\\", mods="ALT", action=wezterm.action.SplitHorizontal({domain="CurrentPaneDomain"})},
  {key="-", mods="ALT", action=wezterm.action.SplitVertical({domain="CurrentPaneDomain"})},

  -- Pane navigation (vim-like with Alt)
  {key="h", mods="ALT", action=wezterm.action.ActivatePaneDirection("Left")},
  {key="j", mods="ALT", action=wezterm.action.ActivatePaneDirection("Down")},
  {key="k", mods="ALT", action=wezterm.action.ActivatePaneDirection("Up")},
  {key="l", mods="ALT", action=wezterm.action.ActivatePaneDirection("Right")},

  -- Pane resizing (vim-like with Alt+Shift)
  {key="h", mods="ALT|SHIFT", action=wezterm.action.AdjustPaneSize({"Left", 5})},
  {key="j", mods="ALT|SHIFT", action=wezterm.action.AdjustPaneSize({"Down", 5})},
  {key="k", mods="ALT|SHIFT", action=wezterm.action.AdjustPaneSize({"Up", 5})},
  {key="l", mods="ALT|SHIFT", action=wezterm.action.AdjustPaneSize({"Right", 5})},

  -- Pane management
  {key="z", mods="ALT", action=wezterm.action.TogglePaneZoomState},
  {key="x", mods="ALT", action=wezterm.action.CloseCurrentPane({confirm=true})},

  -- Copy mode (vim-like)
  {key="[", mods="ALT", action=wezterm.action.ActivateCopyMode},
}

-- Copy mode keybindings (vim-like)
config.key_tables = {
  copy_mode = {
    {key="h", mods="NONE", action=wezterm.action.CopyMode("MoveLeft")},
    {key="j", mods="NONE", action=wezterm.action.CopyMode("MoveDown")},
    {key="k", mods="NONE", action=wezterm.action.CopyMode("MoveUp")},
    {key="l", mods="NONE", action=wezterm.action.CopyMode("MoveRight")},

    {key="v", mods="NONE", action=wezterm.action.CopyMode({SetSelectionMode="Cell"})},
    {key="V", mods="SHIFT", action=wezterm.action.CopyMode({SetSelectionMode="Line"})},

    {key="y", mods="NONE", action=wezterm.action.Multiple({
      {CopyTo="ClipboardAndPrimarySelection"},
      {CopyMode="Close"},
    })},

    {key="Escape", mods="NONE", action=wezterm.action.CopyMode("Close")},
    {key="q", mods="NONE", action=wezterm.action.CopyMode("Close")},
  },

  search_mode = {
    {key="n", mods="NONE", action=wezterm.action.CopyMode("NextMatch")},
    {key="N", mods="SHIFT", action=wezterm.action.CopyMode("PriorMatch")},
    {key="Escape", mods="NONE", action=wezterm.action.CopyMode("Close")},
    {key="Enter", mods="NONE", action=wezterm.action.CopyMode("Close")},
  },
}

-- and finally, return the configuration to wezterm
return config
