# shellcheck shell=bash
repo=${DOTFILES_ROOT:?}
selected=
dotbot=
# Shared shell functions; sourced by the installer and command launcher.
fail() { echo "$*" >&2; exit 1; }
require_mac() { [[ $(uname -sm) == 'Darwin arm64' ]] || fail 'This operation requires an Apple Silicon Mac.'; }
local_settings="$HOME/.config/dotfiles"
read_setting() { [[ ! -f "$local_settings/$1" ]] || cat "$local_settings/$1"; }
save_setting() {
    mkdir -p "$local_settings"
    local temporary
    temporary=$(mktemp "$local_settings/.setting.XXXXXX")
    printf '%s\n' "$2" > "$temporary"
    mv -f -- "$temporary" "$local_settings/$1"
}
private_source() {
    private=$(read_setting private-source)
    [[ -n $private && -f $private/install.conf.yaml ]] || fail 'Run: dotfiles private-setup (defaults to the sibling private checkout; an explicit PATH is optional).'
}
dotbot_command() {
    dotbot=${DOTBOT_BIN:-}
    [[ -n $dotbot ]] || dotbot=$(command -v dotbot || true)
    [[ -n $dotbot ]] || dotbot="$HOME/.local/share/dotfiles/dotbot/bin/dotbot"
    [[ -x $dotbot ]] || fail 'Dotbot is missing. Run install.sh first (or brew install dotbot).'
}
link_repo() {
    local source=$1 mode=$2 preview=${3:-} relative
    dotbot_command
    if [[ $mode == private ]]; then
        export DOTFILES_MACHINE_PROFILE DOTFILES_PRIVATE_ROOT
        DOTFILES_PRIVATE_ROOT=$source
        DOTFILES_MACHINE_PROFILE=$(read_setting brew-profile)
        DOTFILES_MACHINE_PROFILE=${DOTFILES_MACHINE_PROFILE:-personal}
        case $DOTFILES_MACHINE_PROFILE in personal|work) ;; *) fail 'Select personal or work with dotfiles brew-profile.';; esac
        for relative in aws/config ssh/config ssh/hosts atuin/env.sh atuin/ai-token-reference; do
            [[ -f $source/machines/$DOTFILES_MACHINE_PROFILE/$relative ]] || fail "Missing machine configuration: $source/machines/$DOTFILES_MACHINE_PROFILE/$relative"
        done
        echo "AWS, SSH, and Atuin machine configuration: $DOTFILES_MACHINE_PROFILE"
    fi
    if [[ $preview != --dry-run ]]; then
        if [[ $mode == public ]]; then
            export DOTFILES_PRIVATE_ROOT
            DOTFILES_PRIVATE_ROOT=$(read_setting private-source)
            roots=("$source/home" "$HOME" "$source/config" "$HOME/.config" "$source/bin" "$HOME/.local/bin")
            [[ $(uname -s) != Darwin ]] || roots+=("$source/macos/config" "$HOME/.config" "$source/macos/ssh" "$HOME/.ssh")
        else
            roots=("$source/config" "$HOME/.config" "$source/ssh" "$HOME/.ssh"
                   "$source/machines/$DOTFILES_MACHINE_PROFILE/ssh" "$HOME/.ssh"
                   "$source/machines/$DOTFILES_MACHINE_PROFILE/aws" "$HOME/.aws"
                   "$source/machines/$DOTFILES_MACHINE_PROFILE/atuin" "$HOME/.config/atuin-machine")
        fi
        "$repo/scripts/prepare-links" "$mode" "${roots[@]}"
    fi
    if [[ -n $preview ]]; then "$dotbot" -d "$source" -c "$source/install.conf.yaml" "$preview"
    else "$dotbot" -d "$source" -c "$source/install.conf.yaml"; fi
    if [[ -z $preview && -d $HOME/.ssh && $(uname -s) == Darwin ]]; then chmod 700 "$HOME/.ssh"; fi
    if [[ $mode == private && -z $preview && -d $HOME/.aws ]]; then chmod 700 "$HOME/.aws"; fi
    if [[ $mode == public && -z $preview ]] && command -v bat >/dev/null; then bat cache --build >/dev/null; fi
}
brew_profile() {
    require_mac
    selected=${1:-$(read_setting brew-profile)}
    if [[ -z $selected && -t 0 ]]; then read -r -p 'Homebrew profile (personal/work): ' selected; fi
    case $selected in personal|work) ;; *) fail 'Choose --profile personal or --profile work.';; esac
    save_setting brew-profile "$selected"
}
brew_install() {
    brew_profile "${1:-}"
    [[ -f $repo/Brewfile && -f $repo/Brewfile.$selected ]] || fail 'Missing shared or selected Brewfile.'
    if ! command -v brew >/dev/null; then
        [[ ! -x /opt/homebrew/bin/brew ]] || export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
    fi
    command -v brew >/dev/null || fail 'Install Homebrew with install.sh first.'
    brew bundle install --no-upgrade --file "$repo/Brewfile"
    brew bundle install --no-upgrade --file "$repo/Brewfile.$selected"
}
