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

The driver classifies the failure. The classes are `DriverFailureKind.UNIQUE_VIOLATION`, `FOREIGN_KEY_VIOLATION`, `CHECK_VIOLATION`, `NOT_NULL_VIOLATION`, `CONCURRENCY`, `CANCELLED`, `CONNECTION_LOST` and `COMMIT_OUTCOME_UNKNOWN`. If `COMMIT` fails with a lost connection, the commit may have landed. Check the database before you retry or undo.

The `getCause()` of a `QueryException` is a `DriverException`. Its message has a fixed form:

```text
Database failure (SQL state unknown, vendor code 5): concurrency, SQLITE_BUSY
```

The first part always appears. The kinds the driver recognised follow after `: `, as lower-case
words, and the SQLite result code name follows them when Diwan knows the code. With neither a
kind nor a known code, the message is the first part only. The message never holds values or
database text. The Diwan error code that ends the message, described below, holds only constraint
and column names.

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

## Diwan error codes

`DriverException.error()` gives the unified error of a failure: a stable code, the constraint or
index name, and the columns involved. From a `QueryException`, reach the driver exception with
`getCause()`:

```java
try {
    db.insert("insert into users (email) values (?)", email);
} catch (QueryException e) {
    DiwanError error = ((DriverException) e.getCause()).error();
    switch (error.code()) {
        case "DWN-CST-0001":
            return "That email is already registered.";
        case "DWN-TXN-0001":
            return "Please try again.";
        default:
            throw e;
    }
}
```

| Code | Kind | Meaning |
|---|---|---|
| `DWN-CST-0001` | `UNIQUE_VIOLATION` | A unique or primary key was broken. |
| `DWN-CST-0002` | `FOREIGN_KEY_VIOLATION` | A foreign key was broken. |
| `DWN-CST-0003` | `CHECK_VIOLATION` | A check constraint was broken. |
| `DWN-CST-0004` | `NOT_NULL_VIOLATION` | A NOT NULL column received null. |
| `DWN-TXN-0001` | `CONCURRENCY` | A deadlock, a serialization failure or a busy database. Run the work again. |
| `DWN-TXN-0002` | none | Reserved for a lock wait failure. No failure reports it yet. |
| `DWN-TXN-0003` | `COMMIT_OUTCOME_UNKNOWN` | A commit failed on a lost connection, so it may have landed. Check the database. |
| `DWN-CNX-0001` | `CONNECTION_LOST` | The connection to the database was lost. |
| `DWN-QRY-0001` | `CANCELLED` | The statement was cancelled. |
| `DWN-UNK-0000` | none | The driver did not recognise the failure. |

A failure can have more than one kind. Its code is the first row of this table whose kind it has,
so the table runs in precedence order from top to bottom. For example, a failure with both
`CONCURRENCY` and `CONNECTION_LOST` reports `DWN-TXN-0001`.

Codes are public API. A code never changes its meaning, is never renumbered and is never reused. A
new failure gets a new code, and a new driver only maps its own errors to the existing codes. Write
code against `code()`, not against the message text or the vendor code.

`key()` is the name of the constraint or index, and `columns()` lists the columns involved. Both
are empty when the driver cannot give them. They hold schema names, never row values. Each driver
gives:

| Failure | PostgreSQL | SQLite |
|---|---|---|
| Unique | key: the constraint name. Columns: none, since the server does not name them for this error. | Key: none. Columns: the columns of the index. |
| Foreign key | Key: the constraint name. Columns: none. | Nothing. |
| Check | Key: the constraint name. Columns: none. | Key: the constraint name. On older SQLite, such as the one in Android 9, an unnamed check reports its expression text as the key. Name your checks. |
| Not null | Key: none. Columns: the column. | Columns: the column. |

PostgreSQL gives these values from the server's structured error fields, not from the message
text, so they do not depend on the server's language.

The message of a `DriverException` and of a `QueryException` ends with the code, the words of its
kind, and then the key and columns when they are known:

```text
... [DWN-CST-0001 unique violation: users_email_unique (email)]
```

The form is `[<code> <kind words>[: <key>][ (<columns>)]]`. Without a key the colon part is left
out, and without columns the parentheses are left out. A failure Diwan does not recognise ends with
`[DWN-UNK-0000]`. The accessors `sqlState()`, `vendorCode()`, `kinds()` and `databaseMessage()` are
unchanged.

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
| `MigrationChecksumException` | A migration that already ran was edited. Nothing ran. Restore it and change the schema with a new migration. `repairChecksums` is recovery only. |
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
