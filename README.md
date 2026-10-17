# dotfiles

Personal configs. `./install.sh` links the tracked ones into place, installs the
tools they configure (Homebrew preferred), and is safe to re-run at any time.

## Layout

| Repo path | Lives at | What |
|---|---|---|
| `claude/CLAUDE.md` | `~/.config/claude/CLAUDE.md` | Global Claude Code instructions |
| `claude/settings.json` | `~/.config/claude/settings.json` | Claude Code settings, incl. enabled plugins and marketplaces |
| `git/ignore` | `~/.config/git/ignore` | Global gitignore (git's default excludesFile location) |
| `zellij/` | `~/.config/zellij` | Zellij multiplexer config |
| `helix/` | `~/.config/helix` | Helix editor config |
| `yazi/` | `~/.config/yazi` | Yazi file manager config |
| `starship.toml` | `~/.config/starship.toml` | Starship prompt |
| `.zshrc` | `~/.zshrc` | Zsh config (universal; machine-local bits go to `~/.zshrc.local`) |
| `wezterm/` | `~/.config/wezterm` | WezTerm terminal config |

Everything in the "Lives at" column is a symlink into this repo, so editing a live
config edits the repo working tree — review with `git diff`, then commit.

## New machine

```sh
git clone git@github.com:ramory-l/dotfiles.git ~/dotfiles
~/dotfiles/install.sh
exec zsh   # pick up CLAUDE_CONFIG_DIR and the linked .zshrc
claude     # first start pulls the plugins enabled in settings.json; run /plugin if any are missing
```

`install.sh` needs Homebrew for the tool installs — if brew is missing it says so
and skips that section; the symlinking still happens. It installs the tools the
configs are for (zellij, helix, starship, yazi, fzf, fd, repomix) and the Helix
language tooling from `helix/languages.toml` (stylua, marksman, mpls from the
`mhersson/formulas` tap, lua-language-server, typescript-language-server, gopls).
oh-my-zsh and its two custom plugins are cloned automatically; `pplx` uses its
official installer (no brew formula).

## Zsh: universal .zshrc, machine-local .zshrc.local

- `.zshrc` is tracked and identical on every machine: no secrets, no work paths,
  no per-machine env.
- Everything machine-specific lives in `~/.zshrc.local`, which `.zshrc` sources at
  the end and which stays untracked: work kubeconfigs, tokens (read at runtime from
  the macOS Keychain via `security find-generic-password`), anything private.
  `install.sh` creates an empty one if missing.

## Claude Code

- The config dir is `~/.config/claude` (XDG-style): the `CLAUDE_CONFIG_DIR` env var
  points env-var-aware tools there, and `~/.claude` remains as a symlink for
  anything that still expects the default path.
- Only `CLAUDE.md` and `settings.json` are tracked here. The rest of
  `~/.config/claude` (state, history, sessions, credentials, plugin caches) is
  untracked machine state.
- If a tool replaces one of the symlinks with a plain file, re-running `install.sh`
  backs the file up as `*.bak` and restores the link.
- Exception: on the work laptop `settings.json` cannot stay a symlink — the
  `avito ai claude` wrapper rewrites it as a plain file on every launch, adding its own
  keys. The `claude()` function in `~/.zshrc.local` syncs it with the repo before and
  after each run, three-way against `settings.dotfiles-base.json`: repo changes reach
  Claude, `/model` and `/plugin` changes land here as a git diff, and wrapper-owned keys
  are stripped. Re-running `install.sh` there is harmless; the next launch replaces the
  link again.
- `install.sh` registers the Holst desktop MCP server (`http://127.0.0.1:47641/mcp`,
  served by the Holst app while it runs) at user scope, since MCP servers live in the
  untracked `.claude.json`. Use `127.0.0.1`, not `localhost`: Holst doesn't answer on IPv6.
