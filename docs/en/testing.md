# Testing

The `diwan-database-testing` module gives every JUnit 5 test an empty database with your migrations applied, and a set of assertions for reading the result.

## Add the module

Add it to the test scope only.

=== "Gradle (Kotlin)"

    ```kotlin
    dependencies {
        testImplementation("org.aristonis:diwan-database-testing:0.3.0")
    }
    ```

=== "Gradle (Groovy)"

    ```groovy
    dependencies {
        testImplementation 'org.aristonis:diwan-database-testing:0.3.0'
    }
    ```

=== "Maven"

    ```xml
    <dependency>
      <groupId>org.aristonis</groupId>
      <artifactId>diwan-database-testing</artifactId>
      <version>0.3.0</version>
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

## Parameters

A test method may declare these parameters, and the extension fills them:

- `DatabaseAssertions`: the assertions below.
- `QueryFactory`: the query factory you supplied.
- `Connection`: its connection.

`DatabaseAssertions.of(queryFactory)` builds the same object outside JUnit.

## Migrate once per run

The first test class that uses the extension runs `Migrator.fresh()`: it drops every view and table, then runs your migrations. Later classes with the same connection instance and the same migration list reuse that schema. The record is kept in the root store of the JUnit run, so it is shared across classes.

The same connection with a different migration list in the same run is refused with `IllegalStateException`, because migrating again would drop the tables of the classes that already ran. Migrations are compared by class and name, so editing a migration's body inside one run is not noticed.

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
