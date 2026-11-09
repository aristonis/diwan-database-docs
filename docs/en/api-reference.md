# API reference

The Javadoc for every public class of every module is one site, with search across all
modules and a version switch:

- [Newest release](../api/) · [0.3 (newest 0.3.x)](../api/0.3/) · [0.3.0](../api/0.3.0/)
- [Development build](../api/dev/), rebuilt at the end of each sprint

Each module also keeps its own Javadoc on javadoc.io, as a mirror:
`https://javadoc.io/doc/org.aristonis/diwan-database/0.3.0`. You can build the combined site
from the repository with `./gradlew apiDocs`.

All modules use the group `org.aristonis` and the version `0.3.0`. The packages sit under
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
