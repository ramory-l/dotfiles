#!/usr/bin/env bash
# Bootstrap this dotfiles repo onto a machine. Idempotent: safe to re-run.
set -euo pipefail

DOTFILES="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DIR="$HOME/.config"
CLAUDE_DIR="$CONFIG_DIR/claude"

log() { printf '%s\n' "$*"; }

# --- 1. Claude config lives in ~/.config/claude; ~/.claude stays as a compat symlink ---
if [ -d "$HOME/.claude" ] && [ ! -L "$HOME/.claude" ]; then
  if pgrep -qx claude 2>/dev/null; then
    log "!! claude is running — quit it and re-run install.sh to migrate ~/.claude"
  elif [ -e "$CLAUDE_DIR" ]; then
    log "!! both ~/.claude and $CLAUDE_DIR exist — merge them manually first"
  else
    mv "$HOME/.claude" "$CLAUDE_DIR"
    ln -s "$CLAUDE_DIR" "$HOME/.claude"
    log "migrated ~/.claude -> $CLAUDE_DIR"
  fi
fi
mkdir -p "$CLAUDE_DIR" "$CONFIG_DIR/git"
if [ ! -e "$HOME/.claude" ]; then
  ln -s "$CLAUDE_DIR" "$HOME/.claude"
  log "linked ~/.claude -> $CLAUDE_DIR"
fi

# The .claude.json state file follows CLAUDE_CONFIG_DIR too; keep a $HOME symlink for
# processes launched without the env var. A real file in $HOME means such a process
# wrote state there — it is the newer copy, so it wins.
if [ -f "$HOME/.claude.json" ] && [ ! -L "$HOME/.claude.json" ]; then
  mv -f "$HOME/.claude.json" "$CLAUDE_DIR/.claude.json"
  log "moved ~/.claude.json -> $CLAUDE_DIR/.claude.json"
fi
if [ -f "$CLAUDE_DIR/.claude.json" ] && [ ! -e "$HOME/.claude.json" ]; then
  ln -s "$CLAUDE_DIR/.claude.json" "$HOME/.claude.json"
  log "linked ~/.claude.json -> $CLAUDE_DIR/.claude.json"
fi

# --- 2. CLAUDE_CONFIG_DIR for tools that honor the env var ---
ZSHENV="$HOME/.zshenv"
if ! grep -qsF 'CLAUDE_CONFIG_DIR' "$ZSHENV"; then
  printf '\nexport CLAUDE_CONFIG_DIR="$HOME/.config/claude"\n' >> "$ZSHENV"
  log "added CLAUDE_CONFIG_DIR export to ~/.zshenv"
fi

# --- 3. Symlink tracked configs; the repo is the source of truth ---
# On conflict the existing file/dir is kept as *.bak and the repo version wins.
link() {
  local src="$DOTFILES/$1" dst="$2"
  [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ] && return 0
  if [ -e "$dst" ] && [ ! -L "$dst" ]; then
    if [ -d "$dst" ]; then
      if diff -rq "$dst" "$src" >/dev/null 2>&1; then rm -rf "$dst"; else
        mv "$dst" "$dst.bak"
        log "kept old $dst as $dst.bak (repo version wins)"
      fi
    elif ! cmp -s "$dst" "$src"; then
      cp "$dst" "$dst.bak"
      log "kept old $dst as $dst.bak (repo version wins)"
    fi
  fi
  ln -sfn "$src" "$dst"
  log "linked $dst -> $src"
}
link claude/CLAUDE.md     "$CLAUDE_DIR/CLAUDE.md"
link claude/settings.json "$CLAUDE_DIR/settings.json"
link git/ignore           "$CONFIG_DIR/git/ignore"
link zellij               "$CONFIG_DIR/zellij"
link helix                "$CONFIG_DIR/helix"
link yazi                 "$CONFIG_DIR/yazi"
link starship.toml        "$CONFIG_DIR/starship.toml"
link .zshrc               "$HOME/.zshrc"

# ~/.zshrc.local holds machine-local env (work paths, secrets) and is never tracked.
if [ ! -f "$HOME/.zshrc.local" ]; then
  printf '# Machine-local environment — not tracked in dotfiles.\n' > "$HOME/.zshrc.local"
  log "created empty ~/.zshrc.local"
fi

# --- 4. Tools (Homebrew preferred) ---
# ensure <formula> [binary]: install via brew unless the binary or formula is already present
ensure() {
  local formula="$1" bin="${2:-$1}"
  command -v "$bin" >/dev/null 2>&1 && return 0
  brew ls --versions "$formula" >/dev/null 2>&1 && return 0
  brew install "$formula"
}
if command -v brew >/dev/null 2>&1; then
  ensure zellij
  ensure helix hx
  ensure starship
  ensure yazi
  ensure fzf
  ensure fd
  ensure repomix
  # Helix language tooling (see helix/languages.toml and default LSP lookup)
  ensure stylua
  ensure marksman
  ensure mhersson/formulas/mpls mpls
  ensure lua-language-server
  ensure typescript-language-server
  ensure gopls
else
  log "!! Homebrew not found — install it from https://brew.sh and re-run install.sh"
  log "   (skipping tool installs; symlinks above are already in place)"
fi

# oh-my-zsh + the custom plugins .zshrc expects
if [ ! -d "$HOME/.oh-my-zsh" ]; then
  git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git "$HOME/.oh-my-zsh"
  log "installed oh-my-zsh"
fi
ZSH_CUSTOM="$HOME/.oh-my-zsh/custom"
[ -d "$ZSH_CUSTOM/plugins/zsh-autosuggestions" ] || \
  git clone --depth=1 https://github.com/zsh-users/zsh-autosuggestions "$ZSH_CUSTOM/plugins/zsh-autosuggestions"
[ -d "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting" ] || \
  git clone --depth=1 https://github.com/zsh-users/zsh-syntax-highlighting "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting"

# pplx has no brew formula — official installer
if ! command -v pplx >/dev/null 2>&1; then
  curl -fsSL https://github.com/perplexityai/perplexity-cli/releases/latest/download/install.sh | sh
fi

log "done. Restart your shell (exec zsh), then start claude once so it picks up"
log "the plugins enabled in settings.json (run /plugin if any are missing)."
