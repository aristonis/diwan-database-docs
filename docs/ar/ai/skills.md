# المهارات

المهارة (skill) مجلد فيه ملف `SKILL.md` واحد. في رأسه (frontmatter، وهو كتلة YAML في أول الملف) حقلا `name` و`description`. يقرأ الـ agent الوصف ويحمّل المهارة حين تطابق المهمة، فلا تشغل خطواتها مساحة من السياق قبل الحاجة.

## المهارات

| المهارة | تُفعَّل عندما |
|---|---|
| `diwan-usage` | تضيف Diwan، أو تبني `Connection`، أو تختار SQLite أو PostgreSQL، أو تلفّ عملًا في transaction (معاملة)، أو تنقل طبقة JDBC أو SQL قائمة إلى Diwan. |
| `diwan-query-builder` | تكتب أو تراجع استعلامًا بـ `table(...)`: فلاتر، joins، ترقيم صفحات، limit وoffset، قراءة على دفعات، cursors، upsert، row locks (أقفال صفوف)، تعبيرات raw. |
| `diwan-migrations` | تنشئ جدولًا، أو تعدّل عمودًا، أو تضيف migration (تهجيرًا)، أو تملأ قاعدة ببيانات البداية (seeder)، أو تشغّل وتتراجع، أو يظهر خطأ checksum. |
| `diwan-models-relations` | تضيف model (نموذجًا) أو relation (علاقة) أو casts أو scopes أو eager loading، أو تعالج N+1. |
| `diwan-android` | تشغّل Diwan على Android، أو تضبط الـ driver، أو تتعامل مع الـ threads، أو تصغّر بـ R8، أو تصطدم بحد مستوى API. |
| `diwan-report-issue` | يفشل استدعاء في Diwan بطريقة لا تشرحها الوثائق، أو تطلب الإبلاغ عن خلل. |

لكل مهارة الأجزاء نفسها: خطوات المهمة، والواجهة الحقيقية، ومثال أدنى، وقائمة مزالق.

## التثبيت

انسخ المهارات التي تحتاجها من `ai/skills/` في مستودع الكود إلى المجلد الذي يقرأ منه الـ agent مهاراته.

```bash
# Claude Code, one project
cp -r ai/skills/* .claude/skills/

# Claude Code, every project
cp -r ai/skills/* ~/.claude/skills/
```

الوكلاء الآخرون الذين يدعمون صيغة Agent Skills لهم مجلد مهارات خاص بهم. انسخ المجلدات نفسها هناك. أبقِ كل مجلد كاملًا وفيه `SKILL.md`.

عند ترقية Diwan انسخ المهارات من جديد، فإصدارها مرتبط بالكود.

التالي: [القواعد](rules.md) للقائمة الكاملة مع الأسباب.
