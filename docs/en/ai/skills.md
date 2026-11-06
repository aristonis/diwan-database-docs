# Skills

A skill is a folder with one `SKILL.md`. Its frontmatter has a `name` and a `description`. The agent reads the description and loads the skill when the task matches, so the steps do not take space in the context until they are needed.

## The skills

| Skill | Triggers when |
|---|---|
| `diwan-usage` | You add Diwan, build a `Connection`, choose SQLite or PostgreSQL, or wrap work in a transaction. |
| `diwan-query-builder` | You write or review a query with `table(...)`: filters, joins, pagination, chunking, cursors, upsert, row locks, raw expressions. |
| `diwan-migrations` | You create a table, change a column, add a migration, run or roll back, or see a checksum error. |
| `diwan-models-relations` | You add a model, a relation, casts, scopes or eager loading, or fix an N+1. |
| `diwan-android` | You run Diwan on Android, set up the driver, handle threads, shrink with R8, or hit an API-level limit. |
| `diwan-report-issue` | A Diwan call fails in a way the docs do not explain, or you ask to report a bug. |

Every skill has the same parts: task steps, the real API, a minimal example and a list of pitfalls.

## Install

Copy the skills you need from `ai/skills/` in the code repository into the folder your agent reads skills from.

```bash
# Claude Code, one project
cp -r ai/skills/* .claude/skills/

# Claude Code, every project
cp -r ai/skills/* ~/.claude/skills/
```

Other agents that support the Agent Skills format have their own skills directory. Copy the same folders there. Keep each folder whole, with its `SKILL.md` inside.

When you upgrade Diwan, copy the skills again. They are versioned with the code.

Next: [Rules](rules.md) for the full list with reasons.
