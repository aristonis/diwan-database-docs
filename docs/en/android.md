# Android

Diwan runs on Android 9 (API 28) and later through `diwan-database-android`. It is a driver over
Android's own `SQLiteDatabase`, so the schema builder, migrations, query builder and models work as
on the desktop. The module is a plain JAR with no runtime dependency.

=== "Gradle (Kotlin)"
    ```kotlin
    implementation("org.aristonis:diwan-database:0.3.0")
    implementation("org.aristonis:diwan-database-android:0.3.0")
    implementation("org.aristonis:diwan-database-sqlite:0.3.0")
    implementation("org.aristonis:diwan-database-eloquent:0.3.0")   // only if you use models
    ```
=== "Gradle (Groovy)"
    ```groovy
    implementation 'org.aristonis:diwan-database:0.3.0'
    implementation 'org.aristonis:diwan-database-android:0.3.0'
    implementation 'org.aristonis:diwan-database-sqlite:0.3.0'
    implementation 'org.aristonis:diwan-database-eloquent:0.3.0'   // only if you use models
    ```
=== "Maven"
    ```xml
    <dependency>
        <groupId>org.aristonis</groupId>
        <artifactId>diwan-database</artifactId>
        <version>0.3.0</version>
    </dependency>
    <dependency>
        <groupId>org.aristonis</groupId>
        <artifactId>diwan-database-android</artifactId>
        <version>0.3.0</version>
    </dependency>
    <dependency>
        <groupId>org.aristonis</groupId>
        <artifactId>diwan-database-sqlite</artifactId>
        <version>0.3.0</version>
    </dependency>
    <dependency>
        <groupId>org.aristonis</groupId>
        <artifactId>diwan-database-eloquent</artifactId>
        <version>0.3.0</version>
    </dependency>
    <!-- only if you use models -->
    ```

## Set up the driver

Pass a `SQLiteOpenHelper` and let the driver open the database on first use, or pass an open
`SQLiteDatabase`:

=== "Java"
    ```java
    public final class AppDb extends SQLiteOpenHelper {
        AppDb(Context context) { super(context, "app.db", null, 1); }

        @Override public void onConfigure(SQLiteDatabase db) {
            db.setForeignKeyConstraintsEnabled(true);   // Android leaves foreign keys off
            db.enableWriteAheadLogging();
        }
        @Override public void onCreate(SQLiteDatabase db) { }
        @Override public void onUpgrade(SQLiteDatabase db, int from, int to) { }
    }

    DatabaseConfig config = DatabaseConfig.builder()
            .defaultConnection("app")
            .connection(ConnectionConfig.builder("app").driver("android").build())
            .build();

    DatabaseManager manager = DatabaseManager.builder()
            .config(config)
            .connector(AndroidConnector.of(() -> new AppDb(context), SQLiteQuery::of, SQLiteSchema::of))
            .build();

    manager.migrator("app").migrations(migrations).build().run();
    QueryFactory db = manager.query();
    ```
=== "Kotlin"
    ```kotlin
    class AppDb(context: Context) : SQLiteOpenHelper(context, "app.db", null, 1) {
        override fun onConfigure(db: SQLiteDatabase) {
            db.setForeignKeyConstraintsEnabled(true)   // Android leaves foreign keys off
            db.enableWriteAheadLogging()
        }
        override fun onCreate(db: SQLiteDatabase) { }
        override fun onUpgrade(db: SQLiteDatabase, from: Int, to: Int) { }
    }

    val config = DatabaseConfig.builder()
        .defaultConnection("app")
        .connection(ConnectionConfig.builder("app").driver("android").build())
        .build()

    val manager = DatabaseManager.builder()
        .config(config)
        .connector(AndroidConnector.of({ AppDb(context) }, SQLiteQuery::of, SQLiteSchema::of))
        .build()

    manager.migrator("app").migrations(migrations).build().run()
    val db = manager.query()
    ```

`of(SQLiteOpenHelper)` opens the database on the first call that needs it, and that call runs the
helper's `onCreate` or `onUpgrade`. Make the first call off the main thread. The driver never
closes the database; your app owns it.

`AndroidConnector.of(...)` takes the two grammar factories once, here. After that your code asks the manager for `query()`, `schema()` and `migrator(name)` and never names a grammar class. Build the first connection off the main thread.

Without a manager, build a `Connection` with `Connection.builder().name("app").driver(AndroidSqliteDriver.of(new AppDb(context))).build()` and use `SQLiteSchema.of(connection)` and `SQLiteQuery.of(connection)`.

All keys: [Configuration](configuration.md)

## Threading

Android ties a transaction to the thread that began it. Diwan records that thread and refuses to
commit, roll back or close from another one, so keep a whole `transaction(...)` callback on one
thread. Do not switch coroutine contexts or hand work to an executor inside it. A cursor works the
same way: use it only from the thread that opened it.

Run database work off the main thread. Diwan does not move it for you.

## Cursor windows and large reads

Android reads rows through windows of about 2 MB, and Diwan reads whole results into memory except
through `cursor()`. For large tables:

- Page with `limit`, or use `chunkById` and `lazyById`.
- Avoid `cursor()` on a table that changes while you read. The window refills by running the query
  again, so changed rows can be skipped or repeated.
- Keep large blobs out of rows you query in bulk.

## Write-ahead logging

Diwan begins Android transactions with the exclusive `beginTransaction`, or with
`beginTransactionNonExclusive` when the connection sets `transaction_mode` to `immediate` (see
[Connections](connections.md)). Without write-ahead logging, a long transaction blocks reads from
other threads. Call `enableWriteAheadLogging()` in `onConfigure`, as above, and keep
transactions short.

## Deferred foreign keys and commit

With `defer_foreign_keys` on and `foreign_keys` on, `commit()` runs `PRAGMA foreign_key_check` first.
Only the outermost commit does this. If the check finds a broken key, the transaction rolls back,
none of its writes stay, and the commit throws a foreign key `DriverException` that names the child
table. The connection can begin a new transaction after that.

Limits:

- A key declared `DEFERRABLE INITIALLY DEFERRED` in raw DDL is not checked, because the check runs
  only when `defer_foreign_keys` is on.
- The check scans the whole database. An orphan row left from before the transaction also fails the
  commit.

## What needs a newer Android

Android ships its own SQLite, and its version follows the API level.

| Feature | Needs | On older Android |
|---|---|---|
| `upsert` (query builder and models) | SQLite 3.24, API 30 | `UnsupportedOperationException` naming the version, before any SQL |
| Right join | SQLite 3.39, API 34 | SQLite's own error as a `QueryException` |
| `insertOrIgnore`, `updateOrInsert` | any version | works |

`updateOrInsert` reads, then writes, and is not atomic. On API 28 and 29, write a read-then-write
in a transaction instead of `upsert`.

## Decimals and dates

A `decimal` column has numeric affinity, so `10.10` reads as the double `10.1`. For exact values,
use a scaled integer column, or text with a fixed scale. Dates are stored as
`yyyy-MM-dd HH:mm:ss` text, and an `Instant` as UTC text or whole microseconds, as on the desktop
SQLite driver.

## Debug query log

=== "Java"
    ```java
    Connection connection = Connection.builder()
            .name("app").driver(androidDriver).queryLogLimit(200).build();
    if (BuildConfig.DEBUG) {
        connection.events().enableQueryLog();
    }
    for (LoggedQuery entry : connection.events().getQueryLog()) {
        Log.d("diwan", entry.sql() + " " + entry.bindings());
    }
    ```
=== "Kotlin"
    ```kotlin
    val connection = Connection.builder()
        .name("app").driver(androidDriver).queryLogLimit(200).build()
    if (BuildConfig.DEBUG) {
        connection.events().enableQueryLog()
    }
    for (entry in connection.events().queryLog) {
        Log.d("diwan", "${entry.sql()} ${entry.bindings()}")
    }
    ```

## R8 and ProGuard

Diwan uses no reflection, and it finds migrations from the list you give the `Migrator`, not by
scanning. The only thing R8 can break is a default derived from a class name. Do one of these:

- Pass the names explicitly. Override `table()` on each model, and give relations their foreign
  keys, pivot table and `chaperone` names.
- Or keep the model class names:

```
-keepnames class * extends org.aristonis.diwan.database.eloquent.Model
```

Name each migration with a fixed string in `name()` (for example
`2026_10_31_000000_create_users_table`), never from the class name. Do not use compiled bytecode to
detect an edited migration; use `checksum()` instead, see [Migrations](migrations.md).

On Android, `toMap()`, `push()` and `touchOwners()` recurse once per level of the loaded graph. A
very deep chain can overflow a small thread stack, so load it in pieces.

See also [Getting started](getting-started.md) and [Connections](connections.md).
