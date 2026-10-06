# The following lines were added by Docker Desktop to add commands to your PATH.
export PATH="$PATH:/Users/anand/.docker/bin"
# End of Docker Desktop section.

# Available to login shells without loading interactive plugins.
typeset -U path PATH
path=("$HOME/.local/bin" $path)
if [[ $OSTYPE == darwin* ]]; then
  export SSH_AUTH_SOCK="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
  [[ -d /opt/homebrew/bin ]] && path=(/opt/homebrew/bin /opt/homebrew/sbin $path)
  [[ -d "$HOME/Library/Application Support/Herd/bin" ]] && path=("$HOME/Library/Application Support/Herd/bin" $path)
fi
export PATH

# Keep k9s configuration in the same location on macOS and Linux.
export K9S_CONFIG_DIR="$HOME/.config/k9s"

# Optional paths from the previous setup; mise activation still takes precedence.
for _dotfiles_path in "$HOME/.docker/bin" "$HOME/.composer/vendor/bin" "$HOME/Library/Application Support/JetBrains/Toolbox/scripts"; do
  [[ -d "$_dotfiles_path" ]] && path+=("$_dotfiles_path")
done
unset _dotfiles_path
# Shared preferences plus the linked machine's service settings.
[[ ! -r "$HOME/.config/atuin/env.sh" ]] || source "$HOME/.config/atuin/env.sh"
