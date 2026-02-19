return {
  'nvim-treesitter/nvim-treesitter',
  lazy = false,
  build = ':TSUpdate',
  config = function()
    require('nvim-treesitter').install { 'go', 'gomod', 'gosum', 'typescript', 'tsx' }
  end,
}
