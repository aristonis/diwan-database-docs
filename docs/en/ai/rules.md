# Rules

These are the rules in `ai/AGENTS.md`, each with its reason and the page that explains it.

## Always

| Rule | Why | Read |
|---|---|---|
| Close a `QueryCursor` with try-with-resources. | A cursor not read to the end keeps its pooled connection. On PostgreSQL it leaves the session idle in a transaction. A `stream()` releases only when closed. | [Query builder](../query-builder.md) |
| Check a user-supplied sort column against an allowlist. | Column and direction names are quoted as identifiers, not bound, so the builder cannot make them safe. | [Query builder](../query-builder.md) |
| Run row locks only inside a transaction. | PostgreSQL throws `IllegalStateException` for a locked select outside one. | [Query builder](../query-builder.md) |
| Pass values as bindings, with `whereRaw(sql, bindings)` and `selectRaw(sql, bindings)`. | Bindings keep data out of the SQL text. | [Query builder](../query-builder.md) |
| Declare `checksum()` on each migration and give it a fixed `name()`. | Without it an edit to a migration that ran goes unnoticed. A name from the class name changes under R8. | [Migrations](../migrations.md) |
| Declare models as `public static final ModelQuery<T> query`. | It is the one entry per model. No reflection, so it works on Android. | [Models](../models.md) |
| Use `tx` inside `db.transaction(tx -> ...)`. | A call on the root connection would run outside the rollback. For the query factory or schema, call `db.on(tx)`. | [Connections](../connections.md) |
| On Android, name tables and relation keys explicitly, or keep model names. | R8 can rename classes, and defaults come from class names. | [Android](../android.md) |
| Keep an Android transaction and cursor on one thread. | Android ties them to the thread that opened them. Diwan refuses a commit from another thread. | [Android](../android.md) |

## Never

| Rule | Why | Read |
|---|---|---|
| Build SQL by joining strings with user input. | It is SQL injection. Raw methods take the SQL text as given. | [Query builder](../query-builder.md) |
| Edit a migration that already ran. | The record and the database no longer match. Add a new migration. Use `repairChecksums` only after an edit you meant to make. | [Migrations](../migrations.md) |
| Call `upsert` on SQLite older than 3.24. | It throws `UnsupportedOperationException`. That means Android API 28 and 29. | [Android](../android.md) |
| Use reflection or annotations to register models, relations or migrations. | Diwan scans nothing. A name must be in `relations()`, `casts()`, `accessors()` or the migration list. | [Relations](../relations.md) |
| Call the root connection inside its own open transaction; pass `tx` instead. | Strict transactions refuse the call. It would write outside the rollback and can deadlock a small pool. | [Connections](../connections.md) |
| Log connection strings with passwords or bindings with personal data. | Logs and issues are shared. | [Report an issue](report-issue.md) |

See also [Errors and exceptions](../errors.md) for what each failure looks like.
