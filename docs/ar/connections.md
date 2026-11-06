# الاتصالات والمعاملات

`Connection` يرسل SQL إلى قاعدة بيانات واحدة. و`DatabaseManager` يبني اتصالات مُسمّاة من الإعدادات. وكلاهما آمن للمشاركة بين الخيوط (threads).

## اتصال مباشر

```java
Connection db = Connection.builder()
        .name("main")
        .dataSource(dataSource)        // any javax.sql.DataSource, pooled or not
        .build();
```

| دالة الـ builder (باني الكائن) | الأثر |
|---|---|
| `name(String)` | الاسم الظاهر في الأخطاء والأحداث. |
| `dataSource(DataSource)` | مصدر JDBC (واجهة Java للاتصال بقواعد البيانات). استعمل `driver(Driver)` بدلًا منه على Android، أو `connectionProvider(...)` داخل Spring. |
| `tablePrefix(String)` | حروف وأرقام وشرطة سفلية فقط. لا يُعاد كتابة SQL الخام أبدًا. |
| `showBindingsInErrors(boolean)` | مُطفأ افتراضيًا. انظر [الأخطاء](errors.md). |
| `strictTransactions(boolean)` | مُفعّل افتراضيًا. انظر أدناه. |
| `listener(ConnectionListener)` | يضيف مستمعًا (listener). |
| `queryLogLimit(int)` | حجم سجل الاستعلامات، 1000 افتراضيًا. |
| `onCleanupFailure(Consumer<Throwable>)` | يستلم فشل إرجاع الاتصال بعد نجاح العمل. الافتراضي يكتب تحذيرًا في السجل. |

الدوال التي تستدعيها عليه:

| تريد أن | استدعِ |
|---|---|
| تشغّل أي عبارة | `statement` و`unprepared` (SQL خام بلا bindings) |
| تغيّر صفوفًا وتأخذ العدد | `insert` و`update` و`delete` و`affectingStatement` |
| تقرأ صفوفًا | `select` (كل الصفوف) و`selectOne` (أول صف أو فارغ) و`scalar` (قيمة واحدة أو فارغ) و`cursor` (بث الصفوف) |
| تجمّع عملًا | `transaction(callback)` و`beginTransaction()` |
| ترى SQL دون تشغيله | `pretend(callback)` |

كل استدعاء خارج المعاملة يستعير اتصالًا من الـ pool (مجمّع الاتصالات) ويعيده قبل أن ينتهي الاستدعاء. وترمي `scalar` الاستثناء `MultipleColumnsSelectedException` إذا كان في الصف أكثر من عمود.

## DatabaseManager

يقرأ الـ manager الإعدادات عبر `ConfigSource` ويبني كل اتصال عند أول طلب، مرة واحدة لكل اسم حتى مع الاستدعاءات المتزامنة.

```properties
# database.properties
database.default=main
database.connections.main.driver=pgsql
database.connections.main.host=db.internal
database.connections.main.database=shop
database.connections.main.username=shop
database.connections.main.password=${DB_PASSWORD}
database.connections.main.sslmode=require
database.connections.cache.driver=sqlite
database.connections.cache.database=/var/lib/shop/cache.db
```

```java
ConfigSource source = LayeredConfigSource.of(
        EnvConfigSource.system(),                         // wins over the file
        PropertiesConfigSource.of(Path.of("database.properties")));

DatabaseManager db = DatabaseManager.builder()
        .config(DatabaseConfig.from(source))
        .connector(new PostgresConnector(), new SQLiteConnector())
        .build();

QueryFactory shop = db.query();          // default connection
Schema cache = db.schema("cache");       // built on first use
```

دوال وصول أخرى: `connection(name)` و`migrator(name)` (يعيد `Migrator.Builder`) و`usingConnection(name, work)` و`getConnections()` و`hasConnection(name)` و`setDefaultConnection(name)`. اسم غير معروف أو driver (مشغّل) بلا connector (موصّل) يرمي `IllegalArgumentException` يسرد الأسماء المعروفة.

### مفاتيح الإعداد

كل المفاتيح تبدأ بـ `database.`. والاتصال هو `database.connections.<name>.<key>`.

| المفتاح | المعنى |
|---|---|
| `database.default` | اسم الاتصال الافتراضي. مطلوب. |
| `driver` | `sqlite` أو `pgsql` أو `android`: connector مسجَّل. |
| `url` | عنوان JDBC كامل. يحل محل `host` و`port` و`database`. |
| `host` و`port` و`database` | `port` افتراضيه 5432 مع `pgsql`. ومع `sqlite` يكون `database` مسار ملف أو `:memory:`. |
| `username` و`password` | كلمة المرور تُقنَّع (masked) أينما طُبعت الإعدادات. |
| `prefix` | بادئة الجداول، فارغة افتراضيًا. |
| `strict_transactions` | `true` افتراضيًا. |
| `sqlite`: `foreign_keys` و`busy_timeout` | المفاتيح الأجنبية مفعّلة افتراضيًا. و`busy_timeout` هو مدة انتظار الجلسة الثانية على قاعدة في الذاكرة، 30000 ms افتراضيًا. |
| `pgsql`: `sslmode` و`search_path` (أو `schema`) | تُمرَّر إلى العنوان باسم `sslmode` و`currentSchema`. |

أي مفتاح آخر يُحفظ كخيار نصي للـ connector. ويمكن أن تقرأ القيمة من البيئة: `${DB_PASSWORD}` يفشل إن لم يوجد، و`${DB_HOST:-localhost}` يرجع إلى قيمة بديلة، و`$${X}` يبقى نصًا حرفيًا. والإعداد الخاطئ يرمي `DatabaseConfigException`، وهو يسمّي الاتصال والمفتاح ولا يذكر القيمة أبدًا.

المصادر: `MapConfigSource` و`PropertiesConfigSource` و`EnvConfigSource` (المفتاح `database.connections.main.password` يقرأ `DATABASE_CONNECTIONS_MAIN_PASSWORD`) و`LayeredConfigSource` (أول مصدر فيه المفتاح يفوز). طبقة البيئة تتجاوز مفتاحًا موجودًا لكنها لا تنشئ اتصالًا.

على Android ابنِ الإعدادات في الكود:

```java
DatabaseConfig config = DatabaseConfig.builder()
        .defaultConnection("app")
        .connection(ConnectionConfig.builder("app").driver("android").build())
        .build();

DatabaseManager db = DatabaseManager.builder()
        .config(config)
        .connector(AndroidConnector.of(() -> helper, SQLiteQuery::of, SQLiteSchema::of))
        .build();
```

### دورة الحياة

- `purge(name)` و`disconnect(name)` يُسقطان الاتصال المبني ويغلقان ما يملكه. الاستدعاء التالي يبني اتصالًا جديدًا.
- `reconnect(name)` يفعل purge ثم يعيد `Connection` جديدًا.
- `close()` يُنهي كل شيء. بعده يرمي كل استدعاء `IllegalStateException`. استعمل الـ manager داخل try-with-resources (بنية Java لإغلاق المورد تلقائيًا) في الاختبارات.
- لا تفعل purge لاتصال يشغّل عبارة الآن.
- قاعدة SQLite في الذاكرة تستعمل اتصالًا حقيقيًا واحدًا يُعار لجلسة واحدة في كل مرة. والجلسة الثانية على الخيط نفسه تنتظر `busy_timeout` كاملًا ثم تفشل.

## المعاملات

```java
int removed = db.transaction(tx -> {
    tx.update("update users set email = ? where id = ?", "ada@example.org", 1);
    return tx.delete("delete from users where email like ?", "%@spam.test");
});
```

تُثبَّت المعاملة (commit) حين يعود الـ callback (دالة يستدعيها النظام)، وتُلغى (rollback) حين يرمي. استعمل الاتصال الذي سُلّم إليك (`tx`) لكل شيء بالداخل.

مع try-with-resources يلغي الـ scope المعاملة عند الإغلاق ما لم تُنفَّذ `commit()`:

```java
try (TransactionScope tx = db.beginTransaction()) {
    tx.insert("insert into users (email) values (?)", "grace@example.com");
    tx.commit();
}
```

### Savepoints

المعاملة داخل معاملة تستعمل savepoint (نقطة حفظ داخل المعاملة يمكن التراجع إليها وحدها). إذا رمى الـ callback الداخلي والخارجي التقط الاستثناء، يُلغى العمل الداخلي فقط:

```java
db.transaction(outer -> {
    outer.insert("insert into logs (msg) values (?)", "start");
    try {
        outer.transaction(inner -> inner.insert("insert into logs (msg) values (?)", "risky"));
    } catch (RuntimeException ignored) {
        // "risky" is undone, "start" survives
    }
    return null;
});
```

`transactionLevel()` يعيد 0 خارج المعاملة و1 للمعاملة الخارجية. وداخل معاملة تملكها حاوية (Spring) يكون أعلى مستوى لـ Diwan مجرد savepoint، وتحتفظ الحاوية بالـ commit والـ rollback.

### المحاولات (attempts)

```java
db.transaction(tx -> transfer(tx), 3);
```

عند deadlock (تعانق) أو فشل serialization (تحويل النموذج إلى map أو JSON) يُعاد تشغيل الـ callback كله، حتى 3 مرات. والآثار الخارجية داخل الـ callback، كاستدعاء HTTP، تُعاد أيضًا. وفشل `COMMIT` لا يُعاد أبدًا لأنه قد يكون نجح. المعاملة الخارجية وحدها تعيد المحاولة، والمتداخلة ترمي الاستثناء فورًا. وقيمة `attempts` أقل من 1 ترمي `IllegalArgumentException`.

### afterCommit و afterRollback

```java
db.transaction(tx -> {
    tx.insert("insert into orders (id, total) values (?, ?)", orderId, total);
    tx.afterCommit(() -> mailer.sendReceipt(orderId));
    tx.afterRollback(() -> LOG.warning("order was not saved"));
    return orderId;
});
```

- خارج المعاملة تعمل `afterCommit` فورًا وتُهمَل `afterRollback`.
- callbacks الـ `afterCommit` تعمل بعد commit المعاملة الخارجية. والـ savepoint الذي أُلغي يُسقط callbacks الخاصة به.
- المحاولة المُعادة تُسقط callbacks الـ `afterCommit` للمحاولة الفاشلة، فلا يُرسل البريد مرتين.
- تعمل الـ callbacks بعد أن تنتهي المعاملة تمامًا. استعمل الاتصال الجذر (root) بداخلها، لا `tx`.
- callback يرمي استثناءً لا يلغي شيئًا. أول فشل يصل إلى المستدعي.
- إذا انقطع الاتصال أثناء `COMMIT` تصبح النتيجة مجهولة وتعمل `afterRollback` رغم ذلك. افحص قاعدة البيانات قبل أن تتراجع عن شيء كدفعة مالية.
- داخل معاملة فُتحت خارج المكتبة ترمي `afterCommit` الاستثناء `IllegalStateException`.

### المعاملات الصارمة (strict transactions)

افتراضيًا يرفض الاتصال الجذر الاستدعاءات القادمة من خيط داخل إحدى معاملاته. فمثل هذا الاستدعاء يستعير اتصالًا ثانيًا ويكتب خارج الـ rollback وقد يجمّد pool صغيرًا. والفشل هو `IllegalStateException` يطلب منك استعمال `tx`.

```java
Connection db = Connection.builder()
        .name("main")
        .dataSource(dataSource)
        .strictTransactions(false)     // only for deliberate writes outside, like an audit log
        .build();
```

### الجلسات (sessions)

`session(callback)` يمسك اتصالًا فيزيائيًا واحدًا طوال الكتلة، فيبقى إعداد الجلسة مثل `PRAGMA foreign_keys` في SQLite ساريًا حتى مع وجود pool. ولا تبدأ معاملة.

## الأحداث وسجل الاستعلامات

سجّل المستمعين على `events()` الخاصة بالاتصال:

```java
Registration slow = db.events().whenQueryTakesLongerThan(
        Duration.ofMillis(500),
        event -> LOG.warning("slow query " + event.time().toMillis() + " ms: " + event.redacted()));
slow.remove();
```

| الاستدعاء | الاستعمال |
|---|---|
| `listen(handler)` | lambda (دالة مجهولة مختصرة) للحدث `QueryExecuted`. |
| `addListener(ConnectionListener)` | تجاوز `queryExecuted` و`queryFailed` و`transactionBeginning` و`transactionCommitting` و`transactionCommitted` و`transactionRolledBack`. |
| `whenQueryTakesLongerThan(Duration, handler)` | يعمل لكل عبارة بطيئة. |
| `whenQueryingForLongerThan(Duration, handler)` | يعمل مرة واحدة حين يتجاوز المجموع الحد. استدعِ `resetTotalQueryDuration()` لإعادة التسليح. |

كل تسجيل يعيد `Registration`، و`remove()` يلغيه. ولإرفاق مستمع بكل اتصال يبنيه الـ manager استعمل `DatabaseManager.builder().listener(...)`. و`ManagerListener` يسمع `connectionEstablished` كلما بُني اتصال، بما في ذلك بعد `purge`.

يحمل حدث `QueryExecuted` نص SQL والـ bindings والمدة `Duration` واسم الاتصال و`QueryKind` ومستوى المعاملة. قد تحمل الـ bindings كلمات مرور وأسماء. استدعِ `event.redacted()` قبل أن ترسل الحدث إلى أي مكان.

مستمع يرمي بعد عبارة ناجحة يسبب `ListenerFailedException`، ولا تُلغى العبارة. ومستمع `queryFailed` الذي يفشل يُضاف كاستثناء suppressed ولا يحجب `QueryException` أبدًا.

### سجل الاستعلامات

```java
ConnectionEvents events = db.events();
events.enableQueryLog();
List<LoggedQuery> log = events.getQueryLog();   // a copy, oldest first
events.flushQueryLog();
```

السجل مُطفأ افتراضيًا ومحدود الحجم. وعندما يكون `showBindingsInErrors` مُطفأ يخزّن السجل `?` بدل كل binding (معامل مربوط بالاستعلام). فعّله في نسخة debug فقط.

## وضع pretend

```java
List<LoggedQuery> plan = db.pretend(p -> p.statement("drop table users"));
```

لا شيء يصل إلى قاعدة البيانات. القراءات لا تعيد صفوفًا، والأعداد 0، و`statement` تعيد `true`. ويرى المستمعون العبارات بزمن صفر.

## التجميع (pooling)

اتصالات الـ manager الخاصة تستعمل `DriverManager` وتفتح اتصال JDBC جديدًا عند كل استعارة. هذا يناسب الاختبارات والأدوات الصغيرة. أما الخادم فيجب أن يعطي الـ manager `DataSource` مجمّعًا، كما في وصفة HikariCP (مكتبة pool شائعة لـ JDBC) هذه:

```java
HikariConfig hikari = new HikariConfig();
hikari.setJdbcUrl("jdbc:postgresql://db.internal:5432/shop");
hikari.setUsername("shop");
hikari.setPassword(System.getenv("DB_PASSWORD"));
hikari.setMaximumPoolSize(10);

DatabaseManager db = DatabaseManager.builder()
        .config(config)
        .connector(new PostgresConnector())
        .dataSource("main", () -> new HikariDataSource(hikari))
        .build();
```

يعمل الـ supplier حين يُبنى الاتصال أول مرة. وتغلق Diwan الـ data source الذي يطبّق `AutoCloseable` عند `purge` أو `close`، و`HikariDataSource` كذلك. واسم غير مُعدّ يُرفض عند بناء الـ manager. ومع الاتصال المباشر مرّر الـ pool إلى `Connection.builder().dataSource(pool)` وأغلقه بنفسك.

اجعل حجم الـ pool يكفي على الأقل لعدد الخيوط التي تشغّل معاملات في الوقت نفسه. الـ cursor (مؤشر يقرأ الصفوف واحدًا واحدًا) يمسك اتصاله حتى يُغلق، فـ pool من اتصال واحد يتجمّد إذا كتبت داخل الحلقة.
