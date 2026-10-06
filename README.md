# Anand's Dotfiles

My Mac setup and portable zsh environment for cloud based dev environments. Dotbot links ordinary configuration files into your home directory. Homebrew owns Mac apps and general CLI tools; mise owns development-tool versions. Private configuration lives in a separate repository.

## Setup

Apple Silicon Macs use:

```sh
./install.sh --profile personal
# Or: ./install.sh --profile work
```

Interactive setup also accepts `./install.sh` and asks for the Homebrew profile. Setup installs missing dependencies, links public files, and installs the global mise tools. Each operation supports reruns. App authentication and license activation use the applications' own interfaces; [onboarding reference](docs/ONBOARDING.md) describes them. [ACTION_ITEMS.md](ACTION_ITEMS.md) tracks setup and validation tasks.

Configuration-only linking uses:

```sh
./bin/dotfiles diff       # Preview links/backups without changing files
./bin/dotfiles link       # Back up conflicts and create links
```

## Editing

Edit a file through either path:

```sh
code ~/.zshrc
code /path/to/dotfiles/home/.zshrc
```

Both paths refer to the same file. An edit is immediately live on disk, with no apply step. Zsh reads startup files when a shell starts; applications use their own reload behavior. Adding or renaming a managed file requires `dotfiles link` to create its link. `dotfiles apply` is an alias for `link`.

Applications that write through these symlinks also edit the repository. `git diff` shows those changes. An application that replaces a symlink with a regular file breaks the connection; `dotfiles link` backs up that file and restores the link. Herd shell additions require review in Git: remove its nvm block from `home/.zshrc`, leaving mise as Node's owner.

| Source | Target |
| --- | --- |
| `home/.zshrc`, `.zprofile`, `.gitconfig` | Corresponding files in `~/` |
| `config/` | Files under `~/.config/` |
| `macos/config/` | Mac-only files under `~/.config/` |
| `macos/ssh/` | Mac-only files under `~/.ssh/`; 1Password agent defaults |
| `bin/` | Commands under `~/.local/bin/` |
| Private `config/`, `ssh/` | Shared private settings and Git allowed signers |
| Private `machines/personal/`, `machines/work/` | Selected AWS, SSH, and Atuin configuration |

Private `machines/PROFILE/ssh/config` links to `~/.ssh/config.private`. The public macOS SSH config includes it before the 1Password agent default, allowing private overrides without overlapping targets.

The YAML manifests use file globs, so shared configuration directories remain real directories. Public and private files coexist without one repo owning the other's files. Examples live outside managed directories.

## Tool ownership

| Component | Owner |
| --- | --- |
| Configuration links | Dotbot |
| Mac apps and general CLI tools | Homebrew |
| PHP, Composer, local web/database services | Laravel Herd Pro |
| Node, Go, Terraform, kubectl, Helm, AWS CLI, pnpm, Bun | mise |
| npm | Node |
| Docker engine, CLI, Compose | Docker Desktop |
| Editor preferences/extensions | VS Code Settings Sync |
| SSH authentication and Git signing | 1Password |
| Identities, AWS profiles, SSH hosts, Atuin endpoints, fonts | Private repo |

`macos/config/mise/config.toml` uses Node LTS and `latest` for other global tools. Project `mise.toml` files override these defaults. kubectl is the Kubernetes client; cluster versions determine the compatible client version (within one minor release of the API server). Project pins also control Terraform and Helm compatibility. Containers get shell tools; their projects own runtimes.

## Homebrew profiles

| File | Scope |
| --- | --- |
| `Brewfile` | Shared |
| `Brewfile.personal` | Personal Mac |
| `Brewfile.work` | Work Mac |

Add `brew "NAME"` for a CLI or `cask "NAME"` for an app. Move a package into a profile file to scope it to that Mac. The shared list includes `gh`, `glab`, Infisical's official tap, and HashiCorp's Vault tap.

The Infisical and Vault formula entries use `trusted: true`. Homebrew Bundle grants trust to these specific formulas before loading them; the rest of each third-party tap requires its own trust choice.

Formula-level trust requires a fully qualified `owner/tap/formula` name, such as `brew "stategraph/stategraph/stategraph", trusted: true`. Homebrew ignores this trust option on a short name such as `brew "stategraph"`, even with a separate `tap` entry.

```sh
dotfiles brew-profile             # Show saved choice
dotfiles brew-profile work        # Select without installing
dotfiles brew-install             # Install shared + selected packages
dotfiles brew-install --profile personal
```

The selection is a plain local file at `~/.config/dotfiles/brew-profile`. Installation uses `brew bundle --no-upgrade`. Removing entries or changing profiles leaves installed apps in place; deliberate uninstalling uses Homebrew directly. Each profile file is a partial list, so `brew bundle cleanup` against one file is unsuitable.

## Private setup

```sh
dotfiles private-setup             # Reuse the installer's personal/work choice
dotfiles git-identity work
dotfiles atuin-ai
dotfiles fonts-install
```

`private-setup` defaults to `../private` relative to the public checkout, regardless of your working directory. An optional first argument selects another location: `dotfiles private-setup /another/path/private`. Other private commands use the saved location.

Private setup selects Git using this precedence: an explicit `--identity` flag, a saved Git identity, then the installer's saved personal/work choice when the matching identity exists. With no matching choice, interactive setup asks for a Git identity. Identity names are filenames under the private `config/git/identities/` directory. Atuin follows the machine choice together with AWS and SSH.

The machine choice, Git identity, and private checkout path live in `~/.config/dotfiles/`, outside Git. Git's default identity is a local symlink; directory `includeIf` rules in the private Git configuration override it. Each identity contains its 1Password signing configuration. Changing the machine choice preserves the saved Git identity; `dotfiles git-identity NAME` changes it explicitly.

AWS, SSH, and Atuin follow the machine's `brew-profile` choice together. `private-setup`, `link --private`, and configuration updates link only that machine's files from `private/machines/personal/` or `private/machines/work/`. With no saved machine choice, they select personal. Switching `dotfiles brew-profile personal|work` takes effect for these files on the next private link; Git retains its independent saved identity. AWS credentials and cached sessions remain local.

Atuin's shared preferences live in public `config/atuin/config.toml`. Private `machines/PROFILE/atuin/env.sh` supplies service settings through `ATUIN_*` environment variables; a new shell or `source ~/.config/atuin/env.sh` loads edits. History and authentication use Atuin's default local data directory, normally `~/.local/share/atuin`. Its work endpoints and optional 1Password token reference live in ordinary private files. [Atuin reference](docs/ATUIN.md) describes machine configuration and authentication.

Licensed font binaries live privately. Font installation is an explicit copy/validation operation. The public Ghostty configuration selects MonoLisa Code Variable, with bundled JetBrains Mono as the fallback when MonoLisa is unavailable. Ghostty supplies Nerd Font symbol fallback. [Font reference](docs/FONTS.md) describes all collections and patching.

## Updates and repository location

```sh
git diff                         # Review live edits in the current checkout
dotfiles update                  # Fast-forward repos and refresh links
dotfiles doctor                  # Check essential tools and key links
```

Update requires clean repositories and configured upstream branches. It rejects divergence, preserves local commits, and updates configuration only. Symlinked content changes as Git updates the files. New links use the same backup behavior as setup.

Software upgrades are explicit:

```sh
brew update
brew upgrade
MISE_CONFIG_FILE="$HOME/.config/mise/config.toml" mise --cd "$HOME" upgrade --no-prune
```

Global `lts`/`latest` selectors remain moving defaults. `--no-prune` retains installations used by projects. Shell plugins use Git checkouts under `~/.local/share/dotfiles/plugins/`; `git -C PATH pull --ff-only` updates a chosen plugin. Container tools use their upstream installers; `scripts/install-container-tools` installs missing tools. Dotbot's container checkout updates through `git pull --ff-only` followed by `git submodule update --init --recursive` in `~/.local/share/dotfiles/dotbot`.

The standard checkout layout is:

```text
~/dev/dotfiles/
├── public/
└── private/
```

The parent is a directory containing two independent Git repositories. Both repositories can live elsewhere; an explicit private path supports other layouts. Keep their checkouts available because the home files link to them. After moving the pair, run the launcher directly from its new path:

```sh
~/dev/dotfiles/public/bin/dotfiles private-setup
~/dev/dotfiles/public/bin/dotfiles link
```

Only a public move requires just the second command. Local profile choices persist. Private setup refreshes the selected default-identity link.

## Shell and appearance

Plain zsh provides completion, autosuggestions, syntax highlighting, fzf, zoxide, Starship, and Atuin. Ctrl-R opens Atuin; the up arrow keeps normal history navigation. Ghostty, Starship, Atuin, bat, delta, fzf, highlighting, and eza use Catppuccin Mocha colors.

Theme sources and custom settings:

| Component | Theme source |
| --- | --- |
| Ghostty | Bundled `Catppuccin Mocha` theme |
| bat, Atuin, bottom, k9s | Upstream Catppuccin themes; sources and licenses are in `licenses/` |
| zsh syntax highlighting | Official [Catppuccin theme](https://github.com/catppuccin/zsh-syntax-highlighting), stored in `config/zsh/catppuccin-mocha.zsh` and loaded before the plugin |
| fzf | Inline subset of the official Mocha settings, without its border and label colors |
| eza | Custom directory, symlink, and executable colors from the Mocha palette |
| zsh completion and autosuggestions | Custom Mocha color assignments |
| delta | Official bat syntax theme with custom added/removed-line backgrounds |
| Starship | Custom lean prompt based on the supplied references, using the Mocha palette |

`config/starship.toml` uses a lean two-line layout: OS, directory, Git, and relevant language versions on the left; conditional cloud context, command status/duration, and jobs on the right. The second line contains the prompt arrow. AWS appears in directories with Terraform files or `.terraform`. Kubernetes appears for Helm/Kustomize files or YAML containing top-level `apiVersion` and `kind`, in the current directory or its `k8s/`, `kubernetes/`, or `manifests/` directories. Each cloud indicator also requires a locally configured profile or context. These indicators read local settings; they do not authenticate or contact cloud services. Ghostty supplies the MonoLisa font and icon fallback.

Bottom (`btm`) is a system monitor in the shared Brewfile. `config/bottom/bottom.toml` supplies the Catppuccin Mocha theme through its link at `~/.config/bottom/bottom.toml`.

k9s is a Kubernetes terminal interface in the shared Brewfile. `K9S_CONFIG_DIR` points to `~/.config/k9s` on macOS and Linux. Its `config.yaml` selects the official Catppuccin Mocha skin in `skins/catppuccin-mocha.yaml`.

| Interactive command | Replacement |
| --- | --- |
| `cat` | `bat --paging=never --style=plain` |
| `ls`, `ll`, `la` | eza, long listing, long listing with hidden files |
| `tree` | `eza --tree` |
| `cd` | zoxide's `cd` function |
| `grep` | ripgrep |
| `find` | fd |

Aliases activate when the tool exists. They use the replacement's arguments: ripgrep searches recursively and respects ignore files; fd takes a pattern/path instead of `find` expressions. `command cat`, `command ls`, `command grep`, and `command find` invoke originals; `builtin cd` bypasses zoxide. Scripts retain normal command behavior.

```sh
git prune-check             # List merged and squash-merged branches relative to main
git prune-all               # Delete those branches
git prune-all develop       # Choose a different target
```

Both commands check out the target first. Merged branches use `git branch -d`; squash-merged branches use `-D` after combined-patch comparison. Unmerged branches remain, and Git enforces its worktree checks. Comparison objects are unsigned. These aliases call a small Bash helper.

## Containers

GitHub Codespaces invokes executable `install.sh`; `CODESPACES=true` selects container setup. Explicit Dev Containers integration uses:

```json
{
  "dotfiles.repository": "https://github.com/YOUR_ACCOUNT/dotfiles",
  "dotfiles.installCommand": "install-container.sh"
}
```

Debian/Ubuntu amd64 and arm64 are supported. Setup installs missing prerequisites through apt with root or passwordless sudo, then installs Dotbot, mise, Starship, Atuin, and zsh plugins in the user's home. It uses noninteractive upstream binary installers and public configuration. Container authentication and project runtimes belong to the container/project. VS Code's zsh terminal selection belongs to Settings Sync or the project.

## Recovery and tests

Conflicting files get adjacent `.dotbot-backup.TIMESTAMP` backups. Conflicting symlinks get unique backups that preserve their targets. Correct links stay in place on reruns. Parent symlinks and directory/file conflicts stop linking. Resolve an error and rerun the same command.

To restore a file, inspect its backup and the current link, unlink the managed path, then move the selected backup into that path. Git restores changes made through a live link; Dotbot backups cover link installation, not every edit. macOS preference exports live under `~/.local/state/dotfiles/macos-preferences/`.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tests/run.py
# DOTBOT_BIN=/path/to/dotbot/bin/dotbot selects an explicit test executable.
```

[Verification reference](docs/VERIFICATION.md) describes test coverage and commands.
