return {
  'folke/snacks.nvim',
  priority = 1000,
  lazy = false,
  ---@type snacks.Config
  opts = {
    bigfile = { enabled = true },
    scroll = { enabled = true },
    picker = { enabled = true },
    lazygit = { enabled = true },
    gitbrowse = { enabled = true },
  },
  keys = {
    { '<leader>lg', function() Snacks.lazygit() end, desc = 'LazyGit' },
    { '<leader>gB', function() Snacks.gitbrowse() end, desc = 'Git Browse', mode = { 'n', 'v' } },
    -- Picker
    { '<leader><space>', function() Snacks.picker.smart() end, desc = 'Smart Find Files' },
    { '<leader>sf', function() Snacks.picker.files() end, desc = 'Find Files' },
    { '<leader>sg', function() Snacks.picker.grep() end, desc = 'Grep' },
    { '<leader>sb', function() Snacks.picker.buffers() end, desc = 'Buffers' },
    { '<leader>sh', function() Snacks.picker.help() end, desc = 'Help Pages' },
    { '<leader>sd', function() Snacks.picker.diagnostics() end, desc = 'Diagnostics' },
    { '<leader>sr', function() Snacks.picker.recent() end, desc = 'Recent Files' },
  },
}
