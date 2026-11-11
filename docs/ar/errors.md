# الأخطاء

كل استثناءات Diwan Database غير مفحوصة (unchecked). تصل أخطاء قاعدة البيانات كـ `QueryException` أو إحدى فئاته الفرعية. وبقية المجالات ترمي أنواعها الخاصة، وهي مسرودة أدناه.

## أين توجد

| الحزمة (package) | ما تحتويه |
|---|---|
| `org.aristonis.diwan.database.exception` | كل استثناءات النواة، وأصلها المشترك `DatabaseException`. |
| `org.aristonis.diwan.database.eloquent.exception` | كل استثناءات النماذج، وأصلها المشترك `EloquentException` (الذي يرث `DatabaseException`). |

التقط `DatabaseException` لتعالج في مكان واحد أي فشل يأتي من قاعدة البيانات أو المشغّل (driver) أو الترحيل أو النموذج. أما أخطاء شيفرتك أنت، مثل وسيط خاطئ أو استدعاء في حالة غير مناسبة، فتُرمى كـ `IllegalArgumentException` و `IllegalStateException` من JDK، فلا يلتقطها `DatabaseException`.

## QueryException

`QueryException` تعني أن قاعدة البيانات رفضت عبارة. وهي تحمل:

| الدالة | ما تعيده |
|---|---|
| `getConnectionName()` | الاتصال الذي شُغّلت عليه العبارة. |
| `getSql()` | نص SQL. |
| `getBindings()` | القيم التي مرّرتها، كقائمة. |
| `sqlState()` | `Optional<String>` فيه حالة SQL، وفارغ إن لم تعطِ القاعدة حالة. |
| `vendorCode()` | رمز الخطأ الخاص بقاعدة البيانات. |
| `isConcurrencyFailure()` | `true` عند deadlock (تعانق) أو فشل serialization (تحويل النموذج إلى map أو JSON) أو قاعدة مشغولة. |
| `getCause()` | الـ `DriverException` القادم من المشغّل. |

### الأنواع

| النوع | متى | ماذا تفعل |
|---|---|---|
| `UniqueConstraintViolationException` | انكسر مفتاح فريد أو أساسي. | أخبر المستخدم أن القيمة مكررة، أو استعمل `upsert`. |
| `ForeignKeyViolationException` | انكسر مفتاح أجنبي. | أدخل الأب أولًا، أو احذف الأبناء. |
| `QueryException` مع `isConcurrencyFailure()` | deadlock أو فشل serialization أو قاعدة مشغولة. | أعد العمل بـ `transaction(callback, attempts)`. |
| `QueryException` | أي رفض آخر من القاعدة: SQL خاطئ أو جدول مفقود أو اتصال منقطع. | اقرأ `sqlState()` و`getCause()`. |

الفئات الفرعية تمتد من `QueryException`، فـ `catch` واحدة تشملها كلها. التقط النوع المحدد أولًا:

=== "Java"
    ```java
    try {
        db.insert("insert into users (email) values (?)", email);
    } catch (UniqueConstraintViolationException e) {
        return "That email is already registered.";
    } catch (QueryException e) {
        LOG.warning("insert failed on " + e.getConnectionName() + ", state " + e.sqlState().orElse("unknown"));
        throw e;
    }
    ```
=== "Kotlin"
    ```kotlin
    try {
        db.insert("insert into users (email) values (?)", email)
    } catch (e: UniqueConstraintViolationException) {
        return "That email is already registered."
    } catch (e: QueryException) {
        LOG.warning("insert failed on ${e.connectionName}, state ${e.sqlState().orElse("unknown")}")
        throw e
    }
    ```

المشغّل (driver) هو من يصنّف الفشل. والتصنيفات هي `DriverFailureKind.UNIQUE_VIOLATION` و`FOREIGN_KEY_VIOLATION` و`CHECK_VIOLATION` و`NOT_NULL_VIOLATION` و`CONCURRENCY` و`CANCELLED` و`CONNECTION_LOST` و`COMMIT_OUTCOME_UNKNOWN`. إذا فشل `COMMIT` بسبب انقطاع الاتصال فقد يكون التثبيت تمّ. افحص قاعدة البيانات قبل أن تعيد المحاولة أو تتراجع.

الـ `getCause()` في `QueryException` هو `DriverException`. ورسالته بصيغة ثابتة:

```text
Database failure (SQL state unknown, vendor code 5): concurrency, SQLITE_BUSY
```

الجزء الأول يظهر دائمًا. وبعد `: ` تأتي التصنيفات التي عرفها المشغّل بأحرف صغيرة، ثم اسم رمز نتيجة SQLite إذا كان Diwan يعرف الرمز. وإن لم يوجد تصنيف ولا رمز معروف فالرسالة هي الجزء الأول فقط. ولا تحمل الرسالة قيمًا ولا نص قاعدة البيانات أبدًا. ورمز Diwan الذي تنتهي به الرسالة، وهو موصوف أدناه، لا يحمل إلا أسماء القيود والأعمدة.

## معاملة ألغتها جملة فاشلة

على PostgreSQL تُلغي الجملة الفاشلة معاملتها. فيرفض Diwan الجملة التالية أو الـ commit أو تحرير الـ savepoint بـ `IllegalStateException` وليس `QueryException`، ورسالته:

```text
The transaction was aborted by a failed statement; roll back (or roll back to the savepoint) first
```

`getCause()` هو أول فشل. وخطأ الخادم `25P02` لا يصلك أبدًا. تراجع عن المعاملة، أو عن الـ savepoint، فتصير المعاملة صالحة من جديد. الـ callback الخاص بـ `transaction` يتراجع وحده، فلا يظهر هذا إلا حين يلتقط الكود فشلًا ويتابع. انظر [الاتصالات والمعاملات](connections.md#جملة-فاشلة-على-postgresql).

## ما لا تحتويه الرسائل أبدًا

رسالة `QueryException` تبدو هكذا:

```text
SQL: insert into users (email) values (?) (Connection: main, SQL state 23505, vendor code 0)
```

افتراضيًا لا تحتوي قيم bindings ولا نص خطأ قاعدة البيانات، لأن كليهما قد يحمل بيانات شخصية. هذا النص يبقى في `getCause()`.

- `showBindingsInErrors(true)` في builder (باني الكائن) الاتصال يضيف القيم وسبب القاعدة إلى الرسالة. استعمله أثناء التطوير.
- `getBindings()` تحمل القيم في الحالتين. لا تسجّلها حيث يجب ألا تصل البيانات الشخصية.
- سطر سجل يطبع سلسلة الأسباب كلها (cause chain) يُظهر نص القاعدة مهما كان الإعداد. أرسل `getMessage()` وحدها إلى السجلات المشتركة.
- فواصل الأسطر والرموز التحكمية في SQL تُهرَّب (escaped)، وSQL الطويل يُقطع بعد 1000 حرف، وقيمة `byte[]` تظهر كـ `<n bytes>`.
- كلمات المرور لا تظهر أبدًا. `ConnectionConfig` تطبع `***`، و`DatabaseConfigException` تذكر المفتاح ولا تذكر القيمة.
- الأحداث تحمل القيم الخام. استدعِ `redacted()` على `QueryExecuted` أو `QueryFailed` قبل أن تسجّله.
- `QueryException` المُسلسلة (serialized) تحذف الـ bindings المخفية.

## رموز أخطاء Diwan

تعطي `DriverException.error()` الخطأ الموحّد للفشل: رمزًا ثابتًا، واسم القيد (constraint) أو الفهرس، والأعمدة المعنية. من `QueryException` تصل إلى استثناء المشغّل بـ `getCause()`:

=== "Java"
    ```java
    try {
        db.insert("insert into users (email) values (?)", email);
    } catch (QueryException e) {
        DiwanError error = ((DriverException) e.getCause()).error();
        switch (error.code()) {
            case "DWN-CST-0001":
                return "That email is already registered.";
            case "DWN-TXN-0001":
                return "Please try again.";
            default:
                throw e;
        }
    }
    ```
=== "Kotlin"
    ```kotlin
    try {
        db.insert("insert into users (email) values (?)", email)
    } catch (e: QueryException) {
        val error = (e.cause as DriverException).error()
        return when (error.code()) {
            "DWN-CST-0001" -> "That email is already registered."
            "DWN-TXN-0001" -> "Please try again."
            else -> throw e
        }
    }
    ```

| الرمز | التصنيف | المعنى |
|---|---|---|
| `DWN-CST-0001` | `UNIQUE_VIOLATION` | كُسر مفتاح unique أو مفتاح أساسي. |
| `DWN-CST-0002` | `FOREIGN_KEY_VIOLATION` | كُسر مفتاح أجنبي. على PostgreSQL يشمل حالة SQL رقم 23503 و23001 (`restrict_violation`، تُرفع لمفتاح معرّف بـ `restrictOnDelete()`)؛ وكلاهما يحمل اسم القيد في `key()`. |
| `DWN-CST-0003` | `CHECK_VIOLATION` | كُسر قيد check. |
| `DWN-CST-0004` | `NOT_NULL_VIOLATION` | تلقّى عمود NOT NULL قيمة null. |
| `DWN-TXN-0001` | `CONCURRENCY` | deadlock أو فشل serialization أو قاعدة بيانات مشغولة. أعد تنفيذ العمل. |
| `DWN-TXN-0002` | لا يوجد | محجوز لفشل انتظار القفل. لا يُبلّغ عنه أي فشل حتى الآن. |
| `DWN-TXN-0003` | `COMMIT_OUTCOME_UNKNOWN` | فشل commit بسبب انقطاع الاتصال، فقد يكون تمّ. افحص قاعدة البيانات. |
| `DWN-CNX-0001` | `CONNECTION_LOST` | انقطع الاتصال بقاعدة البيانات. |
| `DWN-QRY-0001` | `CANCELLED` | أُلغيت الجملة. |
| `DWN-UNK-0000` | لا يوجد | لم يتعرّف المشغّل على الفشل. |

قد يحمل الفشل أكثر من تصنيف. ورمزه هو أول صف في هذا الجدول يملك الفشل تصنيفه، فالجدول مرتّب بالأسبقية من الأعلى إلى الأسفل. مثلًا، فشل يحمل `CONCURRENCY` و`CONNECTION_LOST` معًا يبلّغ `DWN-TXN-0001`.

الرموز جزء من الـ API العام. الرمز لا يغيّر معناه أبدًا، ولا يُعاد ترقيمه ولا يُعاد استعماله. الفشل الجديد يأخذ رمزًا جديدًا، والمشغّل الجديد يربط أخطاءه هو فقط بالرموز الموجودة. اكتب الشيفرة اعتمادًا على `code()`، لا على نص الرسالة ولا على رمز المورّد (vendor code).

`key()` هو اسم القيد أو الفهرس، و`columns()` تسرد الأعمدة المعنية. كلاهما فارغ عندما لا يستطيع المشغّل إعطاءه. وهما يحملان أسماء المخطط، ولا يحملان قيم الصفوف أبدًا. وهذا ما يعطيه كل مشغّل:

| الفشل | PostgreSQL | SQLite |
|---|---|---|
| Unique | المفتاح: اسم القيد. الأعمدة: لا شيء، لأن الخادم لا يسمّيها في هذا الخطأ. | المفتاح: لا شيء. الأعمدة: أعمدة الفهرس. |
| Foreign key | المفتاح: اسم القيد. الأعمدة: لا شيء. | لا شيء. |
| Check | المفتاح: اسم القيد. الأعمدة: لا شيء. | المفتاح: اسم القيد. في SQLite الأقدم، مثل التي في Android 9، يبلّغ check بلا اسم عن نص تعبيره كمفتاح. سمِّ قيود check عندك. |
| Not null | المفتاح: لا شيء. الأعمدة: العمود. | الأعمدة: العمود. |
| Table (`table()`) | اسم الجدول الذي يسمّيه الخادم. في Foreign key هو الجدول الابن (child) الذي يحمل المفتاح، حتى لو حذفت الأب. | جدول فشل unique أو not null، مقروءًا من الرسالة. فارغ في Foreign key وcheck، وعندما تأتي الأعمدة من جدولين. |

يعطي PostgreSQL هذه القيم من حقول الخطأ المنظّمة في الخادم، لا من نص الرسالة، فلا تعتمد على لغة الخادم.

يكون `table()` فارغًا عندما لا يستطيع المشغّل تسمية جدول. و`DiwanError` المحفوظ بنسخة أقدم يقرأ `table()` فارغًا.

تنتهي رسالة `DriverException` ورسالة `QueryException` بالرمز، ثم كلمات تصنيفه، ثم المفتاح والأعمدة عندما تكون معروفة:

```text
... [DWN-CST-0001 unique violation: users_email_unique (email)]
```

الصيغة هي `[<code> <kind words>[: <key>][ (<columns>)]]`. بلا مفتاح يُحذف جزء النقطتين، وبلا أعمدة تُحذف الأقواس. والفشل الذي لا يتعرّف عليه Diwan ينتهي بـ `[DWN-UNK-0000]`. أما الدوال `sqlState()` و`vendorCode()` و`kinds()` و`databaseMessage()` فلم تتغيّر.

## الاستثناءات حسب المجال

### الاتصال والـ manager

| الاستثناء | المعنى |
|---|---|
| `IllegalStateException` (المعاملات الصارمة) | استُعمل الاتصال الجذر من داخل معاملته. استعمل `tx`، أو ابنِ بـ `strictTransactions(false)`. |
| `MultipleColumnsSelectedException` | قرأت `scalar` صفًا بأعمدة كثيرة. |
| `ListenerFailedException` | رمى مستمع بعد نجاح العبارة. العبارة لا تُلغى. والسبب هو أول فشل في المستمعين. |
| `DatabaseConfigException` | إعداد خاطئ. تمتد من `IllegalArgumentException`. |
| `IllegalArgumentException` | اسم اتصال غير معروف، أو driver بلا connector (موصّل يبني الاتصال من الإعدادات)، أو `attempts` أقل من 1. |
| `IllegalStateException` | الـ manager مغلق، أو سأل مستمع عن الاتصال الذي يُبنى الآن. |

### المخطط والـ migrations

| الاستثناء | المعنى |
|---|---|
| `MigrationFailedException` | فشلت migration (تهجير قاعدة البيانات). السبب (cause) هو الفشل الحقيقي. و`phase()` تقول هل فشلت الـ migration نفسها أم سجلّها فقط. الـ migrations السابقة تبقى مطبّقة. |
| `MigrationChecksumException` | عُدّلت migration سبق تشغيلها. لم يعمل شيء. أعدها كما كانت وغيّر الـ schema بـ migration جديدة. و`repairChecksums` للاسترداد فقط. |
| `MissingMigrationsException` | rollback (تراجع) أو reset سيصل إلى سجلات migrations لا يملكها الـ migrator. انشر الكود الأحدث، أو ابنِ بـ `allowMissingOnRollback()`. |
| `ForeignKeysOffRequiredException` | إعادة بناء جدول في SQLite تتطلب إطفاء المفاتيح الأجنبية. الـ migrator يعالجها. وفي غيره استعمل `Schema.withoutForeignKeyConstraints`. |
| `ForeignKeyCheckException` | كسرت صفوف مفتاحًا أجنبيًا بعد إعادة بناء جدول. التغيير يُلغى. الرسالة تسمّي الجداول والأعداد ولا تذكر قيم الصفوف. |

### النماذج

| الاستثناء | المعنى |
|---|---|
| `ModelNotFoundException` | `findOrFail` وأخواتها لم تجد صفًا. رسالة Laravel: `No query results for model [app.User] 1`. |
| `MultipleRecordsFoundException` | `sole()` طابقت أكثر من صف. |
| `MassAssignmentException` | `fill` ذكرت مفتاحًا لا يسمح به النموذج. |
| `RelationNotFoundException` | اسم علاقة ليس في الصنف. الرسالة تسرد الأسماء المعروفة. |
| `LazyLoadingViolationException` | حُمّلت علاقة بكسل (lazy loading) بينما `preventLazyLoading(true)` مفعّلة. |
| `InvalidCastException` و`InvalidRelationException` و`JsonException` | فشل cast (تحويل نوع قيمة الـ attribute عند القراءة والكتابة) أو تعريف علاقة أو معالجة JSON. |

رسائل استثناءات النماذج تسمّي الصنف والعلاقة ولا تذكر قيمة أي attribute (خاصية).

## الاستثناءات المكبوتة (suppressed)

Diwan لا تبتلع فشلًا أبدًا. إذا حدث فشل ثانٍ أثناء معالجة الأول، مثل rollback يفشل أو مستمع يرمي، يُضاف إلى الأول بـ `addSuppressed`. اطبع stack trace (أثر المكدس) كاملًا أو اقرأ `getSuppressed()` لتراه.
