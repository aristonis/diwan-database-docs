# Diwan Database

Diwan Database is a Java port of Laravel's database layer (`illuminate/database`). It keeps Laravel's method names where they read well in Java: `where`, `orderBy`, `firstOrCreate`, `migrate`. Where PHP shaped Laravel's choices, it uses Java instead: `Optional`, `java.time`, try-with-resources and unchecked exceptions.

You write SQL, query builder calls, migrations and models. The library sends them to SQLite or PostgreSQL, on a server, on the desktop or on Android.

## A first look

Your code asks a `DatabaseManager` for what it needs. The driver is a configuration value, so moving from SQLite to PostgreSQL changes configuration, not code.

```java
QueryFactory db = manager.query();      // from the connection's configuration, no driver class in your code
db.table("users").insert(Map.of("email", "ada@example.com"));
List<Map<String, Object>> rows = db.table("users").orderByDesc("id").limit(10).get();
```

[Getting started](getting-started.md) builds the manager.

## Modules

| Module | Coordinates | What it gives you |
|---|---|---|
| Core | `org.aristonis:diwan-database:0.1.0` | `Connection`, transactions, `DatabaseManager`, the query builder, the schema builder, migrations. No runtime dependency. |
| SQLite | `org.aristonis:diwan-database-sqlite:0.1.0` | The SQLite query and schema grammars. |
| PostgreSQL | `org.aristonis:diwan-database-pgsql:0.1.0` | The PostgreSQL grammars and a migration lock. You add the PostgreSQL JDBC driver yourself. |
| Eloquent | `org.aristonis:diwan-database-eloquent:0.1.0` | Models, relations, eager loading, casts, scopes, soft deletes, model events. |
| Android | `org.aristonis:diwan-database-android:0.1.0` | A driver over Android's own `SQLiteDatabase`. |

## Platforms and databases

- Java 17 or later. The JAR is plain Java 17 bytecode and is tested on JDK 17, 21 and 25.
- Android 9 (API 28) or later, through the Android module. See [Android](android.md).
- Spring and other containers, through a connection provider that reports the container's transaction. Diwan then nests inside it with savepoints and never commits it.
- Databases: SQLite and PostgreSQL. MySQL and SQL Server are not supported.

Version 0.1.0 is not published yet. Build it locally with `./gradlew check` until it is.

## Security

Report a vulnerability privately, through [GitHub private vulnerability reporting](https://github.com/aristonis/diwan-database/security/advisories/new). Never open a public issue for it.

## Where to go next

| You want to | Read |
|---|---|
| Install the library and run a first query | [Getting started](getting-started.md) |
| Open connections, run transactions, listen to queries, set up a pool | [Connections and transactions](connections.md) |
| Read and write rows with `where`, `join`, `paginate` | [Query builder](query-builder.md) |
| Create and change tables | [Schema](schema.md) |
| Version your schema | [Migrations](migrations.md) |
| Work with classes instead of rows | [Models](models.md) and [Relations](relations.md) |
| Run on a phone | [Android](android.md) |
| Know where Diwan differs from Laravel | [Differences from Laravel](differences.md) |
| Catch and understand failures | [Errors](errors.md) |
| Look up a class or method | [API reference](api.md) |
| Move between versions | [Upgrade](upgrade.md) |
| Decode a term | [Glossary](glossary.md) |
