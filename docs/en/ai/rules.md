# Rules

These are the rules in `ai/AGENTS.md`, each with its reason and the page that explains it.

## Order of use

1. Models.
2. The query builder, where a model cannot express the query.
3. `*Raw` methods only for a feature Diwan lacks, with values as bindings. Report the gap: see
   [Report an issue](report-issue.md).

For the schema, use builder methods only, with the same fallback.

## Always

| Rule | Why | Read |
|---|---|---|
| Close a `QueryCursor` with try-with-resources. | A cursor not read to the end keeps its pooled connection. On PostgreSQL it leaves the session idle in a transaction. A `stream()` releases only when closed. | [Query builder](../query-builder.md) |
| Check a user-supplied sort column against an allowlist. | Column and direction names are quoted as identifiers, not bound, so the builder cannot make them safe. | [Query builder](../query-builder.md) |
| Run row locks only inside a transaction. | PostgreSQL throws `IllegalStateException` for a locked select outside one. | [Query builder](../query-builder.md) |
| Declare `checksum()` on each migration as a fixed constant set once, and give it a fixed `name()`. | It detects an accidental edit to a migration that ran; it is not a version. A name from the class name changes under R8. | [Migrations](../migrations.md) |
| Declare models as `public static final ModelQuery<T> query`. | It is the one entry per model. No reflection, so it works on Android. | [Models](../models.md) |
| Use `tx` inside `db.transaction(tx -> ...)`. | A call on the root connection would run outside the rollback. For the query factory or schema, call `db.on(tx)`. | [Connections](../connections.md) |
| On Android, name tables and relation keys explicitly, or keep model names. | R8 can rename classes, and defaults come from class names. | [Android](../android.md) |
| Keep an Android transaction and cursor on one thread. | Android ties them to the thread that opened them. Diwan refuses a commit from another thread. | [Android](../android.md) |

## Never

| Rule | Why | Read |
|---|---|---|
| Build SQL by joining strings with user input. | It is SQL injection. Raw methods take the SQL text as given. | [Query builder](../query-builder.md) |
| Edit a deployed migration or change its checksum. | The record and the database no longer match. Change the schema with a new migration. `repairChecksums` is recovery only: a local database that was never deployed, or a known accident. | [Migrations](../migrations.md) |
| Branch on the database driver in a migration to write two versions of one rule. | One migration runs on every database. Enforce a rule the builder lacks in application code, or report the gap. | [Migrations](../migrations.md) |
| Call `upsert` on SQLite older than 3.24. | It throws `UnsupportedOperationException`. That means Android API 28 and 29. | [Android](../android.md) |
| Use reflection or annotations to register models, relations or migrations. | Diwan scans nothing. A name must be in `relations()`, `casts()`, `accessors()` or the migration list. | [Relations](../relations.md) |
| Call the root connection inside its own open transaction; pass `tx` instead. | Strict transactions refuse the call. It would write outside the rollback and can deadlock a small pool. | [Connections](../connections.md) |
| Log connection strings with passwords or bindings with personal data. | Logs and issues are shared. | [Report an issue](report-issue.md) |

See also [Errors and exceptions](../errors.md) for what each failure looks like.
