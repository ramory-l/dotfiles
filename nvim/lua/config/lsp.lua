vim.lsp.enable {
  'lua_ls',
  'gopls',
  'ts_ls',
}

vim.diagnostic.config {
  -- virtual_lines = true,
  virtual_text = true,
  underline = true,
  update_in_insert = false,
  severity_sort = true,
  float = {
    border = 'rounded',
    source = true,
  },
  signs = {
    text = {
      [vim.diagnostic.severity.ERROR] = '󰅚 ',
      [vim.diagnostic.severity.WARN] = '󰀪 ',
      [vim.diagnostic.severity.INFO] = '󰋽 ',
      [vim.diagnostic.severity.HINT] = '󰌶 ',
    },
    numhl = {
      [vim.diagnostic.severity.ERROR] = 'ErrorMsg',
      [vim.diagnostic.severity.WARN] = 'WarningMsg',
    },
  },
}

-- LSP keybindings
vim.api.nvim_create_autocmd('LspAttach', {
  group = vim.api.nvim_create_augroup('lsp-attach', { clear = true }),
  callback = function(event)
    local map = function(keys, func, desc, mode)
      mode = mode or 'n'
      vim.keymap.set(mode, keys, func, { buffer = event.buf, desc = 'LSP: ' .. desc })
    end

    -- Navigation
    map('gd', vim.lsp.buf.definition, '[G]o to [D]efinition')
    map('gD', vim.lsp.buf.declaration, '[G]o to [D]eclaration')
    map('gr', vim.lsp.buf.references, '[G]o to [R]eferences')
    map('gi', vim.lsp.buf.implementation, '[G]o to [I]mplementation')
    map('gt', vim.lsp.buf.type_definition, '[G]o to [T]ype definition')

    -- Documentation
    map('K', vim.lsp.buf.hover, 'Hover documentation')
    map('<C-k>', vim.lsp.buf.signature_help, 'Signature help')

    -- Actions
    map('<leader>rn', vim.lsp.buf.rename, '[R]e[n]ame')
    map('<leader>ca', vim.lsp.buf.code_action, '[C]ode [A]ction', { 'n', 'x' })

    -- Diagnostics
    map('[d', vim.diagnostic.goto_prev, 'Previous [D]iagnostic')
    map(']d', vim.diagnostic.goto_next, 'Next [D]iagnostic')
  end,
})
