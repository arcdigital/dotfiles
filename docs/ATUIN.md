# Atuin

Shared preferences live in public `config/atuin/config.toml`, linked to `~/.config/atuin/config.toml`. Automatic sync and AI are enabled there, alongside theme, search, workspace, and daemon preferences. Changes to this file are live; a running daemon reads daemon changes when it restarts. Server addresses belong in the private environment files below.

## Machine configuration

Atuin follows the installer's personal/work machine choice, stored at `~/.config/dotfiles/brew-profile`, together with AWS and SSH.

| Machine | Private configuration | Services |
| --- | --- | --- |
| Personal | `machines/personal/atuin/env.sh` | Official sync and AI Hub |
| Work | `machines/work/atuin/env.sh` | Custom sync and AI endpoints |

`dotfiles private-setup` and `dotfiles link --private` link the selected machine's environment file to `~/.config/atuin-machine/env.sh`. Its optional `ai-token-reference` is linked alongside it. Git identity selection is independent. A machine with no saved choice uses personal.

Zsh sources public `config/atuin/env.sh`, which sets `ATUIN_CONFIG_DIR` to the public config directory and loads the private machine environment on Macs. Public-only shells and containers use official service endpoints unless custom addresses are supplied in their environment. Open a new shell or run `source ~/.config/atuin/env.sh` after editing private server settings. Atuin reads its TOML file and environment; no merged configuration is generated.

Atuin uses its default local data directory, normally `~/.local/share/atuin`, for history databases, encryption keys, sessions, and AI data. Logs also use Atuin's default location. These stores live outside Git on each computer; the personal/work choice selects service settings and leaves local history and authentication intact. Ordinary zsh history uses `~/.zsh_history`; importing it into Atuin is an explicit choice.

## Private work configuration

Edit `machines/work/atuin/env.sh` in the private repo and reload the shell environment.

```sh
export ATUIN_SYNC_ADDRESS='https://sync.example.com'

export ATUIN_AI__ENDPOINT='https://ai.example.com'
```

`machines/work/atuin/ai-token-reference` optionally holds one literal 1Password reference:

```text
op://Work Vault/Atuin/token
```

An empty file means no custom token. The file contains a reference, never a token or shell assignment.

## Authentication and AI

These commands use the machine's linked configuration:

```sh
atuin info
atuin config get --resolved sync_address
atuin login
atuin sync
dotfiles atuin-ai
```

`atuin register` creates a sync account on servers that permit registration. Another computer uses the same account's encryption key from your password manager. `atuin import zsh` imports local history; inspect the account and history before choosing that operation.

Personal AI uses Atuin Hub authentication. `dotfiles atuin-ai` loads the same public and private environment files and resolves an optional reference with `op read`, passing the token through `ATUIN_AI__API_TOKEN` to that invocation. Shell startup and linking do not access 1Password. `atuin ai` works directly when the server needs no custom token.

Container-specific environment configuration can supply `ATUIN_SYNC_ADDRESS`, `ATUIN_AI__ENDPOINT`, and optional protocol overrides. Automatic sync and AI enablement belong to the shared TOML configuration. Authentication stores and secret values belong outside the repositories and images.
