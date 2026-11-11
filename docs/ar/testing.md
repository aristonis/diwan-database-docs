# الاختبار (Testing)

تعطي وحدة `diwan-database-testing` كل اختبار JUnit 5 قاعدة بيانات فارغة طُبّقت عليها الـ migrations، مع مجموعة assertions لقراءة النتيجة.

## إضافة الوحدة

أضفها إلى نطاق الاختبار فقط.

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

تحتاج الوحدة إلى JUnit Jupiter بإصدار 5.10 أو أحدث في classpath الاختبار، ولا تجلبه معها. أضف `diwan-database-eloquent` فقط إن استعملت assertions الخاصة بالـ models.

## تسجيل الـ extension

الصنف `RefreshDatabase` هو extension لـ JUnit. سجّله في حقل بـ `@RegisterExtension`. يأخذ المصنع ثلاثة أشياء: supplier يعيد `QueryFactory` للاتصال الجذري، ودالة تبني `Schema` لاتصال، وقائمة الـ migrations التي تبني مخطط الاختبار.

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

يجب أن يعيد الـ supplier نسخة الاتصال نفسها في كل مرة، فهي التي تحدد قاعدة البيانات. للوضع الآخر استعمل `RefreshDatabase.truncate(...)` بالوسائط نفسها.

## rollback أم truncate

| | `rollback` | `truncate` |
|---|---|---|
| كيف تُزال البيانات | تُفتح transaction قبل كل اختبار وتُلغى بعده. | يُثبّت الاختبار فعليًا (commit). بعد كل اختبار تُفرَّغ كل الجداول عدا جدول الـ migrations باستدعاء واحد، وتبدأ الهويات من جديد. |
| السرعة | سريع. | أبطأ. |
| callbacks الـ `afterCommit` | لا تعمل أبدًا: لا شيء يُثبَّت. | تعمل. |
| هل ترى الـ threads الأخرى البيانات | لا. | نعم. |
| JUnit المتوازي | آمن: transaction لكل thread اختبار. | غير مسموح. |

اختر `rollback` افتراضيًا. اختر `truncate` حين يحتاج الاختبار إلى commit حقيقي: hooks الـ `afterCommit`، أو عمل على threads أو executors أخرى، أو كود يفتح اتصالًا خاصًا به.

في وضع rollback تعمل الاستدعاءات التي يجريها الاختبار على الاتصال الجذري من thread الخاصة به داخل transaction الاختبار، حتى مع تفعيل strict transactions. واستدعاء `transaction(...)` داخل الاختبار يصبح savepoint.

في وضع truncate:

- تُقرأ قائمة الجداول مرة واحدة في كل تشغيل، بعد أول اختبار، فجدول ينشئه اختبار لاحقًا لا يُفرَّغ.
- تُزال بادئة الجداول (table prefix) الخاصة بالاتصال من الأسماء المسردة، وتُفرَّغ فقط الجداول التي تحملها. وعلى PostgreSQL تُكتب الجداول خارج `current_schema()` مع اسم الـ schema.
- الجداول الداخلية تُترك: `spatial_ref_sys` على PostgreSQL، و`android_metadata` وجداول FTS المساعدة على SQLite.
- يفشل الـ extension بـ `IllegalStateException` تحت `ExecutionMode.CONCURRENT`. استعمل وضع rollback، أو ضع على الصنف `@Execution(ExecutionMode.SAME_THREAD)`.

## وضع Template

يعطي وضع template كل اختبار قاعدة بيانات خاصة به: نسخة من قالب (template) يحمل المخطط بعد تطبيق الـ migrations. يُثبّت الاختبار التغييرات فعليًا (commit) كما في وضع truncate، لكن لا يرى أي اختبار بيانات اختبار آخر، ويجوز تشغيل الاختبارات بالتوازي.

| | `rollback` | `truncate` | template |
|---|---|---|---|
| ماذا يرى الاختبار | transaction خاصة به تُلغى بعده | قاعدة مشتركة تُفرَّغ بعد كل اختبار | نسخة خاصة به من القالب |
| التثبيت الفعلي (commit) | لا | نعم | نعم |
| JUnit المتوازي | نعم | لا | نعم |
| التكلفة لكل اختبار | الأدنى | truncate واحد | نسخة واحدة وحذف واحد |
| يحتاج إلى | أي قاعدة بيانات | أي قاعدة بيانات | PostgreSQL مع `CREATEDB`، أو SQLite مع `directory(Path)` |

استعمل وضع template حين يحتاج الاختبار إلى تثبيت فعلي، ولا يجوز أن يعتمد على بيانات الاختبارات الأخرى أو يُفسدها: مثل اختبارات تُثبّت على threads أخرى بينما تعمل اختبارات غيرها. استعمل rollback حين لا يحتاج الاختبار إلى تثبيت. واستعمل truncate حين يجب أن تعمل الاختبارات واحدًا تلو الآخر.

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

يحتاج SQLite إلى مجلد. يبني الـ extension القالب فيه، ثم ينسخه لكل اختبار:

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

### كيف يعمل القالب

- يُسمّى القالب باسم قائمة الـ migrations: `diwan_tpl_<hash8>`، حيث تغطي البصمة الصنف والاسم والـ checksum لكل migration بالترتيب. التشغيل الذي له القائمة نفسها يعيد استعمال القالب، وقائمة متغيرة تبني قالبًا جديدًا بجانبه.
- يحصل كل اختبار على نسخة واحدة باسم `diwan_t_<hash8>_<run>_<n>`، وتُحذف النسخة بعد الاختبار.
- يُطبَّق الـ migrate على القالب عبر manager خاص به، ويُغلق قبل أول نسخة. والتشغيلات التي تبدأ معًا تبنيه مرة واحدة.
- يحتفظ التشغيل باتصال واحد من الـ root data source حتى ينتهي، وتعيش أقفاله على ذلك الاتصال. فاجعل الـ root مصدر بيانات تشغيل عادي (driver) أو pool في وضع session، لا pooler في وضع transaction.
- يغلق الـ extension الـ manager الذي يحصل عليه لكل اختبار، فأبقِ pool كل manager صغيرًا: الحد الأقصى 2 اتصالًا يكفي معظم الاختبارات.
- يجب أن يغلق manager الذي يعيده `perDatabase` اتصالاته فورًا عند إغلاقه. فالـ pool الذي يغلقها ببطء قد يُفشل حذف النسخة. في PostgreSQL 13 أو أحدث يستعمل الحذف `FORCE`، وفي الأقدم يترك الإغلاق البطيء النسخة لفحص التشغيل التالي.

### PostgreSQL

- يحتاج الدور إلى `CREATEDB`. بدونه يفشل التشغيل قبل الاختبار الأول، بـ `IllegalStateException` تسمّي الدور وتذكر منحة `ALTER ROLE ... CREATEDB`.
- لا يجوز أن يكون أي session آخر متصلًا بالقالب حين تُنشأ نسخة. يغلق الـ extension جلساته على القالب بعد بنائه. والنسخة تنتظر نحو ثانيتين لـ session يُغلق للتو؛ فإن بقي الـ session مفتوحًا فشلت النسخة بـ `IllegalStateException` تسمّي القالب.
- يضبط `strategy(CopyStrategy)` استراتيجية كل نسخة. تنسخ `FILE_COPY` ملفات القالب وتفرض نقطتي checkpoint. وتعيد `WAL_LOG` تشغيل القالب عبر سجل الكتابة المسبقة (WAL) بلا checkpoint، لكنها تكتب سجلًا أكبر. الافتراضي هو `FILE_COPY` في PostgreSQL 15 أو أحدث، وبلا جملة في الخوادم الأقدم. والاستراتيجية الصريحة على خادم أقدم تفشل حين تُنشأ أول نسخة.
- تُشغّل `FILE_COPY` نقطة checkpoint قبل كل نسخة وبعدها، وهذا يكلّف أكثر على خادم مشترك مشغول. وتناسب `WAL_LOG` القوالب الصغيرة.
- في قياس بـ 20 جدولًا و10 اختبارات، كان متوسط زمن الاختبار: وضع truncate ‏379 ms، و`FILE_COPY` ‏299 ms، و`WAL_LOG` ‏310 ms. واستغرق الإعداد لمرة واحدة 309 ms مع `FILE_COPY` و70 ms مع `WAL_LOG`.
- في PostgreSQL 18 أو أحدث، يمكن للإعداد `file_copy_method` إذا ضُبط على `clone` أن يجعل نسخ `FILE_COPY` أسرع على نظام ملفات يدعم الاستنساخ.
- تُحذف النسخة بـ `FORCE` في PostgreSQL 13 أو أحدث، فتنهي أي session ما زال عليها.

### SQLite

- يسمّي `directory(Path)` مجلد القالب والنسخ. وبدونه يرفض وضع template البدء بـ `IllegalStateException`. وعلى هدف PostgreSQL يُرفض `directory(Path)` بـ `IllegalStateException`.
- تُنشئ الإضافة مجلد النسخ. أما مجلد ملف الـ DataSource الجذري نفسه فيجب أن يكون موجودًا قبل التشغيل.
- كل قاعدة هي الملف `<directory>/<name>.db`. يتلقى `perDatabase` المسار المطلق لذلك الملف، ويجب أن يفتح هذا المسار بالضبط. وإلا فشل التشغيل، والرسالة تذكر المسار المتوقع والمسار المفتوح.
- يُطبَّق الـ migrate على القالب في ملف خاص به، ثم يُنفَّذ عليه checkpoint ويُنقل إلى مكانه. وينسخ كل اختبار هذا الملف، ويحذف النسخة بعد الاختبار مع ملفات `-wal` و`-shm` و`-journal` الخاصة بها.
- يطبَّق `strategy(CopyStrategy)` على PostgreSQL وحده، ويتجاهله SQLite.

### الخيارات

كل خيار يعيد extension جديدًا، والخيار خارج وضع template يرمي `IllegalStateException`.

- `strategy(CopyStrategy)`: استراتيجية النسخ في PostgreSQL. انظر أعلاه.
- `directory(Path)`: المجلد الخاص بـ SQLite. وهو مطلوب هناك.
- `dropStaleTemplates()`: عند بدء التشغيل، يحذف قوالب قوائم migrations الأخرى. في PostgreSQL يبقى القالب الذي ما زال تشغيل آخر ينسخ منه، ويُسجَّل الرفض. وفي SQLite تُحذف ملفات القوالب الأخرى في المجلد مع ملفاتها الجانبية وملفات القفل، ويبقى القالب الذي يملك تشغيل آخر قفل بنائه.

### الاختبارات المتوازية وعدة JVM

- يعمل وضع template مع `ExecutionMode.CONCURRENT`، على عكس وضع truncate.
- يمكن لعدة JVM أن تشترك في خادم واحد أو مجلد واحد، مثل forks الاختبار في Gradle حين يكون `maxParallelForks` أكبر من 1. يبني تشغيل واحد القالب، ويعيد الآخرون استعماله. ويحمل اسم كل نسخة معرّف التشغيل الخاص بـ JVM التي أنشأتها، فلا يأخذ تشغيل نسخة تشغيل آخر.

### البقايا

- يحتفظ التشغيل بقفل ما دام حيًا: قفل استشاري (advisory lock) في PostgreSQL، وقفل ملف في SQLite. وعند بدء تشغيل، يزيل نسخ وقواعد البناء أو ملفاته للتشغيلات المنتهية. ولا يزيل نسخه هو، ويترك ملفات التشغيل الحي كما هي.
- التشغيل الذي تعطل يترك نسخه حتى يبدأ التشغيل التالي.
- النسخة التي لا تُحذف بعد اختبارها تُسجَّل، ولا تتغير نتيجة الاختبار. يزيلها التشغيل التالي.
- لا يزيل الفحص أبدًا القالب النهائي الذي يطابق قائمة الـ migrations الحالية. وتبقى القوالب الأقدم إلا إذا ضُبط `dropStaleTemplates()`.

### الحدود

- قاعدة SQLite في الذاكرة غير مدعومة في وضع template: أعطِ مسار ملف عبر `directory(Path)`.
- Android غير مدعوم: يرفض وضع template مشغّل `android` بـ `IllegalStateException`.
- يعمل وضع template على PostgreSQL وSQLite فقط.

## إعادة ضبط الهويات (restartingIdentities)

على PostgreSQL يلغي rollback الصفوف لكن لا يلغي الـ sequence الذي يقف خلف `id`. بدون هذا الخيار تعتمد الأرقام التي يحصل عليها الاختبار على الاختبارات التي عملت قبله. يعيد `restartingIdentities()` العدّادات إلى بدايتها قبل كل اختبار، فيرى كل اختبار الأرقام نفسها:

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

قبل كل اختبار، بعد تطبيق الـ migrations وقبل أن تُفتح transaction الاختبار، يُضبط عدّاد كل هوية (identity) وكل عمود `serial` للجداول التي يملكها الـ extension على القيمة التي تلي أعلى id مُثبَّت، أو على قيمة البداية إن كان الجدول فارغًا. الصفوف التي ثبّتها migration أو seeder تبقى، فأول صف يُدرجه الاختبار يأخذ الـ id الذي يلي تلك الصفوف. لا يُلغى الضبط بالـ rollback، لأن PostgreSQL لا يتراجع عن الـ sequence أبدًا.

| | PostgreSQL | SQLite |
|---|---|---|
| الـ rollback وحده | يستمر العدّاد في التقدم، فتحصل الاختبارات اللاحقة على أرقام أعلى. | يتراجع العدّاد مع الصفوف، فتتكرر الأرقام. |
| مع `restartingIdentities()` | يبدأ كل اختبار من العدّاد نفسه. | لا يُرسل شيء: الخيار لا يفعل شيئًا. |

لهذا الخيار الحدود التالية:

- يحتاج إلى PostgreSQL بإصدار 10 أو أحدث.
- يضبط فقط الـ sequences التي يملكها عمود من الجداول، مثل عمود الهوية (identity) أو عمود `serial`. الـ sequence الذي لا يملكه أي عمود، مثل واحد أُنشئ وحده واستُعمل كقيمة افتراضية، يُترك كما هو.
- يرسل قبل كل اختبار استعلامًا لسرد الـ sequences التي يملكها، ثم استعلامًا لكل sequence. ويحتاج إلى صلاحية تغيير الـ sequence، ومالك الجدول يملكها.
- يُرفض بـ `IllegalStateException` في وضع truncate، لأنه يعيد ضبط الهويات أصلًا.
- يُرفض تحت `ExecutionMode.CONCURRENT`، لأن الاختبارات تشترك في الـ sequences. ضع على الصنف `@Execution(ExecutionMode.SAME_THREAD)` بدلًا من ذلك.
- الفحص يرى JVM واحدة. لا تُكتشف forks الخاصة بـ Gradle (`maxParallelForks` أكبر من 1) التي تشترك في قاعدة بيانات واحدة. أعطِ كل fork قاعدة بيانات خاصة بها.
- يدفع كل اختبار استعلامًا واحدًا على الـ catalog و`setval` واحدًا لكل sequence. البحث عن أعلى id يمسح الجدول كله إن لم يكن لعمود الـ id فهرس، فاستعمل الخيار في الأصناف التي تعتمد على أرقام الـ id فقط.

## المعاملات (Parameters)

يستطيع أي اختبار أن يعلن هذه المعاملات، والـ extension يملؤها:

- `DatabaseAssertions`: الـ assertions أدناه.
- `QueryFactory`: مصنع الاستعلامات الذي زودته.
- `Connection`: اتصاله.

الدالة `DatabaseAssertions.of(queryFactory)` تبني الكائن نفسه خارج JUnit.

## الـ migrate مرة واحدة في كل تشغيل

أول صنف اختبار يستعمل الـ extension ينفذ `Migrator.fresh()`: يحذف كل الـ views والجداول، ثم يشغّل الـ migrations. الأصناف اللاحقة التي لها نسخة الاتصال نفسها وقائمة الـ migrations نفسها تعيد استعمال ذلك المخطط. يُحفظ السجل في المخزن الجذري لتشغيل JUnit، فهو مشترك بين الأصناف.

الاتصال نفسه مع قائمة migrations مختلفة في التشغيل نفسه يُرفض بـ `IllegalStateException`، لأن إعادة الـ migrate ستحذف جداول الأصناف التي عملت من قبل. تُقارن الـ migrations بالصنف والاسم، فتعديل محتوى migration داخل تشغيل واحد لا يُلاحَظ.

## قاعدة بيانات واحدة، طريقة migrate واحدة

يملك الـ extension مخطط اتصاله: مرة في كل تشغيل يحذف كل الجداول وينفذ قائمته في جدول `migrations` الافتراضي. صنف اختبار ينفذ الـ migrator الخاص بتطبيقك، أو migrator لكل module، على قاعدة البيانات نفسها يصطدم به: الجداول موجودة أصلًا، فيفشل ذلك الـ migrator بخطأ مثل `relation "accounts" already exists`، أو يحذف `fresh()` الخاص به الجداول التي بناها الـ extension للأصناف الأخرى. على كل صنف يستعمل قاعدة البيانات نفسها أن يستعمل الـ extension بقائمة الـ migrations نفسها. الصنف الذي يحتاج طريقة migrate أخرى يأخذ قاعدة بيانات خاصة به.

## الـ Assertions

| الدالة | تنجح عندما |
|---|---|
| `assertHas(table, values)` | يطابق صف كل الأعمدة في `values`. |
| `assertMissing(table, values)` | لا يطابقها أي صف. |
| `assertCount(table, n)` | في الجدول `n` صف بالضبط. |
| `assertEmpty(table)` | لا صفوف في الجدول. |
| `assertModelExists(model)` | صف الـ model موجود، ويُبحث عنه بمفتاحه. |
| `assertModelMissing(model)` | صف الـ model غير موجود. |
| `assertSoftDeleted(model)` | الصف موجود وعمود الحذف (deleted-at) معبّأ. |
| `assertNotSoftDeleted(model)` | الصف موجود وعمود الحذف null. |

كلها ترمي `AssertionError`. تذكر الرسالة اسم الجدول والأعمدة المقارَنة، وتعرض حتى ثلاثة صفوف مشابهة من أصل العدد الكلي، أو تقول إن الجدول فارغ. قيم أعمدة الـ model المخفية لا تُطبع أبدًا.

```text
java.lang.AssertionError: No row in [users] matches {name=bob, active=true}.
Similar rows (first 2 of 2): {id=1, name=ann, active=true}, {id=2, name=cy, active=false}
```

## الحدود

- العمل على thread أخرى لا ينضم إلى transaction الاختبار في وضع rollback. الـ threads والـ executors التي يبدؤها الاختبار، والاختبار تحت `@Timeout(threadMode = SEPARATE_THREAD)`، تُثبَّت فعليًا ولا يُتراجع عنها. استعمل وضع truncate لمثل هذه الاختبارات، أو نظّف بنفسك.
- callbacks الـ `afterCommit` لا تعمل أبدًا في وضع rollback.
- وضع truncate لا يعمل تحت JUnit المتوازي.
- على PostgreSQL تحذف `dropAllTables` الجداول فقط. الأنواع (types) والـ sequences والدوال التي تنشئها migration تبقى، فاحذفها في `down` الخاصة بالـ migration، أو أعطِ الاختبارات schema مخصصة.
- assertions الـ models تحتاج وحدة eloquent.
- JUnit Jupiter بإصدار 5.10 أو أحدث.
