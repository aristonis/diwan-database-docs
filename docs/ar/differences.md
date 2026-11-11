# الفروق عن Laravel

تحافظ Diwan على أسماء دوال Laravel حيث تُقرأ جيدًا في Java. تسرد هذه الصفحة المواضع التي تتصرف فيها بشكل مختلف عن قصد.
كل صف قرار مقصود، وليس ميزة ناقصة.

## اللغة وأشكال القيم المُرجَعة

| Laravel | Diwan |
|---|---|
| `null` أو `false` لـ "غير موجود" | `Optional` من `find` و`first` و`selectOne` و`scalar`؛ و`findOrFail` ترمي استثناءً |
| تواريخ PHP وحروف الصيغ (`Y-m-d`) | `java.time` وأنماط `DateTimeFormatter` (`yyyy-MM-dd`) |
| الصفوف مصفوفات | الصفوف maps غير قابلة للتعديل بترتيب الـ select |
| `getColumns` تعيد مصفوفات | `getColumns` تعيد كائنات `ColumnInfo` مكتوبة النوع |
| القراءة الكسولة تعمل من أي قراءة خاصية | `getAttribute("posts")` لا تحمّل علاقة أبدًا؛ استعمل `related` أو `relatedMany` |
| العلاقات تُوجد باسم الدالة | دالة مكتوبة النوع مع مدخل في `RelationMap`، فلا يكسرها R8 (أدوات تصغير الكود وتشويشه في Android) |
| أسماء morph والـ global scope تُخمَّن من call stack أو من closure | تمرّر الاسم بنفسك |

## الاتصالات والاستعلامات

| Laravel | Diwan |
|---|---|
| callback (دالة يستدعيها النظام) المعاملة يستطيع استعمال أي اتصال | معاملات صارمة (strict): الاتصال الخارجي يرفض الاستدعاءات من داخل معاملته؛ استعمل `tx` الذي أُعطيته |
| قيم الـ bindings تظهر في رسائل الأخطاء | مخفية افتراضيًا؛ فعّل `showBindingsInErrors` |
| `upsert` بقائمة تحديث فارغة تنفّذ إدراجًا عاديًا | تترك الصف المتعارض كما هو |
| `lock('lock in share mode')` نص خام | `LockStrength` و`LockWait` المكتوبان فقط |
| `paginate` يعدّ كل صف في استعلام `distinct` | يعدّ الصفوف المميّزة |
| `cursor()` تعيد lazy collection | `QueryCursor` تغلقه أنت؛ والذي لا يُغلق يحتفظ باتصاله |
| رموز الـ cursor (مؤشر يقرأ الصفوف واحدًا واحدًا) والصفحات مسؤوليتك | الرموز غير موقّعة؛ المزوَّر منها لا يحقن SQL لكنه قد يطلب صفوفًا أخرى مسموحة |
| `chunk` على جدول يكبر | التقسيم بالـ offset (إزاحة) نفسه، فاستعمل `chunkById` |
| جملة فاشلة في معاملة PostgreSQL تعطي خطأ الخادم 25P02 في التالية | يرفض Diwan بنفسه الجملة التالية أو الـ commit أو تحرير الـ savepoint، برسالة تطلب التراجع |
| `whereRaw('? is null', ...)` بعلامة `?` وحدها | على PostgreSQL يحتاج `? is null` إلى cast، مثل `?::text is null`، لأن الخادم لا يعرف نوع العلامة |
| قراءة `NaN` من numeric غير معالجة | عمود numeric في PostgreSQL فيه NaN أو Infinity يفشل بخطأ يسمّي العمود؛ أما أعمدة `float` و`double` فتعيد NaN |

## النماذج

| Laravel | Diwan |
|---|---|
| البيانات المخزَّنة التالفة تُقرأ `null` أو `0` أو `true` | `InvalidCastException` تسمّي النموذج والمفتاح والـ cast (تحويل نوع قيمة الـ attribute عند القراءة والكتابة) |
| فحص التغيّر في JSON والأعداد العشرية فضفاض | JSON بالبنية، والأعداد العشرية ضمن 4 ULP، واللحظات كـ instants |
| `delete()` على نموذج غير موجود في القاعدة | تعيد `false` |
| `increment` على نموذج غير موجود في القاعدة | مرفوضة |
| `saveOrFail` | تحفظ في transaction (معاملة) خاصة وترمي حين لا يكون لنموذج غير تلقائي المفتاح ما يُدرَج |
| الكتابة عبر علاقة من أب بلا مفتاح تكتب مفتاحًا فارغًا | `IllegalStateException` قبل أي SQL |
| التحميل المسبق يقرأ المفاتيح الفارغة كـ `0` | تُهمَل المفاتيح الفارغة |
| `with` على العلاقة نفسها مرتين تُبقي آخر قيد | تنفّذ القيدين معًا |
| قيد التحميل المسبق قد يستعمل `limit` | مرفوض، لأنه سيقطع صفوف كل الآباء معًا |
| listener (مستمع للأحداث) يعيد `true` يُسكت الـ listeners اللاحقة | `false` وحدها توقف |
| `withoutEvents` تكتم كل الـ threads | تكتم الـ thread (خيط تنفيذ) المستدعي فقط، وتبقى hooks النموذج نفسه تعمل |
| الـ global scopes ترثها الأصناف الفرعية | لكل صنف الـ scopes المسجَّلة على `ModelQuery` الخاص به |
| `forceDelete()` على builder تتخطى كل global scope | تتخطى scope الحذف الناعم فقط |
| morph map اختيارية | إلزامية ما لم تستدع `requireMorphMap(false)` |
| `oldestOfMany` قد تعيد أعلى مفتاح بين المتعادلين | تعيد الأدنى |

## فحص المخطط

| Laravel | Diwan |
|---|---|
| `getColumns` تسرد الأعمدة المخفية للجدول الافتراضي (virtual table) | لا تُسرد |
| `hasIndex` تقبل نوع طريقة الفهرس مثل `btree` | لا نوع طريقة: SQLite لا تملك واحدًا. وبدلًا منه يرشّح enum اسمه `IndexType` (`PRIMARY` و`UNIQUE`) |

## تعديل المخطط

| Laravel | Diwan |
|---|---|
| `foreignIdFor($model)` تقبل نموذجًا أو اسم صنف | `foreignIdFor` تأخذ `ForeignKeySource`، و`ModelKeys.of(User.class)` تبني واحدًا من نموذج |
| `foreignIdFor` على نموذج مفتاحه نصي تُنشئ عمود `uuid` | `ModelKeys` ترفض أي مفتاح ليس عددًا صحيحًا ولا UUID ولا ULID برمي `IllegalArgumentException` |
| `comment()` على الجدول تكتب تعليقه على PostgreSQL وMySQL، وليس لـ grammar الـ SQLite كود له | تكتبه PostgreSQL. وتتخطاه SQLite وAndroid بلا خطأ، كما يفعل Laravel. وMySQL غير مدعومة |
| `temporary()` تعمل على SQLite وPostgreSQL، ولا يتحقق grammar الـ SQLite من الجدول المؤقت عند تغييره | تعمل `schema.table` على جدول مؤقت في SQLite للإضافات البسيطة؛ ويُرفض التغيير الذي يحتاج إعادة بناء الجدول برمي `IllegalStateException` |
| `createDatabase($name)` على PostgreSQL تضيف `encoding` من إعداد `charset` في الاتصال حين يكون مضبوطًا | لا توجد جملة encoding. تأخذ قاعدة البيانات الجديدة الترميز الافتراضي للخادم، أو ترميز القالب حين تنسخه |
| `createDatabase($name)` على SQLite تكتب ملفًا فارغًا، فيستبدل الملف الموجود | تفشل إذا كان الملف موجودًا، ولا تستبدله أبدًا |
| `dropDatabaseIfExists($name)` على SQLite تعيد `true` حين لا يوجد ملف، وتحذف الملف الرئيسي وحده | تعيد `false` حين لا يوجد ملف، وتحذف أيضًا ملفات `-wal` و`-shm` و`-journal` |

## إضافات Diwan

لا يملك Laravel أيًّا منها:

- الفهارس الجزئية: `where` و`whereNull` و`whereNotNull` على الفهرس.
- ترتيب الفهرس والـ collation: `asc` و`desc` و`collate` على الفهرس.
- `DiwanError.table()`، أي الجدول الذي يخصّه الفشل.
- `QueryFactory.restartIdentities(tables)` و`RefreshDatabase.rollback(...).restartingIdentities()`، وهما يعيدان عدّادات الهوية (identity) والـ `serial` في PostgreSQL إلى بدايتها، فترى اختبارات وضع rollback الأرقام نفسها في كل تشغيل. مصدر Laravel لا يحوي إعادة ضبط لكل اختبار: فالـ `setval` الوحيد فيه يضبط قيمة البداية عند إنشاء الجدول فقط.
- `createDatabase(name, template)` و`createDatabase(name, template, CopyStrategy)`، وهما تنسخان قاعدة بيانات. يحدد `CopyStrategy` (`FILE_COPY` أو `WAL_LOG`) طريقة النسخ في PostgreSQL 15 وما بعده. لا يملك Laravel وسيطة للقالب.
- `dropDatabaseIfExists(name, force)`، وتنهي الجلسات المتصلة بقاعدة البيانات أولًا في PostgreSQL 13 وما بعده. لا يملك Laravel خيار force.
- `RefreshDatabase.template(...)`، وهو وضع اختبار يحصل فيه كل اختبار على نسخة خاصة به من قالب طُبِّقت عليه الـ migrations، فيجوز له التثبيت الفعلي والعمل بالتوازي. لا يملك Laravel وضع اختبار من هذا النوع.

## ليس في 0.2.0

- أصناف أحداث مخصّصة، وأسماء أحداث نصية، وlisteners بالنمط العام (wildcard).
- `ObservedBy`؛ سجّل observer (مراقب لأحداث النموذج) بـ `observe`.
- MySQL وSQL Server وقواعد البيانات الأخرى. المدعوم: SQLite وPostgreSQL وAndroid.

انظر أيضًا [النماذج](models.md) و[العلاقات](relations.md) و[Query builder](query-builder.md).
