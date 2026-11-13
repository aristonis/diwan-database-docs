# مصانع العلاقات (Factory relations)

يستطيع المصنع بناء رسم كامل من النماذج: مؤلف له مقالات، أو مقال له مؤلف، أو مقال له وسوم. تسمّي علاقة من علاقات النموذج وتمرّر مصنع الطرف الآخر، ويملأ Diwan أعمدة المفاتيح عنك.

تكمل هذه الصفحة صفحة [المصانع](factories.md) وتستعمل الحزمة نفسها `org.aristonis.diwan.database.eloquent.factory`. النوع العام الوحيد الذي تضيفه هو `RecycleMode`.

تستعمل الأمثلة النماذج التالية. يُبنى كل مصنع كما في صفحة المصانع:

| النموذج | العلاقات |
|---|---|
| `Author` | `posts` (`HasMany`) و`profile` (`HasOne`) و`comments` (`MorphMany`) |
| `Post` | `author` (`BelongsTo`) و`comments` (`MorphMany`) و`tags` (`BelongsToMany`) |
| `Comment` | `commentable` (`MorphTo`) |
| `Tag` | لا شيء |

`authors` و`posts` و`comments` و`tags` هي مصانع هذه النماذج.

## النماذج المرتبطة (has)

تنشئ `has(child, relation)` أبناء كل نموذج ينشئه المصنع. تُبحث العلاقة بالاسم في النموذج، ويمكن أن تكون `HasOne` أو `HasMany` أو `MorphOne` أو `MorphMany`. عدد (count) مصنع الابن هو عدد الأبناء لكل أب:

=== "Java"
    ```java
    Author ada = authors.has(posts.count(3), "posts").create();   // one author, three posts

    List<Author> team = authors.has(posts.count(2), "posts").createMany(2);   // two authors, two posts each
    ```
=== "Kotlin"
    ```kotlin
    val ada: Author = authors.has(posts.count(3), "posts").create()   // one author, three posts

    val team: List<Author> = authors.has(posts.count(2), "posts").createMany(2)   // two authors, two posts each
    ```


يُحفظ الأب أولًا. ثم يُنشأ كل ابن وأعمدة العلاقة مضبوطة: المفتاح الأجنبي، وفي علاقة morph عمود النوع أيضًا. تغلب هذه الأعمدة تعريف الابن وحالاته، لأن المفتاح من شأن العلاقة.

يأخذ كل أب دفعته الخاصة من الأبناء. يستمر الـ `Sequence` على الابن داخل دفعة واحدة، ويبدأ من جديد للأب التالي. يمر الابن بكل خطوات إنشائه: حالاته وhooks وروابط `has` و`hasAttached` الخاصة به.

يستطيع الابن قراءة أبيه في حالة أو hook، انظر قسم «الحالات والـ hooks التي تعرف الأب» أدناه.

## ربط نماذج مرتبطة (hasAttached)

تملأ `hasAttached` علاقة متعددة بمتعددة (`BelongsToMany` أو `MorphToMany`). تنشئ النماذج المرتبطة وتكتب صفوف الجدول الوسيط (pivot). وتكتب `MorphToMany` عمود النوع بنفسها.

=== "Java"
    ```java
    List<Tag> existingTags = tags.createMany(2);

    // five forms
    posts.hasAttached(tags.count(2), "tags");
    posts.hasAttached(tags.count(2), Map.of("weight", 1), "tags");
    posts.hasAttached(tags.count(2), p -> Map.of("note", "for " + p.getKey()), "tags");
    posts.hasAttached(tags.count(3), List.of(Map.of("weight", 1), Map.of("weight", 2)), "tags");
    posts.hasAttached(existingTags, Map.of("weight", 1), "tags");   // no tag is created

    Post post = posts.hasAttached(tags.count(2), "tags").create();
    ```
=== "Kotlin"
    ```kotlin
    val existingTags: List<Tag> = tags.createMany(2)

    // five forms
    posts.hasAttached(tags.count(2), "tags")
    posts.hasAttached(tags.count(2), mapOf("weight" to 1), "tags")
    posts.hasAttached(tags.count(2), { p: Model -> mapOf("note" to "for ${p.key}") }, "tags")
    posts.hasAttached(tags.count(3), listOf(mapOf("weight" to 1), mapOf("weight" to 2)), "tags")
    posts.hasAttached(existingTags, mapOf("weight" to 1), "tags")   // no tag is created

    val post: Post = posts.hasAttached(tags.count(2), "tags").create()
    ```


| الصيغة | قيم الـ pivot |
|---|---|
| `hasAttached(factory, relation)` | لا شيء |
| `hasAttached(factory, Map, relation)` | الخريطة نفسها لكل نموذج مرتبط |
| `hasAttached(factory, Function<Model, Map>, relation)` | تستقبل الدالة الأب المحفوظ وتُستدعى مرة لكل نموذج مرتبط |
| `hasAttached(factory, List<Map>, relation)` | المدخلة `i % size` للنموذج المرتبط `i`؛ وإن لم يكن للمصنع المرتبط count فيُضبط على حجم القائمة؛ والقائمة الفارغة خطأ |
| `hasAttached(List<Model>, Map, relation)` | الخريطة نفسها لكل نموذج محفوظ في القائمة؛ ولا يُنشأ شيء |

تُكتب قيم الـ pivot كما تعطيها. لتطبيق casts عليها أعطِ العلاقة صنف pivot بـ `using`. ويجب أن يكون النموذج في القائمة محفوظًا.

يُبنى المصنع المرتبط مثل ابن `has`: يرث الاتصال، ويمر بخطوات إنشائه، ويستطيع قراءة الأب.

## المالكون (forParent)

تضبط `forParent(parent, relation)` مالك علاقة `BelongsTo` أو `MorphTo`. الأب مصنع أو نموذج محفوظ. اسم الدالة `forParent` لأن `for` كلمة محجوزة في Java.

=== "Java"
    ```java
    Post fresh = posts.forParent(authors, "author").create();   // creates an author, then the post

    Author ada = authors.create();
    List<Post> hers = posts.forParent(ada, "author").createMany(3);

    Comment note = comments.forParent(posts, "commentable").create();   // sets the id and the type
    ```
=== "Kotlin"
    ```kotlin
    val fresh: Post = posts.forParent(authors, "author").create()   // creates an author, then the post

    val ada: Author = authors.create()
    val hers: List<Post> = posts.forParent(ada, "author").createMany(3)

    val note: Comment = comments.forParent(posts, "commentable").create()   // sets the id and the type
    ```


يُنشأ الأب من المصنع مرة واحدة لكل استدعاء طرفي (terminal)، فـ `count(3).forParent(authors, "author")` يعطي ثلاث مقالات بمؤلف واحد. واستدعاءان طرفيان ينشئان مؤلفَين. والنموذج الأب غير المحفوظ يرمي `IllegalStateException`.

في علاقة `MorphTo` يُكتب morph class للأب في عمود النوع. يأتي عمودا المفتاح والنوع قبل الحالات، فيستطيع `state` أو `set` أو `Sequence` استبدال المفتاح.

## الحالات والـ hooks التي تعرف الأب

يمكن أن تأخذ الحالة أو الـ hook وسيطًا ثانيًا هو الأب. للابن المصنوع بـ `has` أو `hasAttached` هو الأب المحفوظ. وعلى المستوى الأعلى هو `null`:

=== "Java"
    ```java
    Factory<Post> titled = posts.state((soFar, parent) -> {
        Map<String, Object> out = new LinkedHashMap<>();
        if (parent != null) {
            out.put("title", "By " + parent.getAttribute("name"));
        }
        return out;
    });

    List<String> audit = new ArrayList<>();
    Factory<Author> logged = authors.has(
        posts.afterCreating((post, author) -> audit.add(post.getKey() + " by " + author.getKey())),
        "posts");
    ```
=== "Kotlin"
    ```kotlin
    val titled: Factory<Post> = posts.state { soFar, parent ->
        if (parent == null) mapOf<String, Any>() else mapOf("title" to "By ${parent.getAttribute("name")}")
    }

    val audit = mutableListOf<String>()
    val logged: Factory<Author> = authors.has(
        posts.afterCreating { post, author -> audit.add("${post.key} by ${author.key}") },
        "posts",
    )
    ```


| الدالة | ما تستقبله |
|---|---|
| `state(BiFunction<Map, Model, Map>)` | الخصائص حتى الآن، والأب |
| `afterMaking(BiConsumer<M, Model>)` | النموذج الجديد، والأب |
| `afterCreating(BiConsumer<M, Model>)` | النموذج المحفوظ، والأب |

الصيغ ذات الوسيط الواحد لم تتغير. ويستقبل `Sequence` الفهرس فقط.

## القيم المتداخلة

يمكن أن تكون قيمة في تعريف ما `Factory` أو `Model`. تُستبدل بمفتاح بعد تشغيل كل الحالات:

- `Factory` تنشئ نموذجًا ويُستعمل مفتاحه. وإن كان في مجمّع recycle نموذج من ذلك الصنف فيُستعمل بدلًا منه ولا يُنشأ شيء.
- `Model` محفوظ يعطي مفتاحه.
- `null` يبقى `null`.

=== "Java"
    ```java
    Factory<Post> posts = Factory.of(Post.query.on(manager.query()), () -> {
        Map<String, Object> attrs = new LinkedHashMap<>();
        attrs.put("title", "Hello");
        attrs.put("author_id", authors);   // a Factory: an author is created for each post
        return attrs;
    });

    Author ada = authors.create();
    Post post = posts.create();
    Post other = posts.set("author_id", ada).create();   // a Model: its key is used
    ```
=== "Kotlin"
    ```kotlin
    val posts: Factory<Post> = Factory.of(Post.query.on(manager.query())) {
        linkedMapOf<String, Any>(
            "title" to "Hello",
            "author_id" to authors,   // a Factory: an author is created for each post
        )
    }

    val ada: Author = authors.create()
    val post: Post = posts.create()
    val other: Post = posts.set("author_id", ada).create()   // a Model: its key is used
    ```


يمكن أن يعيد `Supplier` أو `Function` قيمة `Factory` أو `Model` أيضًا. وقيمة `Factory` تستبدلها حالة لاحقة لا تنشئ صفًا. يرث المصنع المتداخل الاتصال ويمر بخطوات إنشائه.

## إعادة الاستخدام (recycle)

افتراضيًا ينشئ كل مصنع متداخل نموذجه الخاص. تعطي `recycle(models...)` الاستدعاء مجمّعًا من النماذج المحفوظة، فيأخذ المصنع المتداخل منه نموذجًا من الصنف المناسب بدل أن ينشئ واحدًا. يخدم المجمّع مصانع `forParent` وقيم `Factory` المتداخلة، على أي عمق في الاستدعاء.

=== "Java"
    ```java
    Author ada = authors.create();
    Author grace = authors.create();

    List<Post> posts3 = posts.recycle(ada, grace).count(3).createMany();   // ada, grace, ada
    ```
=== "Kotlin"
    ```kotlin
    val ada: Author = authors.create()
    val grace: Author = authors.create()

    val posts3: List<Post> = posts.recycle(ada, grace).count(3).createMany()   // ada, grace, ada
    ```


تأخذ `recycle(List)` قائمة. تضيف الاستدعاءات إلى المجمّع، ويُحفظ المثيل نفسه مرة واحدة. تُجمَّع النماذج حسب صنفها بالضبط. والصنف الذي لا نموذج له في المجمّع يُنشأ كالمعتاد.

يحدّد `RecycleMode` كيف يُختار النموذج:

| الوضع | الاختيار |
|---|---|
| `IN_TURN` (الافتراضي) | نماذج الصنف بالترتيب، ثم العودة إلى الأول بعد الأخير |
| `RANDOM` | نموذج عشوائي في كل اختيار |
| `FIRST` | النموذج الأول دائمًا |

اضبطه بـ `recycleMode(mode)`. و`recycleRandom()` هي `RANDOM` بلا seed.

=== "Java"
    ```java
    posts.recycle(ada, grace).recycleMode(RecycleMode.FIRST).count(3).createMany();   // ada, ada, ada
    posts.recycle(ada, grace).recycleRandom().count(3).createMany();
    ```
=== "Kotlin"
    ```kotlin
    posts.recycle(ada, grace).recycleMode(RecycleMode.FIRST).count(3).createMany()   // ada, ada, ada
    posts.recycle(ada, grace).recycleRandom().count(3).createMany()
    ```


### تكرار تشغيل عشوائي

تختار `recycleRandom()` بلا seed اختيارًا مختلفًا في كل استدعاء. لتكرار تشغيل أعطِه seed بـ `recycleRandom(long seed)`. الـ seed نفسه والمجمّع نفسه يعطيان الاختيارات نفسها في كل استدعاء، فيمكن إعادة اختبار فشل مرة. سجّل الـ seed الذي اخترته وأعده لإعادة التشغيل:

=== "Java"
    ```java
    long seed = 20260101L;
    List<Post> first = posts.recycle(ada, grace).recycleRandom(seed).count(5).createMany();
    List<Post> again = posts.recycle(ada, grace).recycleRandom(seed).count(5).createMany();   // same authors in the same order
    ```
=== "Kotlin"
    ```kotlin
    val seed = 20260101L
    val first: List<Post> = posts.recycle(ada, grace).recycleRandom(seed).count(5).createMany()
    val again: List<Post> = posts.recycle(ada, grace).recycleRandom(seed).count(5).createMany()   // same authors in the same order
    ```


تحتفظ `recycleMode(RecycleMode.RANDOM)` بالـ seed إن كان مضبوطًا من قبل. وتمسحه `recycleRandom()`.

يعيش المجمّع طوال استدعاء طرفي واحد. يبدأ `IN_TURN` من النموذج الأول في الاستدعاء التالي، ويبدأ التشغيل ذو الـ seed من seed من جديد. يُستعمل فقط مجمّع المصنع الذي تستدعي عليه الدالة الطرفية. أما `recycle` على مصنع متداخل فيُتجاهل. ويجب أن يكون النموذج المأخوذ من المجمّع محفوظًا وإلا فتُرمى `IllegalStateException`.

## بلا آباء (withoutParents)

تحوّل `withoutParents` قيم `Factory` المتداخلة إلى `null`، فلا يُنشأ صف أب. وتسري على المصنع الذي تُستدعى عليه:

=== "Java"
    ```java
    posts.withoutParents().create();                         // every Factory value is null
    posts.withoutParents(Author.class).create();             // Factory values of Author are null
    posts.withoutParents("author_id").create();              // the Factory value of author_id is null
    ```
=== "Kotlin"
    ```kotlin
    posts.withoutParents().create()                          // every Factory value is null
    posts.withoutParents(Author::class.java).create()        // Factory values of Author are null
    posts.withoutParents("author_id").create()               // the Factory value of author_id is null
    ```


تتراكم الاستدعاءات المتكررة. يأتي المصنع المتداخل بإعداداته الخاصة: لا تصل `withoutParents` على المصنع الخارجي إليه. ويجب أن يقبل العمود `null`.

## ماذا تفعل كل دالة طرفية

| الدالة الطرفية | الآباء (مصنع `forParent` وقيم `Factory` المتداخلة) | `has` و`hasAttached` | الـ hooks |
|---|---|---|---|
| `make` و`makeMany` | تُنشأ وتُحفظ | لا تعمل أبدًا | `afterMaking` |
| `create` و`createMany` | تُنشأ وتُحفظ | تعمل بعد حفظ النموذج | `afterMaking` و`afterCreating` |
| `createQuietly` و`createManyQuietly` | مثل `create` مع كتم أحداث النموذج | مثل `create` | مثل `create` |
| `insert` | تُنشأ وتُحفظ | تُتخطى | لا شيء |
| `raw` و`rawMany` | لا تُنشأ أبدًا | لا تعمل أبدًا | لا شيء |

لا تلمس `raw` قاعدة البيانات أبدًا. قيمة `Model` أو `forParent(Model)` تعطي مفتاحها. أما قيمة `Factory` أو `forParent(Factory)` فترمي `IllegalStateException`، حتى لو كان في مجمّع recycle نموذج من ذلك الصنف.

تُفحص أسماء العلاقات وأنواعها قبل كتابة أول صف، فالاسم أو النوع الخاطئ لا يكتب شيئًا. وتفحص `make` و`insert` و`raw` علاقات `forParent` فقط؛ أما `has` و`hasAttached` فتفحصها الدوال الطرفية التي تشغّلها.

## الاتصال (connection)

يبني المصنع المتداخل (ابن أو نموذج مرتبط أو أب أو قيمة متداخلة) ويحفظ على اتصال المصنع الذي أنشأه، إلا إن أُعطي اتصالًا خاصًا بـ `connection(connection)`. والنموذج الذي تمرره إلى `forParent` أو إلى `hasAttached(List, ...)` يحتفظ باتصاله.

=== "Java"
    ```java
    authors.connection(reporting).has(posts, "posts").create();   // the posts use `reporting` too
    ```
=== "Kotlin"
    ```kotlin
    authors.connection(reporting).has(posts, "posts").create()   // the posts use `reporting` too
    ```


## حارس العمق

مصانع تنشئ بعضها بعضًا، كمؤلف تنشئ مقالاته مؤلفًا، لن تنتهي أبدًا. يوقف الحارس استدعاءً يتداخل أكثر من 32 مستوى ويرمي `IllegalStateException`.

لا توجد transaction حول الشجرة. الصفوف المكتوبة قبل الخطأ تبقى في قاعدة البيانات. وإن أردت الكل أو لا شيء فشغّل الاستدعاء الطرفي داخل transaction خاصة بك.

## تحميل العلاقات

لا يحتاج المصنع إلى دالة لتحميل العلاقات بعد الإنشاء. استعمل hook:

=== "Java"
    ```java
    Author loaded = authors.has(posts.count(2), "posts").afterCreating(a -> a.load("posts")).create();
    ```
=== "Kotlin"
    ```kotlin
    val loaded: Author = authors.has(posts.count(2), "posts").afterCreating { a -> a.load("posts") }.create()
    ```


تعمل الـ hooks بعد إنشاء الأبناء، فتحتويهم العلاقة المحمّلة.

## الأخطاء

تسمّي الرسائل صنفًا أو علاقة، ولا تذكر قيمة أبدًا.

| الحالة | الاستثناء |
|---|---|
| `has` على علاقة ليست `HasOne` أو `HasMany` أو `MorphOne` أو `MorphMany` | `IllegalArgumentException` |
| `hasAttached` على علاقة ليست `BelongsToMany` | `IllegalArgumentException` |
| `forParent` على علاقة ليست `BelongsTo` أو `MorphTo` | `IllegalArgumentException` |
| اسم علاقة غير معروف، أو خريطة `relations()` سيئة | `RelationNotFoundException` و`InvalidRelationException` |
| `forParent(Model)` بنموذج غير محفوظ | `IllegalStateException` |
| `has` والأب بلا قيمة للمفتاح المحلي | `IllegalStateException` |
| `hasAttached` بقائمة pivot فارغة | `IllegalArgumentException` |
| `hasAttached` بنموذج غير محفوظ في القائمة | `IllegalArgumentException` |
| `raw` مع قيمة `Factory` أو `forParent(Factory)` | `IllegalStateException` |
| نموذج مُعاد الاستخدام غير محفوظ | `IllegalStateException` |
| تداخل أعمق من 32 مستوى | `IllegalStateException` |
| وسيط `null` | `NullPointerException` |
