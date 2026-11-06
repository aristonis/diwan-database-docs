# القواعد

هذه قواعد `ai/AGENTS.md`، لكل قاعدة سببها والصفحة التي تشرحها.

## افعل دائمًا

| القاعدة | السبب | اقرأ |
|---|---|---|
| أغلق `QueryCursor` بـ try-with-resources (بنية Java لإغلاق المورد تلقائيًا). | الـ cursor الذي لم يُقرأ حتى النهاية يمسك اتصاله من الـ pool (المجمّع). وعلى PostgreSQL يترك الجلسة معلّقة داخل transaction. والـ `stream()` لا يحرر الاتصال إلا إذا أُغلق. | [باني الاستعلامات](../query-builder.md) |
| قارن عمود الترتيب القادم من المستخدم بـ allowlist (قائمة مسموحة). | تُقتبس أسماء الأعمدة والاتجاهات كمعرّفات ولا تُربط كقيم، فلا يستطيع الباني تأمينها. | [باني الاستعلامات](../query-builder.md) |
| شغّل row locks (أقفال الصفوف) داخل transaction فقط. | PostgreSQL يرمي `IllegalStateException` عند select بقفل خارجها. | [باني الاستعلامات](../query-builder.md) |
| مرّر القيم كـ bindings (معاملات مربوطة) عبر `whereRaw(sql, bindings)` و`selectRaw(sql, bindings)`. | تبقي الـ bindings البيانات خارج نص SQL. | [باني الاستعلامات](../query-builder.md) |
| صرّح بـ `checksum()` في كل migration وأعطه `name()` ثابتًا. | بدونه يمرّ تعديل migration نُفّذ دون أن يلاحظه أحد. والاسم المأخوذ من اسم الصنف يتغيّر تحت R8. | [التهجيرات](../migrations.md) |
| عرّف النماذج بـ `public static final ModelQuery<T> query`. | هي نقطة الدخول الوحيدة لكل نموذج، بلا reflection (انعكاس)، فتعمل على Android. | [النماذج](../models.md) |
| استعمل `tx` داخل `db.transaction(tx -> ...)`. | أي استدعاء على الاتصال الجذر سيجري خارج التراجع. | [الاتصالات](../connections.md) |
| على Android سمِّ الجداول ومفاتيح العلاقات صراحةً، أو أبقِ أسماء النماذج. | R8 قد يعيد تسمية الأصناف، والقيم الافتراضية تُشتق من أسماء الأصناف. | [Android](../android.md) |
| أبقِ transaction والـ cursor في Android على thread (خيط تنفيذ) واحد. | Android يربطهما بالـ thread الذي فتحهما، وDiwan ترفض الـ commit من thread آخر. | [Android](../android.md) |

## لا تفعل أبدًا

| القاعدة | السبب | اقرأ |
|---|---|---|
| لا تبنِ SQL بضمّ نصوص فيها مدخلات المستخدم. | هذا SQL injection (حقن SQL). الدوال الخام تأخذ نص SQL كما هو. | [باني الاستعلامات](../query-builder.md) |
| لا تعدّل migration نُفّذ سابقًا. | السجل وقاعدة البيانات لا يتطابقان بعدها. أضف migration جديدًا. واستعمل `repairChecksums` فقط بعد تعديل قصدته. | [التهجيرات](../migrations.md) |
| لا تستدعِ `upsert` (إدراج أو تحديث عند التعارض) على SQLite أقدم من 3.24. | يرمي `UnsupportedOperationException`. وهذا يعني Android API 28 و29. | [Android](../android.md) |
| لا تستعمل reflection أو annotations (وسومًا) لتسجيل النماذج أو العلاقات أو التهجيرات. | Diwan لا تمسح شيئًا. يجب أن يكون الاسم في `relations()` أو `casts()` أو `accessors()` أو قائمة الـ migrations. | [العلاقات](../relations.md) |
| لا تستدعِ الاتصال الجذر داخل transaction مفتوحة عليه؛ مرّر `tx` بدلًا منه. | الـ strict transactions (المعاملات الصارمة) ترفض الاستدعاء. سيكتب خارج التراجع وقد يسبب deadlock (تعانقًا) في pool صغير. | [الاتصالات](../connections.md) |
| لا تسجّل سلاسل اتصال فيها كلمات مرور ولا bindings فيها بيانات شخصية. | السجلات والـ issues (بلاغات المشكلات) تُشارك مع آخرين. | [الإبلاغ عن مشكلة](report-issue.md) |

انظر أيضًا [الأخطاء والاستثناءات](../errors.md) لشكل كل فشل.
