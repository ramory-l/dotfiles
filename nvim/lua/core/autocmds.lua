vim.api.nvim_create_autocmd('TextYankPost', {
  desc = 'Highlight when yanking (copying) text',
  group = vim.api.nvim_create_augroup('kickstart-highlight-yank', { clear = true }),
  callback = function()
    vim.hl.on_yank()
  end,
})

vim.api.nvim_create_autocmd('FileType', {
  desc = 'Enable treesitter highlighting',
  group = vim.api.nvim_create_augroup('treesitter-highlight', { clear = true }),
  pattern = { 'go', 'gomod', 'gosum', 'typescript', 'typescriptreact' },
  callback = function()
    vim.treesitter.start()
  end,
})
