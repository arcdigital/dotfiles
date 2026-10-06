# Shared by zsh startup and dotfiles atuin-ai; compatible with bash and zsh.
export ATUIN_CONFIG_DIR="$HOME/.config/atuin"
export ATUIN_THEME_DIR="$ATUIN_CONFIG_DIR/themes"
# Service enablement belongs to config.toml, including after a shell reload.
unset ATUIN_AUTO_SYNC ATUIN_AI__ENABLED

if [[ ${OSTYPE:-} == darwin* ]]; then
    # Reset service settings when a shell reloads or changes machine configuration.
    unset ATUIN_SYNC_ADDRESS ATUIN_SYNC_PROTOCOL ATUIN_AI__ENDPOINT ATUIN_AI__ENDPOINT_PROTOCOL
    if [[ -r "$HOME/.config/atuin-machine/env.sh" ]]; then
        source "$HOME/.config/atuin-machine/env.sh"
    fi
fi
