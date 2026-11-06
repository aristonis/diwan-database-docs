# الإبلاغ عن مشكلة

بلّغ عن خلل في المكتبة على https://github.com/aristonis/diwan-database/issues. رابط المستودع يعمل حين يصبح المشروع عامًا.

## قبل أن تبلّغ

1. راجع الدليل الخاص بالميزة. بعض السلوك مذكور في [الفروق عن Laravel](../differences.md) أو [الأخطاء والاستثناءات](../errors.md).
2. اختصر الفشل إلى أصغر كود يفشل، على قاعدة بيانات فارغة.

## القالب

```markdown
**Diwan version:**
**Module:** (core, sqlite, pgsql, eloquent or android)
**Database and version:** (for example SQLite 3.45, PostgreSQL 16)
**Java version or Android API level:**

**Minimal code:**

**Full error, with the cause chain ("Caused by: ..."):**

**Expected:**

**Actual:**
```

الخطأ الكامل مهم. الرسالة العليا وحدها كثيرًا ما تخفي خطأ قاعدة البيانات تحتها. وسلسلة الأسباب (cause chain) هي أسطر `Caused by:` في أثر المكدس.

## لا تضمّن أبدًا

- الأسرار والـ tokens ومفاتيح الـ API.
- سلاسل الاتصال التي فيها كلمات مرور.
- قيم الـ bindings التي فيها بيانات شخصية. استبدل بها قيمًا بديلة.
- مشروعك كله. المثال الأدنى أسرع إصلاحًا.

## قدّمه بـ GitHub CLI

اكتب البلاغ في ملف ثم:

```bash
gh issue create --repo aristonis/diwan-database \
  --title "paginate returns the wrong total with a group by" \
  --body-file issue.md
```

يستطيع الـ agent فعل ذلك بمهارة `diwan-report-issue`. تجمع المهارة الإصدار والمنصة وتكتب الملف وتطلب منك مراجعته قبل أن تقدّمه. انظر [المهارات](skills.md).
