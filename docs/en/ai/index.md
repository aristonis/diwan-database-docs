# AI agents

Diwan ships files that a coding agent (Claude Code, Codex, Cursor and similar) reads to write correct Diwan code in your project. They live in the `ai/` folder of the code repository, next to the source, so they match the version you use.

## What is in `ai/`

| File | What it is |
|---|---|
| `ai/README.md` | What the folder is and how to load it. |
| `ai/AGENTS.md` | The rules file. What Diwan is, the entry point per database, the must and never rules, where the docs live. See [Agent rules file](agent.md). |
| `ai/skills/<name>/SKILL.md` | One skill per task, in the Agent Skills format. See [Skills](skills.md). |

The rules are listed with reasons on [Rules](rules.md). To report a bug, see [Report an issue](report-issue.md). To comment on the docs or a skill, see [Feedback](feedback.md).

## Point an agent at them

1. Paste the block from [Agent rules file](agent.md) into your project's `AGENTS.md` or `CLAUDE.md`.
2. Copy the skills you need into your agent's skills folder:

```bash
cp -r ai/skills/* .claude/skills/
```

3. Ask for the work in plain words. The agent loads a skill when its description matches the task.

The guides on this site stay the source of truth. If a skill and a guide disagree, follow the guide and send feedback.

## llms.txt

An `llms.txt` file for this site, a plain index of the pages for tools that read the web, is planned. It is not published yet. Until then, point an agent at the pages under [Guides](../getting-started.md) or at the `ai/` folder.
