# البدء

تأخذك هذه الصفحة من مشروع فارغ إلى جدول مُهجَّر (migrated) واستعلام ونموذج، على SQLite.

## التثبيت

=== "Gradle (Kotlin)"

    ```kotlin
    dependencies {
        implementation("org.aristonis:diwan-database:0.5.0")
        implementation("org.aristonis:diwan-database-sqlite:0.5.0")
        implementation("org.aristonis:diwan-database-eloquent:0.5.0")   // only if you use models
        runtimeOnly("org.xerial:sqlite-jdbc:3.54.1.0")                  // the JDBC driver
    }
    ```

=== "Gradle (Groovy)"

    ```groovy
    dependencies {
        implementation 'org.aristonis:diwan-database:0.5.0'
        implementation 'org.aristonis:diwan-database-sqlite:0.5.0'
        implementation 'org.aristonis:diwan-database-eloquent:0.5.0'   // only if you use models
        runtimeOnly 'org.xerial:sqlite-jdbc:3.54.1.0'                  // the JDBC driver
    }
    ```

=== "Maven"

    ```xml
    <dependency>
      <groupId>org.aristonis</groupId>
      <artifactId>diwan-database</artifactId>
      <version>0.5.0</version>
    </dependency>
    <dependency>
      <groupId>org.aristonis</groupId>
      <artifactId>diwan-database-sqlite</artifactId>
      <version>0.5.0</version>
    </dependency>
    <dependency>
      <groupId>org.aristonis</groupId>
      <artifactId>diwan-database-eloquent</artifactId>
      <version>0.5.0</version>
    </dependency>
    <dependency>
      <groupId>org.xerial</groupId>
      <artifactId>sqlite-jdbc</artifactId>
      <version>3.54.1.0</version>
      <scope>runtime</scope>
    </dependency>
    ```

مع PostgreSQL استعمل `diwan-database-pgsql` و`org.postgresql:postgresql` بدل زوج SQLite. وعلى Android انظر [Android](android.md).

## افتح اتصالًا

صِف قاعدة البيانات في الإعداد ودع `DatabaseManager` يبني الاتصال عند أول استعمال. لا يذكر كودك أي صنف driver، فالانتقال إلى PostgreSQL لاحقًا تغيير في الإعداد فقط (`driver` يصبح `pgsql` مع host)، ويبقى الكود أدناه كما هو.

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

شغّل SQL الخام عبر الاتصال، والقيم تُربط (bound) ولا تُلصق في نص SQL أبدًا:

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

تعود الصفوف خرائط (maps) للقراءة فقط بأعمدة بترتيب الـ select. وبقية هذه الصفحة تستعمل `manager` و`db` من أعلاه. مفاتيح الإعداد وتعدد الاتصالات المُسمّاة والـ pool في [الاتصالات والمعاملات](connections.md).

### بدون manager

في سكربت أو اختبار يمكنك بناء `Connection` فوق أي `javax.sql.DataSource` وأخذ الـ factories من وحدة الـ grammar:

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

## اكتب migration

الـ `migration` صنف له اسم ودالتا `up` و`down`:

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

شغّله بواسطة `Migrator`:

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

يسجّل الـ migrator كل تشغيل في جدول `migrations`، فاستدعاء `run()` مرة ثانية لا يفعل شيئًا. انظر [Migrations](migrations.md).

## شغّل استعلامًا

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

المزيد في [Query builder](query-builder.md).

## عرّف نموذجًا

النموذج (model) صنف لكل جدول. لا يحتاج annotations ولا reflection (الانعكاس في Java).

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

اسم الجدول `users`، أي صيغة الجمع بحروف snake-case لاسم الصنف. اربط نقطة الدخول بـ query factory مرة واحدة ثم استعملها:

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

لا شيء قابل للإسناد الجماعي (mass assignment) حتى تدرجه في `fillable()`. وبالإعدادات الافتراضية ترمي `fill` الاستثناء `MassAssignmentException`. انظر [Models](models.md) و[Relations](relations.md).

## بعد ذلك

- [الاتصالات والمعاملات](connections.md) للـ pool (مجمّع الاتصالات) والمعاملات والتسجيل.
- [الأخطاء](errors.md) لمعرفة معنى كل فشل.
