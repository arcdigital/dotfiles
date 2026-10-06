# Codex marketplace plugins

`CodexPlugins` records one GitHub marketplace and plugin selector per line:

```text
# GitHub marketplace repository    plugin@marketplace
DietrichGebert/ponytail             ponytail@ponytail
```

Run this from any directory to restore the list:

```sh
dotfiles codex-plugins-install
```

The command requires Codex CLI and jq, which the shared Brewfile supplies. It registers missing marketplaces and installs missing plugins. Existing installations retain their enabled/disabled state. A marketplace name registered to a different source stops the command with an explanation. Reruns resume after a failure.

Add another `OWNER/REPO plugin@marketplace` line to manage another plugin. Repeat the source for multiple plugins from the same marketplace. Blank lines and full-line comments are supported. The marketplace name comes from the upstream catalog and can differ from the GitHub repository name.

Codex owns the downloaded marketplace and plugin caches, authentication, hook trust, and local plugin state. The repo records the desired installation list. `dotfiles link` and `dotfiles update` do not install or upgrade marketplace plugins.

## Updates and removal

Inspect the current state with:

```sh
codex plugin marketplace list
codex plugin list
```

Marketplace refresh is an explicit operation, for example:

```sh
codex plugin marketplace upgrade ponytail
```

Use Codex's plugin management to manage installed versions. `dotfiles codex-plugins-install` skips installed plugins. Removing a line from `CodexPlugins` leaves the installed plugin in place. Deliberate removal uses `codex plugin remove ponytail@ponytail`; remove its manifest entry too to keep it out of subsequent restores.

## Ponytail

Ponytail includes skills and lifecycle hooks. The full plugin's hooks load its behavior into sessions; copying its skill directory alone does not include those hooks. Codex's `/hooks` interface manages hook trust. A new thread loads the installed plugin. Machine-specific trust and authentication tasks live in [ACTION_ITEMS.md](../ACTION_ITEMS.md).

## Other agents

`CodexPlugins` applies to Codex. Claude Code and OpenCode use their own plugin managers and formats. Portable standalone skills in `skills/` are shared by all three tools through the existing directory links; marketplace plugin installations use their host's native manager.

## References

- [Codex marketplace management](https://developers.openai.com/plugins/build/plugins)
- [Ponytail installation](https://github.com/DietrichGebert/ponytail#install)
