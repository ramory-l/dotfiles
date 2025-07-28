return {
  {
    'stevearc/oil.nvim',
    dependencies = { 'nvim-tree/nvim-web-devicons' },
    keys = {
      { '-', '<CMD>Oil<CR>', desc = 'Open parent directory' },
      { '<space>-', '<CMD>Oil --float<CR>', desc = 'Open parent directory (float)' },
    },
    cmd = 'Oil',
    opts = {
      default_file_explorer = true,
      columns = {
        'icon',
        'permissions',
        'size',
        'mtime',
      },
      keymaps = {
        ['<C-v>'] = { 'actions.select', opts = { vertical = true } },
        ['<C-p>'] = { 'actions.preview', opts = { split = 'belowright' } },
      },
      view_options = {
        show_hidden = true,
      },
      watch_for_changes = true,
      win_options = {
        signcolumn = 'yes:2',
        cursorcolumn = false,
      },
      float = {
        preview_split = 'right',
      },
    },
  },
}
