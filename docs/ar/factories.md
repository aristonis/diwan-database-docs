# المصانع (Factories)

يبني المصنع (factory) نماذج للاختبارات وتعبئة البيانات. تكتب تعريفًا واحدًا هو خصائص صف نموذجي، ثم تطلب نموذجًا واحدًا أو عدة نماذج، محفوظة أو غير محفوظة. تغيّر الحالات (states) التعريف في استدعاء واحد، وتغيّره التسلسلات (sequences) من صف إلى آخر.

توجد المصانع في `diwan-database-eloquent`، في الحزمة `org.aristonis.diwan.database.eloquent.factory`، وفيها نوعان عامّان: `Factory` و`Sequence`.

ليس في Diwan بيانات وهمية أو عشوائية. التعريف هو دالة lambda تكتبها أنت: قيمة ثابتة، أو عدّاد، أو أي مكتبة بيانات تستعملها أصلًا. لا شيء في هذه الصفحة يحتاج مكتبة.

## تعريف مصنع

تأخذ `Factory.of` مدخل النموذج و`Supplier` يعيد الخصائص:

=== "Java"
    ```java
    Factory<User> users = Factory.of(User.query.on(manager.query()), () -> Map.of(
        "name", "Ada",
        "email", "ada@example.com",
        "role", "member"));

    User ada = users.create();   // saved, with id and timestamps
    ```
=== "Kotlin"
    ```kotlin
    val users: Factory<User> = Factory.of(User.query.on(manager.query())) {
        mapOf(
            "name" to "Ada",
            "email" to "ada@example.com",
            "role" to "member",
        )
    }

    val ada: User = users.create()   // saved, with id and timestamps
    ```

لا يتغيّر المصنع أبدًا. كل دالة أدناه تعيد مصنعًا جديدًا، فيمكن أن تشترك اختبارات كثيرة في مصنع واحد، ولا تتسرّب حالة أُضيفت في اختبار إلى اختبار آخر.

ويملأ المصنع أيضًا خصائص لا يذكرها `fillable()` في النموذج، فيستطيع التعريف ضبط أي عمود.

### صنف فرعي

للنموذج الذي تبنيه كثيرًا، مدّد `Factory` وضع التعريف في `definition()`. سمِّ كل حالة بدالة تعيد `Factory<M>`:

=== "Java"
    ```java
    public final class UserFactory extends Factory<User> {
        public UserFactory(QueryFactory db) {
            super(User.query.on(db));
        }

        @Override
        protected Map<String, Object> definition() {
            return Map.of("name", "Ada", "email", "ada@example.com", "role", "member");
        }

        public Factory<User> admin() {
            return set("role", "admin");
        }
    }

    List<User> admins = new UserFactory(manager.query()).admin().count(3).createMany();
    ```
=== "Kotlin"
    ```kotlin
    class UserFactory(db: QueryFactory) : Factory<User>(User.query.on(db)) {
        override fun definition(): Map<String, Any> {
            return mapOf("name" to "Ada", "email" to "ada@example.com", "role" to "member")
        }

        fun admin(): Factory<User> {
            return set("role", "admin")
        }
    }

    val admins: List<User> = UserFactory(manager.query()).admin().count(3).createMany()
    ```

تعيد دالة الحالة `Factory<User>` وليس `UserFactory`، فتُستدعى حالات الصنف الفرعي المسمّاة أولًا ثم تتبعها الدوال المتسلسلة: `new UserFactory(db).admin().count(3)`.

## الحالات و set

تغيّر الحالة الخصائص في الاستدعاءات التي تليها. تستبدل `state(Map)` المفاتيح التي تذكرها. وتستبدل `set(name, value)` مفتاحًا واحدًا. وتستقبل `state(UnaryOperator)` نسخة للقراءة فقط من الخصائص المبنية حتى الآن، وتعيد المفاتيح المراد استبدالها:

=== "Java"
    ```java
    Factory<User> admins = users.state(Map.of("role", "admin"));
    Factory<User> renamed = users.set("name", "Grace");
    Factory<User> derived = users.state(soFar -> Map.of("email", soFar.get("name") + "@example.org"));
    ```
=== "Kotlin"
    ```kotlin
    val admins: Factory<User> = users.state(mapOf("role" to "admin"))
    val renamed: Factory<User> = users.set("name", "Grace")
    val derived: Factory<User> = users.state { soFar -> mapOf("email" to "${soFar["name"]}@example.org") }
    ```

تملأ الحالات و`set` النموذج عبر `forceFill` الذي يتجاوز `fillable` و`guarded`، فلا تمرّر إليها بيانات طلب أبدًا. وتنسخ `state(Map)` الـ map نسخًا سطحيًا، فتُشارَك القيم القابلة للتغيير داخلها بين المصانع.

تُطبَّق الحالات بترتيب إضافتها. تغلب الحالة اللاحقة السابقة والتعريف. ويحتفظ المفتاح بموضعه عند استبداله.

## القيم

كل قيمة في تعريف أو حالة أو `set` هي واحدة من ثلاث:

| القيمة | المعنى |
|---|---|
| كائن عادي | تُستعمل كما هي |
| `Supplier` | يُستدعى من دون وسيط، مرة لكل نموذج |
| `Function<Map<String, Object>, Object>` | تُستدعى بنسخة من الخصائص المحلولة حتى الآن |

تُستعمل النتيجة كما هي: `Supplier` يعيد دالة يخزّن تلك الدالة. ويُفحص `Supplier` قبل `Function`.

تحتاج lambda داخل map إلى نوع هدف، فعرّفها أولًا:

=== "Java"
    ```java
    AtomicInteger counter = new AtomicInteger();
    Supplier<Object> number = () -> counter.incrementAndGet();
    Function<Map<String, Object>, Object> email =
        soFar -> soFar.get("name").toString().toLowerCase() + "@example.com";

    Factory<User> numbered = Factory.of(User.query.on(manager.query()), () -> {
        Map<String, Object> attrs = new LinkedHashMap<>();
        attrs.put("name", "User");
        attrs.put("email", email);   // sees name, resolved first
        attrs.put("badge", number);  // a new number for each model
        return attrs;
    });
    ```
=== "Kotlin"
    ```kotlin
    val counter = AtomicInteger()
    val number = Supplier<Any> { counter.incrementAndGet() }
    val email = Function<Map<String, Any?>, Any> { soFar ->
        soFar["name"].toString().lowercase() + "@example.com"
    }

    val numbered: Factory<User> = Factory.of(User.query.on(manager.query())) {
        linkedMapOf("name" to "User", "email" to email, "badge" to number)
    }
    ```

ترى `Function` المفاتيح التي تسبقها في الـ map نفسه، فاستعمل map بترتيب مفاتيح ثابت (`LinkedHashMap` أو `linkedMapOf`) حين تعتمد قيمة على أخرى. لا ترتيب ثابت في `Map.of`؛ فضع القيمة التابعة في حالة لاحقة.

إذا توقّعت `Function` نوع إدخال آخر، يُعاد رمي الـ `ClassCastException` الناتج على صورة `IllegalArgumentException` تسمّي الخاصية وصنف النموذج، ولا تذكر القيمة أبدًا. والاستثناء الأصلي هو السبب (cause).

### بياناتك أنت

للحصول على أسماء أو عناوين أو أرقام عشوائية، مرّر lambda تستدعي المكتبة التي تفضّلها. هذا مثال بـ Datafaker تضيفها إلى بنائك أنت:

=== "Java"
    ```java
    Faker faker = new Faker();
    Supplier<Object> name = () -> faker.name().fullName();
    Supplier<Object> email = () -> faker.internet().emailAddress();

    Factory<User> users = Factory.of(User.query.on(manager.query()), () -> Map.of(
        "name", name,
        "email", email));
    ```
=== "Kotlin"
    ```kotlin
    val faker = Faker()

    val users: Factory<User> = Factory.of(User.query.on(manager.query())) {
        mapOf(
            "name" to Supplier<Any> { faker.name().fullName() },
            "email" to Supplier<Any> { faker.internet().emailAddress() },
        )
    }
    ```

## العدد (count)

تحدّد `count(n)` عدد النماذج التي تبنيها الدوال الجمعية. تقرؤها `makeMany()` و`createMany()` و`createManyQuietly()` و`rawMany()` و`insert()`. تغلب آخر `count`. ومن دونها تبني هذه الدوال نموذجًا واحدًا.

أما الدوال المفردة `make()` و`create()` و`createQuietly()` و`raw()` فتبني نموذجًا واحدًا دائمًا وتتجاهل `count`. والصيغ التي تأخذ رقمًا، مثل `makeMany(5)`، تستعمل ذلك الرقم وتتجاهل `count`. وعدد أقل من واحد لا يبني شيئًا ويعيد قائمة فارغة.

## make و create

تبني `make()` نموذجًا في الذاكرة ولا تحفظه. وتبني `makeMany()` قائمة.

=== "Java"
    ```java
    User draft = users.make();                       // not saved: draft.exists() is false
    List<User> drafts = users.makeMany(5);
    ```
=== "Kotlin"
    ```kotlin
    val draft: User = users.make()                   // not saved: draft.exists() is false
    val drafts: List<User> = users.makeMany(5)
    ```

تبني `create()` النموذج وتحفظه وتعيده. وتفعل `createMany()` الشيء نفسه لقائمة، بحفظ واحد لكل نموذج. وتحفظ `createQuietly()` و`createManyQuietly()` من دون إطلاق أحداث النموذج، بكتم واحد للدفعة كلها.

=== "Java"
    ```java
    User ada = users.create();
    List<User> five = users.count(5).createMany();
    List<User> silent = users.createManyQuietly(3);   // no model event fires
    ```
=== "Kotlin"
    ```kotlin
    val ada: User = users.create()
    val five: List<User> = users.count(5).createMany()
    val silent: List<User> = users.createManyQuietly(3)   // no model event fires
    ```

ترمي `create()` الاستثناء `IllegalStateException` حين يوقف hook حدث نموذج الحفظ أو حين لا يُخزَّن أي صف. تسمّي الرسالة صنف النموذج. وخطأ الحفظ نفسه يصلك كما هو، ولا تعمل hooks الـ `afterCreating` لذلك النموذج.

## الخصائص الخام

تعيد `raw()` الخصائص المحلولة على شكل map ولا تبني نموذجًا. وتعيد `rawMany()` قائمة من الـ maps. استعملها لأجسام الطلبات وبيانات الاختبار.

=== "Java"
    ```java
    Map<String, Object> body = users.set("role", "admin").raw();
    List<Map<String, Object>> bodies = users.rawMany(3);
    ```
=== "Kotlin"
    ```kotlin
    val body: Map<String, Any> = users.set("role", "admin").raw()
    val bodies: List<Map<String, Any>> = users.rawMany(3)
    ```

كل map جديد وهو لك لتغيّره.

## الإدراج (insert)

تكتب `insert()` كل الصفوف بعبارة واحدة ولا تعيد شيئًا:

=== "Java"
    ```java
    users.insert(1000);
    users.count(1000).insert();
    ```
=== "Kotlin"
    ```kotlin
    users.insert(1000)
    users.count(1000).insert()
    ```

تمرّ العبارة عبر مسار الإدراج في النموذج، فتُطبَّق الـ casts والـ timestamps. ولا يُبنى أي نموذج، فلا تعمل hooks الـ `afterMaking` أو `afterCreating`، ولا يُطلق حدث نموذج، لكن `beforeWrite()` يعمل على كل صف. وإذا كان العدد أقل من واحد لا يُكتب شيء.

للعبارة الواحدة حد ربط (999 على SQLite قبل 3.32)، فقسّم الإدراج الكبير جدًا إلى دفعات. ويجب أن تحمل الصفوف كلها المفاتيح نفسها. الحالة التي تضيف مفتاحًا إلى بعض الصفوف فقط (تسلسل تختلف مفاتيح مدخلاته) تفشل بـ `IllegalArgumentException`.

## الـ Hooks

يعمل `afterMaking(hook)` لكل نموذج بعد بنائه، عبر `make` و`makeMany` و`create` و`createMany`. ويعمل `afterCreating(hook)` لكل نموذج بعد حفظه، عبر `create` و`createMany` وصيغ quiet. وتعمل الـ hooks بترتيب إضافتها.

=== "Java"
    ```java
    Factory<User> withPosts = users
        .afterMaking(user -> user.setAttribute("name", "Ada Lovelace"))
        .afterCreating(user -> posts.create(Map.of("user_id", user.getKey(), "title", "Hello")));
    ```
=== "Kotlin"
    ```kotlin
    val withPosts: Factory<User> = users
        .afterMaking { user -> user.setAttribute("name", "Ada Lovelace") }
        .afterCreating { user -> posts.create(mapOf("user_id" to user.key, "title" to "Hello")) }
    ```

تسقط `withoutAfterMaking()` و`withoutAfterCreating()` الـ hooks المضافة حتى الآن. وأي hook يُضاف بعدهما يعمل. ولا تشغّل `insert` و`raw` أي hook.

## الاتصال (connection)

تبني `connection(connection)` وتحفظ على اتصال آخر. ومن دونها يستعمل المصنع الاتصال الذي رُبط به مدخل النموذج:

=== "Java"
    ```java
    User report = users.connection(reportingConnection).create();
    ```
=== "Kotlin"
    ```kotlin
    val report: User = users.connection(reportingConnection).create()
    ```

## المحذوف (trashed)

تعلّم `trashed()` النموذج محذوفًا حذفًا ناعمًا: تضبط عمود deleted-at، قبل يوم من الآن افتراضيًا. وتضبط `trashed(Instant)` تلك اللحظة. يُؤخذ العمود من النموذج، فيعمل النموذج الذي يغيّر اسمه أيضًا.

=== "Java"
    ```java
    Post old = postFactory.trashed().create();
    Post gone = postFactory.trashed(Instant.parse("2026-01-01T00:00:00Z")).create();
    ```
=== "Kotlin"
    ```kotlin
    val old: Post = postFactory.trashed().create()
    val gone: Post = postFactory.trashed(Instant.parse("2026-01-01T00:00:00Z")).create()
    ```

على نموذج بلا soft deletes ترمي `trashed()` الاستثناء `IllegalStateException` عند بناء الصفوف (في `make` أو `create` أو `raw` أو `insert`)، ولا تفشل بصمت أبدًا. أما بناء المصنع نفسه فلا ينفّذ شيئًا.

## التسلسلات (Sequences)

يعطي التسلسل كل نموذج مدخلته. تتكرر المدخلات حين تزيد النماذج عليها. تأخذ `sequence(...)` الـ maps، وتضبط `forEachSequence(...)` العدد أيضًا على عدد المدخلات:

=== "Java"
    ```java
    List<User> mixed = users
        .sequence(Map.of("role", "admin"), Map.of("role", "member"))
        .count(5)
        .createMany();                // admin, member, admin, member, admin

    List<User> pair = users
        .forEachSequence(Map.of("role", "admin"), Map.of("role", "member"))
        .createMany();                // exactly two models
    ```
=== "Kotlin"
    ```kotlin
    val mixed: List<User> = users
        .sequence(mapOf("role" to "admin"), mapOf("role" to "member"))
        .count(5)
        .createMany()                 // admin, member, admin, member, admin

    val pair: List<User> = users
        .forEachSequence(mapOf("role" to "admin"), mapOf("role" to "member"))
        .createMany()                 // exactly two models
    ```

يبدأ التسلسل من جديد في كل استدعاء. استدعاءان لـ `createMany` على المصنع نفسه يبدآن معًا من المدخلة الأولى، لأن الموضع هو موضع الحلقة في الاستدعاء ولا يُحفظ شيء بين الاستدعاءات. وتستعمل `make()` و`create()` و`raw()` المدخلة الأولى دائمًا.

### Sequence

لتحكّم أكبر ابنِ `Sequence` ومرّره إلى `sequence(Sequence)`:

| الدالة | عملها |
|---|---|
| `Sequence.of(maps...)` | مدخلات من maps |
| `Sequence.byIndex(functions...)` | مدخلات من `IntFunction` تستقبل موضع النموذج بدءًا من 0 |
| `and(map)` و`and(function)` | تسلسل جديد بمدخلة زائدة |
| `Sequence.crossJoin(lists...)` | كل توليفة بمدخلة من كل قائمة؛ تتغيّر القائمة الأولى أبطأ، ويغلب المفتاح اللاحق |
| `size()` | عدد المدخلات |

الـ `Sequence` غير قابل للتغيير وآمن للمشاركة. وتستقبل مدخلة `IntFunction` موضع النموذج نفسه، لا موضعها في الدورة، فيمكنها ترقيم الصفوف:

=== "Java"
    ```java
    Sequence numbered = Sequence.byIndex(i -> Map.of("name", "User " + i));

    Sequence grid = Sequence.crossJoin(
        List.of(Map.of("role", "admin"), Map.of("role", "member")),
        List.of(Map.of("active", true), Map.of("active", false)));

    List<User> all = users.sequence(grid).count(4).createMany();
    ```
=== "Kotlin"
    ```kotlin
    val numbered: Sequence = Sequence.byIndex(IntFunction { i -> mapOf("name" to "User $i") })

    val grid: Sequence = Sequence.crossJoin(
        listOf(mapOf("role" to "admin"), mapOf("role" to "member")),
        listOf(mapOf("active" to true), mapOf("active" to false)),
    )

    val all: List<User> = users.sequence(grid).count(4).createMany()
    ```

## الأخطاء

تسمّي الرسائل صنفًا أو موضعًا أو خاصية، ولا تذكر قيمة أبدًا.

| الحالة | الاستثناء |
|---|---|
| `create` وأوقف hook الحفظ أو لم يُخزَّن صف | `IllegalStateException` |
| `trashed` على نموذج بلا soft deletes | `IllegalStateException` |
| `ClassCastException` أثناء حل قيمة | `IllegalArgumentException` تسمّي الخاصية وصنف النموذج، والأصلي هو السبب |
| `Sequence.of()` أو `byIndex()` بلا مدخلة | `IllegalArgumentException` |
| `crossJoin` بلا قائمة، أو بقائمة فارغة، أو بنتيجة أكبر من اللازم | `IllegalArgumentException` |
| `insert` بصفوف مفاتيحها مختلفة | `IllegalArgumentException` |
| وسيط `null` أو مفتاح `null` أو مدخلة تسلسل `null` | `NullPointerException` |

## لاحقًا

مصانع النماذج المرتبطة (`has` و`for`) ومشاركة أب واحد عبر رسم كامل (`recycle`) ليست جزءًا من هذا الإصدار. أنشئ الصفوف المرتبطة في hook من نوع `afterCreating` كما في المثال أعلاه.
