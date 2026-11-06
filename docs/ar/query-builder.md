# Query builder

الـ query builder (باني الاستعلامات) يقرأ الصفوف ويكتبها عبر سلسلة من استدعاءات الدوال. كل قيمة تمررها تُربط كـ parameter، فلا يضع الـ builder بياناتك داخل نص SQL أبدًا.

## الحصول على builder

لكل قاعدة بيانات نقطة دخول واحدة تعيد `QueryFactory`. استدعِ `table(...)` عليها لتبدأ استعلامًا.

```java
import org.aristonis.diwan.database.query.QueryFactory;
import org.aristonis.diwan.database.sqlite.SQLiteQuery;     // diwan-database-sqlite:0.1.0
import org.aristonis.diwan.database.pgsql.PostgresQuery;    // diwan-database-pgsql:0.1.0

QueryFactory query = SQLiteQuery.of(db);        // SQLite, and Android through the same grammar
// QueryFactory query = PostgresQuery.of(db);   // PostgreSQL
```

المتغير `db` هو الـ `Connection` من صفحة [الاتصالات والمعاملات](connections.md). على Android تمرر الـ factory إلى `AndroidConnector`، راجع [Android](android.md). الـ builder غير آمن للاستخدام من عدة threads. الدالة `clone()` تعطيك نسخة مستقلة.

## الاختيار والتصفية

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

الصفوف من نوع `Map<String, Object>`. من المرشحات الأخرى `whereBetween` و`whereLike` و`whereColumn` و`whereAny` و`whereAll` و`whereNone`، والشروط المجمعة بـ `where(q -> ...)`، و`groupBy` مع `having`. الدالتان `toSql()` و`getBindings()` تعرضان ما سينفذه الـ builder.

دوال التاريخ (`whereDate` و`whereMonth` وغيرهما) مخصصة لأعمدة التاريخ النصية. مع أعمدة الـ instant (لحظة زمنية) استخدم `whereInstantBetween(column, from, to)`.

## الربط والاستعلامات الفرعية والاتحاد

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

يُنسخ الاستعلام الفرعي عند إرفاقه، فتغييره لاحقًا لا يغير الاستعلام الخارجي. الـ right join يحتاج SQLite بالإصدار 3.39 أو أحدث، وهو ما يأتي مع Android 14 (API 34) وما بعده. إصدارات SQLite الأقدم على Android تُرجع خطأها الخاص في صورة `QueryException`.

## الدوال التجميعية

```java
long total = query.table("orders").count();
Number revenue = query.table("orders").sum("total");          // 0 when there are no rows
Optional<Object> biggest = query.table("orders").max("total");
Optional<Number> mean = query.table("orders").avg("total");
```

## الإدراج والتحديث والحذف

```java
Object id = query.table("users").insertGetId(Map.of("email", "ada@example.com"));
query.table("users").insert(List.of(Map.of("email", "a@x"), Map.of("email", "b@x")));
query.table("users").where("id", id).update(Map.of("email", "ada@example.org"));
query.table("posts").where("id", 3).increment("views");
query.table("users").where("id", id).delete();
query.table("archive").insertUsing(List.of("id", "total"),
        q -> q.from("orders").select("id", "total").where("status", "closed"));
```

يجوز أن يربط التحديث أو الحذف جداول أخرى. على SQLite هذا يتطلب جدولًا له rowid. الكتابة تحتاج جدولًا، لا استعلامًا فرعيًا ولا `from` خامًا.

### insertOrIgnore وupsert وupdateOrInsert

```java
query.table("users").insertOrIgnore(rows);                       // skips rows that break a unique key
query.table("users").upsert(rows, List.of("email"));             // updates every column of the first row
query.table("users").upsert(rows, List.of("email"), List.of("name"));
query.table("users").upsert(rows, List.of("email"),
        Map.of("votes", Expression.raw("users.votes + 1")));
query.table("users").updateOrInsert(Map.of("email", "a@x"), Map.of("name", "A"));
```

- `insertOrIgnore` تعيد عدد الصفوف التي أُدرجت. على SQLite تتخطى أيضًا الصف الذي يخالف قيد `not null` أو `check`، لا قيد الفرادة فقط.
- `upsert` تحتاج unique index (فهرس فرادة) على الأعمدة الموجودة في `uniqueBy` تمامًا، وإلا ترفضها قاعدة البيانات. وتحتاج SQLite 3.24 أو أحدث (Android API 30 فما فوق). الإصدارات الأقدم ترمي `UnsupportedOperationException` قبل تنفيذ أي SQL.
- إذا كان في الدفعة صفان بنفس مفتاح الفرادة، تطبقهما SQLite بالترتيب فيفوز الأخير. أما PostgreSQL فترفض الجملة. أزل التكرار قبل الإرسال.
- قائمة تحديث فارغة تترك الصف المتعارض كما هو. Laravel تنفذ هنا insert عاديًا يفشل.
- `updateOrInsert` تقرأ ثم تكتب، فهي ليست atomic (ذرّي). قد يدرج مستدعيان معًا. استخدم `upsert` على unique index حين يهمك ذلك.
- `insertOrIgnore` و`upsert` ترسلان كل الصفوف في جملة واحدة. حاصل ضرب الصفوف في الأعمدة يجب أن يبقى تحت حد الـ bindings في الـ driver (مشغّل): 999 على SQLite قبل 3.32، و32766 على SQLite من 3.32، و65535 على PostgreSQL. قسّم الدفعات الأكبر بنفسك، داخل transaction (معاملة) إذا كان يجب أن تنجح معًا.

## Row locks (أقفال الصفوف)

```java
db.transaction(c -> {
    var accounts = PostgresQuery.of(c).table("accounts").where("id", 1).lockForUpdate().get();
    var jobs = PostgresQuery.of(c).table("jobs")
            .lock(LockStrength.UPDATE, LockWait.SKIP_LOCKED).limit(10).get();
    return null;
});
```

`lockForUpdate()` و`sharedLock()` اختصاران لـ `lock(LockStrength.UPDATE)` و`lock(LockStrength.SHARE)`. لا يوجد قفل بنص خام كما في Laravel.

- يحتاج select المقفول على PostgreSQL إلى transaction، ويرمي `IllegalStateException` خارجها. نفّذ الاستعلام على الاتصال الذي يعطيك إياه callback (دالة يستدعيها النظام) الدالة `transaction(...)`.
- SQLite لا تدعم أقفال الصفوف. القفلان البسيطان `UPDATE` و`SHARE` لا يكتبان شيئًا، والأقفال الخاصة بـ PostgreSQL (`NO_KEY_UPDATE` و`KEY_SHARE` و`NOWAIT` و`SKIP_LOCKED`) ترمي `UnsupportedOperationException`. الكود الذي يعتمد على القفل للاستبعاد المتبادل آمن على PostgreSQL فقط.
- الدوال التجميعية و`exists` وعدّاد `paginate` تهمل القفل. والـ union مع قفل مرفوض.

## Pagination (ترقيم الصفحات)

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

`cursorPaginate` تحتاج `orderBy`، ويفضل أن ترتب بأعمدة لا تحمل null أبدًا، لأن null قد يجعلها تتخطى صفوفًا. رموز الـ cursor (مؤشر يقرأ الصفوف واحدًا واحدًا) غير موقّعة. الرمز المزوّر لا يستطيع حقن SQL، لكنه يستطيع طلب أي صفوف يسمح بها الاستعلام أصلًا.

حين يأتي عمود الترتيب من المستخدم، تحقق منه مقابل قائمة ثابتة قبل أن يصل إلى الـ builder:

```java
private static final Set<String> SORTABLE = Set.of("created_at", "total", "id");

String column = SORTABLE.contains(requested) ? requested : "id";
query.table("orders").orderBy(column).orderBy("id").cursorPaginate(20);
```

أسماء الأعمدة والاتجاه تُقتبس كمعرّفات ولا تُربط كقيم، فبناء allowlist (قائمة مسموحة) مسؤوليتك.

## قراءة الجداول الكبيرة

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

`chunk` تقسم بالـ offset (إزاحة)، فالصفوف التي تُدرج أو تُحذف أثناء الحلقة قد تُتخطى أو تُقرأ مرتين. استخدم `chunkById` أو `lazyById` للجدول المتغير. على Android يعيد الـ cursor ملء نافذته بتنفيذ الاستعلام من جديد، فالأفضل هاتان الدالتان هناك أيضًا.

افتح `QueryCursor` دائمًا داخل try-with-resources (بنية Java لإغلاق المورد تلقائيًا). الـ cursor الذي لم يُقرأ حتى النهاية ولم يُغلق يحتفظ باتصاله من الـ pool (مجمّع الاتصالات) إلى الأبد، وقليل منها يستنفد الـ pool. وعلى PostgreSQL يترك جلسة الخادم idle داخل transaction، وهذا يعطل vacuum (عملية تنظيف في PostgreSQL). وعلى SQLite يحمل قفل قراءة، فتنتظر كتابة اتصال آخر أو تفشل بخطأ busy. داخل transaction لا تعمل أي جملة أخرى على الاتصال حتى يُغلق الـ cursor.

الدالتان `iterator()` و`stream()` تتشاركان استخدامًا واحدًا، والاستدعاء الثاني يرمي `IllegalStateException`. إغلاق الـ stream (تدفق) يغلق الـ cursor، فضعه داخل try-with-resources:

```java
try (Stream<Map<String, Object>> rows = query.table("orders").orderBy("id").cursor().stream()) {
    rows.limit(10).forEach(this::export);
}
```

على Android يعمل الـ cursor على الـ thread (خيط تنفيذ) الذي فتحه فقط.

## التعبيرات الخام (Raw expressions)

الدوال `selectRaw` و`whereRaw` و`orderByRaw` و`groupByRaw` و`havingRaw` و`fromRaw` و`Expression.raw` تكتب SQL كما تعطيها تمامًا. ضع القيم في قائمة الـ bindings، لا في النص.

```java
query.table("orders").whereRaw("total > ? and status = ?", List.of(100, status)).get();
// Never: whereRaw("status = '" + status + "'")
```

ابنِ الـ SQL الخام من ثوابت. نص الـ SQL نفسه يجب ألا يأتي من مدخلات المستخدم أبدًا.

التالي: [Schema builder](schema.md)، [Models](models.md)، [الاختلافات عن Laravel](differences.md).
