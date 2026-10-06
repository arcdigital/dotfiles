# Global agent skills

`skills/` holds one directory per shared skill. Each directory contains a regular `SKILL.md` file and any supporting scripts, references, or assets.

```text
skills/
└── find-skills/
    └── SKILL.md
```

`dotfiles link` creates directory links for each skill:

| Tool | Global discovery path |
| --- | --- |
| Codex | `~/.agents/skills/NAME/` |
| Claude Code | `~/.claude/skills/NAME/` |
| OpenCode | Reads both of the paths above |

Both links point to the same repository directory. The parent skills directories remain ordinary directories, so independently installed skills coexist with these links. Codex's bundled `.system` skills and plugin-managed skills stay under their applications' control.

For full Codex plugins with hooks or MCP servers, `CodexPlugins` and `dotfiles codex-plugins-install` manage installation through Codex. See [Plugin management](PLUGINS.md).

## Add or edit a skill

Use the standard [skills CLI](https://github.com/vercel-labs/skills) from this checkout:

```sh
cd ~/dev/dotfiles/public
npx skills add mattpocock/skills --agent codex
dotfiles link
```

The CLI lets you choose skills. Its project installation path, `.agents/skills`, links to this repo's `skills/` folder. `--agent codex` selects that standard path; `dotfiles link` exposes the resulting skills globally to Codex, Claude Code, and OpenCode. Use project scope here, without `--global`, so the files and the CLI's `skills-lock.json` belong to this repo.

For `grill-with-docs` and its two required skills:

```sh
npx skills add mattpocock/skills --agent codex \
  --skill grill-with-docs grilling domain-modeling
dotfiles link
```

`skills-lock.json` records upstream sources and hashes automatically. Commit it with the installed skill files. Keep upstream licenses and attribution with the copied files or in `licenses/`.

Create `skills/my-skill/SKILL.md` in this checkout. Use the same lowercase, hyphen-separated name for the directory and frontmatter:

```markdown
---
name: my-skill
description: Describe the task this skill handles and when to use it.
---

Instructions for the agent.
```

`name` is 1–64 characters and `description` is 1–1024 characters. The names `synced` and `anthropic-skills` are reserved by Claude Code. Keep instructions portable: Claude-specific frontmatter and tool names do not have the same meaning in every application.

Run `dotfiles link` after adding a skill. Edits to existing skills are immediately live on disk; start a new turn or session to refresh the application's discovery. Codex detects changes automatically, with a restart available if a skill does not appear. Claude Code exposes skills as `/my-skill`; Codex supports explicit skill mentions; OpenCode lists them through its skill tool.

## Update or remove a skill

Update CLI-managed skills from this checkout with:

```sh
npx skills update --project
dotfiles link
```

Edits also work directly in `skills/`. Review and commit the changes through the normal repository workflow. `dotfiles update` pulls committed changes using the repo's fast-forward-only update process and refreshes links. It does not download upstream skill updates separately.

To remove a skill, unlink its two global links and remove its project installation from this checkout. For example:

```sh
unlink ~/.agents/skills/my-skill
unlink ~/.claude/skills/my-skill
npx skills remove my-skill --agent codex
```

`dotfiles link` does not delete unrelated skills or automatically remove links to deleted source directories.

## Existing skills and recovery

When a managed name already exists, the linker preserves that directory, file, or conflicting symlink under `~/.local/state/dotfiles/skill-backups/` before replacing it. Backups stay outside the discovery paths to avoid loading duplicate skills. Reruns leave matching links in place.

To restore a backup, unlink the replacement and move the saved item back to its original location. To recover an interrupted installation, run `dotfiles link` again; completed backups remain available.

`skills/` is public repository content. Confidential skill instructions belong in the private repository; this public manifest manages only this checkout's skills.

## Discovery references

- [Codex skills](https://developers.openai.com/codex/skills)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [OpenCode skills](https://opencode.ai/docs/skills/)
