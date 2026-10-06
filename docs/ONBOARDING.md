# Application onboarding reference

The installer owns packages and configuration links. Applications own account login, license activation, permissions, and services. The current setup checklist lives in [ACTION_ITEMS.md](../ACTION_ITEMS.md).

## 1Password and private configuration

1Password's SSH agent supplies SSH authentication and commit signing. Its CLI integration lets `op` resolve references for explicit commands. Git identities use SSH public signing keys and `/Applications/1Password.app/Contents/MacOS/op-ssh-sign`.

Public macOS configuration sets the 1Password agent in `macos/ssh/config` and exports `SSH_AUTH_SOCK` from `home/.zprofile`. SSH optionally includes `~/.ssh/config.private`, linked from private `machines/PROFILE/ssh/config`, before the agent default. Private configuration includes `~/.ssh/hosts` from the same machine profile and accepts additional options or Host blocks. Private overrides take precedence. Containers retain their supplied SSH configuration and agent.

```sh
dotfiles private-setup
dotfiles fonts-install
```

Private setup reuses the installer's personal/work choice unless a saved private choice or explicit flag overrides it. The private repo's README describes identity directory rules, profiles, and active files. Credential caches, tokens, passwords, and SSH private keys stay outside Git.

## Herd and mise

Herd Pro owns PHP, Composer, and selected local services. Public zsh puts Herd's bin directory on PATH and activates mise after private shell additions. Herd's nvm initialization conflicts with mise ownership; review `git diff` in the public repo after Herd changes shell configuration and remove that initialization block directly.

```sh
command -v php
command -v composer
command -v node
mise which node
mise which terraform
mise which kubectl
mise which helm
dotfiles doctor
```

PHP and Composer resolve through `~/Library/Application Support/Herd/bin`. Node resolves through mise. Project configuration overrides global mise versions; `herd php` and `herd composer` select Herd's per-site PHP isolation. `terraform version`, `kubectl version --client`, and `helm version --short` check the clients without accessing infrastructure.

## Docker and Tailscale

Docker Desktop supplies the engine, CLI, and Compose. `docker version` reports client and running-server information. Tailscale uses the standalone app and its system/network extension; authentication and network selection use its own interface.

## Editor and app preferences

VS Code Settings Sync owns preferences and extensions. Appearance selections are Catppuccin Mocha, zsh as the integrated terminal, MonoLisa Code Variable, and optional ligatures. The terminal can use `'MonoLisaCode Variable', 'Symbols Nerd Font Mono'` for symbol fallback. The [font reference](FONTS.md) describes other families.

Other applications use their own sign-in and preference mechanisms. Homebrew's shared/personal/work manifests determine which apps install on each Mac.

## Service CLIs

```sh
gh auth login
glab auth login
infisical login
aws sso login --profile PROFILE
aws sts get-caller-identity --profile PROFILE
```

Vault uses the organization's server address and authentication method. AWS IAM Identity Center profiles contain noncredential configuration; cached SSO sessions remain local. `~/.aws/config` links to private `machines/PROFILE/aws/config`, where `PROFILE` is the machine's saved personal/work choice. The `--profile` argument to AWS commands selects a named AWS account/role within that file. [Atuin reference](ATUIN.md) describes machine-specific sync and AI authentication.

## macOS preferences

`dotfiles macos-preferences` applies Finder path/status bars, extensions, hidden files, folders-first sorting, and current-folder search; bottom Dock with auto-hide and no recents; fixed Spaces order; disabled smart substitutions; dark appearance; key repeat 2 and initial repeat 15 with the accent picker disabled.

The command exports affected preference domains to `~/.local/state/dotfiles/macos-preferences/`. Restoring an entire domain also replaces unrelated values in that domain, so inspect exports before importing them. Some preferences take effect on logout/login.
