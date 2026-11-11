# Testing

The `diwan-database-testing` module gives every JUnit 5 test an empty database with your migrations applied, and a set of assertions for reading the result.

## Add the module

Add it to the test scope only.

=== "Gradle (Kotlin)"

    ```kotlin
    dependencies {
        testImplementation("org.aristonis:diwan-database-testing:0.4.0")
    }
    ```

=== "Gradle (Groovy)"

    ```groovy
    dependencies {
        testImplementation 'org.aristonis:diwan-database-testing:0.4.0'
    }
    ```

=== "Maven"

    ```xml
    <dependency>
      <groupId>org.aristonis</groupId>
      <artifactId>diwan-database-testing</artifactId>
      <version>0.4.0</version>
      <scope>test</scope>
    </dependency>
    ```

The module needs JUnit Jupiter 5.10 or later on your test classpath and does not bring it. Add `diwan-database-eloquent` only if you use the model assertions.

## Register the extension

`RefreshDatabase` is a JUnit extension. Register it in a field with `@RegisterExtension`. The factory takes three things: a supplier of the `QueryFactory` of your root connection, a function that builds the `Schema` for a connection, and the list of migrations that build the test schema.

SQLite:

=== "Java"

    ```java
    class UserTest {
        static final Connection CONNECTION = Connection.builder()
                .name("test")
                .dataSource(new DriverManagerDataSource("jdbc:sqlite:build/test.db", null, null))
                .build();

        @RegisterExtension
        static RefreshDatabase db = RefreshDatabase.rollback(
                () -> SQLiteQuery.of(CONNECTION), SQLiteSchema::of,
                List.of(new CreateUsersTable()));

        @Test
        void savesAUser(DatabaseAssertions assertions, QueryFactory query) {
            query.table("users").insert(Map.of("name", "ann"));

            assertions.assertHas("users", Map.of("name", "ann"));
            assertions.assertCount("users", 1);
        }
    }
    ```

=== "Kotlin"

    ```kotlin
    class UserTest {
        @Test
        fun savesAUser(assertions: DatabaseAssertions, query: QueryFactory) {
            query.table("users").insert(mapOf("name" to "ann"))

            assertions.assertHas("users", mapOf("name" to "ann"))
            assertions.assertCount("users", 1)
        }

        companion object {
            val CONNECTION: Connection = Connection.builder()
                .name("test")
                .dataSource(DriverManagerDataSource("jdbc:sqlite:build/test.db", null, null))
                .build()

            @JvmField
            @RegisterExtension
            val db: RefreshDatabase = RefreshDatabase.rollback(
                { SQLiteQuery.of(CONNECTION) }, SQLiteSchema::of,
                listOf(CreateUsersTable()))
        }
    }
    ```

PostgreSQL:

=== "Java"

    ```java
    @RegisterExtension
    static RefreshDatabase db = RefreshDatabase.rollback(
            () -> PostgresQuery.of(CONNECTION), PostgresSchema::of,
            List.of(new CreateUsersTable()));
    ```

=== "Kotlin"

    ```kotlin
    @JvmField
    @RegisterExtension
    val db: RefreshDatabase = RefreshDatabase.rollback(
        { PostgresQuery.of(CONNECTION) }, PostgresSchema::of,
        listOf(CreateUsersTable()))
    ```

The supplier must return the same connection instance every time. That instance identifies the database. Use `RefreshDatabase.truncate(...)` with the same arguments for the other mode.

## Rollback or truncate

| | `rollback` | `truncate` |
|---|---|---|
| How data is removed | A transaction opens before each test and rolls back after it. | Tests commit for real. After each test, every table except the migrations table is truncated in one call, and identities restart. |
| Speed | Fast. | Slower. |
| `afterCommit` callbacks | Never run: nothing commits. | Run. |
| Other threads see the data | No. | Yes. |
| Parallel JUnit | Safe: one transaction per test thread. | Not allowed. |

Pick `rollback` by default. Pick `truncate` when the test needs real commits: `afterCommit` hooks, work on other threads or executors, or code that opens its own connection.

In rollback mode, calls the test makes on the root connection from its own thread run inside the test transaction, even with strict transactions on. A `transaction(...)` call inside the test becomes a savepoint.

In truncate mode:

- The list of tables is read once per run, after the first test, so a table a test creates later is not emptied.
- The table prefix of the connection is stripped from the listed names, and only tables that carry it are emptied. On PostgreSQL, tables outside `current_schema()` are qualified by their schema.
- Internal tables are left alone: `spatial_ref_sys` on PostgreSQL, `android_metadata` and the FTS shadow tables on SQLite.
- The extension fails with `IllegalStateException` under `ExecutionMode.CONCURRENT`. Use rollback mode, or mark the class `@Execution(ExecutionMode.SAME_THREAD)`.

## Template mode

Template mode gives every test its own database: a copy of a template that holds the migrated
schema. The test commits for real, as in truncate mode, but no test sees another test's data, and
the tests may run in parallel.

| | `rollback` | `truncate` | template |
|---|---|---|---|
| What a test sees | Its own transaction, rolled back after the test | The shared database, emptied after each test | Its own copy of the template |
| Commits are real | No | Yes | Yes |
| Parallel JUnit | Yes | No | Yes |
| Cost per test | Lowest | One truncate | One copy and one drop |
| Needs | Any database | Any database | PostgreSQL with `CREATEDB`, or SQLite with `directory(Path)` |

Use template mode when a test needs real commits and must not depend on, or disturb, the data of
other tests: for example tests that commit on other threads while other tests run. Use rollback when
no commit is needed. Use truncate when the tests must run one at a time.

=== "Java"

    ```java
    // TEST_DB_PASSWORD is read from the environment, never written into the code.
    static final DataSource ROOT = new DriverManagerDataSource(
            "jdbc:postgresql://localhost:5432/postgres", "test_admin", System.getenv("TEST_DB_PASSWORD"));

    @RegisterExtension
    static RefreshDatabase db = RefreshDatabase.template(
            ROOT,
            name -> postgresManager(name),        // a manager on the database `name`
            PostgresSchema::of,
            List.of(new CreateUsersTable()))
        .strategy(CopyStrategy.FILE_COPY);

    static DatabaseManager postgresManager(String database) {
        ConnectionConfig connection = ConnectionConfig.builder("main").driver("pgsql")
                .host("localhost").port(5432).database(database)
                .username("test_admin").password(System.getenv("TEST_DB_PASSWORD")).build();
        return DatabaseManager.builder()
                .config(DatabaseConfig.builder().defaultConnection("main").connection(connection).build())
                .connector(new PostgresConnector())
                .build();
    }
    ```

=== "Kotlin"

    ```kotlin
    companion object {
        // TEST_DB_PASSWORD is read from the environment, never written into the code.
        val ROOT: DataSource = DriverManagerDataSource(
            "jdbc:postgresql://localhost:5432/postgres", "test_admin", System.getenv("TEST_DB_PASSWORD"))

        @JvmField
        @RegisterExtension
        val db: RefreshDatabase = RefreshDatabase.template(
            ROOT,
            { name -> postgresManager(name) },    // a manager on the database `name`
            PostgresSchema::of,
            listOf(CreateUsersTable()))
            .strategy(CopyStrategy.FILE_COPY)

        fun postgresManager(database: String): DatabaseManager {
            val connection = ConnectionConfig.builder("main").driver("pgsql")
                .host("localhost").port(5432).database(database)
                .username("test_admin").password(System.getenv("TEST_DB_PASSWORD")).build()
            return DatabaseManager.builder()
                .config(DatabaseConfig.builder().defaultConnection("main").connection(connection).build())
                .connector(PostgresConnector())
                .build()
        }
    }
    ```

SQLite needs a folder. The extension builds the template there and copies it for each test:

=== "Java"

    ```java
    static final Path DIRECTORY = Path.of("build/template-dbs");

    @RegisterExtension
    static RefreshDatabase db = RefreshDatabase.template(
            new DriverManagerDataSource("jdbc:sqlite:build/template-root.db", null, null),
            file -> sqliteManager(file),          // opens exactly the file it is given
            SQLiteSchema::of,
            List.of(new CreateUsersTable()))
        .directory(DIRECTORY);

    static DatabaseManager sqliteManager(String file) {
        ConnectionConfig connection = ConnectionConfig.builder("main").driver("sqlite").database(file).build();
        return DatabaseManager.builder()
                .config(DatabaseConfig.builder().defaultConnection("main").connection(connection).build())
                .connector(new SQLiteConnector())
                .build();
    }
    ```

=== "Kotlin"

    ```kotlin
    companion object {
        val DIRECTORY: Path = Path.of("build/template-dbs")

        @JvmField
        @RegisterExtension
        val db: RefreshDatabase = RefreshDatabase.template(
            DriverManagerDataSource("jdbc:sqlite:build/template-root.db", null, null),
            { file -> sqliteManager(file) },      // opens exactly the file it is given
            SQLiteSchema::of,
            listOf(CreateUsersTable()))
            .directory(DIRECTORY)

        fun sqliteManager(file: String): DatabaseManager {
            val connection = ConnectionConfig.builder("main").driver("sqlite").database(file).build()
            return DatabaseManager.builder()
                .config(DatabaseConfig.builder().defaultConnection("main").connection(connection).build())
                .connector(SQLiteConnector())
                .build()
        }
    }
    ```

### How the template works

- The template is named after the migration list: `diwan_tpl_<hash8>`, where the hash covers the
  class, name and checksum of each migration, in order. A run with the same list reuses the template;
  a changed list builds a new one next to it.
- Each test gets one copy, named `diwan_t_<hash8>_<run>_<n>`. The copy is removed after the test.
- The template is migrated through its own manager, which is closed before the first copy. Runs that
  start together build it once.
- The root data source gives the run one connection, held until the run ends, and the run's locks
  live on it. Give the root a plain driver data source or a pool in session mode, not a pooler in
  transaction mode.
- The extension closes the manager it gets for each test, so keep each manager's pool small: a
  maximum of 2 connections is enough for most tests.
- A `perDatabase` manager must close its connections at once when it is closed. A pool that closes
  them lazily can make dropping the copy fail. On PostgreSQL 13 or later the drop uses `FORCE`; on
  older servers a slow close leaves the copy behind for the next run's sweep.

### PostgreSQL

- The role needs `CREATEDB`. Without it, the run fails before the first test, with an
  `IllegalStateException` that names the role and shows the `ALTER ROLE ... CREATEDB` grant.
- No other session may be connected to the template when a copy is made. The extension closes its
  own sessions on the template after it builds it. A copy waits about two seconds for a session that
  is just closing; a session that stays open makes the copy fail with an `IllegalStateException` that
  names the template.
- `strategy(CopyStrategy)` sets the strategy of every copy. `FILE_COPY` copies the template's files
  and forces two checkpoints. `WAL_LOG` replays the template through the write-ahead log, with no
  checkpoint but more log written. The default is `FILE_COPY` on PostgreSQL 15 or later and no
  clause on older servers. An explicit strategy on an older server fails when the first copy is made.
- `FILE_COPY` runs a checkpoint before and after each copy, which costs more on a busy shared
  server. `WAL_LOG` suits small templates.
- Measured with 20 tables and 10 tests, mean time per test: truncate mode 379 ms, `FILE_COPY`
  299 ms, `WAL_LOG` 310 ms. The one-time set-up took 309 ms with `FILE_COPY` and 70 ms with
  `WAL_LOG`.
- On PostgreSQL 18 and later, the server setting `file_copy_method` set to `clone` can make
  `FILE_COPY` copies faster on a filesystem that supports cloning.
- A copy is dropped with `FORCE` on PostgreSQL 13 or later, which ends any session still on it.

### SQLite

- `directory(Path)` names the folder of the template and the copies. Without it, template mode
  refuses to start with an `IllegalStateException`. On a PostgreSQL target, `directory(Path)` is
  refused with an `IllegalStateException`.
- The extension creates the copies directory. The folder of the root data source's own file must
  exist before the run.
- Each database is the file `<directory>/<name>.db`. `perDatabase` receives the absolute path of that
  file and must open exactly that path. Otherwise the run fails, and the message gives the expected
  and the opened path.
- The template is migrated into a file of its own, checkpointed, and then moved into place. Each test
  copies that file, and after the test removes the copy with its `-wal`, `-shm` and `-journal` files.
- `strategy(CopyStrategy)` applies to PostgreSQL only; SQLite ignores it.

### Options

Each option returns a new extension, and an option outside template mode throws
`IllegalStateException`.

- `strategy(CopyStrategy)`: the copy strategy on PostgreSQL. See above.
- `directory(Path)`: the folder for SQLite. Required there.
- `dropStaleTemplates()`: when a run starts, drops the templates of other migration lists. On
  PostgreSQL a template that another run is still copying from stays, and the refusal is logged. On
  SQLite the other templates' files in the folder are deleted with their side and lock files; a
  template whose build lock another run holds stays.

### Parallel tests and several JVMs

- Template mode works under `ExecutionMode.CONCURRENT`, unlike truncate mode.
- Several JVMs can share one server or one folder, such as Gradle test forks with `maxParallelForks`
  above 1. One run builds the template and the others reuse it. Each copy name carries the run id of
  its JVM, so a run never takes another run's copy.

### Leftovers

- A run holds a lock while it lives: an advisory lock on PostgreSQL, a file lock on SQLite. When a
  run starts, it removes the copies and build databases or files of runs that have ended. It never
  removes its own, and it leaves the files of a live run alone.
- A crashed run leaves its copies behind until the next run starts.
- A copy that cannot be dropped after its test is logged, and the test's result does not change. The
  next run removes it.
- The sweep never removes a finished template that matches the current migration list. Older
  templates stay unless `dropStaleTemplates()` is set.

### Limits

- In-memory SQLite is not supported in template mode: give a file path with `directory(Path)`.
- Android is not supported: template mode refuses the `android` driver with an
  `IllegalStateException`.
- Template mode runs on PostgreSQL and SQLite only.

## Restart identities

On PostgreSQL a rollback undoes the rows but not the sequence behind an `id`. Without the option, the ids a test gets depend on the tests that ran before it. `restartingIdentities()` sets the counters back before each test, so every test sees the same ids:

=== "Java"

    ```java
    @RegisterExtension
    static RefreshDatabase db = RefreshDatabase.rollback(
            () -> PostgresQuery.of(CONNECTION), PostgresSchema::of,
            List.of(new CreateUsersTable()))
        .restartingIdentities();
    ```

=== "Kotlin"

    ```kotlin
    @JvmField
    @RegisterExtension
    val db: RefreshDatabase = RefreshDatabase.rollback(
        { PostgresQuery.of(CONNECTION) }, PostgresSchema::of,
        listOf(CreateUsersTable()))
        .restartingIdentities()
    ```

Before each test, after the migrations and before the test's transaction opens, each identity and `serial` counter of the tables the extension owns is set to the value after its highest committed id, or to the start value when the table is empty. Rows that a migration or a seeder committed are kept, so the first row a test inserts gets the id after them. The reset is not rolled back, because PostgreSQL never rolls a sequence back.

| | PostgreSQL | SQLite |
|---|---|---|
| Rollback alone | The counter keeps moving, so later tests get higher ids. | The counter rolls back with the rows, so ids repeat. |
| With `restartingIdentities()` | Each test starts from the same counter. | Nothing is sent: the option does nothing. |

The option has these limits:

- It needs PostgreSQL 10 or later.
- It sets only the sequences that a column of the tables owns, such as an identity column or a `serial` column. A sequence that no column owns, such as one created on its own and used as a default, is left alone.
- Before each test it sends one query to list the owned sequences, then one query per sequence. It needs permission to change the sequence; the owner of the table has it.
- It is refused with `IllegalStateException` in truncate mode, which already restarts identities.
- It is refused under `ExecutionMode.CONCURRENT`, because the tests share the sequences. Mark the class `@Execution(ExecutionMode.SAME_THREAD)` instead.
- The check sees one JVM. Gradle forks (`maxParallelForks` above 1) that share one database are not detected. Give each fork its own database.
- Each test pays one catalog query plus one `setval` per sequence. Finding the highest id scans the table when the id column has no index, so keep the option for classes that name ids.

## Parameters

A test method may declare these parameters, and the extension fills them:

- `DatabaseAssertions`: the assertions below.
- `QueryFactory`: the query factory you supplied.
- `Connection`: its connection.

`DatabaseAssertions.of(queryFactory)` builds the same object outside JUnit.

## Migrate once per run

The first test class that uses the extension runs `Migrator.fresh()`: it drops every view and table, then runs your migrations. Later classes with the same connection instance and the same migration list reuse that schema. The record is kept in the root store of the JUnit run, so it is shared across classes.

The same connection with a different migration list in the same run is refused with `IllegalStateException`, because migrating again would drop the tables of the classes that already ran. Migrations are compared by class and name, so editing a migration's body inside one run is not noticed.

## One database, one way to migrate

The extension owns the schema of its connection: once per run it drops every table and runs its
list into the default `migrations` table. A test class that runs your application's own migrator,
or one migrator per module, on the same database collides with it: the tables already exist, so
that migrator fails with an error such as `relation "accounts" already exists`, or its `fresh()`
drops the tables the extension built for the other classes. Every class on one database should
use the extension with the same migration list. A class that must migrate another way gets its
own database.

## Assertions

| Method | Passes when |
|---|---|
| `assertHas(table, values)` | A row matches every column in `values`. |
| `assertMissing(table, values)` | No row matches. |
| `assertCount(table, n)` | The table has exactly `n` rows. |
| `assertEmpty(table)` | The table has no rows. |
| `assertModelExists(model)` | The model's row exists, found by its key. |
| `assertModelMissing(model)` | The model's row does not exist. |
| `assertSoftDeleted(model)` | The row exists with its deleted-at column set. |
| `assertNotSoftDeleted(model)` | The row exists with its deleted-at column null. |

All of them throw `AssertionError`. The failure names the table and the columns compared, and shows up to three similar rows out of the total, or says the table is empty. Values of hidden model columns are never printed.

```text
java.lang.AssertionError: No row in [users] matches {name=bob, active=true}.
Similar rows (first 2 of 2): {id=1, name=ann, active=true}, {id=2, name=cy, active=false}
```

## Limits

- Work on another thread does not join the test transaction in rollback mode. Threads and executors the test starts, and a test under `@Timeout(threadMode = SEPARATE_THREAD)`, commit for real and are not rolled back. Use truncate mode for such tests, or clean up yourself.
- `afterCommit` callbacks never fire in rollback mode.
- Truncate mode does not run under parallel JUnit.
- On PostgreSQL, `dropAllTables` drops tables only. Types, sequences and functions that a migration creates stay, so drop them in the migration's `down`, or give the tests a dedicated schema.
- The model assertions need the eloquent module.
- JUnit Jupiter 5.10 or later.
