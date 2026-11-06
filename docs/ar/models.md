# النماذج

النموذج (model) هو صنف واحد لكل جدول، بأسماء دوال Eloquent (طبقة النماذج والعلاقات المنقولة من Laravel). يحتفظ بخصائصه، ويعرف أيّها تغيّر،
ويكتب المتغيّر فقط. كل استعلام يمرّ عبر [query builder](query-builder.md) (منشئ الاستعلامات)، فتحصل على
الـ SQL نفسه الذي تحصل عليه من `table(...)`.

تعيش النماذج في `diwan-database-eloquent`:

```kotlin
implementation("org.aristonis:diwan-database-eloquent:0.1.0")
```

## تعريف نموذج

يحتاج النموذج إلى مدخل `static` واحد. لا يستعمل reflection (الانعكاس في Java) ولا annotations ولا build plugin، ولذلك يعمل الصنف نفسه على Android.

```java
public final class User extends Model {
    public static final ModelQuery<User> query = ModelQuery.of(User.class, User::new);

    @Override
    protected List<String> fillable() {
        return List.of("name", "email");   // nothing is mass assignable until listed
    }
}

ModelQuery<User> users = User.query.on(SQLiteQuery.of(db));
```

تربط `on(...)` المدخل بـ query factory (مصنع الاستعلامات). داخل transaction (معاملة) اربط النموذج باتصال المعاملة عبر `users.on(c)`
حتى تعمل كل العبارات داخلها.

## ضبط النموذج

تجاوز (override) هذه الدوال لتغيير القيم الافتراضية:

| الدالة | القيمة الافتراضية |
|---|---|
| `table()` | الجمع بصيغة snake-case لاسم الصنف (`BlogPost` تعطي `blog_posts`) |
| `primaryKey()` و`keyType()` و`incrementing()` | `id` و`int` و`true` |
| `connectionName()` | الاتصال الافتراضي |
| `timestamps()` و`createdAtColumn()` و`updatedAtColumn()` | مفعّلة، `created_at`، `updated_at` |
| `timestampFormat()` و`dateFormat()` | نص UTC بصيغة `yyyy-MM-dd HH:mm:ss`؛ و`TimestampFormat.INSTANT` لأعمدة instant (لحظة زمنية محددة) |
| `uniqueIdKind()` | `UniqueIdKind.NONE`؛ و`UUID` (الإصدار 7) أو `ULID` يولّد المفتاح عند الإدراج |
| `perPage()` | حجم الصفحة في `paginate()` بلا وسيط |
| `softDeletes()` و`deletedAtColumn()` | معطّل، `deleted_at` |

يأتي الجمع من مجموعة قصيرة من القواعد الإنجليزية. تجاوز `table()` حين يخطئ التخمين.

## الإسناد الجماعي

تضبط `fill` المفاتيح الموجودة في `fillable()` فقط وتتجاهل الباقي. مع الحماية الافتراضية (`guarded()` تساوي `*` و`fillable()` فارغة)
ترمي `fill` الاستثناء `MassAssignmentException`. أمّا `forceFill` و`Model.unguarded(...)` فتتجاوزان الحماية.

```java
User user = users.make(request);   // fills; "is_admin" in request is dropped
user.save();
```

## الخصائص والـ accessors والـ casts

```java
found.setAttribute("name", "Ada L.");
found.isDirty("name");      // true
found.getDirty();           // {name=Ada L.}
found.save();               // writes name and updated_at only
found.save();               // clean: runs nothing
```

صرّح بالـ casts (تحويل نوع القيمة المخزَّنة) في `casts()` بصيغة Laravel النصية أو بالدوال الجاهزة في `Casts`:

```java
@Override
protected Map<String, Cast<?>> casts() {
    return CastMap.create()
            .put("price", "decimal:2")                      // BigDecimal, scale 2
            .put("is_admin", "bool")                        // Boolean
            .put("options", "json")                         // Map or List
            .put("born_on", "date")                         // LocalDate
            .put("paid_at", Casts.datetime("dd/MM/yyyy"))   // Instant
            .put("status", Casts.enumOf(Status.class))      // the enum constant
            .build();
}
```

```java
Order order = orders.findOrFail(1);
BigDecimal price = (BigDecimal) order.getAttribute("price");
order.getAttributes().get("price");   // the stored form, "12.50"
```

البيانات المخزَّنة التالفة، مثل JSON مكسور أو `"abc"` تحت `int`، ترمي `InvalidCastException`. أمّا Laravel فتقرأ `null` أو `0` هنا.
يقارن فحص التغيّر (dirty check) بالمعنى: JSON بالبنية، واللحظات كـ instants، والتواريخ كتواريخ. قراءة قيمة cast (تحويل نوع قيمة الـ attribute عند القراءة والكتابة) لا تجعل النموذج dirty أبدًا،
لكن تعديل map أعادها cast من نوع `json` يفعل ذلك. ولكتابة cast خاص بك نفّذ `Cast<T>` (الدالتان `get` و`set`).

صيغ التواريخ هي أنماط `DateTimeFormatter` في Java. اكتب `yyyy-MM-dd` لا `Y-m-d` الخاصة بـ PHP: تُترجَم صيغة PHP في Java
لكنها تعني شيئًا آخر.

الـ accessors والـ mutators (دوال القراءة والكتابة المخصّصة للخاصية) تُسجَّل في `accessors()` ولا تُكتشف بالاسم:

```java
@Override
protected Map<String, Attribute<?>> accessors() {
    Map<String, Attribute<?>> map = new LinkedHashMap<>();
    map.put("display_name", Attribute.get((model, value, attrs) -> attrs.get("first") + " " + attrs.get("last")));
    map.put("email", Attribute.set((model, value, attrs) -> value.toString().toLowerCase(Locale.ROOT)));
    return map;
}
```

تُقرأ `casts()` و`accessors()` مرة واحدة لكل صنف، فلا يجوز أن تعتمدا على حالة النسخة.

## الحفظ والإنشاء والبحث

```java
User ada = users.create(Map.of("name", "Ada", "email", "ada@example.com"));  // id, timestamps set
User found = users.findOrFail(ada.getKey());
Optional<User> maybe = users.find(42);
Optional<User> first = users.query().where("email", "ada@example.com").first();

found.update(Map.of("name", "Ada Lovelace"));
found.increment("logins");
found.delete();            // false when the model is not in the database
```

تحفظ `saveOrFail()` وتنفّذ touches الخاصة بها داخل transaction واحدة. وترمي `IllegalStateException` حين يكون لنموذج مفتاحه غير تلقائي
الزيادة لا شيء ليُدرَج. أمّا `save()` العادية فتعيد `true` هناك، كما في Laravel.

البحث عن صف أو إنشاؤه:

```java
User sam = users.firstOrCreate(Map.of("email", "sam@example.com"), Map.of("name", "Sam"));
users.updateOrCreate(Map.of("email", "sam@example.com"), Map.of("name", "Samuel"));
users.firstOrNew(Map.of("email", "new@example.com"), Map.of("name", "New"));   // not saved
```

تكتب `upsert` و`insertOrIgnore` صفوفًا كثيرة بعبارة واحدة. لا تُطلقان أحداث النموذج ولا تطبّقان الـ casts،
لكنهما تملآن المعرّفات الفريدة والـ timestamps:

```java
users.query().upsert(rows, List.of("email"));          // needs a unique index on email
users.query().upsert(rows, List.of("email"), List.of("name"));
users.query().insertOrIgnore(rows);
```

تحتاج `upsert` إلى SQLite 3.24 أو أحدث، أي Android API 30 أو أحدث. انظر [Android](android.md).

## النطاقات (Scopes)

يضيف global scope (نطاق عام) قيدًا إلى كل استعلام للنموذج، بما فيه eager loads و`whereHas`. سجّله مرة واحدة عند بدء التشغيل، باسم:

```java
posts.addGlobalScope("tenant", q -> q.where("tenant_id", 7));

posts.query().withoutGlobalScope("tenant").get();   // one query without it
posts.query().withoutGlobalScopes().get();
```

يجوز للـ scope أن يضيف شروط استعلام فقط. ويجب أن يكون بلا حالة وألّا ينفّذ استعلامًا بنفسه. الصنف الذي ينفّذ `Scope` يُسجَّل عبر
`addGlobalScope(Scope)`، أمّا الـ lambda (دالة مجهولة مختصرة) فتحتاج اسمًا. والـ local scope خطوة قابلة لإعادة الاستعمال تطبّقها على استعلام واحد:

```java
posts.query().scope(q -> q.where("published", true)).get();
```

## الحذف الناعم (Soft deletes)

فعّله بجعل `softDeletes()` تعيد `true`. بعدها:

| تريد | استعمل |
|---|---|
| حذفًا ناعمًا | `delete()` تضبط `deleted_at` (و`updated_at`) |
| إزالة الصف نهائيًا | `forceDelete()` |
| الاستعادة | `restore()` |
| الفحص | `trashed()` |
| قراءة الصفوف المحذوفة مع غيرها أو وحدها | `query().withTrashed()` و`query().onlyTrashed()` |
| إيجاد صف محذوف أو إنشاءه | `restoreOrCreate(attributes)` و`createOrRestore(attributes)` على الاستعلام |

الفهرس الفريد (unique index) يشمل الصفوف المحذوفة أيضًا، فيفشل `create` العادي الذي يعيد مفتاحًا يحمله صف محذوف.
أمّا `restoreOrCreate` فتجد الصف المحذوف وتستعيده. و`forceDelete()` على الاستعلام تتخطى scope الحذف الناعم فقط، فيبقى tenant (مستأجر) scope مطبّقًا.

## الأحداث والـ observers

سجّل الـ listeners (المستمعين) مرة واحدة عند بدء التشغيل على `ModelQuery` الخاص بالنموذج:

```java
posts.events()
        .saving(post -> {                       // return false to stop the save
            if (post.getString("slug") == null) {
                post.setAttribute("slug", slugOf(post.getString("title")));
            }
            return true;
        })
        .created(post -> auditLog.record("post created", post.getKey()));

posts.events().observe(new PostObserver());     // a ModelObserver<Post>
```

الأحداث هي `retrieved` و`saving` و`saved` و`creating` و`created` و`updating` و`updated` و`deleting` و`deleted` و`softDeleted`
و`restoring` و`restored` و`forceDeleting` و`forceDeleted` و`replicating`. الستة التي تعمل قبل الكتابة تستطيع إيقافها بإرجاع `false`.
`false` وحدها توقف؛ أمّا `true` فتترك الـ listener (مستمع للأحداث) التالي يعمل.

تؤجّل `events().afterCommit()` و`ModelObserver.afterCommit()` الـ listener حتى يتم commit (تثبيت المعاملة) للمعاملة الخارجية. والـ rollback (تراجع) يُسقطه.
لتخطي الأحداث استعمل `Model.withoutEvents(() -> ...)` (على هذا thread (خيط تنفيذ) فقط) أو `saveQuietly()` و`deleteQuietly()`. الـ listener الذي يحفظ
نموذجه نفسه يجب أن يستعمل `saveQuietly()` وإلا استدعى نفسه من جديد. وكتابات الـ builder مثل `query().update(...)` لا تحمّل نموذجًا ولا تُطلق حدثًا.

## التسلسل (Serialization)

تطبّق `toMap()` و`toJson()` الدالة `visible()` ثم `hidden()` ثم `appends()`. تخرج اللحظات بصيغة ISO-8601 UTC بدقة الميكروثانية.
وتأتي العلاقات المحمّلة بعد الخصائص، وتنتهي الدورة (cycle) عند تكرارها.

```java
@Override
protected List<String> hidden() { return List.of("password"); }

String json = user.toJson();
```

الـ codec (مُرمِّز JSON) المدمج صارم وفق RFC 8259، والمكتبة لا تضيف أي اعتماد JSON. لاستعمال Jackson أو Gson نفّذ `JsonCodec` وأعده من `jsonCodec()`.

## الـ chunks والقراءة الكسولة والـ cursors والصفحات

```java
users.query().orderBy("id").chunk(500, batch -> { batch.forEach(this::sync); return true; });
users.query().chunkById(500, batch -> { /* rows may change here */ return true; });

for (User u : users.query().orderBy("id").lazy(1000)) { /* one page at a time */ }

try (QueryCursor<User> cursor = users.query().orderBy("id").cursor()) {
    for (User u : cursor) { /* streams one row at a time */ }
}

ModelPage<User> page = users.query().orderBy("name").paginate(20, 2);
page.items();   // ModelCollection<User>
page.total();
```

تقسّم `chunk` الصفوف بالإزاحة (offset)، فاستعمل `chunkById` حين تتغيّر الصفوف أثناء الحلقة. أغلق `cursor()` دائمًا: المفتوح يحتفظ باتصاله.
يرفض الـ cursor (مؤشر يقرأ الصفوف واحدًا واحدًا) الـ eager loads؛ أمّا `lazy()` فتحمّلها لكل صفحة. و`simplePaginate` و`cursorPaginate` تعملان كما في query builder (باني الاستعلامات).

## الحدود

- النماذج ليست آمنة للاستعمال من عدة threads. شارك `ModelQuery`، وأعطِ كل thread نسخه الخاصة.
- من دون cast من نوع `bool`، قيمة `Boolean` تُضبط على عمود SQLite تُقرأ `1` وتبقى dirty مقابل `true`.
- تنتمي الـ listeners والـ scopes إلى الصنف المسجَّل عبر `ModelQuery.of`؛ والصنف الفرعي المسجَّل منفصلًا له قائمته الخاصة.

انظر [العلاقات](relations.md) و[الفروق عن Laravel](differences.md) و[الأخطاء](errors.md).
