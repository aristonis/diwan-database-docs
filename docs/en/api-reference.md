# API reference

The Javadoc of each module, version 0.3.1, on javadoc.io:

[`diwan-database`](https://javadoc.io/doc/org.aristonis/diwan-database/0.3.1) · [`diwan-database-sqlite`](https://javadoc.io/doc/org.aristonis/diwan-database-sqlite/0.3.1) · [`diwan-database-pgsql`](https://javadoc.io/doc/org.aristonis/diwan-database-pgsql/0.3.1) · [`diwan-database-android`](https://javadoc.io/doc/org.aristonis/diwan-database-android/0.3.1) · [`diwan-database-testing`](https://javadoc.io/doc/org.aristonis/diwan-database-testing/0.3.1) · [`diwan-database-eloquent`](https://javadoc.io/doc/org.aristonis/diwan-database-eloquent/0.3.1)

You can also build one combined site for every module, with search across them, from the
repository with `./gradlew apiDocs`.

All modules use the group `org.aristonis` and the version `0.3.1`. The packages sit under
`org.aristonis.diwan.database`.

| Module (artifact) | Add it when | Main entry classes |
|---|---|---|
| `diwan-database` | always | `Connection`, `TransactionScope`, `Migrator`, `Migration`, `Schema`, `Blueprint`, `QueryFactory`, `Builder`, `QueryCursor`, `DatabaseManager` |
| `diwan-database-sqlite` | you use SQLite or Android | `SQLiteSchema.of(db)`, `SQLiteQuery.of(db)` |
| `diwan-database-pgsql` | you use PostgreSQL | `PostgresSchema.of(db)`, `PostgresQuery.of(db)`, `PostgresMigrationLock` |
| `diwan-database-android` | you run on Android | `AndroidSqliteDriver`, `AndroidConnector` |
| `diwan-database-testing` | your tests use the database (test scope) | `RefreshDatabase`, `DatabaseAssertions` |
| `diwan-database-eloquent` | you use models | `Model`, `ModelQuery`, `EloquentBuilder`, `ModelCollection`, `Scope`, `ModelObserver`, `Casts`, `RelationMap` |

## Packages

| Package | Contents |
|---|---|
| `org.aristonis.diwan.database` | `Connection`, `ConnectionBuilder`, `TransactionScope`, `LoggedQuery`, `QueryException` |
| `...database.driver` and `...database.jdbc` | the driver interface and the JDBC adapter |
| `...database.schema` | `Schema`, `Blueprint`, `ColumnDefinition`, `ForeignKeyDefinition` |
| `...database.migrations` | `Migration`, `Migrator`, `MigrationChecksum`, `MigrationResult` |
| `...database.query` | `QueryFactory`, `Builder`, `JoinClause`, `LengthAwarePage`, `SimplePage`, `CursorPage`, `Cursor` |
| `...database.manager` and `...database.config` | `DatabaseManager`, `DatabaseConfig`, config sources |
| `...database.eloquent` | `Model`, `ModelQuery`, `EloquentBuilder`, `ModelCollection`, `ModelPage` |
| `...database.eloquent.casts` | `Cast`, `Casts`, `CastMap` |
| `...database.eloquent.json` | `JsonCodec` |
| `...database.eloquent.relations` | `HasOne`, `HasMany`, `BelongsTo`, `BelongsToMany`, `HasManyThrough`, `MorphTo`, `Pivot`, `MorphMap` |

Classes in packages named `internal` are not part of the public API.

## Where each topic is documented

- Connection and transactions: [Connections](connections.md)
- Queries: [Query builder](query-builder.md)
- Tables: [Schema builder](schema.md) and [Migrations](migrations.md)
- Models: [Models](models.md) and [Relations](relations.md)
- Failures: [Errors](errors.md)
