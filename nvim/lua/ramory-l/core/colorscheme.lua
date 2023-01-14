local status, _ = pcall(vim.cmd, "colorscheme nord")
if not status then
	print("Colorscheme not found!")
	return
end

vim.g.nord_contrast = true
vim.g.nord_borders = false
vim.g.nord_disable_background = false
vim.g.nord_italic = false
vim.g.nord_uniform_diff_background = true
vim.g.nord_bold = false

-- Apply colorscheme options
require("nord").set()

vim.api.nvim_set_hl(0, "Normal", { bg = "none" })
vim.api.nvim_set_hl(0, "NormalFloat", { bg = "none" })
