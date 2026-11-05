# Using the Newton skill with an AI assistant

[`skills/ingetrazo-newton/`](../skills/ingetrazo-newton/SKILL.md) is an Agent Skill: a folder with a `SKILL.md` (frontmatter `name` and `description`, then instructions). It teaches an AI coding assistant how to build and tune models for Newton: the objects and their effects, how to group parts so the simulation is correct and fast, performance options and limits.

It is first of all a skill the assistant picks up **by itself**: the assistant reads the `description` and loads the skill when your request matches (modelling a mechanism for Newton, a slow or odd simulation, inspecting `group.ext["newton"]` in an `.igz`). You do not have to call it. Both tools below can also start a skill explicitly, but that is optional.

The skill does not run Newton or IngeTrazo. To let an assistant drive the open IngeTrazo document, the host has its own, different feature, the AI bridge (MCP), described in the IngeTrazo repository (`docs/ai-bridge.md`). The two combine well but are independent.

The frontmatter (`name: ingetrazo-newton`, `description`) matches the folder name and uses only fields that both Claude Code and Codex accept. Per the current docs, Claude Code treats all fields as optional (`description` recommended), Codex requires `name` and `description`.

## Claude Code

Per the [Claude Code skills documentation](https://code.claude.com/docs/en/skills), a skill is a folder `<name>/SKILL.md` in one of two places:

| Scope | Folder |
|---|---|
| All your projects | `~/.claude/skills/ingetrazo-newton/` |
| One project (commit it to share) | `<project>/.claude/skills/ingetrazo-newton/` |

The documentation names `~/.claude/skills/` only; on Windows that is the same path under your user profile, `%USERPROFILE%\.claude\skills\ingetrazo-newton\` (the home-directory mapping is not spelled out in the docs).

Copy or link, from the repository root:

```bash
# all projects, symlink (follows repository updates)
mkdir -p ~/.claude/skills && ln -s "$PWD/skills/ingetrazo-newton" ~/.claude/skills/ingetrazo-newton
# or one project, copy
mkdir -p /path/to/project/.claude/skills && cp -r skills/ingetrazo-newton /path/to/project/.claude/skills/
```

```powershell
# Windows, copy
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse skills\ingetrazo-newton "$env:USERPROFILE\.claude\skills\"
```

A symlink to a skill folder is supported by Claude Code. A copy does not follow repository updates; copy again after pulling. Claude Code watches the skills folders, so a new or edited skill applies in the running session; if the top-level `skills` folder did not exist when the session started, run `/reload-skills` (or restart).

Check it is loaded: type `/skills` in Claude Code and look for `ingetrazo-newton`. Then ask, for example, "Why does my Newton drawer simulation start so slowly?" and watch for the skill being loaded. Typing `/ingetrazo-newton` at the start of a message runs it explicitly.

## Codex

Per the [Codex skills documentation](https://learn.chatgpt.com/docs/build-skills) (the old developers.openai.com address redirects there), Codex looks for skills in:

| Scope | Folder |
|---|---|
| One repository | `.agents/skills/` in each folder from the working directory up to the repository root |
| User | `$HOME/.agents/skills/` |
| Admin | `/etc/codex/skills/` |

So for Codex the folder is `~/.agents/skills/ingetrazo-newton/` or `<project>/.agents/skills/ingetrazo-newton/`, not a `.claude` folder:

```bash
mkdir -p ~/.agents/skills && ln -s "$PWD/skills/ingetrazo-newton" ~/.agents/skills/ingetrazo-newton
```

Codex follows symlinked skill folders, selects a skill implicitly when the task matches its description, and lists skills with `/skills` in the CLI or IDE extension (or `$` to name one). Changes are detected automatically; restart Codex if one does not show up. I did not run Codex against this skill (untested).

Alternative that works with any assistant reading `AGENTS.md`, without skills support: this repository's [AGENTS.md](../AGENTS.md) is for people developing Newton, not for modelling. For modelling help, copy the content of `SKILL.md` below the frontmatter into the `AGENTS.md` of your own project, or reference it from there.
