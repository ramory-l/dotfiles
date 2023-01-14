# Dotfiles

## What Im Using

Terminal - **Alacritty** + **Tmux**  
Shell - **zsh** with [oh-my-zsh](https://ohmyz.sh/)  
Prompt - [starship](https://starship.rs/)  
Text editor - NeoVim v0.8.1  
Super Fast Window Manager - **yabai** + **skhd** for hotkeys  
Nerd Font

### How to install

#### For MacOS

Alacritty - `brew install --cask --no-quarantine alacritty`  
Shell - `sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"`  
Prompt - `brew install starship`  
Text editor - `brew install neovim`  
Yabai - `brew install koekeishiya/formulae/yabai`  
skhd - `brew install koekeishiya/formulae/skhd`  
Nerd Font - https://github.com/epk/SF-Mono-Nerd-Font

**Where are also some things for NeoVim that you should install for working it properly:**  
ripgrep (for fast grep) - `brew install ripgrep`

May be something else, that I don't remember. (try :checkhealth to see more) =)

### Configuring Tmux

1. Download Tmux Plugin Manager `git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm`
2. Create tmux-session with command `tmux new -s <session-name>`.
3. Within session use `ctrl+a` then `shift-i` (Capital I) to install plugins.

**If something not working properly, please open it's documentation.**
