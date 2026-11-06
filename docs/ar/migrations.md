# Migrations

الـ migration (تهجير قاعدة البيانات) هي تغيير واحد في المخطط، مكتوب كصنف Java له خطوة `up` وخطوة `down` اختيارية. يسجل جدول migrations أيّها نُفذ وفي أي batch (دفعة). فالتشغيل التالي يتخطاها، والـ rollback (تراجع) يلغي آخر دفعة.

## كتابة migration

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

ابدأ كل اسم بتاريخه، لأن الـ migrations المعلقة تُنفذ بترتيب الاسم. لا تعِد تسمية migration نُفذت في أي مكان. أنت تسرد الـ migrations في الكود: لا شيء يُكتشف بمسح الـ classpath (مسار الأصناف). لتنفيذ SQL خام داخل `up` أو `down` استخدم `schema.connection()` ليدخل الـ SQL في transaction (معاملة) الخاصة بالـ migration.

ثلاثة overrides اختيارية: `withinTransaction()` للخروج من الـ transaction المحيطة، و`shouldRun()` لتخطي الـ migration، و`connection()` لإرسالها إلى اتصال مسمى آخر.

## التشغيل والتراجع

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

كل استدعاء يعيد `List<MigrationResult>` فيها اسم الـ migration ونتيجتها `Outcome` (وهي `RAN` أو `SKIPPED` أو `ROLLED_BACK` أو `NOT_FOUND` أو `PRETENDED`) ورقم الـ batch والـ SQL الذي نُفذ.

على SQLite وPostgreSQL تُثبَّت الـ migration وسجلها معًا (commit)، فلا يبقى عند الفشل migration نصف منفذة ولا سجل شارد. الفشل يوقف الاستدعاء بـ `MigrationFailedException`. دالتها `completed()` تسرد ما انتهى، و`phase()` تقول هل فشلت الـ migration أم سجلها فقط. ويرفض الـ migrator العمل داخل transaction فتحتها أنت.

### الحالة وpretend

```java
for (MigrationStatus s : migrator.status()) {
    System.out.println(s.name() + " " + s.state() + " " + s.batch());   // RAN, PENDING or MISSING
}
migrator.pretendRun().forEach(r -> System.out.println(r.name() + " " + r.queries()));
migrator.pretendRollback();
migrator.pretendReset();
```

تشغيلات pretend (وضع المعاينة دون تنفيذ) تسرد الـ SQL ولا تغير شيئًا. الـ migration التي تفحص `hasTable` ترى هناك قاعدة فارغة، فقد يختلف الـ SQL عن التشغيل الحقيقي.

### migrations مفقودة

يتوقف rollback وreset بـ `MissingMigrationsException` حين يكون سجل مسجَّل غير موجود في قائمتك، وهذا يعني غالبًا كودًا أقدم يعمل على قاعدة أحدث. لا يُلغى شيء. أضف `allowMissingOnRollback()` إلى الـ builder (باني الكائن) لتلغي المعروفة وتُبقي السجلات المجهولة، كما تفعل Laravel.

### اتصالات أخرى واسم الجدول

```java
Migrator migrator = Migrator.builder(mainSchema)
        .connection("reports", reportsSchema)     // a migration whose connection() returns "reports"
        .table("schema_migrations")               // the default is "migrations"
        .migrations(List.of(new CreateUsersTable(), new CreateReportsTable()))
        .build();
```

## الأحداث (Events)

الـ `MigrationListener` يراقب عمل الـ migrator. كل دالة فيه اختيارية.

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

لا شيء يمنع عمليتين من التهجير معًا ما لم تضف قفلًا. لدى PostgreSQL قفل مبني على advisory lock (قفل استشاري في PostgreSQL).

```java
Migrator migrator = Migrator.builder(PostgresSchema.of(db))
        .lock(new PostgresMigrationLock(dataSource))     // waits up to 60 seconds by default
        .add(new CreateUsersTable())
        .build();
```

لقاعدة أخرى، نفّذ الواجهة `MigrationLock` (الدالتان `acquire()` و`release()`).

## الـ Checksums

افتراضيًا يمكن تعديل migration نُفذت دون أن يلاحظ أحد. تجاوز `checksum()` لتفعّل الفحص.

```java
@Override
public Optional<String> checksum() {
    return Optional.of("v2");     // a label you bump on purpose, or MigrationChecksum.of(text)
}
```

الدالة `MigrationChecksum.of(String)` تعيد SHA-256 (دالة تجزئة) بصيغة hex للنص، بعد تحويل نهايات الأسطر إلى `\n` وتوحيد الحروف المعلَّمة بصيغة Unicode NFC، فلا يهم كيف حُفظ الملف. لا يحسب Diwan hash للكود المترجم أبدًا، لأنه يتغير بين المترجمات وأدوات التصغير.

- التشغيل يسجل الـ checksum (بصمة رقمية للتهجير) في جدول migrations.
- قبل التشغيل أو تشغيل pretend، يقارن الـ migrator كل migration نُفذت ولها checksum مسجل وآخر معلن. إذا اختلف أي منها ترمي `MigrationChecksumException` قائمةً بها كلها ولا يُنفذ شيء.
- الـ migration التي لا تعلن شيئًا لا تُفحص أبدًا. والتي تبدأ بإعلان checksum يُسجل لها في التشغيل التالي.
- لقبول تعديل مقصود استدعِ `migrator.repairChecksums(migrator.migrations())`. ولمسح كل checksum مسجل استدعِ `migrator.clearChecksums()`. كلتاهما تأخذ قفل الـ migration ولا تطلق أحداثًا.

جدول migrations الذي أُنشئ قبل وجود عمود checksum لا يملكه، ولا يعدّل Diwan الجداول وقت التشغيل. أول استدعاء يحتاج العمود يرمي `IllegalStateException` تتضمن الجملة الوحيدة المطلوب تنفيذها: `alter table migrations add column checksum varchar(64)`. هذا ينطبق فقط على قواعد أُنشئت ببناء تجريبي سابق للإصدار.

## الـ Seeders

الـ seeder (مُغذّي بيانات البداية) يملأ الجداول ببيانات البداية. ورّث `Seeder` واستخدم `SeedContext`.

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

تستطيع `SeedOptions` اختيار اتصال مسمى، ولف التشغيل كله في transaction واحدة، وإضافة `SeederListener`. والـ seeder الذي يستدعي نفسه، مباشرة أو عبر غيره، يرمي `IllegalStateException` تذكر السلسلة.

التالي: [Models](models.md)، [الأخطاء والاستثناءات](errors.md).
