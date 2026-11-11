# الاختبار (Testing)

تعطي وحدة `diwan-database-testing` كل اختبار JUnit 5 قاعدة بيانات فارغة طُبّقت عليها الـ migrations، مع مجموعة assertions لقراءة النتيجة.

## إضافة الوحدة

أضفها إلى نطاق الاختبار فقط.

=== "Gradle (Kotlin)"

    ```kotlin
    dependencies {
        testImplementation("org.aristonis:diwan-database-testing:0.3.1")
    }
    ```

=== "Gradle (Groovy)"

    ```groovy
    dependencies {
        testImplementation 'org.aristonis:diwan-database-testing:0.3.1'
    }
    ```

=== "Maven"

    ```xml
    <dependency>
      <groupId>org.aristonis</groupId>
      <artifactId>diwan-database-testing</artifactId>
      <version>0.3.1</version>
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
