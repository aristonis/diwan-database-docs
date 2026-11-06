# البدء

تأخذك هذه الصفحة من مشروع فارغ إلى جدول مُهجَّر (migrated) واستعلام ونموذج، على SQLite.

## التثبيت

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

مع PostgreSQL استعمل `diwan-database-pgsql` و`org.postgresql:postgresql` بدل زوج SQLite. وعلى Android انظر [Android](android.md).

## افتح اتصالًا

أقصر طريق هو `Connection` مبني فوق أي `javax.sql.DataSource`:

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

القيم تُربط (bound) دائمًا ولا تُلصق في نص SQL أبدًا. وتعود الصفوف خرائط (maps) للقراءة فقط بأعمدة بترتيب الـ select.

إذا كان لتطبيقك أكثر من قاعدة بيانات، أو إعداداته في ملف أو في البيئة، استعمل `DatabaseManager`. يبني كل اتصال مُسمّى عند أول استعمال:

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

الطريقتان مشروحتان في [الاتصالات والمعاملات](connections.md). وبقية هذه الصفحة تستعمل `db` من الطريقة الأولى.

## اكتب migration

الـ `migration` صنف له اسم ودالتا `up` و`down`:

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

شغّله بواسطة `Migrator`:

```java
Migrator migrator = Migrator.builder(SQLiteSchema.of(db))
        .add(new CreateUsersTable())
        .build();

migrator.run();        // creates the migrations table, runs what is pending
migrator.rollback();   // undoes the last batch
```

يسجّل الـ migrator كل تشغيل في جدول `migrations`، فاستدعاء `run()` مرة ثانية لا يفعل شيئًا. انظر [Migrations](migrations.md).

## شغّل استعلامًا

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

المزيد في [Query builder](query-builder.md).

## عرّف نموذجًا

النموذج (model) صنف لكل جدول. لا يحتاج annotations ولا reflection (الانعكاس في Java).

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

اسم الجدول `users`، أي صيغة الجمع بحروف snake-case لاسم الصنف. اربط نقطة الدخول بـ query factory مرة واحدة ثم استعملها:

```java
ModelQuery<User> users = User.query.on(SQLiteQuery.of(db));

User ada = users.create(Map.of("name", "Ada", "email", "ada@example.com"));
User again = users.findOrFail(ada.getKey());

again.setAttribute("name", "Ada L.");
again.save();          // writes name and updated_at only
```

لا شيء قابل للإسناد الجماعي (mass assignment) حتى تدرجه في `fillable()`. وبالإعدادات الافتراضية ترمي `fill` الاستثناء `MassAssignmentException`. انظر [Models](models.md) و[Relations](relations.md).

## بعد ذلك

- [الاتصالات والمعاملات](connections.md) للـ pool (مجمّع الاتصالات) والمعاملات والتسجيل.
- [الأخطاء](errors.md) لمعرفة معنى كل فشل.
