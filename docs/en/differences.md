# Differences from Laravel

Diwan keeps Laravel's method names where they read well in Java. This page lists the places where
it behaves differently on purpose. Each row is a choice, not a missing feature.

## Language and return shapes

| Laravel | Diwan |
|---|---|
| `null` or `false` for "not found" | `Optional` from `find`, `first`, `selectOne` and `scalar`; `findOrFail` throws |
| PHP dates and format letters (`Y-m-d`) | `java.time` and `DateTimeFormatter` patterns (`yyyy-MM-dd`) |
| Rows are arrays | Rows are unmodifiable maps in select order |
| `getColumns` returns arrays | `getColumns` returns typed `ColumnInfo` objects |
| Lazy loading works from any attribute read | `getAttribute("posts")` never loads a relation; use `related` or `relatedMany` |
| Relations found by method name | A typed method plus a `RelationMap` entry, so R8 cannot break it |
| Morph and global-scope names guessed from the call stack or a closure | You pass the name |

## Connections and queries

| Laravel | Diwan |
|---|---|
| A transaction callback can use any connection | Strict transactions: the outer connection refuses calls from inside its own transaction; use the `tx` you are given |
| Binding values appear in error messages | Hidden by default; turn on `showBindingsInErrors` |
| `upsert` with an empty update list runs a plain insert | Leaves a conflicting row as it is |
| `lock('lock in share mode')` raw string | Typed `LockStrength` and `LockWait` only |
| `paginate` counts every row of a `distinct` query | Counts distinct rows |
| `cursor()` returns a lazy collection | `QueryCursor`, which you close; an unclosed one keeps its connection |
| Cursor and page tokens are your problem | Tokens are not signed; a forged one cannot inject SQL but can ask for other allowed rows |
| `chunk` on a growing table | Same offset paging, so use `chunkById` |
| A failed statement in a PostgreSQL transaction gives server error 25P02 on the next one | Diwan refuses the next statement, commit or savepoint release itself, with a message that says to roll back |
| `whereRaw('? is null', ...)` with a bare placeholder | On PostgreSQL a bare `? is null` needs a cast, such as `?::text is null`, because the server cannot tell the type of the placeholder |
| Reading a numeric `NaN` is not handled | A PostgreSQL numeric column holding NaN or Infinity fails with an error that names the column; `float` and `double` columns return NaN |

## Models

| Laravel | Diwan |
|---|---|
| Bad stored data reads as `null`, `0` or `true` | `InvalidCastException` naming the model, key and cast |
| JSON and float dirty checks compare loosely | JSON compares by structure, floats within 4 ULP, moments as instants |
| `delete()` on a model not in the database | Returns `false` |
| `increment` on a model not in the database | Refused |
| `saveOrFail` | Saves in its own transaction and throws when a non-incrementing model has nothing to insert |
| A write through a relation from a parent with no key writes a null key | `IllegalStateException` before any SQL |
| Eager loads read null keys as `0` | Null keys are dropped |
| `with` on the same relation twice keeps the last constraint | Runs both |
| An eager constraint may use `limit` | Refused, since it would cut all parents together |
| A listener returning `true` silences later listeners | Only `false` halts |
| `withoutEvents` mutes every thread | Mutes the calling thread only, and the model's own hooks still run |
| Global scopes are inherited by subclasses | Each class has the scopes registered on its own `ModelQuery` |
| `forceDelete()` on a builder skips every global scope | Skips only the soft-delete scope |
| The morph map is optional | Required unless you call `requireMorphMap(false)` |
| `oldestOfMany` can return the highest key among ties | Returns the lowest |

## Schema inspection

| Laravel | Diwan |
|---|---|
| `getColumns` lists the hidden columns of a virtual table | Left out |
| `hasIndex` takes an index method type such as `btree` | No method type: SQLite has none. An `IndexType` enum (`PRIMARY`, `UNIQUE`) filters instead |

## Schema changes

| Laravel | Diwan |
|---|---|
| `foreignIdFor($model)` takes a model or a class name | `foreignIdFor` takes a `ForeignKeySource`; `ModelKeys.of(User.class)` builds one from a model |
| `foreignIdFor` on a model with a string key makes a `uuid` column | `ModelKeys` refuses a key that is not an integer, UUID or ULID with `IllegalArgumentException`; a key source can still say what it needs |
| `comment()` on a table writes a table comment on PostgreSQL and MySQL; the SQLite grammar has no code for it | PostgreSQL writes it. SQLite and Android skip it without an error, as Laravel does. MySQL is not supported |
| `temporary()` works on SQLite and PostgreSQL; the SQLite grammar has no check for a temporary table on a change | `schema.table` on a temporary table works on SQLite for plain additions; a change that needs a table rebuild is refused with `IllegalStateException` |
| `createDatabase($name)` on PostgreSQL adds `encoding` from the connection's `charset` setting when it is set | No encoding clause. The new database takes the server's default encoding, or its template's encoding when it copies one |
| `createDatabase($name)` on SQLite writes an empty file, which replaces a file that exists | Fails when the file exists, and never overwrites it |
| `dropDatabaseIfExists($name)` on SQLite returns `true` when no file exists, and deletes only the main file | Returns `false` when no file exists, and also deletes the `-wal`, `-shm` and `-journal` files |

## Diwan additions

Laravel has none of these:

- Partial indexes: `where`, `whereNull` and `whereNotNull` on an index.
- Index order and collation: `asc`, `desc` and `collate` on an index.
- `DiwanError.table()`, the table a failure concerns.
- `QueryFactory.restartIdentities(tables)` and `RefreshDatabase.rollback(...).restartingIdentities()`, which set PostgreSQL identity and `serial` counters back so rollback-mode tests see the same ids on every run. The Laravel database source has no per-test reset: its only `setval` sets a start value when a table is created.
- `createDatabase(name, template)` and `createDatabase(name, template, CopyStrategy)`, which copy a database. `CopyStrategy` (`FILE_COPY` or `WAL_LOG`) picks how PostgreSQL 15 and later copy it. Laravel has no template argument.
- `dropDatabaseIfExists(name, force)`, which ends the sessions on the database first, on PostgreSQL 13 and later. Laravel has no force.
- `RefreshDatabase.template(...)`, a test mode in which each test gets its own copy of a migrated template, so tests may commit and run in parallel. Laravel has no test mode of this kind.

## Not in 0.2.0

- Custom event classes, string event names and wildcard listeners.
- `ObservedBy`; register an observer with `observe`.
- MySQL, SQL Server and other databases. SQLite, PostgreSQL and Android are supported.

See also [Models](models.md), [Relations](relations.md) and [Query builder](query-builder.md).
