[[ -o interactive ]] || return
[[ -r "$HOME/.zprofile" ]] && source "$HOME/.zprofile"

HISTFILE="$HOME/.zsh_history"
HISTSIZE=50000
SAVEHIST=50000
setopt HIST_IGNORE_ALL_DUPS HIST_REDUCE_BLANKS SHARE_HISTORY INTERACTIVE_COMMENTS
unsetopt BEEP
bindkey -e
autoload -Uz compinit
[[ -d "$HOME/.docker/completions" ]] && fpath=("$HOME/.docker/completions" $fpath)
mkdir -p "$HOME/.cache/zsh"
compinit -d "$HOME/.cache/zsh/zcompdump-$ZSH_VERSION"

# Custom Mocha colors for completion and autosuggestions.
zstyle ':completion:*' menu select
zstyle ':completion:*' list-colors 'di=38;2;137;180;250' 'ln=38;2;148;226;213'
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=#6c7086'

export BAT_THEME='Catppuccin Mocha'
export FZF_DEFAULT_OPTS='--color=bg+:#313244,bg:#1e1e2e,spinner:#f5e0dc,hl:#f38ba8,fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc,marker:#b4befe,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8,selected-bg:#45475a'
export EZA_COLORS='di=38;2;137;180;250:ln=38;2;148;226;213:ex=38;2;166;227;161'

if (( $+commands[fzf] )) && _dotfiles_fzf=$(fzf --zsh 2>/dev/null); then
  eval "$_dotfiles_fzf"
fi
unset _dotfiles_fzf
if (( $+commands[zoxide] )); then eval "$(zoxide init zsh --cmd cd)"; fi
(( $+commands[bat] )) && alias cat='bat --paging=never --style=plain'
if (( $+commands[eza] )); then
  alias ls='eza --icons=auto'
  alias ll='eza -l --icons=auto'
  alias la='eza -la --icons=auto'
  alias tree='eza --tree --icons=auto'
fi
(( $+commands[rg] )) && alias grep=rg
(( $+commands[fd] )) && alias find=fd

[[ -r "$HOME/.local/share/dotfiles/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh" ]] && source "$HOME/.local/share/dotfiles/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh"
[[ -r "$HOME/.config/zsh/private.zsh" ]] && source "$HOME/.config/zsh/private.zsh"

# Keep mise after Herd/private PATH changes. Do not initialize nvm.
(( $+commands[mise] )) && eval "$(mise activate zsh)"
(( $+commands[starship] )) && eval "$(starship init zsh)"
# Ctrl-R uses Atuin; keep the up arrow for ordinary shell history navigation.
(( $+commands[atuin] )) && eval "$(atuin init zsh --disable-up-arrow)"
# Syntax highlighting installs widgets, so source it last.
# The official Catppuccin theme loads before the plugin.
[[ -r "$HOME/.config/zsh/catppuccin-mocha.zsh" ]] && source "$HOME/.config/zsh/catppuccin-mocha.zsh"
[[ -r "$HOME/.local/share/dotfiles/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" ]] && source "$HOME/.local/share/dotfiles/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
true
# The following lines have been added by Docker Desktop to enable Docker CLI completions.
fpath=(/Users/anand/.docker/completions $fpath)
autoload -Uz compinit
(( ${+_comps[docker]} )) || compinit
# End of Docker CLI completions
