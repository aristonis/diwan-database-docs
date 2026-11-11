# Migrations

A migration is one schema change, written as a Java class with an `up` step and an optional `down`
step. The migrations table records which ones ran and in which batch. The next run skips those, and
a rollback undoes the last batch.

## Write a migration

=== "Java"

    ```java
    import org.aristonis.diwan.database.migrations.Migration;
    import org.aristonis.diwan.database.schema.Schema;

    final class CreateUsersTable extends Migration {
        @Override
        public String name() {
            return "2026_10_31_000000_create_users_table";
        }

        @Override
        public void up(Schema schema) {
            schema.create("users", table -> {
                table.id();
                table.string("email").unique();
            });
        }

        @Override
        public void down(Schema schema) {
            schema.drop("users");
        }
    }
    ```

=== "Kotlin"

    ```kotlin
    import org.aristonis.diwan.database.migrations.Migration
    import org.aristonis.diwan.database.schema.Schema

    class CreateUsersTable : Migration() {
        override fun name() = "2026_10_31_000000_create_users_table"

        override fun up(schema: Schema) {
            schema.create("users") { table ->
                table.id()
                table.string("email").unique()
            }
        }

        override fun down(schema: Schema) {
            schema.drop("users")
        }
    }
    ```

Start each name with its date, because pending migrations run in name order. Never rename a
migration that has run anywhere. You list migrations in code: nothing is found by scanning the
classpath. For raw SQL inside `up` or `down`, use `schema.connection()` so the SQL joins the
migration's transaction.

Three optional overrides: `withinTransaction()` to opt out of the wrapping transaction,
`shouldRun()` to skip the migration, and `connection()` to send it to another named connection.

### Order

Pending migrations always run sorted by name, whatever order you add them in. A list built from
several modules is one list to the migrator, so it is merged by name too: if module B's
migrations sort before module A's and a B table refers to an A table, B's migration runs first
and fails with an error such as `relation "accounts" does not exist`. Name migrations so the sort
follows the dependencies, for example with the date they were written, or a prefix per module
that sorts in dependency order.

```text
2026_01_10_000000_create_accounts_table   (module A, runs first)
2026_01_12_000000_create_entries_table    (module B, refers to accounts)
```

Rollback and reset go the other way: the latest batch first, and inside a batch the highest name
first. There is no option to run in the order of the list.

## Run and undo

`manager.migrator(name)` returns a `Migrator.Builder` for that connection, built from its configuration. Without a manager, use `Migrator.builder(SQLiteSchema.of(connection))` or the `PostgresSchema` equivalent.

=== "Java"

    ```java
    import org.aristonis.diwan.database.migrations.Migrator;

    Migrator migrator = manager.migrator("main")
            .add(new CreateUsersTable())
            .add(new AddBioToUsers())
            .build();

    migrator.run();               // pending migrations, one batch
    migrator.run(true);           // one batch per migration
    migrator.rollback();          // the last batch
    migrator.rollbackSteps(2);    // the last two migrations
    migrator.rollbackBatch(3);    // one named batch
    migrator.reset();             // everything
    ```

=== "Kotlin"

    ```kotlin
    import org.aristonis.diwan.database.migrations.Migrator

    val migrator = manager.migrator("main")
        .add(CreateUsersTable())
        .add(AddBioToUsers())
        .build()

    migrator.run()               // pending migrations, one batch
    migrator.run(true)           // one batch per migration
    migrator.rollback()          // the last batch
    migrator.rollbackSteps(2)    // the last two migrations
    migrator.rollbackBatch(3)    // one named batch
    migrator.reset()             // everything
    ```

Each call returns a `List<MigrationResult>` with the migration name, its `Outcome` (`RAN`,
`SKIPPED`, `ROLLED_BACK`, `NOT_FOUND` or `PRETENDED`), its batch and the SQL it ran.

On SQLite and PostgreSQL a migration and its record commit together, so a failure never leaves a
half-applied migration or a stray record. A failure stops the call with `MigrationFailedException`.
Its `completed()` lists what finished and `phase()` says whether the migration or only its record
failed. The migrator refuses to run inside a transaction you opened.

### Start from scratch

=== "Java"

    ```java
    migrator.fresh();     // drop every view and table, then run all migrations
    ```

=== "Kotlin"

    ```kotlin
    migrator.fresh()     // drop every view and table, then run all migrations
    ```

`fresh()` calls `schema.dropAllViews()` and `schema.dropAllTables()`, including the migrations table, then `run()`, and returns what `run()` returns. Use it for test and local databases, never for a deployed one. See [Schema builder](schema.md#list-and-drop-everything) for what is dropped, and [Testing](testing.md) for the test extension that calls it.

### Status and pretend

=== "Java"

    ```java
    for (MigrationStatus s : migrator.status()) {
        System.out.println(s.name() + " " + s.state() + " " + s.batch());   // RAN, PENDING or MISSING
    }
    migrator.pretendRun().forEach(r -> System.out.println(r.name() + " " + r.queries()));
    migrator.pretendRollback();
    migrator.pretendReset();
    ```

=== "Kotlin"

    ```kotlin
    for (s in migrator.status()) {
        println("${s.name()} ${s.state()} ${s.batch()}")   // RAN, PENDING or MISSING
    }
    migrator.pretendRun().forEach { println("${it.name()} ${it.queries()}") }
    migrator.pretendRollback()
    migrator.pretendReset()
    ```

Pretend runs list the SQL and change nothing. A migration that checks `hasTable` sees an empty
database there, so its SQL can differ from a real run.

### Missing migrations

Rollback and reset stop with `MissingMigrationsException` when a recorded migration is not in your
list, which usually means older code against a newer database. Nothing is undone. Add
`allowMissingOnRollback()` to the builder to undo the known ones and keep the unknown records, as
Laravel does.

### Other connections and the table name

=== "Java"

    ```java
    Migrator migrator = Migrator.builder(mainSchema)
            .connection("reports", reportsSchema)     // a migration whose connection() returns "reports"
            .table("schema_migrations")               // the default is "migrations"
            .migrations(List.of(new CreateUsersTable(), new CreateReportsTable()))
            .build();
    ```

=== "Kotlin"

    ```kotlin
    val migrator = Migrator.builder(mainSchema)
        .connection("reports", reportsSchema)     // a migration whose connection() returns "reports"
        .table("schema_migrations")               // the default is "migrations"
        .migrations(listOf(CreateUsersTable(), CreateReportsTable()))
        .build()
    ```

The migrations table has the columns `id`, `migration` (the name, up to 191 characters, unique),
`batch`, and `checksum` (up to 64 characters, nullable). To read the applied names, use
`migrator.status()` or `migrator.repository().getRan()`, not SQL.

## Events

A `MigrationListener` watches a migrator work. Every method is optional.

=== "Java"

    ```java
    Migrator migrator = manager.migrator("main")
            .add(new CreateUsersTable())
            .listener(new MigrationListener() {
                @Override
                public void migrationStarted(MigrationEvent event) {
                    System.out.println("running " + event.name());
                }

                @Override
                public void migrationFailed(MigrationEvent event, Throwable failure) {
                    System.err.println(event.name() + " failed: " + failure.getMessage());
                }
            })
            .build();
    ```

=== "Kotlin"

    ```kotlin
    val migrator = manager.migrator("main")
        .add(CreateUsersTable())
        .listener(object : MigrationListener {
            override fun migrationStarted(event: MigrationEvent) {
                println("running ${event.name()}")
            }

            override fun migrationFailed(event: MigrationEvent, failure: Throwable) {
                System.err.println("${event.name()} failed: ${failure.message}")
            }
        })
        .build()
    ```

| Method | When |
|---|---|
| `migrationsStarted` | once, before the first migration of a run, rollback or reset |
| `noPendingMigrations` | instead of the one above, when there is nothing to do |
| `migrationStarted`, `migrationEnded` | around one migration |
| `migrationSkipped` | going up, when `shouldRun()` is `false` |
| `migrationFailed` | when a migration or its record failed, just before the exception is thrown |
| `migrationsEnded` | once, after the last migration of a call that succeeded |

`MigrationEvent` carries the direction, name, batch, pretend flag and connection name.
`MigrationsEvent` carries the direction, pretend flag and connection name. Listeners run in
registration order on the calling thread. An exception from `migrationsStarted` or
`migrationStarted` stops the call before that work. From the other "ended" events it propagates after
the work is recorded. From `migrationFailed` it is added as suppressed to the
`MigrationFailedException`. Laravel sends these events through the application's dispatcher and has
none for failures; here you register on the builder.

## Migration lock

Nothing stops two processes from migrating at once unless a lock is held. The migrator takes the lock
before a run, rollback or reset, and releases it when the call ends, whether it succeeded or failed.
Status and pretend calls take no lock. The lock depends on the database:

| Database | Lock | Where the lock lives |
|---|---|---|
| PostgreSQL | `PostgresMigrationLock`, a session advisory lock | A session on the server. If the process dies, the server ends the session and frees the lock. |
| SQLite or Android, file database | `FileMigrationLock` | A file beside the database named `<database>.migrate.lock`. The operating system frees the lock if the process dies. The file is left in place after each run. |
| SQLite or Android, in-memory database | None | Nothing is shared with another process, so there is nothing to lock. |

The manager gives each connection its lock, as in the examples below. The default wait is 60 seconds.
On SQLite and Android, the `lock_wait` option sets it, such as `5s` or `500ms`. On PostgreSQL,
`lock_wait` sets the `lock_timeout` of the sessions instead, and the lock keeps its own 60-second
wait, which you can change with `PostgresMigrationLock(dataSource, name, wait, unit)`.

=== "Java"

    ```java
    Migrator migrator = manager.migrator("main")     // carries the PostgreSQL lock by itself
            .add(new CreateUsersTable())
            .build();
    ```

=== "Kotlin"

    ```kotlin
    val migrator = manager.migrator("main")     // carries the PostgreSQL lock by itself
        .add(CreateUsersTable())
        .build()
    ```

Without a manager, build the migrator on the grammar module and pass the lock yourself:

=== "Java"

    ```java
    Migrator migrator = Migrator.builder(PostgresSchema.of(connection))
            .lock(new PostgresMigrationLock(dataSource))     // waits up to 60 seconds by default
            .add(new CreateUsersTable())
            .build();
    ```

=== "Kotlin"

    ```kotlin
    val migrator = Migrator.builder(PostgresSchema.of(connection))
        .lock(PostgresMigrationLock(dataSource))     // waits up to 60 seconds by default
        .add(CreateUsersTable())
        .build()
    ```

On SQLite or Android, pass `new FileMigrationLock(() -> databaseFile)` the same way.

Some details that apply to the locks above:

- Two migrators in one JVM take turns on the same lock too, so the second waits for the first.
- Network file systems may ignore file locks, and then the lock protects nothing. Keep a SQLite file
  that is migrated on a local disk.
- On Android the lock opens the database first, so the helper's own `onCreate` or `onUpgrade`
  runs before the lock is held. Keep schema changes in migrations, not in the helper.
- A `DataSource` you supply gets the file lock only when the `database` or `url` setting names the
  file. Without either setting, that connection has no lock.
- The PostgreSQL lock holds one session from the pool for the whole run, and the migrator needs
  another, so a pool must allow at least two sessions. With a pool of one, the migrator waits for the
  pool's own timeout and then fails. The error carries a suppressed note that says the pool needs two
  sessions.
- On PostgreSQL, use one lock name per migrations table. Migrators on the same table share the name.
  Migrators on different tables should use different names, or they wait for each other. Through
  the manager, every connection uses the default name `diwan-migrations`, so build the lock yourself
  with `new PostgresMigrationLock(dataSource, name)` to give a table its own name.

For another database, implement `MigrationLock`: `acquire()` and `release()`. Override
`explain(RuntimeException)` when the lock can say why a failed run failed. The default adds nothing.

## Checksums

A migration that has been deployed is locked: never edit it and never change its checksum. Change
the schema with a new migration.

`checksum()` returns a fixed constant for that migration, set once. It detects an accidental edit;
it is not a version. By default a migration that already ran can be edited without anyone noticing,
so override `checksum()` to opt in to the check.

=== "Java"

    ```java
    @Override
    public Optional<String> checksum() {
        return Optional.of("1");     // fixed, never changed, or MigrationChecksum.of(text)
    }
    ```

=== "Kotlin"

    ```kotlin
    override fun checksum(): Optional<String> {
        return Optional.of("1")     // fixed, never changed, or MigrationChecksum.of(text)
    }
    ```

`MigrationChecksum.of(String)` returns a SHA-256 in hex of the text, after line endings become `\n`
and accents are put in Unicode form NFC, so the way the file was saved does not matter. Diwan never
hashes compiled code, because that changes between compilers and shrinkers.

- A run records the checksum in the migrations table.
- Before a run or a pretend run, the migrator compares every migration that already ran and has a
  recorded and a declared checksum. If any differ, `MigrationChecksumException` lists each one and
  nothing runs.
- A migration that declares nothing is never checked. One that starts declaring a checksum has it
  recorded on the next run.
- Recovery only, for a local database that was never deployed or a known accident: call
  `migrator.repairChecksums(migrator.migrations())` to rewrite each recorded checksum to the
  declared one, or `migrator.clearChecksums()` to drop every recorded checksum. Both take the
  migration lock and fire no events.

## Seeders

A seeder fills tables with starting data. Extend `Seeder` and use the `SeedContext`.

=== "Java"

    ```java
    final class DatabaseSeeder extends Seeder {
        @Override
        protected void run(SeedContext context) {
            context.query().table("users").insertOrIgnore(Map.of("email", "admin@example.com"));
            context.call(RolesSeeder::new);        // callOnce skips a seeder already run, callSilent hides its events
        }
    }

    manager.seed(DatabaseSeeder::new);                                             // a DatabaseManager
    manager.seed(DatabaseSeeder::new, SeedOptions.defaults().inTransaction(true));
    ```

=== "Kotlin"

    ```kotlin
    class DatabaseSeeder : Seeder() {
        override fun run(context: SeedContext) {
            context.query().table("users").insertOrIgnore(mapOf("email" to "admin@example.com"))
            context.call(::RolesSeeder)        // callOnce skips a seeder already run, callSilent hides its events
        }
    }

    manager.seed(::DatabaseSeeder)                                             // a DatabaseManager
    manager.seed(::DatabaseSeeder, SeedOptions.defaults().inTransaction(true))
    ```

`SeedOptions` can pick a named connection, wrap the whole run in one transaction and add a
`SeederListener`. A seeder that calls itself, directly or through others, throws
`IllegalStateException` that names the chain.

Next: [Models](models.md), [Errors and exceptions](errors.md).

## Method reference

Public methods that the sections above do not cover, one row per method name (overloads share a row).

| Method | On | What it does | Example |
|---|---|---|---|
| `repository` | `Migrator` | Returns the repository of the migrations table on the default connection. | `migrator.repository()` |
