# النماذج

النموذج (model) هو صنف واحد لكل جدول، بأسماء دوال Eloquent (طبقة النماذج والعلاقات المنقولة من Laravel). يحتفظ بخصائصه، ويعرف أيّها تغيّر،
ويكتب المتغيّر فقط. كل استعلام يمرّ عبر [query builder](query-builder.md) (منشئ الاستعلامات)، فتحصل على
الـ SQL نفسه الذي تحصل عليه من `table(...)`.

تعيش النماذج في `diwan-database-eloquent`:

```kotlin
implementation("org.aristonis:diwan-database-eloquent:0.3.0")
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

ModelQuery<User> users = User.query.on(manager.query());
```

تربط `on(...)` المدخل بـ query factory (مصنع الاستعلامات)، وعادةً `manager.query()`، فلا يذكر النموذج أي صنف driver. داخل transaction (معاملة) اربط النموذج عبر `User.query.on(db.on(tx))`
حتى تعمل كل العبارات على المعاملة.

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

يخزّن `Casts.instant()` قيمة `Instant` مهما كان `timestampFormat()` في النموذج. استعمله لأعمدة `Blueprint.instant`. والأعمدة `created_at` و`updated_at` و`deleted_at` تكتبها مباشرةً عمليات soft delete والتحديث الجماعي و`touch`، وبصيغة النموذج دائمًا. لذلك إذا كانت هذه الأعمدة من نوع `instant` فالنموذج يحتاج `TimestampFormat.INSTANT`. أما نموذج بصيغة TEXT يضع cast الـ instant على أحدها فيفشل عند أول استعمال، والرسالة تسمّي العمود.

```java
@Override
protected TimestampFormat timestampFormat() { return TimestampFormat.INSTANT; }

@Override
protected Map<String, Cast<?>> casts() {
    return CastMap.create().put("sent_at", Casts.instant()).build();   // any other instant column
}
```

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

### decimal صارم للمال

يقرأ `decimal:2` ويكتب أي رقم بخانتين عشريتين ويقرّب الخانات الزائدة half up، كما يفعل Laravel. للمال، صرّح بالعمود بنفس أرقام الـ migration الخاصة به، فيفحص الـ cast ما يتّسع له العمود:

```java
// migration: table.decimal("total", 6, 2)   -- 6 digits in all, 2 after the point
@Override
protected Map<String, Cast<?>> casts() {
    return CastMap.create()
            .put("total", Casts.decimal(6, 2))                          // decimal:6,2
            .put("tax", Casts.decimal(6, 2, RoundingMode.HALF_EVEN))    // decimal:6,2,HALF_EVEN
            .build();
}
```

وتعمل نصوص المواصفة (spec) أيضًا: `decimal:6,2` و`decimal:6,2,HALF_EVEN` (اسم الوضع بأي حالة أحرف). الرقم الأول هو إجمالي الخانات والثاني عدد الخانات بعد الفاصلة. يجب أن يحقق كلاهما `0 <= scale <= precision`، والتصريح الخاطئ يرمي `IllegalArgumentException`.

عند تعيين قيمة:

- الخانات العشرية الأكثر من الـ scale مرفوضة افتراضيًا. أما الوضع (mode) فيقرر ما يحدث لها بدل ذلك: `Casts.decimal(6, 2)` ترفض `10.125`، و`Casts.decimal(6, 2, HALF_UP)` تخزّن `10.13`.
- الخانات الصحيحة الأكثر من `precision - scale` مرفوضة دائمًا مهما كان الوضع. مع `decimal:6,2` تُرفض `10000.00`، وكذلك `9999.999` تحت `HALF_UP`، لأن التقريب يحملها إلى `10000.00`.
- القيمة المرفوضة ترمي `InvalidCastException`. تسمّي الرسالة النموذج والـ attribute والقاعدة التي كُسرت، ولا تحتوي القيمة أبدًا.

القراءة تعيد `BigDecimal` بالـ scale المصرّح به، فتعود `12.5` على هيئة `12.50`.

| الوضع (Mode) | القاعدة | مثال، `decimal:6,2,MODE` | المخزَّن |
|---|---|---|---|
| `UNNECESSARY` (الافتراضي) | يرفض أي خانة عشرية زائدة. | تبقى `10.12` كما هي `10.12`؛ و`10.125` ترمي | `10.12` |
| `HALF_UP` | يقرّب إلى الأقرب، والتعادل بعيدًا عن الصفر. | `10.125` | `10.13` |
| `HALF_EVEN` | يقرّب إلى الأقرب، والتعادل إلى الخانة الزوجية (تقريب المصرفيين). | `10.125` | `10.12` |
| `DOWN` | يقطع نحو الصفر. | `10.129` | `10.12` |
| `UP` | يقرّب بعيدًا عن الصفر. | `10.121` | `10.13` |
| `FLOOR` | يقرّب نحو سالب اللانهاية. | `-10.121` | `-10.13` |
| `CEILING` | يقرّب نحو موجب اللانهاية. | `-10.129` | `-10.12` |

### قاعدة الـ 15 رقمًا على SQLite

تحتفظ SQLite بعمود decimal كعدد double، يتسع لنحو 15 رقمًا معنويًا. لذلك يرفض الـ cast الصارم على SQLite أي قيمة فيها أكثر من 15 رقمًا معنويًا. ويسمّي `InvalidCastException` العمود ولا يذكر القيمة أبدًا. أما PostgreSQL فتخزّن decimal دقيقًا ولم تتغيّر.

هذا تغيير في السلوك لمن يرقّي: قيمة كانت تُقبل سابقًا وفيها أكثر من 15 رقمًا ترمي الآن. وللاحتفاظ بقيم أطول دقيقة على SQLite استعمل عمود نص مع `Casts.decimalText(precision, scale)`، وهو يحتفظ بقواعد الدقة والمنازل الصارمة لكنه يتخطى حد الخمسة عشر رقمًا:

```java
// migration: table.string("rate")   -- text column, exact digits
.put("rate", Casts.decimalText(30, 15))
```

`Casts.decimal(scale)` (`decimal:2`) لم تتغيّر: لا حدّ لها على الـ precision وتقرّب half up. استعمل الصيغة الصارمة للمال، ليتّسع العمود دائمًا للقيمة المخزّنة.

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

تملأ `fillAndInsert` و`fillAndInsertOrIgnore` و`fillAndInsertGetId` كل صف كما تفعل `fill`، ثم تدرجه. تُستدعى على `EloquentBuilder` الذي تعيده `query()`، لا على `ModelQuery`:

```java
Member.query.on(db).query().fillAndInsert(rows);
int added = Member.query.on(db).query().fillAndInsertOrIgnore(rows);
Object id = Member.query.on(db).query().fillAndInsertGetId(row);
```

الملء هنا يتجاوز حماية `fillable`، فلا تمرّر بيانات الطلب إلى هذه الدوال دون فحص. تُطبَّق الـ casts، وتُضبط المعرّفات الفريدة والـ timestamps، وتبقى قيمة `created_at` أو `updated_at` الموجودة في الصف كما هي. تعمل `beforeWrite()` على كل صف، لكن لا يُطلق أي حدث نموذج. وصيغ القوائم تكتب كل الصفوف بعبارة واحدة، فيجب أن تحمل الصفوف كلها الأعمدة نفسها، وأن تبقى الدفعة الكبيرة تحت حد الربط (999 على SQLite قبل 3.32).

## اختصارات الاستعلام

تصفّي `whereBelongsTo` أبناء أب عبر علاقة `belongsTo` التي يعلنها الابن. من دون اسم تستعمل اسم صنف الأب بصيغة camel case، فيكون `user` للصنف `User`. مع R8 أو أي إعادة تسمية أخرى، مرّر اسم العلاقة:

```java
ModelQuery<Post> posts = Post.query.on(db);
posts.query().whereBelongsTo(ada).get();                          // relation "user"
posts.query().whereBelongsTo(ada, "author").get();
posts.query().whereBelongsTo(List.of(ada, sam), "author").get();  // one in clause
posts.query().where("pinned", true).orWhereBelongsTo(ada, "author").get();
```

ترفض هاتان الدالتان مجموعة فارغة، وأبًا من صنف خاطئ، وأبًا بلا قيمة مفتاح.

تعيد `pluck(column, key)` خريطة من عمود المفتاح إلى العمود، بالقيم الخام كما تعطيها `pluck(column)`:

```java
Map<Object, Object> ids = Member.query.on(db).query().pluck("id", "code");   // code -> id
```

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

## مرجع الدوال

الدوال العامة التي لا تغطيها الأقسام السابقة، بصف واحد لكل اسم دالة (الـ overloads في صف واحد).

| الدالة | على | ماذا تفعل | مثال |
|---|---|---|---|
| `getInteger` `getLong` `getDouble` `getBigDecimal` `getBoolean` `getInstant` | `Model` | قراءات مُنمَّطة لخاصية: من أي عدد صحيح أو نص رقمي (`getInteger` و`getLong`)، أو رقم (`getDouble`)، أو عشري دقيق (`getBigDecimal`)، أو boolean (`getBoolean`: غير صفر أو `1`/`true`)، أو لحظة زمنية (`getInstant`). | `post.getInteger("views")` |
| `hasAttribute` | `Model` | تعيد هل يحمل النموذج خاصية، حتى لو كانت قيمتها null. | `post.hasAttribute("title")` |
| `hasCast` `getCasts` `mergeCasts` `withCasts` | `Model`, `EloquentBuilder` | الـ casts: `hasCast` تخبر هل للخاصية cast، و`getCasts` تعيد الـ casts المحسومة، و`mergeCasts` تضيف casts لنسخة واحدة، و`withCasts` (على الاستعلام) تطبق casts على كل نموذج يقرؤه. | `post.mergeCasts(Map.of("meta", "json"))` |
| `getOriginal` `getRawOriginal` `originalIsEquivalent` | `Model` | `getOriginal` تعيد القيمة الأصلية لخاصية عبر الـ accessor أو الـ cast، و`getRawOriginal` كما خُزّنت بلا cast، و`originalIsEquivalent` تخبر هل القيمة الحالية تساوي الأصلية. | `post.getRawOriginal("title")` |
| `isClean` `wasChanged` `getChanges` `getPrevious` | `Model` | تتبّع التغييرات: `isClean` (لا تختلف أي خاصية عن أصلها)، و`wasChanged` و`getChanges` (ما غيّره آخر حفظ)، و`getPrevious` (القيم التي استبدلها). | `post.wasChanged("title")` |
| `syncOriginal` `syncOriginalAttribute` `syncOriginalAttributes` `syncChanges` `discardChanges` `setRawAttributes` | `Model` | تعيد ضبط خط الأساس للتغييرات: تجعل القيم الحالية هي الأصلية (كلها أو واحدة أو عدة)، وتسجّل تغييرات آخر حفظ (`syncChanges`)، وتعيد كل خاصية إلى أصلها (`discardChanges`)، أو تستبدل كل الخصائص خامًا (`setRawAttributes`). | `post.discardChanges()` |
| `preventSilentlyDiscardingAttributes` | `Model` | تحدد، لكل النماذج في العملية، هل ترمي `fill` استثناءً للمفاتيح التي كانت ستُسقطها بصمت. | `Model.preventSilentlyDiscardingAttributes(true)` |
| `getFillable` `getGuarded` `isFillable` `isGuarded` `isUnguarded` `totallyGuarded` | `Model` | إعدادات الإسناد الجماعي: مفاتيح fillable وguarded، وهل يمكن إسناد مفتاح، وهل الحماية معطّلة في هذا الـ thread، وهل يمنع النموذج الإسناد الجماعي كليًا. | `post.isFillable("title")` |
| `getHidden` `getVisible` `setHidden` `setVisible` `makeHidden` `makeVisible` `getAppends` `setAppends` `append` `withoutAppends` | `Model` | قوائم التسلسل: تقرأ أو تستبدل الخصائص المخفية والظاهرة والمضافة (المحسوبة)، وتضيف إليها (`makeHidden` و`append`)، أو تُظهر المخفية (`makeVisible`)، أو تزيل كل المضافة (`withoutAppends`). | `post.makeHidden("secret")` |
| `getTable` `getKeyName` `getKeyType` `getIncrementing` `getQualifiedKeyName` `qualifyColumn` `getForeignKey` `getPerPage` `getUniqueIdKind` | `Model` | إعدادات النموذج كما يحسمها: الجدول، واسم المفتاح الأساسي ونوعه، وهل تولّد قاعدة البيانات المفتاح، والمفتاح مسبوقًا باسم الجدول (`users.id`)، وعمود مسبوق باسم الجدول، واسم المفتاح الأجنبي الذي تستخدمه الجداول الأخرى لهذا النموذج، وحجم الصفحة الافتراضي، ونوع المعرّف الفريد. | `post.getQualifiedKeyName()` |
| `getConnection` `getConnectionName` `setConnection` `getQueryFactory` `newBaseQuery` | `Model` | الوصول للاتصال: اتصال النموذج واسمه، وربط النموذج بـ query factory (`setConnection`)، والـ factory الذي يستخدمه، وbuilder أساسي جديد على جدول النموذج. | `post.newBaseQuery().where("id", 1)` |
| `Casts.instant` | `Casts` | cast يخزّن `Instant` مهما كانت صيغة طوابع النموذج، لأعمدة `Blueprint.instant`. وأعمدة الطوابع تحتاج أيضًا `TimestampFormat.INSTANT`. | `.put("sent_at", Casts.instant())` |
| `Casts.decimal` | `Casts` | الدالة `decimal(scale)` هي الـ cast المقرِّب `decimal:N`. أما `decimal(precision, scale[, mode])` فهي الـ cast الصارم: precision وscale كما في `Blueprint.decimal`، والخانات العشرية الزائدة مرفوضة ما لم يُعطَ وضع تقريب. | `.put("total", Casts.decimal(6, 2))` |
| `getJsonCodec` `getDateFormat` `getTimestampFormat` `setClock` | `Model` | إعدادات الوقت وJSON: الـ codec خلف casts الـ JSON وصيغة JSON، ونمط الطوابع النصية، وطريقة كتابة الطوابع، والساعة التي يقرأ منها النموذج الطوابع. | `post.setClock(clock)` |
| `getCreatedAtColumn` `getUpdatedAtColumn` `getDeletedAtColumn` `getQualifiedDeletedAtColumn` `usesTimestamps` | `Model` | أعمدة الطوابع: أسماء أعمدة created-at وupdated-at وdeleted-at (الأخير أيضًا مسبوقًا بالجدول)، وهل يكتب النموذج الطوابع الآن. | `post.usesTimestamps()` |
| `freshTimestamp` `freshTimestampValue` `fromDateTime` `updateTimestamps` | `Model` | دوال مساعدة للطوابع: اللحظة الحالية من ساعة النموذج بالصيغة التي يخزّنها، وتحويل لحظة إلى هذه الصيغة، وضبط `updated_at` (و`created_at` للنموذج الجديد) ما لم يكونا معدّلين. | `post.updateTimestamps()` |
| `withoutTimestamps` `withoutTouchingOn` `touch` `touchQuietly` `touchOwners` | `Model` | التحديث بالـ touch: `touch` تحدّث الطوابع وتحفظ، و`touchQuietly` تفعل ذلك بإسكات المستمعين، و`touchOwners` تضبط `updated_at` على العلاقات المذكورة في `touches()`، و`withoutTimestamps` و`withoutTouchingOn` تشغّلان callback بإيقاف الطوابع أو touch المالكين في هذا الـ thread. | `post.touch()` |
| `decrement` | `Model`, `EloquentBuilder` | تطرح مقدارًا (1 افتراضيًا) من عمود في صف هذا النموذج، مثل `increment` للإضافة؛ وتعيد عدد الصفوف المتأثرة. | `post.decrement("stock")` |
| `is` `isNot` | `Model` | تخبران هل نموذج آخر هو نفس الصف (نفس المفتاح والجدول واسم الاتصال)، أو لا. | `a.is(b)` |
| `fresh` | `Model`, `ModelCollection` | تعيد نسخة جديدة محمّلة من قاعدة البيانات بحسب المفتاح كما قُرئ آخر مرة (وللـ collection تعيد القائمة المحدّثة). | `post.fresh()` |
| `newInstance` `withoutRelations` `replicate` `replicateQuietly` | `Model` | نسخ: `newInstance` تنشئ نسخة فارغة بنفس الاتصال والساعة، و`withoutRelations` تنسخ النموذج بلا علاقات محمّلة، و`replicate` تنشئ نسخة غير محفوظة بلا المفتاح والطوابع، و`replicateQuietly` تنسخ مع إسكات المستمعين المسجّلين. | `post.replicate()` |
| `forceDeleteQuietly` `restoreQuietly` `updateQuietly` | `Model` | حذف نهائي أو استرجاع أو تحديث لنموذج مع إسكات المستمعين المسجّلين. | `post.updateQuietly(Map.of("title", "x"))` |
| `isForceDeleting` `isSoftDeletable` `wasRecentlyCreated` | `Model` | فحوص حالة: هل يجري `forceDelete()` الآن، وهل يستخدم النموذج الحذف الناعم، وهل أدرج آخر حفظ الصف. | `post.wasRecentlyCreated()` |
| `getMorphClass` | `Model` | تعيد الاسم المخزَّن في عمود نوع morph لهذا النموذج. | `post.getMorphClass()` |
| `relation` `getRelation` `getRelationValue` `getRelations` `relationLoaded` `setRelation` `setRelations` `unsetRelation` | `Model` | حالة العلاقات: بناء علاقة بالاسم (`relation`)، وقراءة علاقة محمّلة دون تحميل (`getRelation`)، وقراءتها أو تحميلها كسولًا (`getRelationValue`)، وقراءة كل العلاقات المحمّلة، وفحص هل علاقة محمّلة، وضبط العلاقات المحمّلة أو استبدالها أو نسيانها. | `post.relationLoaded("user")` |
| `loadAggregate` `loadAvg` `loadMax` `loadMin` `loadSum` `loadMorph` `loadMorphCount` | `Model`, `ModelCollection` | تحمّل تجميعات لعمود مرتبط على النموذج (`loadSum` و`loadAvg` و`loadMax` و`loadMin` و`loadAggregate`)، وتحمّل علاقات أو أعدادًا على المالك الذي حمّلته علاقة morph-to، بحسب صنف المالك (`loadMorph` و`loadMorphCount`). وهي موجودة أيضًا على `ModelCollection`. | `post.loadSum("comments", "votes")` |
| `count` | `EloquentBuilder` | تعدّ الصفوف المطابقة (وصيغ التجميع `sum` و`avg` و`min` و`max` تعمل بالطريقة نفسها). | `Post.query().where("published", true).count()` |
| `all` | `ModelQuery` | تعيد كل نماذج الجدول. | `Post.query().all()` |
| `destroy` `forceDestroy` | `ModelQuery` | تحمّل النماذج بالمفاتيح المعطاة وتحذف كلًا منها فتعمل hooks كل نموذج (و`forceDestroy` تشمل المحذوفة ناعمًا وتحذفها نهائيًا). | `Post.query().destroy(1, 2)` |
| `forceCreate` | `EloquentBuilder`, `ModelQuery` | تملأ نموذجًا جديدًا من map متجاهلةً الحماية، وتحفظه. | `Post.query().forceCreate(attrs)` |
| `createOrFirst` | `EloquentBuilder` | تنشئ نموذجًا؛ وإن رفضه فهرس unique تعيد النموذج الموجود المطابق. | `Post.query().createOrFirst(attrs)` |
| `findMany` `findOr` `findOrNew` `firstOr` `firstOrFail` `firstWhere` `sole` | `EloquentBuilder`, `ModelQuery` | دوال بحث إضافية: `findMany` (عدة مفاتيح، ولا استعلام للقائمة الفارغة)، و`findOr`/`firstOr` (نتيجة callback إن لم يوجد)، و`findOrNew` (نموذج جديد غير محفوظ)، و`firstOrFail`، و`firstWhere` (عمود يساوي قيمة)، و`sole` (النتيجة الوحيدة، بقراءة صفين على الأكثر). | `Post.query().firstWhere("slug", s)` |
| `each` `lazyById` | `EloquentBuilder` | قراءة بالجملة: `each` تمرّر كل نموذج إلى predicate (حتى يعيد false)؛ و`lazyById` تعيد النماذج كتسلسل كسول يُقرأ على دفعات بالمفتاح الأساسي. | انظر «الـ chunks والقراءة الكسولة والـ cursors والصفحات» |
| `hydrate` | `EloquentBuilder`, `ModelQuery` | تبني نماذج من صفوف خام دون تنفيذ استعلام. | `Post.query().hydrate(rows)` |
| `getModel` `getModelClass` `newModel` | `EloquentBuilder`, `ModelQuery` | النموذج الذي يُبنى عليه الاستعلام: نسخة منه (`getModel`)، أو صنفه (`getModelClass`)، أو نموذج جديد فارغ مرتبط باتصال المدخل وساعته (`newModel`). | `Post.query().newModel()` |
| `using` `withClock` | `ModelQuery` | تعيدان مدخلًا تجد نماذجه الـ factory باسم الاتصال في resolver (`using`)، أو تقرأ الطوابع من ساعة معطاة (`withClock`). | `Post.query().withClock(clock)` |
| `preventsLazyLoading` | `ModelQuery` | تعيد هل التحميل الكسول ممنوع، كما ضبطته `preventLazyLoading(boolean)`. | `Post.query().preventsLazyLoading()` |
| `addGlobalScopes` `clearGlobalScopes` `getGlobalScope` `getGlobalScopes` `hasGlobalScope` `removeGlobalScope` `withGlobalScope` `withoutGlobalScopesExcept` `removedScopes` `scopes` | `ModelQuery`, `EloquentBuilder` | سجل الـ scopes: إضافة عدة global scopes دفعة واحدة، ومسحها أو جلبها أو سردها أو فحصها أو إزالتها بالاسم، وإضافة واحد إلى استعلام واحد، وإسقاط كل scope ما عدا المسمّاة، وسرد الأسماء المُزالة، وتطبيق عدة local scopes بالترتيب (`scopes`). | `Post.query().withoutGlobalScopesExcept("tenant")` |
| `withoutTrashed` | `EloquentBuilder` | تستبعد الصفوف المحذوفة ناعمًا، حتى بعد `withTrashed()`. | `Post.query().withoutTrashed()` |
| `withOnly` `without` `getEagerLoads` | `EloquentBuilder` | التحميل المسبق: `withOnly` تستبدل كل تحميل مسبق، و`without` تزيل التحميلات بالمسار الدقيق (`without("posts")` تُبقي `posts.comments`)، و`getEagerLoads` تعيد المجموعة الحالية. | `Post.query().withOnly("user")` |
| `toBase` `getBindings` `toSql` `lock` `lockForUpdate` `sharedLock` | `EloquentBuilder` | الوصول لطبقة SQL: نسخة من الـ builder المغلَّف مع تطبيق الـ global scopes (`toBase`)، وقيم select المربوطة والـ SQL (`getBindings` و`toSql`)، وأقفال الصفوف (`lock` و`lockForUpdate` و`sharedLock`). | `Post.query().lockForUpdate()` |
| `forPage` `skip` `take` `reorder` `inRandomOrder` `oldest` `orderByDesc` `orderByRaw` `pluck` `value` `selectRaw` `leftJoin` | `EloquentBuilder` | دوال الـ query builder التي يمرّرها `EloquentBuilder` بنفس المعنى: الصفحات (`forPage` و`skip` و`take`)، والترتيب (`reorder` و`inRandomOrder` و`oldest` و`orderByDesc` و`orderByRaw`)، والقراءة (`pluck`، وتقبل أيضًا عمود مفتاح على هيئة `pluck(column, key)` وتعيد خريطة، و`value`)، و`selectRaw` و`leftJoin`. | انظر [Query builder](query-builder.md) |
| `whereBelongsTo` `orWhereBelongsTo` | `EloquentBuilder` | تصفّي الأبناء بحسب أب عبر علاقة `belongsTo`: افتراضيًا باسم صنف الأب بصيغة camel case، أو باسم العلاقة إن أُعطي ثانيًا. وتعطي المجموعة جملة `in` واحدة. وصيغة `or` تربط بـ OR. | `posts.query().whereBelongsTo(ada, "author")` |
| `fillAndInsert` `fillAndInsertOrIgnore` `fillAndInsertGetId` | `EloquentBuilder` | تملأ كل صف كما تفعل `fill` دون حماية `fillable`، ثم تدرج الصفوف بعبارة واحدة (`fillAndInsertGetId` تدرج صفًا واحدًا وتعيد مفتاحه). | `Member.query.on(db).query().fillAndInsert(rows)` |
| `whereKey` `whereKeyNot` | `EloquentBuilder` | تقيّد المفتاح الأساسي مسبوقًا بالجدول: `users.id = ?`، أو `in` لمجموعة (و`whereKeyNot` تستبعد). | `Post.query().whereKey(ids)` |
| `whereGroup` `orWhereGroup` | `EloquentBuilder` | تضيف مجموعة شروط بين أقواس تُبنى على Eloquent builder لنفس النموذج (`orWhereGroup` تربطها بـ OR)، مثل `where(Closure)` في Laravel. | `q.whereGroup(g -> g.where("a", 1).orWhere("b", 2))` |
| `whereInstantBetween` | `EloquentBuilder` | تضيف شرطًا للحظات في مدى نصف مفتوح. | `q.whereInstantBetween("created_at", from, to)` |
| `whereBetween` `whereNotBetween` `orWhereBetween` `whereColumn` `orWhereColumn` `whereDate` `whereDay` `whereMonth` `whereYear` `whereTime` `whereExists` `whereNotExists` `whereIn` `whereNotIn` `orWhereIn` `orWhereNotIn` `whereLike` `whereNotLike` `orWhereLike` `whereNot` `orWhereNot` `whereNull` `orWhereNull` `whereNotNull` `orWhereNotNull` `whereRaw` `orWhereRaw` | `EloquentBuilder` | عائلة `where` من الـ query builder، متاحة أيضًا على `EloquentBuilder` بنفس المعنى (صيغ `or...` تربط بـ OR). | انظر [Query builder](query-builder.md) |
| `whereDoesntHave` `orWhereDoesntHave` `orDoesntHave` `orHas` `orWhereHas` `orWhereRelation` | `EloquentBuilder` | شروط وجود العلاقة مع `OR` والنفي: لا نموذج مرتبط يطابق قيدًا (`whereDoesntHave`)، وصيغ `or`، وشرط or على عمود نموذج مرتبط (`orWhereRelation`). | `Post.query().whereDoesntHave("comments")` |
| `whereDoesntHaveMorph` `doesntHaveMorph` `orDoesntHaveMorph` `orHasMorph` `orWhereDoesntHaveMorph` `orWhereHasMorph` `whereMorphRelation` `whereMorphDoesntHaveRelation` `orWhereMorphRelation` `orWhereMorphDoesntHaveRelation` `whereNotMorphedTo` `orWhereMorphedTo` `orWhereNotMorphedTo` | `EloquentBuilder` | استعلامات وجود morph-to: مالك من أحد الأنواع المعطاة (أو بلا مالك)، بقيد أو بمقارنة عمود، وهل تشير morph-to إلى هدف. صيغ `or` تربط بـ OR. | `q.orHasMorph("imageable", Post.class)` |
| `contains` `modelKeys` `size` | `ModelCollection` | أساسيات الـ collection: هل تحوي القائمة نموذجًا (نفس الصف، أو نموذجًا بمفتاح أساسي)، والمفاتيح الأساسية بترتيب القائمة، وعدد النماذج. | `posts.modelKeys()` |
| `hasMorePages` | `ModelPage`, `SimpleModelPage` | تعيد هل تليها صفحة. | `page.hasMorePages()` |
| `currentPage` `lastPage` | `ModelPage`, `SimpleModelPage` | أرقام الصفحات في كائن الصفحة: الصفحة الحالية بدءًا من 1، والصفحة الأخيرة. | `page.lastPage()` |
| `nextCursor` `previousCursor` | `CursorModelPage` | تعيدان cursor الصفحة التالية أو السابقة. | `page.nextCursor()` |
