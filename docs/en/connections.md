# Connections and transactions

A `Connection` sends SQL to one database. A `DatabaseManager` builds named connections from configuration. Both are safe to share between threads.

## DatabaseManager

The manager reads configuration through a `ConfigSource` and builds each connection the first time you ask for it, once per name even under concurrent calls.

Your code asks the manager for what it needs and never names a driver class: `manager.query()` returns the `QueryFactory`, `manager.schema()` the `Schema` and `manager.migrator(name)` a `Migrator.Builder`, all built from the connection's `driver` setting. Switching from SQLite to PostgreSQL is a configuration change.

```properties
# database.properties
database.default=main
database.connections.main.driver=pgsql
database.connections.main.host=db.internal
database.connections.main.database=shop
database.connections.main.username=shop
database.connections.main.password=${DB_PASSWORD}
database.connections.main.sslmode=require
database.connections.cache.driver=sqlite
database.connections.cache.database=/var/lib/shop/cache.db
```

```java
ConfigSource source = LayeredConfigSource.of(
        EnvConfigSource.system(),                         // wins over the file
        PropertiesConfigSource.of(Path.of("database.properties")));

DatabaseManager db = DatabaseManager.builder()
        .config(DatabaseConfig.from(source))
        .connector(new PostgresConnector(), new SQLiteConnector())
        .build();

QueryFactory shop = db.query();          // default connection
Schema cache = db.schema("cache");       // built on first use
```

Other accessors: `connection(name)`, `migrator(name)` (a `Migrator.Builder`), `usingConnection(name, work)`, `getConnections()`, `hasConnection(name)`, `setDefaultConnection(name)`. An unknown name or a driver with no connector throws `IllegalArgumentException` that lists the known names.

### Configuration keys

All keys start with `database.`. A connection is `database.connections.<name>.<key>`.

| Key | Meaning |
|---|---|
| `database.default` | Name of the default connection. Required. |
| `driver` | `sqlite`, `pgsql` or `android`: a registered connector. |
| `url` | A complete JDBC URL. Replaces `host`, `port` and `database`. |
| `host`, `port`, `database` | `port` defaults to 5432 for `pgsql`. For `sqlite`, `database` is a file path or `:memory:`. |
| `username`, `password` | The password is masked wherever the configuration prints. |
| `prefix` | Table prefix, empty by default. |
| `strict_transactions` | `true` by default. |
| `sqlite`: `foreign_keys`, `busy_timeout` | Foreign keys on by default. `busy_timeout` is how long a second in-memory session waits, 30000 ms by default. |
| `pgsql`: `sslmode`, `search_path` (or `schema`) | Passed to the URL as `sslmode` and `currentSchema`. |

Any other key is kept as a string option for the connector. A value can read the environment: `${DB_PASSWORD}` fails if unset, `${DB_HOST:-localhost}` falls back, `$${X}` stays literal. A bad configuration throws `DatabaseConfigException`, which names the connection and key but never the value.

Sources: `MapConfigSource`, `PropertiesConfigSource`, `EnvConfigSource` (`database.connections.main.password` reads `DATABASE_CONNECTIONS_MAIN_PASSWORD`) and `LayeredConfigSource` (the first source with the key wins). An environment layer overrides a key but cannot create a connection.

On Android, build the configuration in code:

```java
DatabaseConfig config = DatabaseConfig.builder()
        .defaultConnection("app")
        .connection(ConnectionConfig.builder("app").driver("android").build())
        .build();

DatabaseManager db = DatabaseManager.builder()
        .config(config)
        .connector(AndroidConnector.of(() -> helper, SQLiteQuery::of, SQLiteSchema::of))
        .build();
```

### Lifecycle

- `purge(name)` and `disconnect(name)` drop the built connection and close what it owns. The next call builds a new one.
- `reconnect(name)` purges and returns a new `Connection`.
- `close()` retires everything. Afterwards every call throws `IllegalStateException`. Use the manager in try-with-resources in tests.
- Do not purge a connection that is running a statement.
- An in-memory SQLite database uses one real connection, lent to one session at a time. A second session on the same thread waits the full `busy_timeout` and then fails.

## Without a manager

```java
Connection db = Connection.builder()
        .name("main")
        .dataSource(dataSource)        // any javax.sql.DataSource, pooled or not
        .build();
```

| Builder method | Effect |
|---|---|
| `name(String)` | The name shown in errors and events. |
| `dataSource(DataSource)` | The JDBC source. Use `driver(Driver)` instead for Android, or `connectionProvider(...)` inside Spring. |
| `tablePrefix(String)` | Letters, digits and underscores only. Raw SQL is never rewritten. |
| `showBindingsInErrors(boolean)` | Off by default. See [Errors](errors.md). |
| `strictTransactions(boolean)` | On by default. See below. |
| `listener(ConnectionListener)` | Attaches a listener. |
| `queryLogLimit(int)` | Size of the query log, 1000 by default. |
| `onCleanupFailure(Consumer<Throwable>)` | Receives a failure to return a connection after the work succeeded. The default logs a warning. |

The methods you call on it:

| You want to | Call |
|---|---|
| Run any statement | `statement`, `unprepared` (raw SQL, no bindings) |
| Change rows and get a count | `insert`, `update`, `delete`, `affectingStatement` |
| Read rows | `select` (all rows), `selectOne` (first row or empty), `scalar` (one value or empty), `cursor` (stream rows) |
| Group work | `transaction(callback)`, `beginTransaction()` |
| See SQL without running it | `pretend(callback)` |

Each call outside a transaction borrows a pooled connection and returns it before the call ends. `scalar` throws `MultipleColumnsSelectedException` when the row has more than one column.

To get the factories from a `Connection` you built yourself, use the grammar module directly: `SQLiteQuery.of(db)` and `SQLiteSchema.of(db)`, or `PostgresQuery.of(db)` and `PostgresSchema.of(db)`.

## Transactions

```java
int removed = db.transaction(tx -> {
    tx.update("update users set email = ? where id = ?", "ada@example.org", 1);
    return tx.delete("delete from users where email like ?", "%@spam.test");
});
```

The transaction commits when the callback returns and rolls back when it throws. Use the connection you were handed (`tx`) for everything inside. Inside a transaction, call `db.on(tx)` so the work runs on the transaction.

With try-with-resources, a scope that rolls back on close unless `commit()` ran:

```java
try (TransactionScope tx = db.beginTransaction()) {
    tx.insert("insert into users (email) values (?)", "grace@example.com");
    tx.commit();
}
```

### Savepoints

A transaction inside a transaction uses a savepoint. If the inner callback throws and the outer one catches it, only the inner work is undone:

```java
db.transaction(outer -> {
    outer.insert("insert into logs (msg) values (?)", "start");
    try {
        outer.transaction(inner -> inner.insert("insert into logs (msg) values (?)", "risky"));
    } catch (RuntimeException ignored) {
        // "risky" is undone, "start" survives
    }
    return null;
});
```

`transactionLevel()` returns 0 outside a transaction and 1 for the outermost one. Inside a transaction a container owns (Spring), the outermost Diwan level is a savepoint, and the container keeps commit and rollback.

### Attempts

```java
db.transaction(tx -> transfer(tx), 3);
```

On a deadlock or serialization failure, the whole callback runs again, up to 3 times. Outside effects in the callback, such as an HTTP call, run again too. A failed `COMMIT` is never retried, because it may have landed. Only the outermost transaction retries; a nested one rethrows at once. `attempts` below 1 throws `IllegalArgumentException`.

### afterCommit and afterRollback

```java
db.transaction(tx -> {
    tx.insert("insert into orders (id, total) values (?, ?)", orderId, total);
    tx.afterCommit(() -> mailer.sendReceipt(orderId));
    tx.afterRollback(() -> LOG.warning("order was not saved"));
    return orderId;
});
```

- Outside a transaction, `afterCommit` runs at once and `afterRollback` is dropped.
- `afterCommit` callbacks run after the outermost commit. A rolled-back savepoint drops its own callbacks.
- A retried attempt drops the failed attempt's `afterCommit` callbacks, so a mail is not sent twice.
- Callbacks run after the transaction has fully ended. Use the root connection inside them, not `tx`.
- A callback that throws never rolls anything back. The first failure reaches the caller.
- If the connection drops during `COMMIT`, the outcome is unknown and `afterRollback` still runs. Check the database before you undo anything such as a payment.
- Inside a transaction opened outside the library, `afterCommit` throws `IllegalStateException`.

### Strict transactions

By default the root connection refuses calls from a thread that is inside one of its own transactions. Such a call would borrow a second connection, write outside the rollback and can deadlock a small pool. The failure is an `IllegalStateException` that tells you to use `tx`.

```java
Connection db = Connection.builder()
        .name("main")
        .dataSource(dataSource)
        .strictTransactions(false)     // only for deliberate writes outside, like an audit log
        .build();
```

### Sessions

`session(callback)` holds one physical connection for a block, so a session setting such as SQLite's `PRAGMA foreign_keys` stays in force even with a pool. It starts no transaction.

## Events and the query log

Register listeners on the connection's `events()`:

```java
Registration slow = db.events().whenQueryTakesLongerThan(
        Duration.ofMillis(500),
        event -> LOG.warning("slow query " + event.time().toMillis() + " ms: " + event.redacted()));
slow.remove();
```

| Call | Use |
|---|---|
| `listen(handler)` | A lambda for `QueryExecuted`. |
| `addListener(ConnectionListener)` | Override `queryExecuted`, `queryFailed`, `transactionBeginning`, `transactionCommitting`, `transactionCommitted`, `transactionRolledBack`. |
| `whenQueryTakesLongerThan(Duration, handler)` | Fires for each slow statement. |
| `whenQueryingForLongerThan(Duration, handler)` | Fires once when the total passes the limit. Call `resetTotalQueryDuration()` to re-arm. |

Every registration returns a `Registration`; `remove()` undoes it. To attach a listener to every connection a manager builds, use `DatabaseManager.builder().listener(...)`. A `ManagerListener` hears `connectionEstablished` each time a connection is built, including after `purge`.

A `QueryExecuted` event holds the SQL, the bindings, the `Duration`, the connection name, the `QueryKind` and the transaction level. Bindings can hold passwords and names. Call `event.redacted()` before you send an event anywhere.

A listener that throws after a successful statement raises `ListenerFailedException`; the statement is not undone. A failing `queryFailed` listener is added as a suppressed exception and never hides the `QueryException`.

### Query log

```java
ConnectionEvents events = db.events();
events.enableQueryLog();
List<LoggedQuery> log = events.getQueryLog();   // a copy, oldest first
events.flushQueryLog();
```

The log is off by default and bounded. With `showBindingsInErrors` off, it stores `?` for every binding. Turn that on only in a debug build.

## Pretend mode

```java
List<LoggedQuery> plan = db.pretend(p -> p.statement("drop table users"));
```

Nothing reaches the database. Reads return no rows, counts are 0, and `statement` returns `true`. Listeners see the statements with a time of zero.

## Pooling

The manager's own connections use `DriverManager` and open a new JDBC connection per checkout. That suits tests and small tools. A server should hand the manager a pooled `DataSource`, as in this HikariCP recipe:

```java
HikariConfig hikari = new HikariConfig();
hikari.setJdbcUrl("jdbc:postgresql://db.internal:5432/shop");
hikari.setUsername("shop");
hikari.setPassword(System.getenv("DB_PASSWORD"));
hikari.setMaximumPoolSize(10);

DatabaseManager db = DatabaseManager.builder()
        .config(config)
        .connector(new PostgresConnector())
        .dataSource("main", () -> new HikariDataSource(hikari))
        .build();
```

The supplier runs when the connection is first built. Diwan closes a data source that is `AutoCloseable` on `purge` or `close`, and `HikariDataSource` is. A name that is not configured is refused when the manager is built. With a direct connection, pass the pool to `Connection.builder().dataSource(pool)` and close it yourself.

Size the pool for at least the threads that run transactions at once. A cursor holds its connection until it is closed, so a pool of one deadlocks if you write inside the loop.

## Method reference

Public methods that the sections above do not cover, one row per method name (overloads share a row).

| Method | On | What it does | Example |
|---|---|---|---|
| `getName` `getTablePrefix` `getDriverInfo` | `Connection` | Connection facts: the name the connection was built with, the prefix added to table names, and a description of the database behind it. | `conn.getTablePrefix()` |
| `canDeferUntilCommit` | `Connection` | Tells whether `afterCommit(Runnable)` can wait for a commit on this connection. | `conn.canDeferUntilCommit()` |
| `getDefaultConnection` | `DatabaseManager` | Returns the name of the connection `connection()` uses on this thread. | `db.getDefaultConnection()` |
| `seed` | `DatabaseManager` | Runs a seeder with the default connection, outside a transaction. | `db.seed(new UserSeeder())` |
