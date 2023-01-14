local impatient_status, _ = pcall(require, "impatient")
if not impatient_status then
	print("Impatient not installed with packer yet, please restart NeoVim.")
end

require("ramory-l.plugins-setup")
require("ramory-l.core.options")
require("ramory-l.core.keymaps")
require("ramory-l.core.colorscheme")
require("ramory-l.plugins.nvim-tree")
require("ramory-l.plugins.lualine")
require("ramory-l.plugins.telescope")
require("ramory-l.plugins.lsp-zero")
require("ramory-l.plugins.mason-null-ls")
require("ramory-l.plugins.autopairs")
require("ramory-l.plugins.treesitter")
require("ramory-l.plugins.gitsigns")
