# Releases

The full list of changes in each version is in the
[changelog](https://github.com/aristonis/diwan-database/blob/main/CHANGELOG.md). Each tagged version
also has a page on [GitHub Releases](https://github.com/aristonis/diwan-database/releases), with the
same notes and the release files.

## 0.1.0 (first release, not yet published)

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
