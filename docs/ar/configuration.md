# مرجع الإعدادات

كل مفتاح إعداد يقرؤه Diwan في مكان واحد. المفاتيح نفسها مع Maven وGradle: يقرؤها Diwan وقت التشغيل من ملف properties أو من متغيرات البيئة أو من map، فلا يعتمد شيء هنا على أداة البناء.

ضع ملف properties في `src/main/resources` (مثل `database.properties`)، وملف الاختبارات فقط في `src/test/resources`. المجلدان واحد مع Maven وGradle، وكلاهما يصل إلى classpath. حمّل الملف بـ `PropertiesConfigSource.fromClasspath("database.properties")`، أو من مسار بـ `PropertiesConfigSource.of(Path.of(...))`.

القيمة الخاطئة ترمي `DatabaseConfigException`، وهو يسمّي الاتصال والمفتاح ولا يطبع القيمة أبدًا، فلا تصل كلمة سر خاطئة الكتابة إلى سجل (log).

## مصادر الإعدادات والأسبقية

`ConfigSource` يجيب عن سؤال واحد: ما قيمة هذا المفتاح. و`DatabaseConfig.from(source)` يقرأ منه كل المفاتيح أدناه.

| المصدر | يقرأ من | ملاحظات |
|---|---|---|
| `PropertiesConfigSource` | ملف `.properties`: `Path` أو `InputStream` أو مورد classpath | يُقرأ بترميز UTF-8. ملف غير موجود يرمي `UncheckedIOException`. |
| `EnvConfigSource` | متغيرات البيئة (`EnvConfigSource.system()`) أو map تعطيها (`EnvConfigSource.of(map)`) | يُبحث عن المفتاح كما كُتب أولًا، ثم بصيغته الكبيرة مع استبدال كل `.` بـ `_`. المفتاح `database.connections.main.password` يقرأ `DATABASE_CONNECTIONS_MAIN_PASSWORD`. |
| `MapConfigSource` | `Map<String, String>` | تُنسخ الـ map، ويُرفض مفتاح أو قيمة `null`. |
| `LayeredConfigSource` | عدة مصادر | أول مصدر فيه المفتاح يفوز: `LayeredConfigSource.of(first, second, ...)`. |

طبقة البيئة تتجاوز مفتاحًا يعرّفه مصدر آخر، لكنها لا تنشئ اتصالًا: أسماء الاتصالات تُستخرج من المفاتيح التي تحملها الطبقات، وأسماء البيئة بأحرف كبيرة.

### الاستبدال داخل القيم

يمكن لأي قيمة أن تقرأ متغيرًا:

| الصيغة | النتيجة |
|---|---|
| `${NAME}` | قيمة `NAME`؛ ترمي خطأ إن لم يكن معيّنًا. |
| `${NAME:-fallback}` | قيمة `NAME`، أو `fallback` إن لم يكن معيّنًا. |
| `$${NAME}` | النص الحرفي `${NAME}`. |

تأتي المتغيرات من الوسيط الثاني في `DatabaseConfig.from(source, vars)`، وهو بيئة النظام عند استعمال `from(source)`. إشارة غير مغلقة أو متداخلة في أخرى أو بلا اسم ترمي `DatabaseConfigException`.

### بناء الـ manager من الإعدادات

=== "Java"

    ```java
    ConfigSource source = LayeredConfigSource.of(
            EnvConfigSource.system(),                              // wins over the file
            PropertiesConfigSource.fromClasspath("database.properties"));

    DatabaseManager db = DatabaseManager.builder()
            .config(DatabaseConfig.from(source))
            .connector(new SQLiteConnector(), new PostgresConnector())
            .build();
    ```

=== "Kotlin"

    ```kotlin
    val source: ConfigSource = LayeredConfigSource.of(
        EnvConfigSource.system(),                                  // wins over the file
        PropertiesConfigSource.fromClasspath("database.properties"),
    )

    val db = DatabaseManager.builder()
        .config(DatabaseConfig.from(source))
        .connector(SQLiteConnector(), PostgresConnector())
        .build()
    ```

وتعمل الـ map بالطريقة نفسها بلا ملف:

=== "Java"

    ```java
    DatabaseConfig config = DatabaseConfig.from(MapConfigSource.of(Map.of(
            "database.default", "main",
            "database.connections.main.driver", "sqlite",
            "database.connections.main.database", ":memory:")));
    ```

=== "Kotlin"

    ```kotlin
    val config = DatabaseConfig.from(
        MapConfigSource.of(
            mapOf(
                "database.default" to "main",
                "database.connections.main.driver" to "sqlite",
                "database.connections.main.database" to ":memory:",
            ),
        ),
    )
    ```

## database.default

| المفتاح | النوع | الافتراضي | يقرؤه | المعنى |
|---|---|---|---|---|
| `database.default` | نص: اسم اتصال | لا يوجد، مطلوب | كل الـ drivers | الاتصال الذي تستعمله `manager.connection()` و`manager.query()` و`manager.schema()` حين لا تعطي اسمًا. |

يجب أن يسمّي اتصالًا معرَّفًا تحت `database.connections.<name>`. المفتاح المفقود يرمي `Missing config key [database.default]`، واسم بلا اتصال يرمي خطأ يسرد الاتصالات المعروفة.

```properties
database.default=main
```

## مفاتيح الاتصال (كل الـ drivers)

الاتصال هو `database.connections.<name>.<key>`. والـ `<name>` مقطع تختاره أنت؛ به تطلب الاتصال من الـ manager، ويظهر في كل خطأ.

| المفتاح | النوع | الافتراضي | يقرؤه | المعنى |
|---|---|---|---|---|
| `driver` | نص | لا يوجد، مطلوب | الكل | `sqlite` أو `pgsql` أو `android`: اسم connector مسجَّل. اتصال بلا driver يرمي خطأ. |
| `url` | عنوان JDBC | لا يوجد | `sqlite` و`pgsql` | عنوان JDBC كامل. عند تعيينه لا تُستعمل `host` و`port` ولا `database` (مع `pgsql`). يُقنَّع العنوان أينما طُبعت الإعدادات. |
| `host` | نص | لا يوجد | `pgsql` | مضيف الخادم. عنوان IPv6 يوضع بين قوسين تلقائيًا. مطلوب مع `pgsql` عند غياب `url`. |
| `port` | عدد صحيح من 1 إلى 65535 | `5432` مع `pgsql` | `pgsql` | منفذ الخادم. أي قيمة أخرى ترمي `must be a whole number` أو `port must be between 1 and 65535`. |
| `database` | نص | لا يوجد | `sqlite` و`pgsql` | مع `pgsql` اسم قاعدة البيانات (مطلوب بلا `url`). ومع `sqlite` مسار ملف أو `:memory:` (مطلوب بلا `url`). |
| `username` | نص | لا يوجد | `sqlite` و`pgsql` | اسم الدخول، يُمرَّر إلى مشغّل JDBC. |
| `password` | نص | لا يوجد | `sqlite` و`pgsql` | كلمة المرور، تُمرَّر إلى مشغّل JDBC. تُقنَّع بـ `***` أينما طُبعت الإعدادات. |
| `prefix` | نص | فارغ | الكل | يُضاف أمام كل اسم جدول. أحرف ASCII وأرقام وشرطات سفلية فقط. |
| `strict_transactions` | `true` أو `false` (بأي حالة أحرف) | `true` | الكل | يرفض استدعاء من خيط داخل معاملة فتحها لكنه يمر عبر الاتصال الجذر. أوقفه فقط لكود يكتب خارج المعاملة عمدًا. أي قيمة أخرى ترمي `must be true or false`. |

أي مفتاح آخر مباشرة تحت الاتصال يُحفظ كخيار نصي للـ connector؛ والأقسام التالية تسرد ما تقرؤه الـ connectors. الخيار غير المعروف يُتجاهل.

```properties
database.connections.main.driver=pgsql
database.connections.main.host=${DB_HOST:-localhost}
database.connections.main.port=5432
database.connections.main.database=shop
database.connections.main.username=shop
database.connections.main.password=${DB_PASSWORD}
database.connections.main.prefix=app_
```

## SQLite

الـ driver هو `sqlite`. تُضاف الخيارات إلى عنوان JDBC سواء جاء من `url` أو من `database`. وما كُتب أصلًا داخل `url` نفسه يبقى كما هو.

| المفتاح | النوع | الافتراضي | المعنى |
|---|---|---|---|
| `database` | مسار ملف أو `:memory:` | لا يوجد | الملف يفتح تلك القاعدة. و`:memory:` (وكذلك الهدف الفارغ أو `file::memory:` أو `mode=memory`) يفتح قاعدة خاصة في الذاكرة تعيش ما دام الاتصال. بلا `url` وبلا `database` يرمي الاتصال `needs a database path or :memory:`. |
| `foreign_keys` | `true`/`false` أو `1`/`0` أو `on`/`off` | `true` | يفعّل فرض المفاتيح الأجنبية في كل جلسة. أي قيمة أخرى ترمي `must be true or false`. |
| `busy_timeout` | عدد صحيح بالميلي ثانية، 0 أو أكثر | `30000` | مدة انتظار الجلسة للقفل قبل أن تفشل. القيمة السالبة أو غير الرقمية ترمي خطأ. |
| `lock_wait` | مدة: `5s` أو `500ms` أو أرقام بالميلي ثانية | لا يوجد | الانتظار نفسه الذي يحدده `busy_timeout` لكن بصيغة مدة. إن عُيّنا معًا وجب أن يعطيا العدد نفسه من الميلي ثانية وإلا رمى الاتصال خطأ. يجب أن يكون أكبر من 0 وأقل من أو يساوي 2147483647 ms. |
| `transaction_mode` | `deferred` أو `immediate` أو `exclusive` (بأي حالة أحرف) | افتراضي مشغّل SQLite، أي `deferred` | نوع المعاملة التي يبدؤها `BEGIN`. أي قيمة أخرى ترمي `must be deferred, immediate or exclusive`. |

```properties
database.connections.main.driver=sqlite
database.connections.main.database=/var/lib/shop/shop.db
database.connections.main.foreign_keys=true
database.connections.main.lock_wait=5s
database.connections.main.transaction_mode=immediate
```

## PostgreSQL

الـ driver هو `pgsql`. وانظر أيضًا قسم «مفاتيح الاتصال» لـ `host` و`port` و`database` و`username` و`password`.

| المفتاح | النوع | الافتراضي | المعنى |
|---|---|---|---|
| `sslmode` | نص | لا يوجد | يُضاف إلى العنوان كمعامل `sslmode` (`disable` أو `require` أو `verify-full` وغيرها كما يعرّفها مشغّل JDBC الخاص بـ PostgreSQL). يُتخطى إن كان في `url` أصلًا أو كانت القيمة فارغة. |
| `search_path` | نص | لا يوجد | يُضاف إلى العنوان باسم `currentSchema`: الـ schema التي تستعملها الجلسة أولًا. يُتخطى إن كان `currentSchema` في `url` أصلًا. |
| `schema` | نص | لا يوجد | مثل `search_path`؛ يُستعمل فقط حين لا يكون `search_path` معيّنًا. |
| `lock_wait` | مدة: `5s` أو `500ms` أو أرقام بالميلي ثانية | لا يوجد | يضيف `-c lock_timeout=<ms>` إلى معامل `options` في العنوان: مدة انتظار الجملة للقفل. يجب أن يكون أكبر من 0 وأقل من أو يساوي 2147483647 ms وإلا رمى الاتصال خطأ. |
| `timezone` | نص | لا يوجد | يضبط المنطقة الزمنية لكل جلسة، كما يفعل خيار `timezone` في Laravel: اسم IANA مثل `UTC` أو إزاحة مثل `+03:00`. ينفّذ Diwan الأمر `SET TIME ZONE '<value>'` على كل اتصال يسلّمه، سواء بُني مصدر البيانات من الإعدادات أو قُدّم جاهزًا. وإن كان التجمّع يعيد ضبط الجلسات بـ `DISCARD ALL` أو `RESET ALL` فإنه يلغي هذا الضبط: فاضبط المنطقة في SQL التهيئة الخاص بالتجمّع أو على الخادم. لا يقبل إلا الحروف والأرقام و`/ _ + - :` وإلا رمى الاتصال خطأ. معطّل افتراضيًا. |

ويحصل اتصال `pgsql` أيضًا على قفل ترحيل (migration lock)، وهو قفل استشاري (advisory lock) على مستوى الجلسة يمنع عمليتين من ترحيل قاعدة واحدة معًا. ولا يحتاج مفتاحًا.

بلا `timezone` تحوّل PostgreSQL القيمة بمنطقة الجلسة، وهي تتبع الـ JVM. خزّن `Instant` في عمود `timestamptz`، فهو يحفظ اللحظة أيًا كانت المنطقة. ولوضع قيم `Instant` في أعمدة `timestamp` العادية اضبط `timezone=UTC`: بدونه يتزحزح الوقت المخزَّن بمنطقة الـ JVM أو الجلسة. ويغيّر ضبط `timezone` أيضًا شكل `now()` الذي يطبعه الخادم وما تحمله القيمة الافتراضية لعمود `timestamp`.

```properties
database.connections.main.driver=pgsql
database.connections.main.url=jdbc:postgresql://db.internal:5432/shop
database.connections.main.sslmode=require
database.connections.main.search_path=app
database.connections.main.lock_wait=10s
database.connections.main.timezone=UTC
```

## Android

الـ driver هو `android`. قاعدة البيانات نفسها تأتي من `SQLiteOpenHelper` الذي تعطيه لـ `AndroidConnector.of(...)` في الكود، فلا تُقرأ مفاتيح الاتصال `url` و`host` و`port` و`database` و`username` و`password`. أما `prefix` و`strict_transactions` فتبقيان سارييْن. انظر [Android](android.md).

| المفتاح | النوع | الافتراضي | المعنى |
|---|---|---|---|
| `lock_wait` | مدة: `5s` أو `500ms` أو أرقام بالميلي ثانية | غير معيّن: تبقي القاعدة مهلتها الخاصة | مدة انتظار الجلسة للقفل. يجب أن يكون أكبر من 0 وإلا رمى الاتصال خطأ. |
| `transaction_mode` | `immediate` أو `exclusive` (بأي حالة أحرف) | `exclusive` | `immediate` يستعمل معاملة غير حصرية (non-exclusive). و`deferred` يرمي خطأ (Android لا تستطيع بدء معاملة deferred)، وكذلك أي قيمة أخرى. |

```properties
database.connections.app.driver=android
database.connections.app.lock_wait=3s
database.connections.app.transaction_mode=immediate
```

## الإعدادات في الكود

هذه لا تُقرأ من ملف. تضبطها على الـ builder حين تنشئ الاتصال بنفسك بـ `Connection.builder()`؛ أما الـ connector المبني عبر `DatabaseManager` فيضبط `name` و`tablePrefix` و`strictTransactions` من الإعدادات عنك.

| الإعداد | النوع | الافتراضي | المعنى |
|---|---|---|---|
| `name(...)` | نص | لا يوجد، مطلوب | اسم الاتصال الظاهر في كل `QueryException`. الاسم الفارغ يرمي خطأ. |
| `tablePrefix(...)` | نص | فارغ | مثل المفتاح `prefix`. أي حرف غير ASCII أو رقم أو شرطة سفلية يرمي `IllegalArgumentException`. |
| `strictTransactions(...)` | `boolean` | `true` | مثل المفتاح `strict_transactions`. |
| `showBindingsInErrors(...)` | `boolean` | `false` | يُلحق قيم الـ bindings برسائل `QueryException`. قد تحمل الـ bindings بيانات شخصية فلذلك هو مغلق؛ والاستثناء يحملها في `getBindings()` في الحالتين. |
| `onCleanupFailure(...)` | `Consumer<Throwable>` | يسجّل تحذيرًا عبر `java.util.logging` | يستقبل فشل إعادة الجلسة بعد أن نجح العمل فعلًا. هذا الفشل لا يُفشل الاستدعاء أبدًا. وقد يُستدعى من أي خيط. |
| `queryLogLimit(...)` | عدد صحيح، 1 أو أكثر | `1000` | عدد الجمل التي يحتفظ بها سجل الاستعلامات متى فُعّل `enableQueryLog()`؛ وعند امتلائه يُحذف الأقدم. |
| `listener(...)` | `ConnectionListener` | لا يوجد | يضيف مستمعًا لأحداث الاستعلامات والمعاملات؛ استدعِه مرة لكل مستمع. |
| `DatabaseManager.builder().dataSource(name, supplier)` | `Supplier<DataSource>` | لا يوجد | يعطي اتصالًا data source خاصًا بك (مثل pool) بدل عنوان JDBC المبني من الإعدادات. |

=== "Java"

    ```java
    Connection connection = Connection.builder()
            .name("main")
            .dataSource(dataSource)
            .tablePrefix("app_")
            .strictTransactions(true)
            .showBindingsInErrors(false)
            .onCleanupFailure(e -> log.warn("cleanup failed", e))
            .queryLogLimit(500)
            .build();
    ```

=== "Kotlin"

    ```kotlin
    val connection = Connection.builder()
        .name("main")
        .dataSource(dataSource)
        .tablePrefix("app_")
        .strictTransactions(true)
        .showBindingsInErrors(false)
        .onCleanupFailure { e -> log.warn("cleanup failed", e) }
        .queryLogLimit(500)
        .build()
    ```

## الترحيل (Migrations)

تُضبط إعدادات الترحيل في الكود على `Migrator.Builder`؛ ولا يوجد لها مفتاح properties. وتضيف `manager.migrator(name)` قفل الاتصال نفسه تلقائيًا متى كان لدى الـ connector قفل (`pgsql` لديه؛ و`sqlite` و`android` بلا قفل).

| الإعداد | النوع | الافتراضي | المعنى |
|---|---|---|---|
| `table(...)` | نص | `migrations` | جدول الترحيل، بدون `prefix` الاتصال. يجب أن يكون الاسم بعد البادئة أحرفًا صغيرة وأرقامًا وشرطات سفلية، ويبدأ بحرف أو شرطة سفلية، وطوله 63 حرفًا على الأكثر، وإلا رمى `build()` خطأ. |
| `lock(...)` | `MigrationLock` | `MigrationLock.NONE` | القفل المأخوذ حول كل تشغيل وتراجع (rollback) وإعادة ضبط (reset). |
| `allowMissingOnRollback()` | لا شيء | مغلق: يُرفض التراجع وإعادة الضبط إن وُجد سجل بلا ترحيل | يسمح بهما كما يفعل Laravel، ويبلّغ عن السجلات المجهولة بالنتيجة `NOT_FOUND`. |

=== "Java"

    ```java
    Migrator migrator = db.migrator("main")
            .table("schema_history")
            .allowMissingOnRollback()
            .migrations(migrations)
            .build();
    ```

=== "Kotlin"

    ```kotlin
    val migrator = db.migrator("main")
        .table("schema_history")
        .allowMissingOnRollback()
        .migrations(migrations)
        .build()
    ```

## مثال كامل

```properties
# src/main/resources/database.properties
database.default=main

# PostgreSQL, the main database
database.connections.main.driver=pgsql
database.connections.main.host=${DB_HOST:-localhost}
database.connections.main.port=5432
database.connections.main.database=shop
database.connections.main.username=shop
database.connections.main.password=${DB_PASSWORD}
database.connections.main.prefix=app_
database.connections.main.strict_transactions=true
database.connections.main.sslmode=require
database.connections.main.search_path=app
database.connections.main.lock_wait=10s

# SQLite, a local cache
database.connections.cache.driver=sqlite
database.connections.cache.database=/var/lib/shop/cache.db
database.connections.cache.foreign_keys=true
database.connections.cache.busy_timeout=5000
database.connections.cache.transaction_mode=immediate

# SQLite, in memory (tests)
database.connections.test.driver=sqlite
database.connections.test.database=:memory:

# Android (the helper is given in code)
database.connections.app.driver=android
database.connections.app.lock_wait=3s
database.connections.app.transaction_mode=immediate
```

<!--
Acceptance map: where the code reads each key.
database.default: diwan-database/core/src/main/java/org/aristonis/diwan/database/manager/DatabaseConfig.java:33,80,248-255
database.connections.<name>: DatabaseConfig.java:34,85,92
driver: DatabaseConfig.java:106; ConnectionConfig.java:build() requires it
url: DatabaseConfig.java:109; sqlite/SQLiteConnector.java:133; pgsql/PostgresConnector.java:102
host: DatabaseConfig.java:112; PostgresConnector.java:134
port: DatabaseConfig.java:115,parsePort; ConnectionConfig.java:25,294; PostgresConnector.java:43,142
database: DatabaseConfig.java:118; SQLiteConnector.java:137; PostgresConnector.java:136
username: DatabaseConfig.java:121; SQLiteConnector.java:211; PostgresConnector.java:96
password: DatabaseConfig.java:124; SQLiteConnector.java:211; PostgresConnector.java:97
prefix: DatabaseConfig.java:127; SQLiteConnector.java:99; PostgresConnector.java:68; android/AndroidConnector.java:95
strict_transactions: DatabaseConfig.java:35,130,parseBoolean; SQLiteConnector.java:99; PostgresConnector.java:68; AndroidConnector.java:95
foreign_keys: sqlite/SQLiteConnector.java:63,177-196
busy_timeout: SQLiteConnector.java:64,66,163-168,226-256
lock_wait: config/LockWaitOption.java:KEY,parseMillis; SQLiteConnector.java:164,228; PostgresConnector.java:112; AndroidConnector.java:100
transaction_mode: SQLiteConnector.java:65,150-161; AndroidConnector.java:46,104-121
sslmode: PostgresConnector.java:103
search_path: PostgresConnector.java:104
timezone: PostgresConnector.java:132
schema: PostgresConnector.java:106
${...} interpolation: config/ConfigInterpolator.java:resolve,substitute
env name mapping: config/EnvConfigSource.java:65
layered first-wins: config/LayeredConfigSource.java:get
Settings in code: core/.../database/ConnectionBuilder.java:61 (name),126 (tablePrefix),143 (showBindingsInErrors),158 (strictTransactions),173 (onCleanupFailure),187 (listener),201 (queryLogLimit); event/ConnectionEvents.java:41 (default 1000); manager/DatabaseManager.java:495 (dataSource)
Migrations: migrations/Migrator.java:731 (table),744 (lock),770 (allowMissingOnRollback); migrations/DatabaseMigrationRepository.java:38 (DEFAULT_TABLE),68; manager/Connector.java:71 (lock); manager/DatabaseManager.java:155-162
-->
