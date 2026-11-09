# Query builder

الـ query builder (باني الاستعلامات) يقرأ الصفوف ويكتبها عبر سلسلة من استدعاءات الدوال. كل قيمة تمررها تُربط كـ parameter، فلا يضع الـ builder بياناتك داخل نص SQL أبدًا.

## الحصول على builder

اطلب `QueryFactory` من الـ `DatabaseManager`. يُبنى من إعداد الاتصال، فلا يذكر كودك أي صنف driver، وتغيير قاعدة البيانات تغيير في الإعداد فقط. استدعِ `table(...)` عليه لتبدأ استعلامًا.

=== "Java"

    ```java
    import org.aristonis.diwan.database.query.QueryFactory;

    QueryFactory query = manager.query();            // the default connection
    QueryFactory cache = manager.query("cache");     // a named connection
    ```

=== "Kotlin"

    ```kotlin
    import org.aristonis.diwan.database.query.QueryFactory

    val query = manager.query()            // the default connection
    val cache = manager.query("cache")     // a named connection
    ```

المتغير `manager` هو الـ `DatabaseManager` من صفحة [الاتصالات والمعاملات](connections.md). الـ builder غير آمن للاستخدام من عدة threads. الدالة `clone()` تعطيك نسخة مستقلة. تسمّي أمثلة هذه الصفحة الـ factory باسم `query`.

بدون manager، خذ الـ factory من وحدة الـ grammar الخاصة بقاعدة بياناتك:

=== "Java"

    ```java
    QueryFactory query = SQLiteQuery.of(connection);       // SQLite, and Android through the same grammar
    // QueryFactory query = PostgresQuery.of(connection);  // PostgreSQL
    ```

=== "Kotlin"

    ```kotlin
    val query = SQLiteQuery.of(connection)       // SQLite, and Android through the same grammar
    // val query = PostgresQuery.of(connection)  // PostgreSQL
    ```

داخل transaction (معاملة) استدعِ `query.on(c)` حتى يعمل العمل على المعاملة، كما في مثال row locks أدناه. وعلى Android راجع [Android](android.md).

## الاختيار والتصفية

=== "Java"

    ```java
    List<Map<String, Object>> rows = query.table("orders")
            .select("id", "total")
            .where("status", "open")
            .where("total", ">", 1000)
            .orWhere("priority", true)
            .whereIn("region", List.of("eu", "us"))
            .whereNotNull("customer_id")
            .orderByDesc("id")
            .limit(10)
            .get();

    Optional<Map<String, Object>> one = query.table("users").find(7);
    Optional<Object> email = query.table("users").where("id", 7).value("email");
    boolean any = query.table("orders").where("status", "open").exists();
    ```

=== "Kotlin"

    ```kotlin
    val rows = query.table("orders")
        .select("id", "total")
        .where("status", "open")
        .where("total", ">", 1000)
        .orWhere("priority", true)
        .whereIn("region", listOf("eu", "us"))
        .whereNotNull("customer_id")
        .orderByDesc("id")
        .limit(10)
        .get()

    val one = query.table("users").find(7)
    val email = query.table("users").where("id", 7).value("email")
    val any = query.table("orders").where("status", "open").exists()
    ```

الصفوف من نوع `Map<String, Object>`. من المرشحات الأخرى `whereBetween` و`whereLike` و`whereContains` (انظر أدناه) و`whereColumn` و`whereAny` و`whereAll` و`whereNone`، والشروط المجمعة بـ `where(q -> ...)`، و`groupBy` مع `having`. الدالتان `toSql()` و`getBindings()` تعرضان ما سينفذه الـ builder.

الدالة `where(column, operator, value)` تقبل عوامل المقارنة (operators) في الـ builder (`=` و`<` و`>` و`<=` و`>=` و`<>` و`!=` و`like` و`not like` و`ilike` وغيرها) وعوامل الـ grammar (قواعد توليد SQL) الخاصة بها. العامل المجهول يُعامل كأنه القيمة، فـ `where("total", "=>", 10)` يقارن `total` بالنص `=>`، كما في Laravel.

### القوائم الفارغة

قائمة `whereIn` الفارغة لا تطابق أي صف (`0 = 1`). وقائمة `whereNotIn` الفارغة تطابق كل الصفوف (`1 = 1`)، كما في Laravel. هذا هو الجواب الصحيح لـ «كل صف عدا لا شيء»، لكنه في delete يحذف كل ما تختاره الشروط الأخرى. تأكد أن القائمة الفارغة تعني «لا شيء» فعلًا وليس «لم تُحمَّل»:

=== "Java"

    ```java
    // "delete the task's alarms except these": with keep empty, every alarm of the task goes
    query.table("alarms").where("task_id", taskId).whereNotIn("id", keep).delete();
    ```

=== "Kotlin"

    ```kotlin
    // "delete the task's alarms except these": with keep empty, every alarm of the task goes
    query.table("alarms").where("task_id", taskId).whereNotIn("id", keep).delete()
    ```

دوال التاريخ (`whereDate` و`whereMonth` وغيرهما) مخصصة لأعمدة التاريخ النصية. مع أعمدة الـ instant (لحظة زمنية) استخدم `whereInstantBetween(column, from, to)`.

## البحث في مدخلات المستخدم

الدوال `whereContains` و`whereStartsWith` و`whereEndsWith` تجد نصًا كتبه المستخدم. وهي تعامل النص دائمًا كما هو حرفيًا: الرموز `%` و`_` و`!` تطابق نفسها، ولا تعمل أبدًا كرموز بدل (wildcards).

=== "Java"

    ```java
    List<Map<String, Object>> rows = query.table("users")
            .whereContains("name", userInput)            // the name holds the input, as typed
            .orWhereStartsWith("email", prefix)
            .whereNotEndsWith("email", ".test", true)    // case-sensitive
            .get();
    ```

=== "Kotlin"

    ```kotlin
    val rows = query.table("users")
        .whereContains("name", userInput)            // the name holds the input, as typed
        .orWhereStartsWith("email", prefix)
        .whereNotEndsWith("email", ".test", true)    // case-sensitive
        .get()
    ```

تأخذ كل دالة `(column, value)` أو `(column, value, caseSensitive)`. والقيمة الافتراضية للعلم `false`، كما في `whereLike`. ولكل مرساة أربع صيغ: `whereContains` و`orWhereContains` و`whereNotContains` و`orWhereNotContains`، وكذلك `StartsWith` و`EndsWith`.

- القيمة `null` ترمي `IllegalArgumentException`.
- القيمة الفارغة تطابق كل صف عموده ليس null، لأن كل نص يبدأ وينتهي بالنص الفارغ. والعمود null لا يطابق أبدًا.

تُربط القيمة معاملًا واحدًا. ويهرّبها Diwan أولًا، مع `!` كحرف تهريب: يصير `!` إلى `!!`، ثم يُضاف `!` قبل `%` و`_`. ويعتمد الـ SQL على قاعدة البيانات:

| قاعدة البيانات | الافتراضي (`caseSensitive` false) | `caseSensitive` true |
|---|---|---|
| PostgreSQL | `col::text ilike ? escape '!'` | `col::text like ? escape '!'` |
| SQLite | `col like ? escape '!'` | `col glob ?` |

الـ GLOB في SQLite بلا حرف تهريب، فالصيغة الحساسة لحالة الأحرف تضع `*` و`?` و`[` بين أقواس مربعة، فيطابق كلٌّ منها نفسه.

ملاحظات:

- المطابقة الافتراضية في SQLite تتجاهل حالة الأحرف ASCII فقط، فلا يطابق `É` الحرف `é` هناك.
- لا تستعمل SQLite فهرسًا مع `LIKE` ومعها جملة `ESCAPE`. أما `whereStartsWith` الحساسة لحالة الأحرف فتستعمل `GLOB` بدلها، ويمكنها استعمال فهرس على عمود بترتيب (collation) `BINARY`.
- في PostgreSQL يمكن لـ `whereStartsWith` الحساسة لحالة الأحرف استعمال فهرس `text_pattern_ops` على عمود نصي. أما `ilike` فلا يمكنها استعمال فهرس B-tree عادي؛ وفي جدول كبير يخدم فهرس GIN من `pg_trgm` (`create index ... using gin (col gin_trgm_ops)`) البحث بالاحتواء والبداية والنهاية في الحالتين. ويُقارَن العمود بصيغة `col::text`، لذلك لا يطابق فهرسٌ على عمود غير نصي.

### whereLike تبقى خامًا

تعمل `whereLike` كما في Laravel: النمط صيغة LIKE خام، فـ `%` و`_` رموز بدل ولا يُهرَّب شيء. استعملها للأنماط التي تكتبها بنفسك. لا تمرّر مدخلات المستخدم إلى `whereLike`، حتى مع إضافة `%` حولها. استعمل لذلك `whereContains` أو `whereStartsWith` أو `whereEndsWith`.

=== "Java"

    ```java
    query.table("users").whereLike("name", "A%");   // names that start with A, as written
    ```

=== "Kotlin"

    ```kotlin
    query.table("users").whereLike("name", "A%")   // names that start with A, as written
    ```

## الربط والاستعلامات الفرعية والاتحاد

=== "Java"

    ```java
    List<Map<String, Object>> rows = query.table("orders")
            .join("customers", "customers.id", "=", "orders.customer_id")
            .leftJoinSub(query.table("payments").selectRaw("order_id, sum(amount) as paid")
                    .groupBy("order_id"), "p", "p.order_id", "=", "orders.id")
            .whereExists(q -> q.from("notes").whereColumn("notes.order_id", "orders.id"))
            .select("orders.id", "customers.name", "p.paid")
            .get();

    List<Object> ids = query.table("orders").select("id").where("status", "open")
            .union(query.table("archived_orders").select("id"))
            .orderByDesc("id")
            .limit(20)
            .pluck("id");
    ```

=== "Kotlin"

    ```kotlin
    val rows = query.table("orders")
        .join("customers", "customers.id", "=", "orders.customer_id")
        .leftJoinSub(query.table("payments").selectRaw("order_id, sum(amount) as paid")
            .groupBy("order_id"), "p", "p.order_id", "=", "orders.id")
        .whereExists { q -> q.from("notes").whereColumn("notes.order_id", "orders.id") }
        .select("orders.id", "customers.name", "p.paid")
        .get()

    val ids = query.table("orders").select("id").where("status", "open")
        .union(query.table("archived_orders").select("id"))
        .orderByDesc("id")
        .limit(20)
        .pluck("id")
    ```

يُنسخ الاستعلام الفرعي عند إرفاقه، فتغييره لاحقًا لا يغير الاستعلام الخارجي. الـ right join يحتاج SQLite بالإصدار 3.39 أو أحدث، وهو ما يأتي مع Android 14 (API 34) وما بعده. إصدارات SQLite الأقدم على Android تُرجع خطأها الخاص في صورة `QueryException`.

## الدوال التجميعية

=== "Java"

    ```java
    long total = query.table("orders").count();
    Number revenue = query.table("orders").sum("total");          // 0 when there are no rows
    Optional<Object> biggest = query.table("orders").max("total");
    Optional<Number> mean = query.table("orders").avg("total");
    ```

=== "Kotlin"

    ```kotlin
    val total = query.table("orders").count()
    val revenue = query.table("orders").sum("total")          // 0 when there are no rows
    val biggest = query.table("orders").max("total")
    val mean = query.table("orders").avg("total")
    ```

### مجاميع decimal الدقيقة

ترجع `sum` قيمة `Number`. وللمال استعمل `sumDecimal` التي ترجع `BigDecimal` بالـ scale الذي تعطيه:

=== "Java"

    ```java
    BigDecimal paid = query.table("payments").sumDecimal("amount", 2);                       // HALF_UP
    BigDecimal net = query.table("payments").sumDecimal("amount", 2, RoundingMode.HALF_EVEN);
    ```

=== "Kotlin"

    ```kotlin
    val paid = query.table("payments").sumDecimal("amount", 2)                      // HALF_UP
    val net = query.table("payments").sumDecimal("amount", 2, RoundingMode.HALF_EVEN)
    ```

- على PostgreSQL المجموع دقيق.
- على SQLite تكون `SUM` عددًا من نوع double ويقرّبه Diwan إلى الـ scale. وهذا مناسب للمجاميع العادية وتقريبي للكبيرة جدًا (ملايين القيم الكبيرة).
- غياب الصفوف يعطي صفرًا بالـ scale (`0.00`).
- للـ Eloquent builder الدوال نفسها عبر `query()`.

## الإدراج والتحديث والحذف

=== "Java"

    ```java
    Object id = query.table("users").insertGetId(Map.of("email", "ada@example.com"));
    query.table("users").insert(List.of(Map.of("email", "a@x"), Map.of("email", "b@x")));
    query.table("users").where("id", id).update(Map.of("email", "ada@example.org"));
    query.table("posts").where("id", 3).increment("views");
    query.table("users").where("id", id).delete();
    query.table("archive").insertUsing(List.of("id", "total"),
            q -> q.from("orders").select("id", "total").where("status", "closed"));
    ```

=== "Kotlin"

    ```kotlin
    val id = query.table("users").insertGetId(mapOf("email" to "ada@example.com"))
    query.table("users").insert(listOf(mapOf("email" to "a@x"), mapOf("email" to "b@x")))
    query.table("users").where("id", id).update(mapOf("email" to "ada@example.org"))
    query.table("posts").where("id", 3).increment("views")
    query.table("users").where("id", id).delete()
    query.table("archive").insertUsing(listOf("id", "total")) { q ->
        q.from("orders").select("id", "total").where("status", "closed")
    }
    ```

لتفريغ عدة جداول معًا استدعِ `truncate` على المصنع:

=== "Java"

    ```java
    query.truncate(List.of("posts", "comments"));          // empty them, restart identities
    query.truncate(List.of("users"), true);                // cascade: also empty tables that refer to users
    ```

=== "Kotlin"

    ```kotlin
    query.truncate(listOf("posts", "comments"))          // empty them, restart identities
    query.truncate(listOf("users"), true)                // cascade: also empty tables that refer to users
    ```

القائمة الفارغة لا تنفذ شيئًا، والاسم null أو الفارغ يرمي استثناء. على PostgreSQL هي عبارة واحدة `truncate ... restart identity`، و`cascade` هو الأصلي فيها. على SQLite وAndroid تُحذف الصفوف مع تجاوز فحص المفاتيح الأجنبية، والـ `cascade` محاكى: كل جدول يشير إلى الجداول المذكورة، مباشرة أو عبر جداول أخرى، يُفرَّغ أيضًا، الأبناء أولًا، كما تفعل PostgreSQL، لكن المحاكاة تتبع فقط الجداول التي تحمل بادئة الاتصال (table prefix). وتُعاد ضبط صفوف `sqlite_sequence` المقابلة، وتُعالَج قاعدة لا تحتوي جدول `sqlite_sequence`. أما تفريغ جدول واحد بالـ builder فلم يتغير.

يجوز أن يربط التحديث أو الحذف جداول أخرى. على SQLite هذا يتطلب جدولًا له rowid. الكتابة تحتاج جدولًا، لا استعلامًا فرعيًا ولا `from` خامًا.

### insertOrIgnore وupsert وupdateOrInsert

=== "Java"

    ```java
    query.table("users").insertOrIgnore(rows);                       // skips rows that break a unique key
    query.table("users").upsert(rows, List.of("email"));             // updates every column of the first row
    query.table("users").upsert(rows, List.of("email"), List.of("name"));
    query.table("users").upsert(rows, List.of("email"),
            Map.of("votes", Expression.raw("users.votes + 1")));
    query.table("users").updateOrInsert(Map.of("email", "a@x"), Map.of("name", "A"));
    ```

=== "Kotlin"

    ```kotlin
    query.table("users").insertOrIgnore(rows)                        // skips rows that break a unique key
    query.table("users").upsert(rows, listOf("email"))              // updates every column of the first row
    query.table("users").upsert(rows, listOf("email"), listOf("name"))
    query.table("users").upsert(rows, listOf("email"),
        mapOf("votes" to Expression.raw("users.votes + 1")))
    query.table("users").updateOrInsert(mapOf("email" to "a@x"), mapOf("name" to "A"))
    ```

- `insertOrIgnore` تعيد عدد الصفوف التي أُدرجت. على SQLite تتخطى أيضًا الصف الذي يخالف قيد `not null` أو `check`، لا قيد الفرادة فقط.
- `upsert` تحتاج unique index (فهرس فرادة) على الأعمدة الموجودة في `uniqueBy` تمامًا، وإلا ترفضها قاعدة البيانات. وتحتاج SQLite 3.24 أو أحدث (Android API 30 فما فوق). الإصدارات الأقدم ترمي `UnsupportedOperationException` قبل تنفيذ أي SQL.
- إذا كان في الدفعة صفان بنفس مفتاح الفرادة، تطبقهما SQLite بالترتيب فيفوز الأخير. أما PostgreSQL فترفض الجملة. أزل التكرار قبل الإرسال.
- قائمة تحديث فارغة تترك الصف المتعارض كما هو. Laravel تنفذ هنا insert عاديًا يفشل.
- `updateOrInsert` تقرأ ثم تكتب، فهي ليست atomic (ذرّي). قد يدرج مستدعيان معًا. استخدم `upsert` على unique index حين يهمك ذلك.
- `insertOrIgnore` و`upsert` ترسلان كل الصفوف في جملة واحدة. حاصل ضرب الصفوف في الأعمدة يجب أن يبقى تحت حد الـ bindings في الـ driver (مشغّل): 999 على SQLite قبل 3.32، و32766 على SQLite من 3.32، و65535 على PostgreSQL. قسّم الدفعات الأكبر بنفسك، داخل transaction (معاملة) إذا كان يجب أن تنجح معًا.

## Row locks (أقفال الصفوف)

=== "Java"

    ```java
    connection.transaction(c -> {
        var accounts = query.on(c).table("accounts").where("id", 1).lockForUpdate().get();
        var jobs = query.on(c).table("jobs")
                .lock(LockStrength.UPDATE, LockWait.SKIP_LOCKED).limit(10).get();
        return null;
    });
    ```

=== "Kotlin"

    ```kotlin
    connection.transaction { c ->
        val accounts = query.on(c).table("accounts").where("id", 1).lockForUpdate().get()
        val jobs = query.on(c).table("jobs")
            .lock(LockStrength.UPDATE, LockWait.SKIP_LOCKED).limit(10).get()
        null
    }
    ```

`lockForUpdate()` و`sharedLock()` اختصاران لـ `lock(LockStrength.UPDATE)` و`lock(LockStrength.SHARE)`. لا يوجد قفل بنص خام كما في Laravel.

- يحتاج select المقفول على PostgreSQL إلى transaction، ويرمي `IllegalStateException` خارجها. نفّذ الاستعلام على الاتصال الذي يعطيك إياه callback (دالة يستدعيها النظام) الدالة `transaction(...)`.
- SQLite لا تدعم أقفال الصفوف. كل قوة قفل (`UPDATE` و`SHARE` و`NO_KEY_UPDATE` و`KEY_SHARE`) لا تكتب شيئًا هناك: SQLite تقفل قاعدة البيانات كلها، وعند أول كتابة في الـ transaction فقط. و`NOWAIT` و`SKIP_LOCKED` ترميان `UnsupportedOperationException`. الكود الذي يعتمد على القفل للاستبعاد المتبادل آمن على PostgreSQL فقط.
- الدوال التجميعية و`exists` وعدّاد `paginate` تهمل القفل. والـ union مع قفل مرفوض.

### قفل بمدة (timed lock)

=== "Java"

    ```java
    connection.transaction(c -> {
        var row = query.on(c).table("accounts").where("id", 1)
                .lock(LockStrength.UPDATE, Duration.ofSeconds(2)).first();
        return row;
    });
    ```

=== "Kotlin"

    ```kotlin
    connection.transaction { c ->
        val row = query.on(c).table("accounts").where("id", 1)
            .lock(LockStrength.UPDATE, Duration.ofSeconds(2)).first()
        row
    }
    ```

تنتظر `lock(strength, Duration)` قفل الصف هذه المدة كحد أقصى، ثم ترمي `QueryException` تعيد `isConcurrencyFailure()` فيه `true`.

- على PostgreSQL فقط. تحتاج إلى transaction مفتوحة وترمي `IllegalStateException` خارجها. وSQLite وAndroid ترميان `UnsupportedOperationException`.
- تسري على هذه الجملة وحدها. يعيد Diwan قيمة `lock_timeout` السابقة بعد الجملة.
- على cursor مقفول يسري الحد أثناء فتح الـ cursor فقط. والجلبات اللاحقة بلا حد.
- حد الجملة أقوى من `lockWait` للـ transaction ومن مفتاح الإعداد `lock_wait`. انظر [الاتصالات](connections.md#lock-wait).

## Pagination (ترقيم الصفحات)

=== "Java"

    ```java
    LengthAwarePage page = query.table("orders").orderBy("id").paginate(20, 3);   // per page, page number
    long total = page.total();
    SimplePage simple = query.table("orders").orderBy("id").simplePaginate(20, 3);
    boolean more = simple.hasMorePages();

    CursorPage first = query.table("orders").orderByDesc("created_at").orderBy("id").cursorPaginate(20);
    String token = first.nextCursor().map(Cursor::encode).orElse(null);           // send to the client
    CursorPage next = query.table("orders").orderByDesc("created_at").orderBy("id")
            .cursorPaginate(20, Cursor.decode(token));
    ```

=== "Kotlin"

    ```kotlin
    val page = query.table("orders").orderBy("id").paginate(20, 3)   // per page, page number
    val total = page.total()
    val simple = query.table("orders").orderBy("id").simplePaginate(20, 3)
    val more = simple.hasMorePages()

    val first = query.table("orders").orderByDesc("created_at").orderBy("id").cursorPaginate(20)
    val token = first.nextCursor().map { it.encode() }.orElse(null)   // send to the client
    val next = query.table("orders").orderByDesc("created_at").orderBy("id")
        .cursorPaginate(20, Cursor.decode(token))
    ```

`cursorPaginate` تحتاج `orderBy`، ويفضل أن ترتب بأعمدة لا تحمل null أبدًا، لأن null قد يجعلها تتخطى صفوفًا. رموز الـ cursor (مؤشر يقرأ الصفوف واحدًا واحدًا) غير موقّعة. الرمز المزوّر لا يستطيع حقن SQL، لكنه يستطيع طلب أي صفوف يسمح بها الاستعلام أصلًا.

حين يأتي عمود الترتيب من المستخدم، تحقق منه مقابل قائمة ثابتة قبل أن يصل إلى الـ builder:

=== "Java"

    ```java
    private static final Set<String> SORTABLE = Set.of("created_at", "total", "id");

    String column = SORTABLE.contains(requested) ? requested : "id";
    query.table("orders").orderBy(column).orderBy("id").cursorPaginate(20);
    ```

=== "Kotlin"

    ```kotlin
    val sortable = setOf("created_at", "total", "id")

    val column = if (requested in sortable) requested else "id"
    query.table("orders").orderBy(column).orderBy("id").cursorPaginate(20)
    ```

أسماء الأعمدة والاتجاه تُقتبس كمعرّفات ولا تُربط كقيم، فبناء allowlist (قائمة مسموحة) مسؤوليتك.

## قراءة الجداول الكبيرة

=== "Java"

    ```java
    // Offset batches. Return false to stop. Needs an order.
    query.table("orders").orderBy("id").chunk(500, rows -> { rows.forEach(this::recalculate); return true; });

    // Key batches. Safe when rows change during the loop.
    query.table("orders").where("status", "open").chunkById(500, rows -> { /* ... */ return true; });

    // One page per step, no connection held between pages.
    for (Map<String, Object> row : query.table("orders").orderBy("id").lazy(1000)) {
        export(row);
    }

    // Streams rows from one open statement.
    try (QueryCursor<Map<String, Object>> rows = query.table("orders").orderBy("id").cursor()) {
        for (Map<String, Object> row : rows) {
            export(row);
        }
    }
    ```

=== "Kotlin"

    ```kotlin
    // Offset batches. Return false to stop. Needs an order.
    query.table("orders").orderBy("id").chunk(500) { rows -> rows.forEach { recalculate(it) }; true }

    // Key batches. Safe when rows change during the loop.
    query.table("orders").where("status", "open").chunkById(500) { rows -> /* ... */ true }

    // One page per step, no connection held between pages.
    for (row in query.table("orders").orderBy("id").lazy(1000)) {
        export(row)
    }

    // Streams rows from one open statement.
    query.table("orders").orderBy("id").cursor().use { rows ->
        for (row in rows) {
            export(row)
        }
    }
    ```

`chunk` تقسم بالـ offset (إزاحة)، فالصفوف التي تُدرج أو تُحذف أثناء الحلقة قد تُتخطى أو تُقرأ مرتين. استخدم `chunkById` أو `lazyById` للجدول المتغير. على Android يعيد الـ cursor ملء نافذته بتنفيذ الاستعلام من جديد، فالأفضل هاتان الدالتان هناك أيضًا.

افتح `QueryCursor` دائمًا داخل try-with-resources (بنية Java لإغلاق المورد تلقائيًا). الـ cursor الذي لم يُقرأ حتى النهاية ولم يُغلق يحتفظ باتصاله من الـ pool (مجمّع الاتصالات) إلى الأبد، وقليل منها يستنفد الـ pool. وعلى PostgreSQL يترك جلسة الخادم idle داخل transaction، وهذا يعطل vacuum (عملية تنظيف في PostgreSQL). وعلى SQLite يحمل قفل قراءة، فتنتظر كتابة اتصال آخر أو تفشل بخطأ busy. داخل transaction لا تعمل أي جملة أخرى على الاتصال حتى يُغلق الـ cursor.

الدالتان `iterator()` و`stream()` تتشاركان استخدامًا واحدًا، والاستدعاء الثاني يرمي `IllegalStateException`. إغلاق الـ stream (تدفق) يغلق الـ cursor، فضعه داخل try-with-resources:

=== "Java"

    ```java
    try (Stream<Map<String, Object>> rows = query.table("orders").orderBy("id").cursor().stream()) {
        rows.limit(10).forEach(this::export);
    }
    ```

=== "Kotlin"

    ```kotlin
    query.table("orders").orderBy("id").cursor().stream().use { rows ->
        rows.limit(10).forEach { export(it) }
    }
    ```

على Android يعمل الـ cursor على الـ thread (خيط تنفيذ) الذي فتحه فقط.

## التعبيرات الخام (Raw expressions)

الدوال `selectRaw` و`whereRaw` و`orderByRaw` و`groupByRaw` و`havingRaw` و`fromRaw` و`Expression.raw` تكتب SQL كما تعطيها تمامًا. ضع القيم في قائمة الـ bindings، لا في النص.

=== "Java"

    ```java
    query.table("orders").whereRaw("total > ? and status = ?", List.of(100, status)).get();
    // Never: whereRaw("status = '" + status + "'")
    ```

=== "Kotlin"

    ```kotlin
    query.table("orders").whereRaw("total > ? and status = ?", listOf(100, status)).get()
    // Never: whereRaw("status = '" + status + "'")
    ```

ابنِ الـ SQL الخام من ثوابت. نص الـ SQL نفسه يجب ألا يأتي من مدخلات المستخدم أبدًا.

التالي: [Schema builder](schema.md)، [Models](models.md)، [الاختلافات عن Laravel](differences.md).

## مرجع الدوال

الدوال العامة التي لا تغطيها الأقسام السابقة، بصف واحد لكل اسم دالة (الـ overloads في صف واحد).

| الدالة | على | ماذا تفعل | مثال |
|---|---|---|---|
| `addBinding` `addBindings` `setBindings` `getRawBindings` | `Builder` | تقرأ القيم المربوطة (bindings) حسب الـ bucket (مثل `select` و`where` و`having`) أو تغيّرها. `addBinding` و`addBindings` تضيفان، و`setBindings` تستبدل bucket كاملًا، و`getRawBindings` تعيد كل الـ buckets. | `q.addBinding("where", 5)` |
| `addSelect` `selectSub` | `Builder` | تضيف إلى قائمة الأعمدة المختارة: استعلامًا فرعيًا بـ alias (`addSelect` و`selectSub`) أو تعبيرًا خامًا (`selectRaw`). | `q.selectSub(sub, "post_count")` |
| `distinct` | `Builder` | تجعل الاستعلام يعيد الصفوف المختلفة فقط. | `q.distinct().select("city")` |
| `average` `min` | `Builder` | `average` اسم بديل لـ `avg`. و`min` تعيد أصغر قيمة في عمود. | `q.min("price")` |
| `first` | `Builder` | تنفّذ الاستعلام بحد صف واحد على نسخة منه، وتعيد ذلك الصف. | `q.where("id", 1).first()` |
| `doesntExist` | `Builder` | تعيد هل لا يطابق أي صف. | `q.where("email", e).doesntExist()` |
| `each` `eachById` `chunkMap` | `Builder` | تمرّر الصفوف إلى callback أو تحوّلها صفحة بصفحة: `each` تقرأ 1000 صف في كل صفحة، و`eachById` تقسّم حسب الـ id، و`chunkMap` تحوّل كل صف وتعيد النتائج. | انظر «قراءة الجداول الكبيرة» |
| `chunkByIdDesc` `lazyByIdDesc` | `Builder` | تقرآن صفحات الـ id من الأعلى إلى الأدنى، بـ callback (`chunkByIdDesc`) أو بـ iterable كسول (`lazyByIdDesc`). | انظر «قراءة الجداول الكبيرة» |
| `forPage` `forPageAfterId` `forPageBeforeId` | `Builder` | تختار صفحة من الصفوف. `forPage` بـ offset وlimit، و`forPageAfterId` تأخذ الـ ids الأكبر من آخر id (الأصغر أولًا)، و`forPageBeforeId` تأخذ الأصغر منه (الأكبر أولًا). | `q.forPage(2, 15)` |
| `getCountForPagination` | `Builder` | تعدّ الصفوف التي تعرضها كل الصفحات معًا، على نسخة فلا يتغيّر الـ builder. | انظر «Pagination (ترقيم الصفحات)» |
| `crossJoin` `crossJoinSub` `leftJoin` `leftJoinWhere` `rightJoin` `rightJoinSub` `rightJoinWhere` `joinSub` `joinWhere` | `Builder` | صيغ ربط إضافية: `crossJoin` بلا شروط، و`leftJoin` و`rightJoin` على عمودين، وصيغ `...Sub` على استعلام فرعي، وصيغ `...Where` تقارن عمودًا بقيمة مربوطة. | `q.leftJoin("posts", "users.id", "posts.user_id")` |
| `fromSub` `getFrom` | `Builder` | `fromSub` تقرأ من استعلام فرعي بـ alias. و`getFrom` تعيد الجدول. | `q.fromSub(sub, "recent")` |
| `unionAll` | `Builder` | تضم استعلامًا بـ `union all` الذي يُبقي الصفوف المكررة. | انظر «الربط والاستعلامات الفرعية والاتحاد» |
| `hasJoins` `newQuery` | `Builder`, `JoinClause` | `hasJoins` تخبر هل في الاستعلام joins. و`newQuery` تعيد builder جديدًا فارغًا على نفس الاتصال والـ grammar والـ processor. | `q.newQuery().table("posts")` |
| `getConnection` `connection` `grammar` `getGrammar` `processor` `getProcessor` | `Builder`, `QueryFactory` | تعيد الأجزاء التي يعمل عليها الاستعلام: الاتصال، والـ grammar الذي يبني الـ SQL، والـ processor الذي يشكّل النتائج. وعلى `QueryFactory` تعيد ما يخص الـ factory نفسه. | `q.getGrammar()` |
| `query` | `QueryFactory` | تبدأ استعلامًا بلا جدول، مثلًا لـ `selectRaw("1")`. | `factory.query().selectRaw("1")` |
| `decrement` `decrementEach` `incrementEach` | `Builder` | `decrement` تطرح 1 (أو مقدارًا) من عمود الصفوف المطابقة. و`incrementEach` و`decrementEach` تغيّران عدة أعمدة دفعة واحدة. | `q.where("id", 1).decrement("stock")` |
| `insertOrIgnoreUsing` | `Builder` | تدرج الصفوف التي يعيدها استعلام فرعي وتتخطى الصفوف التي تخالف قيد unique أو primary key. | انظر «insertOrIgnore وupsert وupdateOrInsert» |
| `truncate` | `Builder` | تفرّغ الجدول. | `q.table("logs").truncate()` |
| `latest` `oldest` | `Builder` | ترتّب حسب `created_at`، الأحدث أولًا (`latest`) أو الأقدم أولًا (`oldest`). | `q.latest()` |
| `inRandomOrder` | `Builder` | ترتّب عشوائيًا. | `q.inRandomOrder().limit(1)` |
| `reorder` `reorderDesc` | `Builder` | `reorder` تزيل كل ترتيب وقيمه المربوطة، بما فيها ترتيب الـ union. و`reorderDesc` تستبدل كل ترتيب بعمود واحد تنازليًا. | `q.reorder("id")` |
| `offset` `skip` `take` | `Builder` | `offset` تتخطى صفوفًا (والقيمة السالبة تعني صفرًا). و`skip` اسم بديل لـ `offset`، و`take` اسم بديل لـ `limit`. | `q.skip(10).take(5)` |
| `toRawSql` | `Builder` | `toRawSql` تبني الاستعلام مع كتابة القيم المربوطة نصًا حرفيًا، للعرض والـ logging فقط. | `q.where("id", 1).toRawSql()` |
| `whereNot` `orWhereNot` | `Builder` | شرط منفي يقارن عمودًا بقيمة بالمساواة (`orWhereNot` تربطه بـ OR). | `q.whereNot("status", "draft")` |
| `whereNull` `orWhereNull` | `Builder`, `JoinClause` | شرط أن كل عمود قيمته null (`orWhereNull` تربطه بـ OR). | `q.whereNull("deleted_at")` |
| `whereNotNull` `orWhereNotNull` | `Builder` | شرط أن كل عمود قيمته ليست null (`orWhereNotNull` تربطه بـ OR). | `q.whereNotNull("email")` |
| `whereNotIn` `orWhereIn` `orWhereNotIn` | `Builder` | شروط IN وNOT IN، هنا على صفوف استعلام فرعي، مع صيغ `or`. | `q.orWhereIn("id", sub)` |
| `whereNotBetween` `orWhereBetween` `orWhereNotBetween` | `Builder` | شروط BETWEEN وNOT BETWEEN لزوج من القيم، مع صيغ `or`. | `q.whereNotBetween("age", 18, 65)` |
| `whereBetweenColumns` `whereNotBetweenColumns` `orWhereBetweenColumns` `orWhereNotBetweenColumns` | `Builder` | عمود يقع (أو لا يقع) بين عمودين آخرين، مع صيغ `or`. | `q.whereBetweenColumns("price", "min", "max")` |
| `whereValueBetween` `whereValueNotBetween` `orWhereValueBetween` `orWhereValueNotBetween` | `Builder` | قيمة تقع (أو لا تقع) بين عمودين، مع صيغ `or`. | `q.whereValueBetween(5, "low", "high")` |
| `orWhereColumn` | `Builder` | تقارن عمودين بالمساواة (تربطها `orWhereColumn` بـ OR). | `q.orWhereColumn("a", "b")` |
| `whereNotExists` `orWhereExists` `orWhereNotExists` | `Builder` | شروط EXISTS وNOT EXISTS على استعلام فرعي، مع صيغ `or`. | `q.whereNotExists(sub -> ...)` |
| `whereNotLike` `orWhereLike` `orWhereNotLike` | `Builder` | شروط LIKE وNOT LIKE غير حساسة لحالة الأحرف، مع صيغ `or`. | `q.whereNotLike("name", "a%")` |
| `whereContains` `whereStartsWith` `whereEndsWith`، مع صيغ `or` و`Not` و`orNot` | `Builder` | بحث نصي لمدخلات المستخدم، تبقى فيه القيمة حرفية دائمًا، مع علم `caseSensitive` اختياري. | `q.whereContains("name", input)` |
| `orWhereAll` `orWhereAny` `orWhereNone` | `Builder` | مجموعات `or` على عدة أعمدة: كل الأعمدة تساوي القيمة (`All`)، أو واحد منها على الأقل (`Any`)، أو لا واحد (`None`). | `q.orWhereAny(cols, "x")` |
| `whereDay` `whereYear` `whereTime` `orWhereDate` `orWhereDay` `orWhereMonth` `orWhereYear` `orWhereTime` | `Builder` | شروط على جزء من عمود تاريخ أو وقت نصي: اليوم أو الشهر أو السنة أو الوقت (والتاريخ في `orWhereDate`)، بالمساواة. صيغ `or` تربط بـ OR. | `q.whereYear("created_at", 2026)` |
| `whereIntegerInRaw` | `Builder` | عمود ضمن قائمة أعداد صحيحة تُكتب داخل الـ SQL ولا تُربط؛ والقائمة الفارغة لا تطابق أي صف. | `q.whereIntegerInRaw("id", List.of(1, 2))` |
| `whereNullSafeEquals` `orWhereNullSafeEquals` | `Builder` | مقارنة تعدّ قيمتي null متساويتين، مع صيغة `or`. | `q.whereNullSafeEquals("a", null)` |
| `whereRowValues` `orWhereRowValues` | `Builder` | تقارن صفًا من الأعمدة بصف من القيم: `(a, b) < (?, ?)`. | `q.whereRowValues(cols, "<", vals)` |
| `orWhereRaw` `orHavingRaw` | `Builder` | SQL موثوق يُربط بالشروط السابقة بـ OR، في `where` أو `having`. | `q.orWhereRaw("a > b")` |
| `groupWheresAt` | `Builder` | تعيد تجميع شروط where حول فهرس معيّن. | - |
| `orHaving` `orHavingBetween` `orHavingNotBetween` `orHavingNull` `orHavingNotNull` `orHavingNested` `havingBetween` `havingNotBetween` `havingNull` `havingNotNull` `havingNested` | `Builder` | شروط having: between وnot between وnull وnot null ومجموعة متداخلة بين أقواس. صيغ `orHaving...` تربط بـ OR. | `q.havingNotNull("total")` |
| `on` `orOn` | `JoinClause` | داخل join، تضيف شرطًا يقارن عمودين بالمساواة (`orOn` تربطه بـ OR). | `join.on("a.id", "b.a_id")` |
| `getTable` `getType` | `JoinClause` | على `JoinClause`، تعيدان الجدول المربوط ونوع الـ join. | `join.getType()` |
| `close` `isClosed` | `QueryCursor` | `close` تحرّر الـ statement وكل ما يحمله الـ cursor (والاستدعاء الثاني لا يفعل شيئًا)، و`isClosed` تخبر هل أُغلق الـ cursor. | `try (var c = q.cursor()) { ... }` |
| `currentPage` `lastPage` `perPage` `items` | `LengthAwarePage`, `SimplePage`, `CursorPage` | تقرأ كائن الصفحة: رقم الصفحة بدءًا من 1، ورقم الصفحة الأخيرة (1 إن لم يطابق صف)، وحجم الصفحة، والصفوف. | `page.items()` |
| `previousCursor` | `CursorPage` | تعيد cursor الصفحة التي قبل هذه. | `page.previousCursor()` |
| `encode` | `Cursor` | تكتب الـ cursor نصًا صالحًا للـ URL (base64url بلا padding). | `cursor.encode()` |
| `parameter` `parameters` | `Cursor` | تعيد قيمة عمود ترتيب واحد، أو كل قيم الترتيب في الـ cursor. | `cursor.parameter("id")` |
| `pointsToNextItems` `pointsToPreviousItems` | `Cursor` | تخبران هل يقود الـ cursor إلى الصفوف بعد موضعه أو قبله. | `cursor.pointsToNextItems()` |
| `toString` `equals` `hashCode` | `LengthAwarePage`, `SimplePage`, `CursorPage`, `Cursor` | نص ومساواة وhash قياسية لقيم الصفحات والـ cursors. | - |
| `on` | `QueryFactory` | تعيد هذا الـ factory مربوطًا باتصال آخر لقاعدة البيانات نفسها، مثل الاتصال الذي تعطيك إياه المعاملة. وترمي `IllegalArgumentException` مع نوع آخر من قواعد البيانات. | `query.on(tx)` |
