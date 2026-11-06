# Migrations

A migration is one schema change, written as a Java class with an `up` step and an optional `down`
step. The migrations table records which ones ran and in which batch. The next run skips those, and
a rollback undoes the last batch.

## Write a migration

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

Start each name with its date, because pending migrations run in name order. Never rename a
migration that has run anywhere. You list migrations in code: nothing is found by scanning the
classpath. For raw SQL inside `up` or `down`, use `schema.connection()` so the SQL joins the
migration's transaction.

Three optional overrides: `withinTransaction()` to opt out of the wrapping transaction,
`shouldRun()` to skip the migration, and `connection()` to send it to another named connection.

## Run and undo

```java
import org.aristonis.diwan.database.migrations.Migrator;

Migrator migrator = Migrator.builder(SQLiteSchema.of(db))
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

Each call returns a `List<MigrationResult>` with the migration name, its `Outcome` (`RAN`,
`SKIPPED`, `ROLLED_BACK`, `NOT_FOUND` or `PRETENDED`), its batch and the SQL it ran.

On SQLite and PostgreSQL a migration and its record commit together, so a failure never leaves a
half-applied migration or a stray record. A failure stops the call with `MigrationFailedException`.
Its `completed()` lists what finished and `phase()` says whether the migration or only its record
failed. The migrator refuses to run inside a transaction you opened.

### Status and pretend

```java
for (MigrationStatus s : migrator.status()) {
    System.out.println(s.name() + " " + s.state() + " " + s.batch());   // RAN, PENDING or MISSING
}
migrator.pretendRun().forEach(r -> System.out.println(r.name() + " " + r.queries()));
migrator.pretendRollback();
migrator.pretendReset();
```

Pretend runs list the SQL and change nothing. A migration that checks `hasTable` sees an empty
database there, so its SQL can differ from a real run.

### Missing migrations

Rollback and reset stop with `MissingMigrationsException` when a recorded migration is not in your
list, which usually means older code against a newer database. Nothing is undone. Add
`allowMissingOnRollback()` to the builder to undo the known ones and keep the unknown records, as
Laravel does.

### Other connections and the table name

```java
Migrator migrator = Migrator.builder(mainSchema)
        .connection("reports", reportsSchema)     // a migration whose connection() returns "reports"
        .table("schema_migrations")               // the default is "migrations"
        .migrations(List.of(new CreateUsersTable(), new CreateReportsTable()))
        .build();
```

## Events

A `MigrationListener` watches a migrator work. Every method is optional.

```java
Migrator migrator = Migrator.builder(SQLiteSchema.of(db))
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

Nothing stops two processes from migrating at once unless you plug in a lock. PostgreSQL has one
built on an advisory lock.

```java
Migrator migrator = Migrator.builder(PostgresSchema.of(db))
        .lock(new PostgresMigrationLock(dataSource))     // waits up to 60 seconds by default
        .add(new CreateUsersTable())
        .build();
```

For another database, implement `MigrationLock` (`acquire()` and `release()`).

## Checksums

By default a migration that already ran can be edited without anyone noticing. Override `checksum()`
to opt in to a check.

```java
@Override
public Optional<String> checksum() {
    return Optional.of("v2");     // a label you bump on purpose, or MigrationChecksum.of(text)
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
- To accept an intended edit, call `migrator.repairChecksums(migrator.migrations())`. To drop every
  recorded checksum, call `migrator.clearChecksums()`. Both take the migration lock and fire no
  events.

A migrations table created before the checksum column existed does not have it, and Diwan does not
alter tables at run time. The first call that needs the column throws `IllegalStateException` with
the one statement to run: `alter table migrations add column checksum varchar(64)`. This applies to
databases created by a pre-release build only.

## Seeders

A seeder fills tables with starting data. Extend `Seeder` and use the `SeedContext`.

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

`SeedOptions` can pick a named connection, wrap the whole run in one transaction and add a
`SeederListener`. A seeder that calls itself, directly or through others, throws
`IllegalStateException` that names the chain.

Next: [Models](models.md), [Errors and exceptions](errors.md).
