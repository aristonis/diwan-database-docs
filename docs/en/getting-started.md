# Getting started

This page takes you from an empty project to a migrated table, a query and a model, on SQLite.

## Install

Gradle (Kotlin DSL):

```kotlin
dependencies {
    implementation("org.aristonis:diwan-database:0.1.0")
    implementation("org.aristonis:diwan-database-sqlite:0.1.0")
    implementation("org.aristonis:diwan-database-eloquent:0.1.0")   // only if you use models
    runtimeOnly("org.xerial:sqlite-jdbc:3.54.1.0")                  // the JDBC driver
}
```

Maven:

```xml
<dependency>
  <groupId>org.aristonis</groupId>
  <artifactId>diwan-database</artifactId>
  <version>0.1.0</version>
</dependency>
<dependency>
  <groupId>org.aristonis</groupId>
  <artifactId>diwan-database-sqlite</artifactId>
  <version>0.1.0</version>
</dependency>
<dependency>
  <groupId>org.aristonis</groupId>
  <artifactId>diwan-database-eloquent</artifactId>
  <version>0.1.0</version>
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

The shortest route is a `Connection` built over any `javax.sql.DataSource`:

```java
import org.aristonis.diwan.database.Connection;
import org.aristonis.diwan.database.jdbc.DriverManagerDataSource;

Connection db = Connection.builder()
        .name("main")
        .dataSource(new DriverManagerDataSource("jdbc:sqlite:app.db", null, null))
        .build();

db.statement("create table notes (id integer primary key, body text not null)");
db.insert("insert into notes (body) values (?)", "hello");
List<Map<String, Object>> rows = db.select("select id, body from notes");
```

Values are always bound, never pasted into the SQL. Rows come back as read-only maps with columns in select order.

For an application with more than one database, or with settings in a file or the environment, use `DatabaseManager`. It builds each named connection on first use:

```java
DatabaseConfig config = DatabaseConfig.from(MapConfigSource.of(Map.of(
        "database.default", "main",
        "database.connections.main.driver", "sqlite",
        "database.connections.main.database", "app.db")));

DatabaseManager manager = DatabaseManager.builder()
        .config(config)
        .connector(new SQLiteConnector())
        .build();

Connection main = manager.connection();
QueryFactory query = manager.query();
Schema schema = manager.schema();
```

Both routes are covered in [Connections and transactions](connections.md). The rest of this page uses `db` from the first one.

## Write a migration

A migration is a class with a name, an `up` and a `down`:

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

Run it with a `Migrator`:

```java
Migrator migrator = Migrator.builder(SQLiteSchema.of(db))
        .add(new CreateUsersTable())
        .build();

migrator.run();        // creates the migrations table, runs what is pending
migrator.rollback();   // undoes the last batch
```

The migrator records each run in a `migrations` table, so `run()` a second time does nothing. See [Migrations](migrations.md).

## Run a query

```java
QueryFactory query = SQLiteQuery.of(db);

Object id = query.table("users").insertGetId(Map.of(
        "name", "Ada", "email", "ada@example.com"));

List<Map<String, Object>> found = query.table("users")
        .where("email", "like", "%@example.com")
        .orderByDesc("id")
        .limit(10)
        .get();

long total = query.table("users").count();
query.table("users").where("id", id).update(Map.of("name", "Ada L."));
```

More in [Query builder](query-builder.md).

## Define a model

A model is a class per table. It needs no annotations and no reflection.

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

The table is `users`, the snake-case plural of the class name. Bind the entry to a query factory once, then use it:

```java
ModelQuery<User> users = User.query.on(SQLiteQuery.of(db));

User ada = users.create(Map.of("name", "Ada", "email", "ada@example.com"));
User again = users.findOrFail(ada.getKey());

again.setAttribute("name", "Ada L.");
again.save();          // writes name and updated_at only
```

Nothing is mass assignable until you list it in `fillable()`. With the defaults, `fill` throws `MassAssignmentException`. See [Models](models.md) and [Relations](relations.md).

## Next

- [Connections and transactions](connections.md) for pools, transactions and logging.
- [Errors](errors.md) for what each failure means.
