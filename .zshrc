# Path to your Oh My Zsh installation.
export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME="robbyrussell"

plugins=(git zsh-autosuggestions zsh-syntax-highlighting)

source $ZSH/oh-my-zsh.sh

# User configuration

export EDITOR=hx
export VISUAL="$EDITOR"
export PATH="$HOME/.local/bin:$PATH"
export PATH="$HOME/go/bin:$PATH"

alias k=kubectl

# Set up fzf key bindings and fuzzy completion
source <(fzf --zsh)

export FZF_DEFAULT_COMMAND="fd --hidden --strip-cwd-prefix --exclude .git"
export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
export FZF_ALT_C_COMMAND="fd --type=d --hidden --strip-cwd-prefix --exclude .git"

# Use fd (https://github.com/sharkdp/fd) for listing path candidates.
_fzf_compgen_path() {
	fd --hidden --exclude .git . "$1"
}

# Use fd to generate the list for directory completion
_fzf_compgen_dir() {
	fd --type=d --hidden --exclude .git . "$1"
}

eval "$(starship init zsh)"

# Machine-local environment (work paths, secrets) — never tracked in dotfiles.
[ -f "$HOME/.zshrc.local" ] && source "$HOME/.zshrc.local"
