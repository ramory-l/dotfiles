local lsp_status, lsp = pcall(require, "lsp-zero")
if not lsp_status then
	return
end

local cmp_status, cmp = pcall(require, "cmp")
if not cmp_status then
	return
end

local lspkind_status, lspkind = pcall(require, "lspkind")
if not lspkind_status then
	return
end

local lspsaga_status, lspsaga = pcall(require, "lspsaga")
if not lspsaga_status then
	return
end

lsp.set_preferences({
	suggest_lsp_servers = true,
	setup_servers_on_start = true,
	set_lsp_keymaps = false,
	configure_diagnostics = true,
	cmp_capabilities = true,
	manage_nvim_cmp = true,
	call_servers = "local",
	sign_icons = {
		error = "✘",
		warn = "▲",
		hint = "⚑",
		info = "",
	},
})

-- init better lsp gui
lspsaga.setup({})

-- make sure these servers are installed
lsp.ensure_installed({
	"sumneko_lua",
	"html",
	"cssls",
	"tsserver",
})

-- the function below will be executed whenever
-- a language server is attached to a buffer
lsp.on_attach(function(client, bufnr)
	local keymap = vim.keymap
	local opts = { noremap = true, silent = true, buffer = bufnr }

	-- set keybinds
	keymap.set("n", "gf", "<cmd>Lspsaga lsp_finder<CR>", opts) -- show definition, references
	keymap.set("n", "gD", "<Cmd>lua vim.lsp.buf.declaration()<CR>", opts) -- got to declaration
	keymap.set("n", "gd", "<cmd>Lspsaga peek_definition<CR>", opts) -- see definition and make edits in window
	keymap.set("n", "gi", "<cmd>lua vim.lsp.buf.implementation()<CR>", opts) -- go to implementation
	keymap.set("n", "<leader>ca", "<cmd>Lspsaga code_action<CR>", opts) -- see available code actions
	keymap.set("n", "<leader>rn", "<cmd>Lspsaga rename<CR>", opts) -- smart rename
	keymap.set("n", "<leader>D", "<cmd>Lspsaga show_line_diagnostics<CR>", opts) -- show  diagnostics for line
	keymap.set("n", "<leader>d", "<cmd>Lspsaga show_cursor_diagnostics<CR>", opts) -- show diagnostics for cursor
	keymap.set("n", "[d", "<cmd>Lspsaga diagnostic_jump_prev<CR>", opts) -- jump to previous diagnostic in buffer
	keymap.set("n", "]d", "<cmd>Lspsaga diagnostic_jump_next<CR>", opts) -- jump to next diagnostic in buffer
	keymap.set("n", "K", "<cmd>Lspsaga hover_doc<CR>", opts) -- show documentation for what is under cursor
	keymap.set("n", "<leader>o", "<cmd>LSoutlineToggle<CR>", opts) -- see outline on right hand side
end)

lsp.setup_nvim_cmp({
	mapping = cmp.mapping.preset.insert({
		["<C-i>"] = cmp.mapping.complete(),
		["<C-b>"] = cmp.mapping.scroll_docs(-4),
		["<C-f>"] = cmp.mapping.scroll_docs(4),
		["<C-e>"] = cmp.mapping.abort(), -- close completion window
		["<CR>"] = cmp.mapping.confirm({ select = false }),
	}),
	completion = {
		completeopt = "menu,menuone,noselect",
	},
	formatting = {
		format = lspkind.cmp_format({
			maxwidth = 50,
			ellipsis_char = "...",
		}),
	},
})

-- configure lua server
lsp.configure("sumneko_lua", {
	settings = {
		Lua = {
			-- make the language server recognize "vim" global
			diagnostics = {
				globals = { "vim" },
			},
			workspace = {
				-- make language server aware of runtime files
				library = {
					[vim.fn.expand("$VIMRUNTIME/lua")] = true,
					[vim.fn.stdpath("config") .. "/lua"] = true,
				},
			},
		},
	},
})

lsp.setup()
