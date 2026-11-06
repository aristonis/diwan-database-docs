# Diwan Database

Diwan Database هي نسخة Java من طبقة قواعد البيانات في Laravel (`illuminate/database`). تحتفظ بأسماء الدوال كما هي في Laravel حيث تقرأ جيدًا في Java: `where` و`orderBy` و`firstOrCreate` و`migrate`. وحيث فرضت PHP خيارات Laravel، تستعمل المكتبة أدوات Java: `Optional` و`java.time` وtry-with-resources (بنية Java لإغلاق المورد تلقائيًا) والاستثناءات غير المفحوصة (unchecked exceptions).

أنت تكتب SQL واستدعاءات الـ query builder (باني الاستعلامات) والـ `migration` (تهجير قاعدة البيانات) والـ models (النماذج). والمكتبة ترسلها إلى SQLite أو PostgreSQL، على الخادم أو سطح المكتب أو Android.

## الوحدات

| الوحدة | الإحداثيات | ماذا تعطيك |
|---|---|---|
| Core | `org.aristonis:diwan-database:0.1.0` | `Connection` والمعاملات (transactions) و`DatabaseManager` وباني الاستعلامات وباني المخطط (schema builder) والـ `migration`. بلا أي اعتماد وقت التشغيل. |
| SQLite | `org.aristonis:diwan-database-sqlite:0.1.0` | قواعد (grammar) الاستعلام والمخطط الخاصة بـ SQLite. |
| PostgreSQL | `org.aristonis:diwan-database-pgsql:0.1.0` | قواعد PostgreSQL وقفل للـ `migration`. تضيف مشغّل PostgreSQL JDBC (واجهة Java للاتصال بقواعد البيانات) بنفسك. |
| Eloquent (طبقة النماذج والعلاقات المنقولة من Laravel) | `org.aristonis:diwan-database-eloquent:0.1.0` | النماذج والعلاقات والتحميل المسبق (eager loading) والـ casts والـ scopes والحذف الناعم (soft deletes) وأحداث النموذج. |
| Android | `org.aristonis:diwan-database-android:0.1.0` | مشغّل (driver) فوق `SQLiteDatabase` الخاصة بـ Android. |

## المنصات وقواعد البيانات

- Java 17 أو أحدث. ملف JAR هو bytecode عادي لـ Java 17 ومُختبَر على JDK 17 و21 و25.
- Android 9 (API 28) أو أحدث، عبر وحدة Android. انظر [Android](android.md).
- Spring وغيرها من الحاويات، عبر connection provider (مزوّد اتصالات JDBC) يُبلّغ عن معاملة الحاوية. عندها تعمل Diwan داخلها بـ savepoint (نقطة حفظ داخل المعاملة) ولا تُنهي المعاملة أبدًا.
- قواعد البيانات: SQLite وPostgreSQL. MySQL وSQL Server غير مدعومتين.

الإصدار 0.1.0 غير منشور بعد. ابنِه محليًا بالأمر `./gradlew check` إلى أن يُنشر.

## إلى أين تذهب بعد ذلك

| تريد أن | اقرأ |
|---|---|
| تثبّت المكتبة وتشغّل أول استعلام | [البدء](getting-started.md) |
| تفتح اتصالات وتشغّل معاملات وتراقب الاستعلامات وتضبط pool (مجمّع الاتصالات) | [الاتصالات والمعاملات](connections.md) |
| تقرأ الصفوف وتكتبها بـ `where` و`join` و`paginate` | [Query builder](query-builder.md) |
| تنشئ الجداول وتعدّلها | [Schema](schema.md) |
| تدير إصدارات المخطط | [Migrations](migrations.md) |
| تعمل بأصناف بدل الصفوف | [Models](models.md) و[Relations](relations.md) |
| تشغّل على هاتف | [Android](android.md) |
| تعرف أين تختلف Diwan عن Laravel | [الفروق عن Laravel](differences.md) |
| تلتقط الأخطاء وتفهمها | [الأخطاء](errors.md) |
| تبحث عن صنف أو دالة | [مرجع API](api.md) |
| تنتقل بين الإصدارات | [الترقية](upgrade.md) |
| تفهم مصطلحًا | [المسرد](glossary.md) |
