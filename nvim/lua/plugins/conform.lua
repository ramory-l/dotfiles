return {
  'stevearc/conform.nvim',
  opts = {
    formatters_by_ft = {
      lua = { 'stylua' },
      go = { 'goimports', 'golines', 'gofmt' },
    },
    format_on_save = {
      lsp_fallback = true,
    },
  },
}
