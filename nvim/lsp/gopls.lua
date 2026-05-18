return {
  cmd = { 'gopls' },
  filetypes = { 'go' },
  root_markers = { 'go.mod', 'go.work', '.git' },
  settings = {
    gopls = {
      buildFlags = { '-tags=wireinject migrate' },
    },
  },
}
