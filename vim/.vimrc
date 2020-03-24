call plug#begin('~/.vim/plugged')
Plug 'scrooloose/nerdtree', { 'on':  'NERDTreeToggle' }
Plug 'jiangmiao/auto-pairs'
Plug 'tpope/vim-fugitive'
Plug 'airblade/vim-gitgutter'
Plug 'kien/ctrlp.vim'
Plug 'easymotion/vim-easymotion'
Plug 'bling/vim-airline'
Plug 'flazz/vim-colorschemes'
call plug#end()

syntax on
set number
set expandtab
set tabstop=4

set hlsearch
set incsearch
set noeb vb t_vb=
colorscheme OceanicNext
"mappings

map <C-n> :NERDTreeToggle<CR>
