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

المشغّل (driver) هو من يصنّف الفشل. والتصنيفات هي `DriverFailureKind.UNIQUE_VIOLATION` و`FOREIGN_KEY_VIOLATION` و`CONCURRENCY` و`CANCELLED` و`CONNECTION_LOST` و`COMMIT_OUTCOME_UNKNOWN`. إذا فشل `COMMIT` بسبب انقطاع الاتصال فقد يكون التثبيت تمّ. افحص قاعدة البيانات قبل أن تعيد المحاولة أو تتراجع.

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
| `MigrationChecksumException` | عُدّلت migration سبق تشغيلها. لم يعمل شيء. أعدها كما كانت، أو اقبل التغيير بـ `repairChecksums`. |
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
