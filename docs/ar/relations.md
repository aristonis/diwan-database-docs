# العلاقات

العلاقة (relation) هي دالة مكتوبة النوع في النموذج، مع اسم في `relations()`. تصل هذه الخريطة باسم مثل `"posts"` إلى الدالة
بلا reflection (الانعكاس في Java)، فلا يستطيع R8 (أدوات تصغير الكود وتشويشه في Android) كسرها. تفحص Diwan الخريطة مرة واحدة لكل صنف عند أول استعمال،
والخطأ يفشل بـ `InvalidRelationException` يسمّي النموذج والعلاقة.

=== "Java"
    ```java
    public final class User extends Model {
        public static final ModelQuery<User> query = ModelQuery.of(User.class, User::new);

        @Override
        protected RelationMap<?> relations() {
            return RelationMap.of(User.class).add("posts", User::posts);
        }

        public HasMany<Post> posts() {
            return hasMany(Post.class, "user_id");      // hasOne works the same way
        }
    }

    public final class Post extends Model {
        public static final ModelQuery<Post> query = ModelQuery.of(Post.class, Post::new);

        @Override
        protected RelationMap<?> relations() {
            return RelationMap.of(Post.class).add("author", Post::author);
        }

        public BelongsTo<User> author() {
            return belongsTo(User.class, "user_id");    // the foreign key is required
        }
    }
    ```
=== "Kotlin"
    ```kotlin
    class User : Model() {
        override fun relations(): RelationMap<*> {
            return RelationMap.of(User::class.java).add("posts", User::posts)
        }

        fun posts(): HasMany<Post> {
            return hasMany(Post::class.java, "user_id")      // hasOne works the same way
        }

        companion object {
            val query: ModelQuery<User> = ModelQuery.of(User::class.java, ::User)
        }
    }

    class Post : Model() {
        override fun relations(): RelationMap<*> {
            return RelationMap.of(Post::class.java).add("author", Post::author)
        }

        fun author(): BelongsTo<User> {
            return belongsTo(User::class.java, "user_id")    // the foreign key is required
        }

        companion object {
            val query: ModelQuery<Post> = ModelQuery.of(Post::class.java, ::Post)
        }
    }
    ```

## أنواع العلاقات

| النوع | يُصرَّح بـ |
|---|---|
| واحد لواحد، واحد لمتعدد | `hasOne` و`hasMany` و`belongsTo` |
| متعدد لمتعدد | `belongsToMany` |
| عبر جدول وسيط | `hasOneThrough` و`hasManyThrough` |
| متعددة الأشكال (polymorphic) | `morphOne` و`morphMany` و`morphTo` و`morphToMany` و`morphedByMany` |
| صف واحد يُختار من متعدد | `latestOfMany` و`oldestOfMany` و`ofMany` و`one()` |

## قراءة علاقة

القراءة الكسولة (lazy loading) تعمل مرة واحدة وتبقي النتيجة في النموذج. و`getAttribute("posts")` لا تحمّل علاقة أبدًا.

=== "Java"
    ```java
    ModelCollection<Post> posts = user.relatedMany("posts");   // select * from posts where user_id = ?
    User author = post.related("author");                      // null when there is none
    ModelCollection<Post> recent = user.posts().where("published", true).latest().get();
    ```
=== "Kotlin"
    ```kotlin
    val posts: ModelCollection<Post> = user.relatedMany("posts")   // select * from posts where user_id = ?
    val author: User? = post.related("author")                     // null when there is none
    val recent: ModelCollection<Post> = user.posts().where("published", true).latest().get()
    ```

تعيد `withDefault()` على `hasOne` أو `belongsTo` نموذجًا فارغًا حين لا يوجد شيء.

## التحميل المسبق (Eager loading)

حمّل مسبقًا لتتجنب استعلامًا لكل نموذج. تتداخل المسارات بالنقاط، و`name:col,...` تختار أعمدة (يُضاف المفتاح المطابق)،
والقيد يضيّق استعلام العلاقة:

=== "Java"
    ```java
    ModelCollection<User> all = users.with("posts.comments").get();   // three queries in all
    users.with("posts", q -> q.where("published", true)).get();
    users.query().with("posts:id,title").paginate(20, 1);

    all.load("posts.author");        // on a collection already read
    user.loadMissing("posts");       // only what is not loaded yet
    ```
=== "Kotlin"
    ```kotlin
    val all: ModelCollection<User> = users.with("posts.comments").get()   // three queries in all
    users.with("posts") { q -> q.where("published", true) }.get()
    users.query().with("posts:id,title").paginate(20, 1)

    all.load("posts.author")        // on a collection already read
    user.loadMissing("posts")       // only what is not loaded yet
    ```

تُهمَل المفاتيح الفارغة (null)، وتُقسَّم قوائم المفاتيح الطويلة كي تبقى تحت حد المعاملات في SQLite وPostgreSQL.
القيد المسبق ينفَّذ مرة لكل دفعة (batch) مفاتيح زائد مرة، فاجعله بلا آثار جانبية. ولا يجوز له ضبط `limit` أو `offset`.
`cursor()` يرفض التحميل المسبق؛ و`lazy()` يحمّله لكل صفحة.

لاكتشاف مشكلة N+1 (استعلام إضافي لكل صف) أثناء التطوير، ارفض القراءات الكسولة على النماذج الآتية من نتيجة متعددة الصفوف.
هذا إعداد على مستوى العملية كلها؛ استدعِه مرة عند بدء التشغيل:

=== "Java"
    ```java
    ModelQuery.preventLazyLoading(true);
    users.query().get().get(0).relatedMany("posts");   // LazyLoadingViolationException
    ```
=== "Kotlin"
    ```kotlin
    ModelQuery.preventLazyLoading(true)
    users.query().get()[0].relatedMany<Post>("posts")   // LazyLoadingViolationException
    ```

## has وwhereHas والتجميعات

=== "Java"
    ```java
    users.query().has("posts").get();
    users.query().has("posts", ">=", 3).get();
    users.query().whereHas("posts", q -> q.where("title", "like", "Java%")).get();
    users.query().doesntHave("posts.comments").get();
    users.query().whereRelation("posts", "published", true).get();
    ```
=== "Kotlin"
    ```kotlin
    users.query().has("posts").get()
    users.query().has("posts", ">=", 3).get()
    users.query().whereHas("posts") { q -> q.where("title", "like", "Java%") }.get()
    users.query().doesntHave("posts.comments").get()
    users.query().whereRelation("posts", "published", true).get()
    ```

تُترجم هذه إلى استعلامات فرعية (subqueries) من نوع `exists`. عُدّ الصفوف المرتبطة أو اجمعها أو افحصها دون تحميلها. كل استدعاء
يضيف استعلامًا فرعيًا واحدًا، اسمه `<relation>_<function>_<column>` أو ما تحدده بـ `as`:

=== "Java"
    ```java
    users.query()
            .withCount("posts")                                        // posts_count
            .withCount(Map.of("posts as published", q -> q.where("published", true)))
            .withSum("orders", "total")                                // orders_sum_total
            .withExists("posts")                                       // posts_exists, a Boolean
            .get();

    all.loadCount("posts");              // the same aggregates on models already read
    user.loadExists(Map.of("posts", q -> q.where("published", true)));
    ```
=== "Kotlin"
    ```kotlin
    users.query()
        .withCount("posts")                                        // posts_count
        .withCount(mapOf("posts as published" to Consumer<EloquentBuilder<*>> { q -> q.where("published", true) }))
        .withSum("orders", "total")                                // orders_sum_total
        .withExists("posts")                                       // posts_exists, a Boolean
        .get()

    all.loadCount("posts")              // the same aggregates on models already read
    user.loadExists(mapOf("posts" to Consumer<EloquentBuilder<*>> { q -> q.where("published", true) }))
    ```

تعمل `withMin` و`withMax` و`withAvg` و`withAggregate(relation, column, function)` بالطريقة نفسها. بعد `withCount` استعمل `addSelect`
لا `select`: فـ `select` تستبدل الأعمدة وتُسقط التجميع.

ما يجوز أن يحويه closure القيد:

- في `has` و`whereHas` و`whereRelation` يعمل الـ closure على الاستعلام الفرعي `exists`. يجوز له إضافة `join` و`orderBy` و`limit` و`offset`
  و`groupBy` و`having`. وتشكّل شروط `where` فيه مجموعة واحدة حين تحوي `or`، فلا يستطيع `orWhere` توسيع مطابقة العلاقة نفسها.
- مع العدّ (`whereHas("posts", q -> ..., ">", 2)`) تُسقَط الترتيبات و`limit` و`offset`، وترمي `groupBy` و`having` الاستثناء
  `IllegalArgumentException`.
- في `withCount` وبقية التجميعات تعمل الـ joins وشروط `where`. وتُمسح `select` و`orderBy` و`limit` و`offset`. أمّا `groupBy` و`having`
  و`distinct` والاتحادات (unions) فترمي `IllegalArgumentException`.

## عبر وسيط، وmorph، وواحد من متعدد

=== "Java"
    ```java
    public HasManyThrough<Post> posts() {
        return hasManyThrough(Post.class, User.class);   // posts of the users of this country
    }

    public MorphMany<Comment> comments() { return morphMany(Comment.class, "commentable"); }
    public MorphTo<Model> commentable()  { return morphTo("commentable"); }
    public HasOne<Order> latestOrder()   { return hasOne(Order.class).latestOfMany(); }
    ```
=== "Kotlin"
    ```kotlin
    fun posts(): HasManyThrough<Post> {
        return hasManyThrough(Post::class.java, User::class.java)   // posts of the users of this country
    }

    fun comments(): MorphMany<Comment> = morphMany(Comment::class.java, "commentable")
    fun commentable(): MorphTo<Model> = morphTo("commentable")
    fun latestOrder(): HasOne<Order> = hasOne(Order::class.java).latestOfMany()
    ```

علاقة through تنشئ الصف البعيد دون ربطه بالصف الوسيط؛ أنشئ الصف الوسيط بنفسك. واستعمل دوال البحث والصفحات والمُكرِّرات
الخاصة بعلاقة through كأي علاقة أخرى.

علاقة morph تخزّن اسمًا مستعارًا (alias) في `commentable_type`. سجّل كل أب مرة واحدة عند بدء التشغيل:

=== "Java"
    ```java
    Map<String, Class<? extends Model>> map = new LinkedHashMap<>();
    map.put("post", Post.class);
    map.put("video", Video.class);
    MorphMap.morphMap(map);
    ```
=== "Kotlin"
    ```kotlin
    val map = LinkedHashMap<String, Class<out Model>>()
    map["post"] = Post::class.java
    map["video"] = Video::class.java
    MorphMap.morphMap(map)
    ```

بلا alias ترمي Diwan الاستثناء `ClassMorphViolationException`، إلا إذا اخترت عدم الإلزام بـ `MorphMap.requireMorphMap(false)`.
رشّح على `morphTo` بـ `whereHasMorph` و`hasMorph` و`whereMorphedTo`، وحمّل مسبقًا لكل صنف أب بـ `withMorph`.
وتُرفض `has` و`whereHas` على `morphTo`.

تختار `latestOfMany` و`oldestOfMany` و`ofMany(column, "min" | "max")` صفًا واحدًا لكل أب. و`hasMany(...).one()` تحوّل علاقة متعددة إلى واحدة.
الشروط المضافة على العلاقة ترشّح الصف المختار بعد اختياره. ضع الشرط في قيد `ofMany` لاختيار أحدث طلب مدفوع.

## الكتابة عبر علاقة

يُضبط المفتاح الأجنبي (foreign key) عنك. الأب الذي لا مفتاح له بعد يرمي `IllegalStateException` قبل أي SQL.

=== "Java"
    ```java
    Post post = user.posts().create(Map.of("title", "Hello"));   // user_id set
    user.posts().saveMany(List.of(draftA, draftB));             // no transaction
    post.author().associate(otherUser);                         // sets user_id and the relation
    post.author().dissociate();
    ```
=== "Kotlin"
    ```kotlin
    val post = user.posts().create(mapOf("title" to "Hello"))   // user_id set
    user.posts().saveMany(listOf(draftA, draftB))              // no transaction
    post.author().associate(otherUser)                         // sets user_id and the relation
    post.author().dissociate()
    ```

## الكتابة في جدول الربط (pivot)

تقرأ `belongsToMany` عبر جدول ربط، افتراضيًا `role_user` بالمفتاحين `user_id` و`role_id`. يحمل كل صف مرتبط صفَّ الربط الخاص به باسم `pivot`.

=== "Java"
    ```java
    public BelongsToMany<Role> roles() {
        return belongsToMany(Role.class).withPivot("status").withTimestamps();
    }

    user.roles().attach(5, Map.of("status", "active"));
    user.roles().detach(5);
    SyncResult changes = user.roles().sync(List.of(1, 2, 3));
    changes.getAttached();   // ids added
    changes.getDetached();   // ids removed
    user.roles().syncWithoutDetaching(List.of(4));
    user.roles().toggle(List.of(1, 9));
    user.roles().updateExistingPivot(1, Map.of("status", "paused"));

    Pivot.of(user.roles().first().orElseThrow()).getString("status");   // read the joining row
    user.roles().wherePivot("status", "active").get();
    ```
=== "Kotlin"
    ```kotlin
    fun roles(): BelongsToMany<Role> {
        return belongsToMany(Role::class.java).withPivot("status").withTimestamps()
    }

    user.roles().attach(5, mapOf("status" to "active"))
    user.roles().detach(5)
    val changes: SyncResult = user.roles().sync(listOf(1, 2, 3))
    changes.attached   // ids added
    changes.detached   // ids removed
    user.roles().syncWithoutDetaching(listOf(4))
    user.roles().toggle(listOf(1, 9))
    user.roles().updateExistingPivot(1, mapOf("status" to "paused"))

    Pivot.of(user.roles().first().orElseThrow()).getString("status")   // read the joining row
    user.roles().wherePivot("status", "active").get()
    ```

يمكن أن تكون `ids` معرّفًا أو نموذجًا مرتبطًا أو مجموعة من أيٍّ منهما أو map من المعرّف إلى خصائص pivot (جدول الربط في علاقة متعدد لمتعدد). أنشئ فهرسًا على جدول الربط:
فريدًا على (`user_id`, `role_id`) وآخر على `role_id`. سلسلة شروط `or` في قراءة متعدد لمتعدد لا تُجمَّع، فجمّعها بدالة
`where(q -> ...)` الخاصة بالعلاقة. العمود المرتبط المسمّى `pivot_x` ينتقل إلى صف الربط. وpivot الخاص بـ `morphToMany` يحمل نوع العلاقة دائمًا؛
وقيمة نوع مختلفة في الخصائص ترمي `IllegalArgumentException`.

## تحديث الطوابع الزمنية للأب (touch)

سمِّ العلاقات في `touches()` لتحديث `updated_at` للأب حين يتغيّر الابن:

=== "Java"
    ```java
    public final class Comment extends Model {
        @Override
        protected Set<String> touches() { return Collections.singleton("post"); }
    }

    comment.save();    // then: update posts set updated_at = ? where posts.id = ?
    Model.withoutTouching(Post.class, () -> importComments(rows));   // this thread only
    ```
=== "Kotlin"
    ```kotlin
    class Comment : Model() {
        override fun touches(): Set<String> = Collections.singleton("post")
    }

    comment.save()    // then: update posts set updated_at = ? where posts.id = ?
    Model.withoutTouching(Post::class.java) { importComments(rows) }   // this thread only
    ```

الحفظ الذي غيّر شيئًا، والحذف، ينفّذ كلٌّ منهما `UPDATE` خامًا واحدًا لكل مالك يُلمَس، بلا أحداث وبلا `SELECT`. يحتفظ كائن المالك في الذاكرة
بـ `updated_at` القديم؛ استدعِ `refresh()` لإعادة تحميله. غلّف الاستيراد الكبير بـ `withoutTouching`.

## حفظ شبكة نماذج وربط الأبناء

تحفظ `push()` النموذج ثم كل علاقة محمّلة تحته، بالعمق أولًا. تعيد `false` عند أول حفظ فاشل ولا تفتح transaction (معاملة). وتضبط `chaperone("post")`
على `hasMany` الأب في كل ابن بلا استعلام.

## الأداء وR8

- أنشئ فهرسًا (index) لكل مفتاح أجنبي في الأبناء تستعمله `has` و`whereHas` و`withCount` و`load*`. كل واحدة تنفّذ استعلامًا فرعيًا مترابطًا لكل صف خارجي.
- لمس أب ساخن (hot) من أبناء كثيرين يسبّب انتظار أقفال (`SQLITE_BUSY` في SQLite).
- الـ class literal مثل `Post.class` لا يشغّل static initializer للصنف. المس مدخل `query` لكل نموذج عند بدء التشغيل، قبل أن تذكره علاقة.
- يعيد R8 تسمية الأصناف، وتشتق Diwan المفتاح الأجنبي الافتراضي والجدول وجدول pivot وتخمين `chaperone` من اسم الصنف. على Android مرّر المفاتيح والجداول
  والأسماء صراحةً كما في أمثلة هذه الصفحة. انظر [Android](android.md).

## مرجع الدوال

الدوال العامة التي لا تغطيها الأقسام السابقة، بصف واحد لكل اسم دالة (الـ overloads في صف واحد).

| الدالة | على | ماذا تفعل | مثال |
|---|---|---|---|
| `getParent` `getRelated` `getQuery` `getResults` `getRelationName` | كل العلاقات | فحص علاقة: النموذج الذي بُنيت عليه، ونسخة النموذج المرتبط، واستعلام العلاقة مع القيود الكسولة، ونتيجتها بشكل العلاقة (نموذج واحد أو null لعلاقة مفردة، وcollection لعلاقة متعددة)، واسمها. | `post.relation("comments").getResults()` |
| `oldest` `orderByDesc` `take` `whereColumn` `whereIn` `whereNotIn` `whereNull` `whereNotNull` `scopes` `withoutTrashed` `withoutGlobalScopesExcept` | كل العلاقات | دوال استعلام تمرّرها العلاقة إلى استعلام النموذج المرتبط بالمعنى نفسه في `EloquentBuilder`: `oldest` و`orderByDesc` و`take` و`whereColumn` و`whereIn` و`whereNotIn` و`whereNull` و`whereNotNull` و`scopes` و`withoutTrashed` و`withoutGlobalScopesExcept`. | `post.relation("comments").oldest()` |
| `rawUpdate` | كل العلاقات | تنفّذ UPDATE للأعمدة المعطاة على الاستعلام الكسول، مع الشروط المضافة إلى العلاقة. | `rel.rawUpdate(Map.of("seen", true))` |
| `touch` | كل العلاقات | تضبط طابع التحديث لكل صف مرتبط تقرؤه العلاقة على الآن، بـ `UPDATE` خام واحد: بلا select ولا events ولا casts. | `rel.touch()` |
| `createMany` | `HasOne`, `HasMany`, `BelongsToMany`, `MorphOne`, `MorphMany`, `MorphToMany` | تنشئ نموذجًا مرتبطًا لكل سجل بالترتيب، مثل `create`. | `user.posts().createMany(List.of(a, b))` |
| `getForeignKeyName` `getLocalKeyName` `getParentKey` `getQualifiedForeignKeyName` `getMorphType` `getMorphTypeName` `getMorphClass` | `HasOne`, `HasMany`, `BelongsTo`, `MorphOne`, `MorphMany`, `MorphTo`, `HasOneThrough`, `HasManyThrough`, `MorphPivot`, `MorphToMany` | أسماء مفاتيح علاقات has-one/has-many (والـ morph): عمود المفتاح الأجنبي في الجدول المرتبط (عادي أو مسبوق بالجدول)، وعمود الأب الذي يشير إليه، وقيمة الأب لهذا المفتاح، وعمود نوع morph وصنف الأب المخزَّن فيه. | `user.posts().getForeignKeyName()` |
| `inverse` `withoutChaperone` `withoutInverse` | `HasOne`, `HasMany`, `MorphOne`, `MorphMany`, `BelongsToMany`, `MorphToMany` | ربط الابن بالأب: `inverse` تضبط الأب على كل ابن باسم العلاقة العكسية المخمَّن (مثل `chaperone`)؛ و`withoutChaperone` و`withoutInverse` توقفان هذا الربط. | `user.posts().inverse()` |
| `isOneOfMany` `ofManyAs` | `HasOne`, `MorphOne`, `HasOneThrough` | واحد من متعدد: هل حُوّلت العلاقة إلى هذا النوع، وتسمية الاستعلام الفرعي المنضم. | انظر «عبر وسيط، وmorph، وواحد من متعدد» |
| `getChild` `getOwnerKeyName` `getQualifiedOwnerKeyName` | `BelongsTo`, `MorphTo` | أسماء مفاتيح belongs-to: النموذج الذي يحمل المفتاح الأجنبي (مثل `getParent`)، وعمود مفتاح المالك، وهذا العمود مسبوقًا بجدول المالك. | `post.relation("user").getOwnerKeyName()` |
| `createOrFirst` `findMany` `findOr` `findOrNew` `firstOr` `firstOrFail` `firstWhere` `sole` `each` `lazyById` | `BelongsToMany`, `MorphToMany`, `HasOneThrough`, `HasManyThrough` | دوال بحث وقراءة على العلاقات المتعددة، بنفس معناها في `EloquentBuilder`، ومحصورة في صفوف العلاقة. | `user.posts().firstOrFail()` |
| `findSole` | `HasOneThrough`, `HasManyThrough` | تجد النموذج المرتبط الوحيد بالمفتاح المعطى، بقراءة صفين على الأكثر، فيُرفض مفتاح يرتبط بعدة صفوف وسيطة. | `country.posts().findSole(5)` |
| `getForeignPivotKeyName` `getRelatedPivotKeyName` `getParentKeyName` `getRelatedKeyName` `getQualifiedForeignPivotKeyName` `getQualifiedRelatedPivotKeyName` `getQualifiedParentKeyName` `getQualifiedRelatedKeyName` `getTable` | `Pivot`, `BelongsToMany`, `MorphToMany` | أسماء مفاتيح وجداول علاقة many-to-many: أعمدة الـ pivot التي تحمل مفتاح الأب ومفتاح النموذج المرتبط، وأعمدة الأب والمرتبط التي تشير إليها (عادية أو مسبوقة بالجدول)، وجدول الـ pivot. | `rel.getTable()` |
| `getPivotAccessor` `getPivotClass` `getPivotColumns` `createdAt` `updatedAt` `using` | `BelongsToMany`, `MorphToMany` | إعدادات الـ pivot: الاسم الذي يُخزَّن تحته الـ pivot في كل نموذج مرتبط، وصنفه، وأعمدة الـ pivot الإضافية، وأعمدة الطوابع إن احتفظت العلاقة بها، و`using` لبناء الـ pivot بصنف مخصّص. | `rel.getPivotColumns()` |
| `newPivot` `newExistingPivot` `newPivotQuery` `newPivotStatement` | `BelongsToMany`, `MorphToMany` | بناء كائنات واستعلامات الـ pivot: `newPivot` لصف واحد، و`newExistingPivot` لصف موجود في قاعدة البيانات، و`newPivotQuery` لاستعلام على جدول الـ pivot مقيَّد بالأب، و`newPivotStatement` لاستعلام بلا أي شرط. | `rel.newPivotQuery()` |
| `wherePivotBetween` `wherePivotNotBetween` `wherePivotIn` `wherePivotNotIn` `wherePivotNull` `wherePivotNotNull` `orWherePivot` `orWherePivotBetween` `orWherePivotNotBetween` `orWherePivotIn` `orWherePivotNotIn` `orWherePivotNull` `orWherePivotNotNull` | `BelongsToMany`, `MorphToMany` | تقيّد العلاقة على عمود في الـ pivot: between وnot between وin وnot in وnull وnot null. صيغ `orWherePivot...` تربط بـ OR. | `rel.wherePivotIn("role", roles)` |
| `orderByPivot` `orderByPivotDesc` | `BelongsToMany`, `MorphToMany` | ترتّب الاستعلام حسب عمود في الـ pivot، تصاعديًا أو تنازليًا. | `rel.orderByPivot("position")` |
| `withPivotValue` | `BelongsToMany`, `MorphToMany` | تصفّي جدول الـ pivot بـ `column = value` وتسجّل الزوج، فتُعرف قيمة الـ pivot لهذا العمود. | `rel.withPivotValue("type", "admin")` |
| `syncWithPivotValues` | `BelongsToMany`, `MorphToMany` | تزامن الـ ids وتكتب خصائص pivot نفسها لكل منها؛ والقيمة المشتركة تتقدّم على قيمة خاصة بـ id لنفس العمود. | `rel.syncWithPivotValues(ids, Map.of("active", true))` |
| `isInverse` `getQualifiedMorphTypeName` | `MorphToMany` | morph many-to-many: هل هذا هو الجانب العكسي (`morphedByMany`)، وعمود النوع في جدول الـ pivot مسبوقًا بالجدول. | `rel.isInverse()` |
| `getFirstKeyName` `getSecondLocalKeyName` `getQualifiedFirstKeyName` `getQualifiedSecondLocalKeyName` `getQualifiedLocalKeyName` `getQualifiedFarKeyName` | `HasOneThrough`, `HasManyThrough` | أسماء مفاتيح علاقة through: عمود الجدول الوسيط الذي يحمل مفتاح الأب البعيد، والعمود الذي يشير إليه المفتاح الثاني، وأعمدة الأب البعيد والجدول المرتبط، مسبوقة بجداولها حيث يدل الاسم. | `rel.getQualifiedFirstKeyName()` |
| `throughParentSoftDeletes` `withTrashedParents` | `HasOneThrough`, `HasManyThrough` | علاقات through والحذف الناعم: هل يستخدم النموذج الوسيط الحذف الناعم (فتُستبعد الآباء المحذوفة ناعمًا)، و`withTrashedParents` تُبقيها. | `rel.withTrashedParents()` |
| `fromAttributes` `fromRawAttributes` `setPivotKeys` `setRelatedModel` `getRelatedModel` `getPivotParent` | `Pivot` | بناء وربط `Pivot`: `fromAttributes` و`fromRawAttributes` تبنيان واحدًا لصف قُرئ عبر نموذج أب (والثانية تضبط الخصائص خامة)، و`setPivotKeys` تضبط عمودي مفتاحي الأب والمرتبط، و`setRelatedModel`/`getRelatedModel` تضبط النموذج المرتبط وتقرؤه، و`getPivotParent` تعيد الأب الذي قُرئ عبره. | `pivot.getPivotParent()` |
| `getCreatedAtColumn` `getUpdatedAtColumn` `fresh` `decrement` | `Pivot` | الـ `Pivot` كنموذج: عمودا طابعي الإنشاء والتحديث، ونسخة جديدة من قاعدة البيانات، وإنقاص عمود رقمي. | `pivot.fresh()` |
| `empty` `modelClass` `names` `resolve` | `RelationMap` | `RelationMap`: `empty` تعيد map نموذج بلا علاقات، و`modelClass` الصنف الذي بُنيت له، و`names` أسماء العلاقات بترتيب إضافتها، و`resolve` تبني علاقة بالاسم لنموذج. | `model.relations().names()` |
