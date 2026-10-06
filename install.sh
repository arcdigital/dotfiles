#!/bin/bash
# shellcheck source-path=SCRIPTDIR
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
export DOTFILES_ROOT="$repo"
# shellcheck source=scripts/common.sh
source "$repo/scripts/common.sh"
mode=mac; profile=
[[ ${CODESPACES:-false} != true ]] || mode=container
while [[ $# -gt 0 ]]; do
    case $1 in
        --container) mode=container; shift;;
        --profile) [[ $# -gt 1 ]] || fail 'Missing profile'; profile=$2; shift 2;;
        -h|--help) echo 'Usage: ./install.sh [--profile personal|work] | --container'; exit;;
        *) fail "Unknown option: $1";;
    esac
done
[[ -z $profile || $profile == personal || $profile == work ]] || fail 'Expected personal or work.'
export PATH="$HOME/.local/bin:$PATH"
if [[ $mode == container ]]; then
    [[ -z $profile ]] || fail 'Homebrew profiles are Mac-only.'
    [[ $(uname -s) == Linux ]] || fail 'Container setup requires Linux.'
    # shellcheck source=/dev/null
    source /etc/os-release
    case ${ID:-} in debian|ubuntu) ;; *) fail 'Supported containers: Debian/Ubuntu.';; esac
    missing=()
    for tool in python3 zsh git curl; do command -v "$tool" >/dev/null || missing+=("$tool"); done
    [[ -s /etc/ssl/certs/ca-certificates.crt ]] || missing+=(ca-certificates)
    if [[ ${#missing[@]} -gt 0 ]]; then
        elevate=()
        if [[ $(id -u) != 0 ]]; then
            if ! command -v sudo >/dev/null || ! sudo -n true; then fail "Install prerequisites as root: ${missing[*]}"; fi
            elevate=(sudo -n)
        fi
        "${elevate[@]}" env DEBIAN_FRONTEND=noninteractive apt-get update
        "${elevate[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${missing[@]}" ca-certificates
    fi
    "$repo/scripts/install-container-tools"
else
    require_mac
    xcode-select -p >/dev/null 2>&1 || fail 'Run xcode-select --install, then rerun.'
    brew_profile "$profile"
    if [[ -x /opt/homebrew/bin/brew ]]; then export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"; fi
    if ! command -v brew >/dev/null; then
        installer=$(mktemp)
        trap 'rm -f -- "$installer"' EXIT
        curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$installer"
        /bin/bash "$installer"
        export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
    fi
    brew_install "$selected"
fi
# Plugins are installed once. Updating them is a separate explicit operation.
for plugin in zsh-autosuggestions zsh-syntax-highlighting; do
    destination="$HOME/.local/share/dotfiles/plugins/$plugin"
    if [[ ! -d $destination/.git ]]; then
        [[ ! -e $destination ]] || fail "Incomplete plugin checkout: $destination. Move it aside and rerun."
        mkdir -p "$(dirname -- "$destination")"
        git clone --depth 1 "https://github.com/zsh-users/$plugin.git" "$destination"
    fi
done
"$repo/bin/dotfiles" link
if [[ $mode == mac ]]; then
    mise trust "$HOME/.config/mise/config.toml"
    MISE_CONFIG_FILE="$HOME/.config/mise/config.toml" mise --cd "$HOME" install
    echo 'Public setup ready. See docs/ONBOARDING.md; restore the private repo after authentication.'
    echo 'Restore Codex marketplace plugins with: dotfiles codex-plugins-install'
    if [[ -t 0 ]]; then
        read -r -p 'Apply the separate macOS preferences step now? [y/N] ' answer
        [[ $answer != y && $answer != Y ]] || "$repo/bin/dotfiles" macos-preferences
    fi
else
    echo 'Container shell ready. Select zsh in VS Code; project mise files own runtimes.'
fi
