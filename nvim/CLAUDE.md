# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Neovim configuration using lazy.nvim as the plugin manager. The config is written in Lua and follows a modular structure with separate directories for core settings, plugins, and LSP configurations.

## Architecture

### Entry Point
- `init.lua` - Requires core modules in order:
  1. `config.lazy` - Bootstraps lazy.nvim, sets leader keys (`<space>` / `\`), disables netrw
  2. `config.lsp` - Configures LSP via `vim.lsp.enable()` and sets up diagnostics/keybindings
  3. `core.options` - `vim.opt` settings (line numbers, relative numbers, clipboard, cursorline)
  4. `core.keymaps` - Core keybindings
  5. `core.autocmds` - Autocommands (currently: yank highlight)

### Directory Structure
```
.
├── init.lua
├── lsp/                       # LSP server configs (not plugin configs)
│   ├── lua_ls.lua            # Declares 'vim' global to suppress false diagnostics
│   └── gopls.lua
├── lua/
│   ├── core/                 # options, keymaps, autocmds
│   ├── config/               # lazy.lua bootstrap, lsp.lua setup
│   └── plugins/              # Auto-imported by lazy.nvim
└── .stylua.toml
```

## LSP Setup

Uses Neovim's built-in `vim.lsp.enable()` API (requires Neovim 0.11+). Server configs live in `lsp/` (not `lua/plugins/`). Each config returns a table with `cmd`, `filetypes`, `root_markers`, and optionally `settings`. Servers are enabled in `lua/config/lsp.lua`.

Active servers: `lua_ls`, `gopls`

## Adding New LSP Servers

1. Create `lsp/<server_name>.lua` returning:
```lua
return {
  cmd = { 'server-command' },
  filetypes = { 'filetype' },
  root_markers = { '.git', 'project-file' },
  settings = {},
}
```
2. Add the server name to the list in `lua/config/lsp.lua`.

## Adding New Plugins

Create a file in `lua/plugins/` returning a lazy.nvim plugin spec. It will be auto-imported on next restart. Use `opts = {}` key for configuration when possible.

## Installed Plugins

| Plugin | Purpose |
|--------|---------|
| catppuccin/nvim | Colorscheme (Frappe flavor, transparent background) |
| nvim-lualine/lualine.nvim | Statusline (catppuccin theme) |
| stevearc/oil.nvim | File explorer (replaces netrw) |
| stevearc/conform.nvim | Formatter (format-on-save) |
| saghen/blink.cmp | Completion engine |
| lewis6991/gitsigns.nvim | Git decorations and hunk actions |
| folke/snacks.nvim | Picker, LazyGit, Git Browse, smooth scroll, bigfile handling |
| folke/which-key.nvim | Keybinding hints |
| tpope/vim-sleuth | Auto-detect indentation |

## Formatting

conform.nvim handles format-on-save with LSP fallback:
- **Lua**: `stylua` (config in `.stylua.toml`: 2-space indent, single quotes, no-call-parens, 160 col width)
- **Go**: `goimports` → `golines` → `gofmt` (in order)

## Completion (blink.cmp)

- Keymap preset: `default` (C-y to accept, C-n/C-p to select, C-e to hide)
- Sources: LSP, path, snippets, buffer
- Cmdline completion enabled with auto-show menu
- Documentation auto-shows on hover
- Uses pre-built Rust binaries (pinned to release tag `*`)

## Key Bindings Reference

**Core (always active):**
- `<C-h/j/k/l>` - Navigate windows
- `<Esc>` - Clear search highlight
- `-` / `<space>-` - Open Oil (inline / floating)

**LSP (in LSP-attached buffers):**
- `gd/gD/gr/gi/gt` - Definition / Declaration / References / Implementation / Type def
- `K` - Hover docs, `<C-k>` - Signature help (overrides window-nav in LSP buffers)
- `<leader>rn` - Rename, `<leader>ca` - Code action
- `[d` / `]d` - Previous / next diagnostic

**Git (gitsigns):**
- `]c` / `[c` - Next / prev hunk
- `<leader>hs/hr` - Stage / reset hunk (also works in visual mode)
- `<leader>hS/hR` - Stage / reset buffer
- `<leader>hp/hi` - Preview hunk / inline preview
- `<leader>hb` - Blame line (full)
- `<leader>hd/hD` - Diff this / diff against HEAD~
- `<leader>hq/hQ` - Quickfix current / all hunks
- `<leader>tb` - Toggle line blame, `<leader>tw` - Toggle word diff
- `ih` (text object) - Select hunk

**Snacks (picker, lazygit, gitbrowse):**
- `<leader><space>` - Smart find files
- `<leader>sf` - Find files
- `<leader>sg` - Grep
- `<leader>sb` - Buffers
- `<leader>sh` - Help pages
- `<leader>sd` - Diagnostics
- `<leader>sr` - Recent files
- `<leader>lg` - Open LazyGit TUI
- `<leader>gB` - Git browse (open in browser, normal + visual)

**Oil (inside Oil buffer):**
- `<C-v>` - Open in vertical split
- `<C-p>` - Preview (belowright split)
- Hidden files shown by default

**which-key groups:** `<leader>s` (Search), `<leader>t` (Toggle), `<leader>h` (Git Hunk)
