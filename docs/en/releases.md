# Releases

The full list of changes in each version is in the
[changelog](https://github.com/aristonis/diwan-database/blob/main/CHANGELOG.md). Each tagged version
also has a page on [GitHub Releases](https://github.com/aristonis/diwan-database/releases), with the
same notes and the release files.

## 0.4.0 (2026-11-11)

Schema, migrations and test support. Code compiled against 0.3.x must be recompiled; see the
[upgrade guide](upgrade.md). It adds:

- **Schema:** inspection (`getColumns`, `hasColumns`, `getIndexListing`, `hasIndex`), partial and
  ordered indexes, `rawIndex`, temporary tables, table comments and `foreignIdFor`. See
  [Schema](schema.md).
- **Migrations:** SQLite and Android file databases are locked while migrating. See
  [Migrations](migrations.md).
- **Testing:** rollback mode can restart PostgreSQL identities; template mode gives each test its
  own database copy; `Schema.createDatabase` and `dropDatabaseIfExists`. See [Testing](testing.md).
- **Fixes:** PostgreSQL aborted transactions fail clearly; an Android deferred-key commit rolls
  back; `OffsetTime` values; `DiwanError.table()`. See [Errors](errors.md).

## 0.3.1 (2026-11-09)

A fix release for 0.3.0. Nothing breaks.

- **SQLite and Android:** `truncate` and `RefreshDatabase` truncate mode no longer fail on a table
  whose `restrictOnDelete()` key refers to itself. See [Query builder](query-builder.md).
- **PostgreSQL:** a restrict violation (SQL state 23001) is a `ForeignKeyViolationException` that
  names its constraint. See [Errors](errors.md).

## 0.3.0 (2026-11-09)

What apps built on 0.2.0 asked for. It adds:

- **Testing:** the new `diwan-database-testing` artifact with `RefreshDatabase` (rollback or
  truncate between tests) and database assertions. See [Testing](testing.md).
- **Money:** strict `Casts.decimal(precision, scale)`, `Casts.decimalText`, and `sumDecimal`.
- **Queries:** `whereContains`, `whereStartsWith`, `whereEndsWith` for user input; lock wait limits
  per transaction, per statement and per connection; `truncate` of many tables.
- **Schema:** table and view listing, `dropAllTables`, `dropAllViews` and `Migrator.fresh()`.
- **Errors:** constraint names, columns and stable `DWN-` error codes on driver failures.

Nothing breaks; see the [upgrade guide](upgrade.md) for the one message change.

## 0.2.0 (2026-11-08)

Fixes and Laravel ports that apps built on 0.1.0 asked for. It adds:

- **Schema:** column collation with a portable binary order, and foreign key names from
  `constrained(table, column, name)`.
- **Models:** `fillAndInsert` and its siblings, `whereBelongsTo`, a keyed `pluck`, and
  `Casts.instant()`.
- **SQLite:** the `transaction_mode` option, key-level row locks as no-ops, and `busy_timeout` on
  file databases.
- **Errors:** driver failure messages that name the kind Diwan recognised.

Nothing breaks; see the [upgrade guide](upgrade.md) for the four behaviour changes.

## 0.1.0 (first release, 2026-11-07)

The first public version. It brings:

- **Connections:** nested transactions with savepoints, pretend mode, the database manager with
  configuration, and a JDBC adapter that can join a Spring transaction.
- **Query builder:** reads, writes, joins, unions, pagination, cursors, upsert and row locks, with
  Laravel's method names.
- **Schema builder:** tables, columns, indexes, foreign keys, checks and `change()`.
- **Migrations:** the migrator with batches, rollback, status, a migration lock on PostgreSQL and
  optional checksums.
- **Models:** casts, accessors, events, scopes, soft deletes and relations with eager loading, with
  no reflection.
- **Platforms:** Java 17 or later, Android 9 (API 28) or later; SQLite and PostgreSQL.

To move between versions, see the [upgrade guide](upgrade.md).
