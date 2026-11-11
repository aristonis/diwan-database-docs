# Getting started

This page takes you from an empty project to a migrated table, a query and a model, on SQLite.

## Install

=== "Gradle (Kotlin)"

    ```kotlin
    dependencies {
        implementation("org.aristonis:diwan-database:0.4.0")
        implementation("org.aristonis:diwan-database-sqlite:0.4.0")
        implementation("org.aristonis:diwan-database-eloquent:0.4.0")   // only if you use models
        runtimeOnly("org.xerial:sqlite-jdbc:3.54.1.0")                  // the JDBC driver
    }
    ```

=== "Gradle (Groovy)"

    ```groovy
    dependencies {
        implementation 'org.aristonis:diwan-database:0.4.0'
        implementation 'org.aristonis:diwan-database-sqlite:0.4.0'
        implementation 'org.aristonis:diwan-database-eloquent:0.4.0'   // only if you use models
        runtimeOnly 'org.xerial:sqlite-jdbc:3.54.1.0'                  // the JDBC driver
    }
    ```

=== "Maven"

    ```xml
    <dependency>
      <groupId>org.aristonis</groupId>
      <artifactId>diwan-database</artifactId>
      <version>0.4.0</version>
    </dependency>
    <dependency>
      <groupId>org.aristonis</groupId>
      <artifactId>diwan-database-sqlite</artifactId>
      <version>0.4.0</version>
    </dependency>
    <dependency>
      <groupId>org.aristonis</groupId>
      <artifactId>diwan-database-eloquent</artifactId>
      <version>0.4.0</version>
    </dependency>
    <dependency>
      <groupId>org.xerial</groupId>
      <artifactId>sqlite-jdbc</artifactId>
      <version>3.54.1.0</version>
      <scope>runtime</scope>
    </dependency>
    ```

For PostgreSQL, use `diwan-database-pgsql` and `org.postgresql:postgresql` instead of the SQLite pair. On Android, see [Android](android.md).

## Open a connection

Describe the database in configuration and let `DatabaseManager` build the connection on first use. Your code never names a driver class, so moving to PostgreSQL later is a configuration change (`driver` is `pgsql`, plus a host) and the code below stays the same.

=== "Java"

    ```java
    import org.aristonis.diwan.database.manager.DatabaseManager;

    DatabaseConfig config = DatabaseConfig.from(MapConfigSource.of(Map.of(
            "database.default", "main",
            "database.connections.main.driver", "sqlite",
            "database.connections.main.database", "app.db")));

    DatabaseManager manager = DatabaseManager.builder()
            .config(config)
            .connector(new SQLiteConnector())
            .build();

    QueryFactory db = manager.query();      // the default connection
    Schema schema = manager.schema();
    ```

=== "Kotlin"

    ```kotlin
    import org.aristonis.diwan.database.manager.DatabaseManager

    val config = DatabaseConfig.from(MapConfigSource.of(mapOf(
        "database.default" to "main",
        "database.connections.main.driver" to "sqlite",
        "database.connections.main.database" to "app.db")))

    val manager = DatabaseManager.builder()
        .config(config)
        .connector(SQLiteConnector())
        .build()

    val db = manager.query()      // the default connection
    val schema = manager.schema()
    ```

Run raw SQL through the connection, with values bound and never pasted into the SQL:

=== "Java"

    ```java
    Connection conn = manager.connection();
    conn.statement("create table notes (id integer primary key, body text not null)");
    conn.insert("insert into notes (body) values (?)", "hello");
    List<Map<String, Object>> rows = conn.select("select id, body from notes");
    ```

=== "Kotlin"

    ```kotlin
    val conn = manager.connection()
    conn.statement("create table notes (id integer primary key, body text not null)")
    conn.insert("insert into notes (body) values (?)", "hello")
    val rows = conn.select("select id, body from notes")
    ```

Rows come back as read-only maps with columns in select order. The rest of this page uses `manager` and `db` from above. Configuration keys, several named connections and pools are in [Connections and transactions](connections.md).

### Without a manager

For a script or a test you can build a `Connection` over any `javax.sql.DataSource` and take the factories from the grammar module:

=== "Java"

    ```java
    Connection conn = Connection.builder()
            .name("main")
            .dataSource(new DriverManagerDataSource("jdbc:sqlite:app.db", null, null))
            .build();
    QueryFactory db = SQLiteQuery.of(conn);        // PostgresQuery.of(conn) on PostgreSQL
    Schema schema = SQLiteSchema.of(conn);
    ```

=== "Kotlin"

    ```kotlin
    val conn = Connection.builder()
        .name("main")
        .dataSource(DriverManagerDataSource("jdbc:sqlite:app.db", null, null))
        .build()
    val db = SQLiteQuery.of(conn)        // PostgresQuery.of(conn) on PostgreSQL
    val schema = SQLiteSchema.of(conn)
    ```

## Write a migration

A migration is a class with a name, an `up` and a `down`:

=== "Java"

    ```java
    import org.aristonis.diwan.database.migrations.Migration;
    import org.aristonis.diwan.database.schema.Schema;

    final class CreateUsersTable extends Migration {
        @Override
        public String name() {
            return "2026_11_01_000000_create_users_table";
        }

        @Override
        public void up(Schema schema) {
            schema.create("users", table -> {
                table.id();
                table.string("name");
                table.string("email").unique();
                table.timestamps();
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
        override fun name() = "2026_11_01_000000_create_users_table"

        override fun up(schema: Schema) {
            schema.create("users") { table ->
                table.id()
                table.string("name")
                table.string("email").unique()
                table.timestamps()
            }
        }

        override fun down(schema: Schema) {
            schema.drop("users")
        }
    }
    ```

Run it with a `Migrator`:

=== "Java"

    ```java
    Migrator migrator = manager.migrator("main")
            .add(new CreateUsersTable())
            .build();

    migrator.run();        // creates the migrations table, runs what is pending
    migrator.rollback();   // undoes the last batch
    ```

=== "Kotlin"

    ```kotlin
    val migrator = manager.migrator("main")
        .add(CreateUsersTable())
        .build()

    migrator.run()        // creates the migrations table, runs what is pending
    migrator.rollback()   // undoes the last batch
    ```

The migrator records each run in a `migrations` table, so `run()` a second time does nothing. See [Migrations](migrations.md).

## Run a query

=== "Java"

    ```java
    Object id = db.table("users").insertGetId(Map.of(
            "name", "Ada", "email", "ada@example.com"));

    List<Map<String, Object>> found = db.table("users")
            .where("email", "like", "%@example.com")
            .orderByDesc("id")
            .limit(10)
            .get();

    long total = db.table("users").count();
    db.table("users").where("id", id).update(Map.of("name", "Ada L."));
    ```

=== "Kotlin"

    ```kotlin
    val id = db.table("users").insertGetId(mapOf(
        "name" to "Ada", "email" to "ada@example.com"))

    val found = db.table("users")
        .where("email", "like", "%@example.com")
        .orderByDesc("id")
        .limit(10)
        .get()

    val total = db.table("users").count()
    db.table("users").where("id", id).update(mapOf("name" to "Ada L."))
    ```

More in [Query builder](query-builder.md).

## Define a model

A model is a class per table. It needs no annotations and no reflection.

=== "Java"

    ```java
    import org.aristonis.diwan.database.eloquent.Model;
    import org.aristonis.diwan.database.eloquent.ModelQuery;

    public final class User extends Model {
        public static final ModelQuery<User> query = ModelQuery.of(User.class, User::new);

        @Override
        protected List<String> fillable() {
            return List.of("name", "email");
        }
    }
    ```

=== "Kotlin"

    ```kotlin
    import org.aristonis.diwan.database.eloquent.Model
    import org.aristonis.diwan.database.eloquent.ModelQuery

    class User : Model() {
        override fun fillable(): List<String> = listOf("name", "email")

        companion object {
            val query: ModelQuery<User> = ModelQuery.of(User::class.java, ::User)
        }
    }
    ```

The table is `users`, the snake-case plural of the class name. Bind the entry to a query factory once, then use it:

=== "Java"

    ```java
    ModelQuery<User> users = User.query.on(db);

    User ada = users.create(Map.of("name", "Ada", "email", "ada@example.com"));
    User again = users.findOrFail(ada.getKey());

    again.setAttribute("name", "Ada L.");
    again.save();          // writes name and updated_at only
    ```

=== "Kotlin"

    ```kotlin
    val users = User.query.on(db)

    val ada = users.create(mapOf("name" to "Ada", "email" to "ada@example.com"))
    val again = users.findOrFail(ada.key)

    again.setAttribute("name", "Ada L.")
    again.save()          // writes name and updated_at only
    ```

Nothing is mass assignable until you list it in `fillable()`. With the defaults, `fill` throws `MassAssignmentException`. See [Models](models.md) and [Relations](relations.md).

## Next

- [Connections and transactions](connections.md) for pools, transactions and logging.
- [Errors](errors.md) for what each failure means.
