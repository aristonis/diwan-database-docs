# Android

تعمل Diwan على Android 9 (API 28) وما بعده عبر `diwan-database-android`. هو driver (مشغّل) فوق `SQLiteDatabase` الخاصة بـ Android،
فيعمل schema builder (باني المخطط) والـ migrations وquery builder (باني الاستعلامات) والنماذج كما على سطح المكتب. الوحدة JAR عادي بلا اعتماد وقت تشغيل.

```kotlin
implementation("org.aristonis:diwan-database:0.1.0")
implementation("org.aristonis:diwan-database-android:0.1.0")
implementation("org.aristonis:diwan-database-sqlite:0.1.0")
implementation("org.aristonis:diwan-database-eloquent:0.1.0")   // only if you use models
```

## إعداد الـ driver

مرّر `SQLiteOpenHelper` ودع الـ driver يفتح قاعدة البيانات عند أول استعمال، أو مرّر `SQLiteDatabase` مفتوحة:

```java
public final class AppDb extends SQLiteOpenHelper {
    AppDb(Context context) { super(context, "app.db", null, 1); }

    @Override public void onConfigure(SQLiteDatabase db) {
        db.setForeignKeyConstraintsEnabled(true);   // Android leaves foreign keys off
        db.enableWriteAheadLogging();
    }
    @Override public void onCreate(SQLiteDatabase db) { }
    @Override public void onUpgrade(SQLiteDatabase db, int from, int to) { }
}

DatabaseConfig config = DatabaseConfig.builder()
        .defaultConnection("app")
        .connection(ConnectionConfig.builder("app").driver("android").build())
        .build();

DatabaseManager manager = DatabaseManager.builder()
        .config(config)
        .connector(AndroidConnector.of(() -> new AppDb(context), SQLiteQuery::of, SQLiteSchema::of))
        .build();

manager.migrator("app").migrations(migrations).build().run();
QueryFactory db = manager.query();
```

تفتح `of(SQLiteOpenHelper)` قاعدة البيانات عند أول استدعاء يحتاجها، وهذا الاستدعاء يشغّل `onCreate` أو `onUpgrade` في الـ helper.
اجعل الاستدعاء الأول خارج الـ main thread (خيط تنفيذ). لا يغلق الـ driver قاعدة البيانات أبدًا؛ تطبيقك يملكها.

تأخذ `AndroidConnector.of(...)` الـ factories الخاصة بالـ grammar مرة واحدة هنا. بعد ذلك يطلب كودك من الـ manager الدوال `query()` و`schema()` و`migrator(name)` ولا يذكر أي صنف grammar. ابنِ أول اتصال خارج الـ main thread.

بدون manager ابنِ `Connection` بـ `Connection.builder().name("app").driver(AndroidSqliteDriver.of(new AppDb(context))).build()` واستعمل `SQLiteSchema.of(connection)` و`SQLiteQuery.of(connection)`.

## الـ threads

يربط Android الـ transaction (معاملة) بالـ thread الذي بدأها. تسجّل Diwan ذلك الـ thread وترفض الـ commit (تثبيت المعاملة) أو الـ rollback (تراجع) أو الإغلاق من thread آخر،
فأبقِ callback (دالة يستدعيها النظام) الـ `transaction(...)` كاملًا على thread واحد. لا تبدّل سياق coroutine ولا تسلّم العمل إلى executor داخله.
والـ cursor (مؤشر يقرأ الصفوف واحدًا واحدًا) كذلك: استعمله من الـ thread الذي فتحه فقط.

شغّل عمل قاعدة البيانات خارج الـ main thread. لا تنقله Diwan عنك.

## نوافذ الـ cursor والقراءات الكبيرة

يقرأ Android الصفوف عبر نوافذ (windows) بحجم 2 MB تقريبًا، وتقرأ Diwan النتائج كاملة في الذاكرة إلا عبر `cursor()`. للجداول الكبيرة:

- قسّم القراءة بـ `limit`، أو استعمل `chunkById` و`lazyById`.
- تجنّب `cursor()` على جدول يتغيّر أثناء القراءة. تُعاد تعبئة النافذة بتشغيل الاستعلام من جديد، فقد تُتخطى صفوف متغيّرة أو تتكرر.
- أبعد الـ blobs الكبيرة عن الصفوف التي تستعلم عنها بالجملة.

## الـ Write-ahead logging

`beginTransaction` في Android حصرية (exclusive). بلا write-ahead logging (WAL، سجل الكتابة المسبقة) تمنع transaction طويلة القراءات من threads أخرى.
استدعِ `enableWriteAheadLogging()` في `onConfigure` كما أعلاه، وأبقِ المعاملات قصيرة.

## ما يحتاج Android أحدث

يأتي Android بنسخة SQLite خاصة به، ونسختها تتبع مستوى الـ API.

| الميزة | تحتاج | على Android أقدم |
|---|---|---|
| `upsert` (في query builder والنماذج) | SQLite 3.24، أي API 30 | `UnsupportedOperationException` تسمّي النسخة، قبل أي SQL |
| right join | SQLite 3.39، أي API 34 | خطأ SQLite نفسه ضمن `QueryException` |
| `insertOrIgnore` و`updateOrInsert` | أي نسخة | تعمل |

`updateOrInsert` تقرأ ثم تكتب وليست ذرّية (atomic). على API 28 و29 اكتب قراءة ثم كتابة داخل transaction بدل `upsert`.

## الأعداد العشرية والتواريخ

عمود `decimal` له numeric affinity، فتُقرأ `10.10` على أنها العدد `10.1` من نوع double. للمال الدقيق استعمل عمودًا صحيحًا بوحدات صغرى.
تُخزَّن التواريخ نصًا بصيغة `yyyy-MM-dd HH:mm:ss`، والـ `Instant` نصًا بتوقيت UTC أو ميكروثواني صحيحة، كما في SQLite على سطح المكتب.

## سجل الاستعلامات للتصحيح

```java
Connection connection = Connection.builder()
        .name("app").driver(androidDriver).queryLogLimit(200).build();
if (BuildConfig.DEBUG) {
    connection.events().enableQueryLog();
}
for (LoggedQuery entry : connection.events().getQueryLog()) {
    Log.d("diwan", entry.sql() + " " + entry.bindings());
}
```

## R8 وProGuard

لا تستعمل Diwan reflection (الانعكاس في Java)، وتجد الـ migrations من القائمة التي تعطيها لـ `Migrator` لا بالمسح. الشيء الوحيد الذي قد يكسره R8 (أدوات تصغير الكود وتشويشه في Android) هو قيمة افتراضية
مشتقة من اسم صنف. افعل أحد أمرين:

- مرّر الأسماء صراحةً. تجاوز `table()` في كل نموذج، وأعطِ العلاقات مفاتيحها الأجنبية وجدول pivot (جدول الربط في علاقة متعدد لمتعدد) وأسماء `chaperone`.
- أو احتفظ بأسماء أصناف النماذج:

```
-keepnames class * extends org.aristonis.diwan.database.eloquent.Model
```

سمِّ كل migration (تهجير قاعدة البيانات) بنص ثابت في `name()` (مثل `2026_10_31_000000_create_users_table`) ولا تشتقه من اسم الصنف. ولا تستعمل الـ bytecode المترجم لاكتشاف
migration معدَّلة؛ استعمل `checksum()` بدلًا من ذلك، انظر [التهجيرات](migrations.md).

على Android تستدعي `toMap()` و`push()` و`touchOwners()` نفسها تعاودًا بمقدار مستوى لكل طبقة من الرسم المحمَّل. قد تفيض سلسلة عميقة جدًا في stack صغير،
فحمّلها على أجزاء.

انظر أيضًا [البدء](getting-started.md) و[الاتصالات](connections.md).
