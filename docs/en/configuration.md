# Configuration reference

Every configuration key Diwan reads, in one place. The keys are the same for Maven and Gradle: Diwan reads them at run time from a properties file, environment variables or a map, so nothing here depends on the build tool.

Put the properties file in `src/main/resources` (for example `database.properties`); a test-only file goes in `src/test/resources`. Both folders are the same for Maven and Gradle, and both end up on the classpath. Load the file with `PropertiesConfigSource.fromClasspath("database.properties")`, or from a path with `PropertiesConfigSource.of(Path.of(...))`.

A bad value throws `DatabaseConfigException`, which names the connection and the key and never prints the value, so a mistyped secret does not reach a log.

## Config sources and precedence

A `ConfigSource` answers one question: what is the value of this key. `DatabaseConfig.from(source)` reads every key below from it.

| Source | Reads from | Notes |
|---|---|---|
| `PropertiesConfigSource` | A `.properties` file: a `Path`, an `InputStream` or a classpath resource | Read as UTF-8. A missing file throws `UncheckedIOException`. |
| `EnvConfigSource` | Environment variables (`EnvConfigSource.system()`) or a map you give it (`EnvConfigSource.of(map)`) | A key is looked up as written first, then as its upper-case form with each `.` replaced by `_`. `database.connections.main.password` reads `DATABASE_CONNECTIONS_MAIN_PASSWORD`. |
| `MapConfigSource` | A `Map<String, String>` | The map is copied; a `null` key or value is refused. |
| `LayeredConfigSource` | Several sources | The first source that has the key wins: `LayeredConfigSource.of(first, second, ...)`. |

An environment layer can override a key that another source defines, but it cannot create a connection: the connection names are listed from the keys the layers contain, and environment names are upper case.

### Interpolation

Any value can read a variable:

| Form | Result |
|---|---|
| `${NAME}` | The value of `NAME`; throws if it is not set. |
| `${NAME:-fallback}` | The value of `NAME`, or `fallback` when it is not set. |
| `$${NAME}` | The literal text `${NAME}`. |

The variables come from the second argument of `DatabaseConfig.from(source, vars)`, which is the system environment when you use `from(source)`. A reference that is not closed, nested inside another, or has no name throws `DatabaseConfigException`.

### Building the manager from config

=== "Java"

    ```java
    ConfigSource source = LayeredConfigSource.of(
            EnvConfigSource.system(),                              // wins over the file
            PropertiesConfigSource.fromClasspath("database.properties"));

    DatabaseManager db = DatabaseManager.builder()
            .config(DatabaseConfig.from(source))
            .connector(new SQLiteConnector(), new PostgresConnector())
            .build();
    ```

=== "Kotlin"

    ```kotlin
    val source: ConfigSource = LayeredConfigSource.of(
        EnvConfigSource.system(),                                  // wins over the file
        PropertiesConfigSource.fromClasspath("database.properties"),
    )

    val db = DatabaseManager.builder()
        .config(DatabaseConfig.from(source))
        .connector(SQLiteConnector(), PostgresConnector())
        .build()
    ```

A map works the same way and needs no file:

=== "Java"

    ```java
    DatabaseConfig config = DatabaseConfig.from(MapConfigSource.of(Map.of(
            "database.default", "main",
            "database.connections.main.driver", "sqlite",
            "database.connections.main.database", ":memory:")));
    ```

=== "Kotlin"

    ```kotlin
    val config = DatabaseConfig.from(
        MapConfigSource.of(
            mapOf(
                "database.default" to "main",
                "database.connections.main.driver" to "sqlite",
                "database.connections.main.database" to ":memory:",
            ),
        ),
    )
    ```

## database.default

| Key | Type | Default | Read by | Meaning |
|---|---|---|---|---|
| `database.default` | text: a connection name | none, required | all drivers | The connection `manager.connection()`, `manager.query()` and `manager.schema()` use when you give no name. |

It must name a connection that is configured under `database.connections.<name>`. A missing key throws `Missing config key [database.default]`; a name with no connection throws an error that lists the known connections.

```properties
database.default=main
```

## Connection keys (all drivers)

A connection is `database.connections.<name>.<key>`. The `<name>` is the segment you choose; it is how you ask the manager for the connection and it appears in every error.

| Key | Type | Default | Read by | Meaning |
|---|---|---|---|---|
| `driver` | text | none, required | all | `sqlite`, `pgsql` or `android`: the name of a registered connector. A connection with no driver throws. |
| `url` | JDBC URL | none | `sqlite`, `pgsql` | A complete JDBC URL. When set, `host`, `port` and (for `pgsql`) `database` are not used. The URL is masked wherever the config prints. |
| `host` | text | none | `pgsql` | Server host. An IPv6 address is bracketed for you. Required for `pgsql` when there is no `url`. |
| `port` | whole number, 1 to 65535 | `5432` for `pgsql` | `pgsql` | Server port. Anything else throws `must be a whole number` or `port must be between 1 and 65535`. |
| `database` | text | none | `sqlite`, `pgsql` | For `pgsql`, the database name (required without `url`). For `sqlite`, a file path or `:memory:` (required without `url`). |
| `username` | text | none | `sqlite`, `pgsql` | Login name, passed to the JDBC driver. |
| `password` | text | none | `sqlite`, `pgsql` | Password, passed to the JDBC driver. Masked as `***` wherever the config prints. |
| `prefix` | text | empty | all | Added in front of every table name. ASCII letters, digits and underscores only. |
| `strict_transactions` | `true` or `false` (any case) | `true` | all | Refuses a call from a thread that is inside a transaction it opened but goes through the root connection. Switch it off only for code that writes outside the transaction on purpose. Any other value throws `must be true or false`. |

Any other key directly under a connection is kept as a text option for the connector; the sections below list the ones the connectors read. An unknown option is ignored.

```properties
database.connections.main.driver=pgsql
database.connections.main.host=${DB_HOST:-localhost}
database.connections.main.port=5432
database.connections.main.database=shop
database.connections.main.username=shop
database.connections.main.password=${DB_PASSWORD}
database.connections.main.prefix=app_
```

## SQLite

Driver `sqlite`. Options are added to the JDBC URL, whether it comes from `url` or from `database`. A setting already written in the `url` itself is left as it is.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `database` | file path or `:memory:` | none | A file opens that database. `:memory:` (also an empty target, `file::memory:` or `mode=memory`) opens one private in-memory database that lives as long as the connection. Without `url` and `database` the connection throws `needs a database path or :memory:`. |
| `foreign_keys` | `true`/`false`, `1`/`0`, `on`/`off` | `true` | Turns on foreign key enforcement for every session. Any other value throws `must be true or false`. |
| `busy_timeout` | whole number of milliseconds, 0 or more | `30000` | How long a session waits for a lock before it fails. A negative or non-numeric value throws. |
| `lock_wait` | duration: `5s`, `500ms` or digits as milliseconds | none | The same wait as `busy_timeout`, written as a duration. When both are set they must give the same number of milliseconds, or the connection throws. Must be greater than 0 and at most 2147483647 ms. |
| `transaction_mode` | `deferred`, `immediate`, `exclusive` (any case) | the SQLite driver default, `deferred` | The kind of transaction `BEGIN` starts. Any other value throws `must be deferred, immediate or exclusive`. |

```properties
database.connections.main.driver=sqlite
database.connections.main.database=/var/lib/shop/shop.db
database.connections.main.foreign_keys=true
database.connections.main.lock_wait=5s
database.connections.main.transaction_mode=immediate
```

## PostgreSQL

Driver `pgsql`. See also [connection keys](#connection-keys-all-drivers) for `host`, `port`, `database`, `username` and `password`.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `sslmode` | text | none | Added to the URL as the `sslmode` parameter (`disable`, `require`, `verify-full` and so on, as the PostgreSQL JDBC driver defines them). Skipped when the `url` already has it or the value is blank. |
| `search_path` | text | none | Added to the URL as `currentSchema`: the schema the session uses first. Skipped when the `url` already has `currentSchema`. |
| `schema` | text | none | The same as `search_path`; used only when `search_path` is not set. |
| `lock_wait` | duration: `5s`, `500ms` or digits as milliseconds | none | Adds `-c lock_timeout=<ms>` to the URL `options` parameter: how long a statement waits for a lock. Must be greater than 0 and at most 2147483647 ms, otherwise the connection throws. |
| `timezone` | text | none | Sets the time zone of every session, as Laravel's `timezone` option does: an IANA name such as `UTC` or an offset such as `+03:00`. Diwan runs `SET TIME ZONE '<value>'` on each connection it hands out, whether the data source is built from the settings or supplied. A pool that resets sessions with `DISCARD ALL` or `RESET ALL` undoes it: set the zone in the pool's init SQL or on the server instead. Only letters, digits and `/ _ + - :` are accepted, otherwise the connection throws. Off by default. |

With no `timezone`, PostgreSQL converts a value with the session zone, which follows the JVM. Store an `Instant` in a `timestamptz` column, which keeps the moment whatever the zone. To put `Instant` values into plain `timestamp` columns, set `timezone=UTC`: without it the stored wall time shifts by the JVM or session zone. Setting `timezone` also changes how the server prints `now()` and what a `timestamp` default holds.

A `pgsql` connection also gets a migration lock, a session advisory lock that keeps two processes from migrating one database at once. It needs no key.

```properties
database.connections.main.driver=pgsql
database.connections.main.url=jdbc:postgresql://db.internal:5432/shop
database.connections.main.sslmode=require
database.connections.main.search_path=app
database.connections.main.lock_wait=10s
database.connections.main.timezone=UTC
```

## Android

Driver `android`. The database itself comes from the `SQLiteOpenHelper` you give `AndroidConnector.of(...)` in code, so the connection keys `url`, `host`, `port`, `database`, `username` and `password` are not read. `prefix` and `strict_transactions` still apply. See [Android](android.md).

| Key | Type | Default | Meaning |
|---|---|---|---|
| `lock_wait` | duration: `5s`, `500ms` or digits as milliseconds | unset: the database keeps its own timeout | How long a session waits for a lock. Must be greater than 0, otherwise the connection throws. |
| `transaction_mode` | `immediate` or `exclusive` (any case) | `exclusive` | `immediate` uses a non-exclusive transaction. `deferred` throws (Android cannot begin one) and so does any other value. |

```properties
database.connections.app.driver=android
database.connections.app.lock_wait=3s
database.connections.app.transaction_mode=immediate
```

## Settings in code

These are not read from a file. You set them on the builder when you create a connection yourself with `Connection.builder()`; a connector built through `DatabaseManager` sets `name`, `prefix` and `strictTransactions` from the config for you.

| Setting | Type | Default | Meaning |
|---|---|---|---|
| `name(...)` | text | none, required | The connection name shown in every `QueryException`. A blank name throws. |
| `tablePrefix(...)` | text | empty | Same as the `prefix` key. Anything but ASCII letters, digits and underscores throws `IllegalArgumentException`. |
| `strictTransactions(...)` | `boolean` | `true` | Same as the `strict_transactions` key. |
| `showBindingsInErrors(...)` | `boolean` | `false` | Appends binding values to `QueryException` messages. Bindings can hold personal data, so it is off; the exception carries them in `getBindings()` either way. |
| `onCleanupFailure(...)` | `Consumer<Throwable>` | logs a warning through `java.util.logging` | Receives a failure to give a session back after the work already succeeded. Such a failure never fails the call. May be called from any thread. |
| `queryLogLimit(...)` | whole number, 1 or more | `1000` | How many statements the query log keeps once `enableQueryLog()` is on; the oldest entry is dropped when it is full. |
| `listener(...)` | `ConnectionListener` | none | Adds a listener for query and transaction events; call it once per listener. |
| `DatabaseManager.builder().dataSource(name, supplier)` | `Supplier<DataSource>` | none | Gives a connection your own data source (for example a pool) instead of the JDBC URL from the config. |

=== "Java"

    ```java
    Connection connection = Connection.builder()
            .name("main")
            .dataSource(dataSource)
            .tablePrefix("app_")
            .strictTransactions(true)
            .showBindingsInErrors(false)
            .onCleanupFailure(e -> log.warn("cleanup failed", e))
            .queryLogLimit(500)
            .build();
    ```

=== "Kotlin"

    ```kotlin
    val connection = Connection.builder()
        .name("main")
        .dataSource(dataSource)
        .tablePrefix("app_")
        .strictTransactions(true)
        .showBindingsInErrors(false)
        .onCleanupFailure { e -> log.warn("cleanup failed", e) }
        .queryLogLimit(500)
        .build()
    ```

## Migrations

The migrations settings are set in code on the `Migrator.Builder`; no properties key exists for them. `manager.migrator(name)` already adds the connection's own lock when its connector has one (`pgsql` does; `sqlite` and `android` have none).

| Setting | Type | Default | Meaning |
|---|---|---|---|
| `table(...)` | text | `migrations` | The migrations table, without the connection `prefix`. The prefixed name must be lowercase letters, digits and underscores, start with a letter or underscore, and be at most 63 characters, otherwise `build()` throws. |
| `lock(...)` | `MigrationLock` | `MigrationLock.NONE` | The lock taken around every run, rollback and reset. |
| `allowMissingOnRollback()` | none | off: rollback and reset are refused when a record has no migration | Lets them go ahead, as Laravel does, and reports unknown records as `NOT_FOUND`. |

=== "Java"

    ```java
    Migrator migrator = db.migrator("main")
            .table("schema_history")
            .allowMissingOnRollback()
            .migrations(migrations)
            .build();
    ```

=== "Kotlin"

    ```kotlin
    val migrator = db.migrator("main")
        .table("schema_history")
        .allowMissingOnRollback()
        .migrations(migrations)
        .build()
    ```

## Full example

```properties
# src/main/resources/database.properties
database.default=main

# PostgreSQL, the main database
database.connections.main.driver=pgsql
database.connections.main.host=${DB_HOST:-localhost}
database.connections.main.port=5432
database.connections.main.database=shop
database.connections.main.username=shop
database.connections.main.password=${DB_PASSWORD}
database.connections.main.prefix=app_
database.connections.main.strict_transactions=true
database.connections.main.sslmode=require
database.connections.main.search_path=app
database.connections.main.lock_wait=10s

# SQLite, a local cache
database.connections.cache.driver=sqlite
database.connections.cache.database=/var/lib/shop/cache.db
database.connections.cache.foreign_keys=true
database.connections.cache.busy_timeout=5000
database.connections.cache.transaction_mode=immediate

# SQLite, in memory (tests)
database.connections.test.driver=sqlite
database.connections.test.database=:memory:

# Android (the helper is given in code)
database.connections.app.driver=android
database.connections.app.lock_wait=3s
database.connections.app.transaction_mode=immediate
```

<!--
Acceptance map: where the code reads each key.
database.default: diwan-database/core/src/main/java/org/aristonis/diwan/database/manager/DatabaseConfig.java:33,80,248-255
database.connections.<name>: DatabaseConfig.java:34,85,92
driver: DatabaseConfig.java:106; ConnectionConfig.java:build() requires it
url: DatabaseConfig.java:109; sqlite/SQLiteConnector.java:133; pgsql/PostgresConnector.java:102
host: DatabaseConfig.java:112; PostgresConnector.java:134
port: DatabaseConfig.java:115,parsePort; ConnectionConfig.java:25,294; PostgresConnector.java:43,142
database: DatabaseConfig.java:118; SQLiteConnector.java:137; PostgresConnector.java:136
username: DatabaseConfig.java:121; SQLiteConnector.java:211; PostgresConnector.java:96
password: DatabaseConfig.java:124; SQLiteConnector.java:211; PostgresConnector.java:97
prefix: DatabaseConfig.java:127; SQLiteConnector.java:99; PostgresConnector.java:68; android/AndroidConnector.java:95
strict_transactions: DatabaseConfig.java:35,130,parseBoolean; SQLiteConnector.java:99; PostgresConnector.java:68; AndroidConnector.java:95
foreign_keys: sqlite/SQLiteConnector.java:63,177-196
busy_timeout: SQLiteConnector.java:64,66,163-168,226-256
lock_wait: config/LockWaitOption.java:KEY,parseMillis; SQLiteConnector.java:164,228; PostgresConnector.java:112; AndroidConnector.java:100
transaction_mode: SQLiteConnector.java:65,150-161; AndroidConnector.java:46,104-121
sslmode: PostgresConnector.java:103
search_path: PostgresConnector.java:104
timezone: PostgresConnector.java:132
schema: PostgresConnector.java:106
${...} interpolation: config/ConfigInterpolator.java:resolve,substitute
env name mapping: config/EnvConfigSource.java:65
layered first-wins: config/LayeredConfigSource.java:get
Settings in code: core/.../database/ConnectionBuilder.java:61 (name),126 (tablePrefix),143 (showBindingsInErrors),158 (strictTransactions),173 (onCleanupFailure),187 (listener),201 (queryLogLimit); event/ConnectionEvents.java:41 (default 1000); manager/DatabaseManager.java:495 (dataSource)
Migrations: migrations/Migrator.java:731 (table),744 (lock),770 (allowMissingOnRollback); migrations/DatabaseMigrationRepository.java:38 (DEFAULT_TABLE),68; manager/Connector.java:71 (lock); manager/DatabaseManager.java:155-162
-->
