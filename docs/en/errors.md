# Errors

Every exception in Diwan Database is unchecked. Database failures arrive as `QueryException` or one of its subclasses. The other areas throw their own types, listed below.

## Where they live

| Package | Holds |
|---|---|
| `org.aristonis.diwan.database.exception` | Every core exception, and their parent `DatabaseException`. |
| `org.aristonis.diwan.database.eloquent.exception` | Every model exception, and their parent `EloquentException` (which extends `DatabaseException`). |

Catch `DatabaseException` to handle any failure from the database, a driver, a migration or a model in one place. Mistakes in your own code, such as a wrong argument or a call in the wrong state, are reported with the JDK's `IllegalArgumentException` and `IllegalStateException` instead, so `DatabaseException` does not catch them.

## QueryException

A `QueryException` means the database refused a statement. It carries:

| Method | Returns |
|---|---|
| `getConnectionName()` | The connection the statement ran on. |
| `getSql()` | The SQL text. |
| `getBindings()` | The values you passed, as a list. |
| `sqlState()` | An `Optional<String>` with the SQL state, empty when the database gave none. |
| `vendorCode()` | The database's own error code. |
| `isConcurrencyFailure()` | `true` for a deadlock, serialization failure or busy database. |
| `getCause()` | The `DriverException` from the driver. |

### Kinds

| Type | When | What you do |
|---|---|---|
| `UniqueConstraintViolationException` | A unique or primary key was broken. | Report a duplicate to the user, or use `upsert`. |
| `ForeignKeyViolationException` | A foreign key was broken. | Insert the parent first, or delete the children. |
| `QueryException` with `isConcurrencyFailure()` | Deadlock, serialization failure or busy database. | Run the work again with `transaction(callback, attempts)`. |
| `QueryException` | Anything else the database refused: bad SQL, a missing table, a lost connection. | Read `sqlState()` and `getCause()`. |

The subclasses extend `QueryException`, so one `catch` covers all of them. Catch the specific type first:

```java
try {
    db.insert("insert into users (email) values (?)", email);
} catch (UniqueConstraintViolationException e) {
    return "That email is already registered.";
} catch (QueryException e) {
    LOG.warning("insert failed on " + e.getConnectionName() + ", state " + e.sqlState().orElse("unknown"));
    throw e;
}
```

The driver classifies the failure. The classes are `DriverFailureKind.UNIQUE_VIOLATION`, `FOREIGN_KEY_VIOLATION`, `CONCURRENCY`, `CANCELLED`, `CONNECTION_LOST` and `COMMIT_OUTCOME_UNKNOWN`. If `COMMIT` fails with a lost connection, the commit may have landed. Check the database before you retry or undo.

## What messages never contain

The message of a `QueryException` reads like this:

```text
SQL: insert into users (email) values (?) (Connection: main, SQL state 23505, vendor code 0)
```

By default it holds no binding values and no database error text, because both can hold personal data. That text stays in `getCause()`.

- `showBindingsInErrors(true)` on the connection builder adds the values and the database's reason to the message. Use it in development.
- `getBindings()` carries the values either way. Do not log it where personal data must not go.
- A log line that prints the whole cause chain shows the database's text whatever the setting. Send `getMessage()` to shared logs.
- Line breaks and control characters in the SQL are escaped, long SQL is cut after 1000 characters, and a `byte[]` shows as `<n bytes>`.
- Passwords never appear. `ConnectionConfig` prints `***`, and `DatabaseConfigException` names the key but never the value.
- Events carry raw values. Call `redacted()` on a `QueryExecuted` or `QueryFailed` before you log it.
- A serialized `QueryException` leaves out hidden bindings.

## Exceptions by area

### Connection and manager

| Exception | Meaning |
|---|---|
| `IllegalStateException` (strict transactions) | The root connection was used from inside its own transaction. Use `tx`, or build with `strictTransactions(false)`. |
| `MultipleColumnsSelectedException` | `scalar` read a row with several columns. |
| `ListenerFailedException` | A listener threw after the statement succeeded. The statement is not undone. The cause is the first listener failure. |
| `DatabaseConfigException` | A bad configuration. Extends `IllegalArgumentException`. |
| `IllegalArgumentException` | An unknown connection name, a driver with no connector, or `attempts` below 1. |
| `IllegalStateException` | The manager is closed, or a listener asked for the connection being built. |

### Schema and migrations

| Exception | Meaning |
|---|---|
| `MigrationFailedException` | A migration failed. The cause is the real failure. `phase()` says whether the migration or only its record failed. Earlier migrations stay applied. |
| `MigrationChecksumException` | A migration that already ran was edited. Nothing ran. Restore it, or accept the change with `repairChecksums`. |
| `MissingMigrationsException` | A rollback or reset would reach records whose migrations the migrator does not have. Deploy the newer code, or build with `allowMissingOnRollback()`. |
| `ForeignKeysOffRequiredException` | A SQLite table rebuild needs foreign keys off. The migrator handles it. Elsewhere, use `Schema.withoutForeignKeyConstraints`. |
| `ForeignKeyCheckException` | Rows broke a foreign key after a table rebuild. The change is undone. The message names tables and counts, never row values. |

### Models

| Exception | Meaning |
|---|---|
| `ModelNotFoundException` | `findOrFail` and similar found no row. Laravel's message: `No query results for model [app.User] 1`. |
| `MultipleRecordsFoundException` | `sole()` matched more than one row. |
| `MassAssignmentException` | `fill` named a key the model does not allow. |
| `RelationNotFoundException` | A relation name the class does not have. The message lists known names. |
| `LazyLoadingViolationException` | A relation was lazy loaded while `preventLazyLoading(true)` is set. |
| `InvalidCastException`, `InvalidRelationException`, `JsonException` | A cast, a relation definition or JSON handling failed. |

The messages of the model exceptions name the class and the relation, never an attribute value.

## Suppressed exceptions

Diwan never swallows a failure. When a second failure happens while handling the first, such as a rollback that fails or a listener that throws, it is added to the first with `addSuppressed`. Print the full stack trace or read `getSuppressed()` to see it.
