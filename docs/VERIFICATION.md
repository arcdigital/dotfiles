# Verification

Tests run against temporary homes and fixture repositories. They link fixture files, use mock package commands, and keep the user's actual configuration separate. The test suite requires Dotbot 1.24+; optional client checks also use mise, Starship, and Atuin executables.

The suite contains 47 tests, including optional checks with real mise, Starship, and Atuin clients. Shell fixtures isolate mocked or missing tools from Homebrew packages on the test host. The private font manifests validate all 44 original MonoLisa 3.000 files; the public source contains no licensed font binaries or private identity values.

Machine tests verify personal/work AWS, SSH, and Atuin selection together, live edits, dry-run selection, backups, reruns, relocation, missing-file failures, and preservation of local AWS credentials and SSO caches. Atuin checks cover machine configuration, retention of existing history in the default data directory across machine choices, optional AI token lookup, and public service defaults. SSH checks inspect effective options with `ssh -G` without connecting to a host.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tests/run.py
# Explicit tools:
DOTBOT_BIN=/path/to/dotbot/bin/dotbot python3 tests/run.py
# Optional client checks:
DOTBOT_BIN=/path/to/dotbot/bin/dotbot MISE_BIN=/path/to/mise \
  STARSHIP_BIN=/path/to/starship ATUIN_BIN=/path/to/atuin python3 tests/run.py
```

Coverage includes live edits in both directions, idempotent links, file/symlink backups, conflicting parents/directories, interruption recovery, dry-run behavior, checkout relocation, public/private target separation, machine Git identities, directory overrides, commit-signing settings, Atuin machine/token handling, Homebrew profile isolation, inherited personal/work defaults, explicit and saved Git identity overrides, and fast-forward configuration updates. Git pruning tests exercise merged, squash-merged, and unmerged branches in disposable repositories. Font fixtures exercise imports, metadata, version checks, collision detection, patcher output validation, and backup-preserving installation.

Shell validation uses:

```sh
shellcheck -x install.sh install-container.sh bin/* scripts/*.sh \
  scripts/prepare-links scripts/git-prune scripts/install-container-tools scripts/macos-preferences
bash -n install.sh
zsh -n home/.zshrc
zsh -n home/.zprofile
ruby -c Brewfile
ruby -c Brewfile.personal
ruby -c Brewfile.work
```

The Docker smoke test uses a non-root home:

```sh
docker build -f tests/Dockerfile -t dotfiles-check .
docker run --rm dotfiles-check
```

CI defines Ubuntu 24.04 and Debian 12 jobs for Linux amd64/arm64. Platform-selection tests run with a controlled `uname`; they verify configuration selection, while Docker smoke jobs exercise Linux execution. The smoke test checks repeat installation, backups, tool commands, and the absence of global runtimes/private configuration in a container.

Automated font validation covers embedded metadata and checksums. The patcher tests use synthetic fonts and a simulated Docker process to check parallel job limits, writable temporary inputs, preserved failure output, and exact family/style naming across Hairline, heavier weights, and italic variants. The real Docker run validates all 20 patched MonoLisa 3.000 faces with Nerd Fonts 3.5.1, including unique PostScript names, original metrics flags, GSUB table presence, and unchanged source checksums. The combined private collection contains 64 fonts. Application rendering, licenses, live authentication, and infrastructure access use the checks in [ACTION_ITEMS.md](../ACTION_ITEMS.md).
