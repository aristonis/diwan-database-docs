# Migrations

الـ migration (تهجير قاعدة البيانات) هي تغيير واحد في المخطط، مكتوب كصنف Java له خطوة `up` وخطوة `down` اختيارية. يسجل جدول migrations أيّها نُفذ وفي أي batch (دفعة). فالتشغيل التالي يتخطاها، والـ rollback (تراجع) يلغي آخر دفعة.

## كتابة migration

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

ابدأ كل اسم بتاريخه، لأن الـ migrations المعلقة تُنفذ بترتيب الاسم. لا تعِد تسمية migration نُفذت في أي مكان. أنت تسرد الـ migrations في الكود: لا شيء يُكتشف بمسح الـ classpath (مسار الأصناف). لتنفيذ SQL خام داخل `up` أو `down` استخدم `schema.connection()` ليدخل الـ SQL في transaction (معاملة) الخاصة بالـ migration.

ثلاثة overrides اختيارية: `withinTransaction()` للخروج من الـ transaction المحيطة، و`shouldRun()` لتخطي الـ migration، و`connection()` لإرسالها إلى اتصال مسمى آخر.

### الترتيب

تُنفَّذ الـ migrations المعلقة دائمًا مرتبة بالاسم، أيًّا كان الترتيب الذي أضفتها به. القائمة المبنية من عدة modules هي قائمة واحدة عند الـ migrator، فتُدمج بالاسم أيضًا: إن كانت أسماء migrations الـ module ب تُرتَّب قبل أسماء الـ module أ، وكان جدول في ب يشير إلى جدول في أ، فستُنفذ migration ب أولًا وتفشل بخطأ مثل `relation "accounts" does not exist`. سمِّ الـ migrations بحيث يتبع الترتيبُ الاعتمادياتِ، مثلًا بتاريخ كتابتها، أو ببادئة لكل module تُرتَّب بحسب الاعتماد.

```text
2026_01_10_000000_create_accounts_table   (module أ، تُنفذ أولًا)
2026_01_12_000000_create_entries_table    (module ب، تشير إلى accounts)
```

الـ rollback والـ reset يسيران بالعكس: آخر batch أولًا، وداخل الـ batch الاسم الأعلى أولًا. لا يوجد خيار للتنفيذ بترتيب القائمة.

## التشغيل والتراجع

تعيد `manager.migrator(name)` كائن `Migrator.Builder` لذلك الاتصال، مبنيًا من إعداده. بدون manager استعمل `Migrator.builder(SQLiteSchema.of(connection))` أو ما يقابله في `PostgresSchema`.

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

كل استدعاء يعيد `List<MigrationResult>` فيها اسم الـ migration ونتيجتها `Outcome` (وهي `RAN` أو `SKIPPED` أو `ROLLED_BACK` أو `NOT_FOUND` أو `PRETENDED`) ورقم الـ batch والـ SQL الذي نُفذ.

على SQLite وPostgreSQL تُثبَّت الـ migration وسجلها معًا (commit)، فلا يبقى عند الفشل migration نصف منفذة ولا سجل شارد. الفشل يوقف الاستدعاء بـ `MigrationFailedException`. دالتها `completed()` تسرد ما انتهى، و`phase()` تقول هل فشلت الـ migration أم سجلها فقط. ويرفض الـ migrator العمل داخل transaction فتحتها أنت.

### البدء من الصفر

=== "Java"

    ```java
    migrator.fresh();     // drop every view and table, then run all migrations
    ```

=== "Kotlin"

    ```kotlin
    migrator.fresh()     // drop every view and table, then run all migrations
    ```

تستدعي `fresh()` الدالتين `schema.dropAllViews()` و`schema.dropAllTables()`، ومنها جدول الـ migrations، ثم `run()`، وتعيد ما تعيده `run()`. استعملها لقواعد الاختبار والقواعد المحلية، لا لقاعدة منشورة. انظر [الـ Schema builder](schema.md#list-and-drop-everything) لما يُحذف، و[الاختبار](testing.md) للـ extension الذي يستدعيها.

### الحالة وpretend

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

تشغيلات pretend (وضع المعاينة دون تنفيذ) تسرد الـ SQL ولا تغير شيئًا. الـ migration التي تفحص `hasTable` ترى هناك قاعدة فارغة، فقد يختلف الـ SQL عن التشغيل الحقيقي.

### migrations مفقودة

يتوقف rollback وreset بـ `MissingMigrationsException` حين يكون سجل مسجَّل غير موجود في قائمتك، وهذا يعني غالبًا كودًا أقدم يعمل على قاعدة أحدث. لا يُلغى شيء. أضف `allowMissingOnRollback()` إلى الـ builder (باني الكائن) لتلغي المعروفة وتُبقي السجلات المجهولة، كما تفعل Laravel.

### اتصالات أخرى واسم الجدول

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

جدول الـ migrations أعمدته `id` و`migration` (الاسم، حتى 191 حرفًا، فريد) و`batch` و`checksum` (حتى 64 حرفًا، يقبل null). لقراءة الأسماء المنفّذة استعمل `migrator.status()` أو `migrator.repository().getRan()`، لا SQL.

## الأحداث (Events)

الـ `MigrationListener` يراقب عمل الـ migrator. كل دالة فيه اختيارية.

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

| الدالة | متى تُستدعى |
|---|---|
| `migrationsStarted` | مرة واحدة، قبل أول migration في تشغيل أو rollback أو reset |
| `noPendingMigrations` | بدل السابقة، حين لا يوجد ما يُنفذ |
| `migrationStarted`, `migrationEnded` | حول migration واحدة |
| `migrationSkipped` | عند الصعود، حين تكون `shouldRun()` تساوي `false` |
| `migrationFailed` | حين تفشل migration أو سجلها، قبل رمي الاستثناء مباشرة |
| `migrationsEnded` | مرة واحدة، بعد آخر migration في استدعاء نجح |

الـ `MigrationEvent` يحمل الاتجاه والاسم ورقم الـ batch وعلامة pretend واسم الاتصال. والـ `MigrationsEvent` يحمل الاتجاه وعلامة pretend واسم الاتصال. تُستدعى الـ listeners بترتيب تسجيلها على الـ thread (خيط تنفيذ) المستدعي. استثناء من `migrationsStarted` أو `migrationStarted` يوقف الاستدعاء قبل ذلك العمل. ومن أحداث "الانتهاء" الأخرى ينتشر بعد تسجيل العمل. ومن `migrationFailed` يُضاف كـ suppressed إلى `MigrationFailedException`. في Laravel تمر هذه الأحداث عبر dispatcher (موزّع الأحداث) التطبيق وليس فيها حدث للفشل. هنا تسجل الـ listener (مستمع للأحداث) على الـ builder.

## قفل الـ migration (Migration lock)

لا شيء يمنع عمليتين من التهجير معًا ما لم يكن هناك قفل ممسوك. يأخذ الـ migrator القفل قبل كل تشغيل أو تراجع أو reset، ويعيده حين ينتهي الاستدعاء، نجح أو فشل. استدعاءات الحالة وpretend لا تأخذ قفلًا. ونوع القفل يتبع قاعدة البيانات:

| قاعدة البيانات | القفل | أين يعيش القفل |
|---|---|---|
| PostgreSQL | `PostgresMigrationLock`، وهو advisory lock (قفل استشاري في PostgreSQL) على مستوى الجلسة (session) | جلسة على الخادم. إذا مات التطبيق أنهى الخادم الجلسة وحرّر القفل. |
| SQLite أو Android مع ملف قاعدة بيانات | `FileMigrationLock` | ملف بجانب قاعدة البيانات اسمه `<database>.migrate.lock`. يحرره نظام التشغيل إذا مات التطبيق. يبقى الملف في مكانه بعد كل تشغيل. |
| SQLite أو Android في الذاكرة | لا قفل | لا شيء يُشارَك مع عملية أخرى، فلا يوجد ما يُقفل. |

يمنح الـ manager كل اتصال قفله، كما في الأمثلة أدناه. مدة الانتظار 60 ثانية افتراضيًا. على SQLite وAndroid يحددها الخيار `lock_wait`، مثل `5s` أو `500ms`. على PostgreSQL يضبط `lock_wait` الـ `lock_timeout` للجلسات، ويبقى للقفل مدة انتظاره الخاصة وهي 60 ثانية، ويمكن تغييرها بـ `PostgresMigrationLock(dataSource, name, wait, unit)`.

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

بدون manager ابنِ الـ migrator على وحدة الـ grammar ومرّر القفل بنفسك:

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

على SQLite وAndroid مرّر `new FileMigrationLock(() -> databaseFile)` بالطريقة نفسها.

بعض التفاصيل التي تنطبق على الأقفال أعلاه:

- داخل الـ JVM الواحدة يأخذ الـ migrators دورهم على القفل نفسه أيضًا، فينتظر الثاني الأول.
- قد تتجاهل أنظمة الملفات الشبكية (network file systems) أقفال الملفات، فلا يحمي القفل شيئًا حينها. أبقِ ملف SQLite الذي يُهاجَر على قرص محلي.
- على Android، يفتح القفل قاعدة البيانات أولًا، فيعمل `onCreate` أو `onUpgrade` الخاص بالـ helper قبل أن يُؤخذ القفل. ضع تغييرات المخطط في الـ migrations، لا في الـ helper.
- الـ `DataSource` الذي تزوّده يأخذ قفل الملف فقط إذا ذكر الإعداد `database` أو `url` الملف. من دون أيّ منهما لا يكون لذلك الاتصال قفل.
- يمسك قفل PostgreSQL جلسة واحدة من الـ pool طوال التشغيل، والـ migrator يحتاج جلسة أخرى، لذلك يجب أن يسمح الـ pool بجلستين على الأقل. مع pool من جلسة واحدة ينتظر الـ migrator مهلة الـ pool نفسها ثم يفشل، ويحمل الخطأ ملاحظة (suppressed exception) تقول إن الـ pool يحتاج جلستين.
- على PostgreSQL استخدم اسم قفل واحدًا لكل جدول migrations. الـ migrators على الجدول نفسه تشترك في الاسم، والجداول المختلفة يُفضَّل أن تختلف أسماؤها، وإلا انتظرت بعضها. عبر الـ manager يستخدم كل اتصال الاسم الافتراضي `diwan-migrations`، فابنِ القفل بنفسك بـ `new PostgresMigrationLock(dataSource, name)` لإعطاء جدول اسمه الخاص.

لقاعدة أخرى، نفّذ الواجهة `MigrationLock` (الدالتان `acquire()` و`release()`). وأضف `explain(RuntimeException)` إذا كان القفل قادرًا على تفسير سبب فشل التشغيل؛ والافتراضي لا يفعل شيئًا.

## الـ Checksums

الـ migration المنشور مقفل: لا تعدّله أبدًا ولا تغيّر checksum الخاص به. غيّر الـ schema بـ migration جديد.

الدالة `checksum()` تعيد قيمة ثابتة لذلك الـ migration، تُضبط مرة واحدة. هي تكشف تعديلًا عرضيًا؛ وليست رقم إصدار. افتراضيًا يمكن تعديل migration نُفذت دون أن يلاحظ أحد، لذا تجاوز `checksum()` لتفعّل الفحص.

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

الدالة `MigrationChecksum.of(String)` تعيد SHA-256 (دالة تجزئة) بصيغة hex للنص، بعد تحويل نهايات الأسطر إلى `\n` وتوحيد الحروف المعلَّمة بصيغة Unicode NFC، فلا يهم كيف حُفظ الملف. لا يحسب Diwan hash للكود المترجم أبدًا، لأنه يتغير بين المترجمات وأدوات التصغير.

- التشغيل يسجل الـ checksum (بصمة رقمية للتهجير) في جدول migrations.
- قبل التشغيل أو تشغيل pretend، يقارن الـ migrator كل migration نُفذت ولها checksum مسجل وآخر معلن. إذا اختلف أي منها ترمي `MigrationChecksumException` قائمةً بها كلها ولا يُنفذ شيء.
- الـ migration التي لا تعلن شيئًا لا تُفحص أبدًا. والتي تبدأ بإعلان checksum يُسجل لها في التشغيل التالي.
- للاسترداد فقط، في قاعدة محلية لم تُنشر قط أو بعد حادث معروف: استدعِ `migrator.repairChecksums(migrator.migrations())` لإعادة كتابة كل checksum مسجل بالمعلن، أو `migrator.clearChecksums()` لمسح كل checksum مسجل. كلتاهما تأخذ قفل الـ migration ولا تطلق أحداثًا.

## الـ Seeders

الـ seeder (مُغذّي بيانات البداية) يملأ الجداول ببيانات البداية. ورّث `Seeder` واستخدم `SeedContext`.

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

تستطيع `SeedOptions` اختيار اتصال مسمى، ولف التشغيل كله في transaction واحدة، وإضافة `SeederListener`. والـ seeder الذي يستدعي نفسه، مباشرة أو عبر غيره، يرمي `IllegalStateException` تذكر السلسلة.

التالي: [Models](models.md)، [الأخطاء والاستثناءات](errors.md).

## مرجع الدوال

الدوال العامة التي لا تغطيها الأقسام السابقة، بصف واحد لكل اسم دالة (الـ overloads في صف واحد).

| الدالة | على | ماذا تفعل | مثال |
|---|---|---|---|
| `repository` | `Migrator` | تعيد repository جدول الـ migrations على الاتصال الافتراضي. | `migrator.repository()` |
