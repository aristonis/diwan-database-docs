# Report an issue

File a library bug at https://github.com/aristonis/diwan-database/issues. The repository URL works once the project is public.

## Before you file

1. Check the guide for the feature. Some behavior is listed on [Differences from Laravel](../differences.md) or [Errors and exceptions](../errors.md).
2. Reduce the failure to the smallest code that still fails, on an empty database.

## Template

```markdown
**Diwan version:**
**Module:** (core, sqlite, pgsql, eloquent or android)
**Database and version:** (for example SQLite 3.45, PostgreSQL 16)
**Java version or Android API level:**

**Minimal code:**

**Full error, with the cause chain ("Caused by: ..."):**

**Expected:**

**Actual:**
```

The full error matters. A top-line message alone often hides the database error underneath.

## Never include

- Secrets, tokens and API keys.
- Connection strings with passwords.
- Binding values that hold personal data. Replace them with placeholders.
- Your whole project. A minimal example is faster to fix.

## File it with the GitHub CLI

Write the report to a file, then:

```bash
gh issue create --repo aristonis/diwan-database \
  --title "paginate returns the wrong total with a group by" \
  --body-file issue.md
```

An agent can do the same with the `diwan-report-issue` skill. It gathers the version and platform, writes the file, and asks you to check it before it files anything. See [Skills](skills.md).
