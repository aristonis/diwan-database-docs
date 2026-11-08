# Schema builder

الـ `Schema` تنشئ الجداول وتغيّرها. تصف الجدول داخل callback (دالة يستدعيها النظام) على `Blueprint` (مخطط الجدول)، ثم تحوله الـ grammar (قواعد توليد SQL الخاصة بكل قاعدة بيانات) الخاصة بقاعدة بياناتك إلى SQL.

```java
Schema schema = manager.schema();      // the default connection; manager.schema("cache") for another
```

المتغير `manager` هو الـ `DatabaseManager` من صفحة [الاتصالات والمعاملات](connections.md). تُبنى الـ `Schema` من إعداد الاتصال، فلا يذكر كودك أي صنف driver. بدون manager استعمل وحدة الـ grammar: `SQLiteSchema.of(connection)`، أو `PostgresSchema.of(connection)` مع PostgreSQL.

## الإنشاء والتعديل والحذف

```java
schema.create("users", table -> {
    table.id();
    table.string("email").unique();
    table.booleanColumn("active").defaultValue(true);
    table.enumColumn("role", List.of("admin", "member")).defaultValue("member");
    table.rememberToken();
    table.softDeletes();
    table.timestamps();
});

schema.table("users", table -> table.text("bio").nullable());   // add a column
schema.rename("users", "people");
schema.dropIfExists("people");                                  // drop(...) fails if it is missing
```

الدالتان `create` و`table` تأخذان `Consumer<Blueprint>`. حين يحتاج استدعاء واحد إلى عدة جمل (جدول مع unique index)، تنفذها SQLite داخل transaction (معاملة) واحدة، فلا يبقى شيء ناقص عند الفشل. بادئة الجداول (table prefix) في الاتصال توضع قبل كل جدول وكل اسم index مولَّد.

## أنواع الأعمدة

الأسماء التي تتعارض مع كلمات Java المحجوزة لها لاحقة: `booleanColumn` و`floatColumn` و`doubleColumn` و`charColumn` و`enumColumn`. و`default` في Laravel هي `defaultValue`.

| المجموعة | الدوال |
|---|---|
| المفاتيح | `id`, `increments`, `bigIncrements`, `foreignId`, `foreignUuid`, `foreignUlid` |
| الأعداد الصحيحة | `tinyInteger`, `smallInteger`, `mediumInteger`, `integer`, `bigInteger` وصيغ `unsigned*` |
| الأعداد | `decimal(column, total, places)`, `floatColumn`, `doubleColumn` |
| النصوص | `string(column[, length])`, `charColumn`, `text`, `mediumText`, `longText` |
| التواريخ والأوقات | `date`, `dateTime`, `time`, `timestamp`, صيغ `*Tz`, `year`, `instant` |
| أخرى | `booleanColumn`, `json`, `jsonb`, `binary`, `uuid`, `ulid`, `ipAddress`, `macAddress`, `enumColumn`, `set` |
| اختصارات | `timestamps`, `softDeletes`, `rememberToken`, عائلة `morphs` |

العمود `instant` يخزن microseconds كاملة على SQLite و`timestamptz` على PostgreSQL، وتحوّل بـ `Instants.toMicros` و`Instants.read`. SQLite ليس فيها ما يشبه `set`، فترفض هذا النوع.
في النموذج اكتب العمود `instant` عبر `Casts.instant()`. أما أعمدة الطوابع (`created_at` و`updated_at` و`deleted_at`) فاضبط `TimestampFormat.INSTANT` على النموذج بدلًا من ذلك. انظر [النماذج](models.md#accessors-casts).

## المعدّلات (Modifiers)

```java
table.string("slug", 120).nullable().unique();
table.timestamp("seen_at").useCurrent();
table.integer("qty").check("qty > 0");
table.integer("total").storedAs("qty * price");
```

الشائعة منها `nullable` و`defaultValue` و`useCurrent` و`unique` و`index` و`primary` و`autoIncrement` و`unsigned` و`comment` و`virtualAs` و`storedAs`. SQLite تتجاهل `unsigned` و`comment`. وتضيف عمودًا `not null` بلا قيمة افتراضية فقط ما دام الجدول فارغًا. والـ enum على SQLite يرفض أي قيمة خارج قائمته، ويحافظ على هذه القاعدة عبر إعادات بناء الجدول اللاحقة.

### الـ Collation (قواعد مقارنة النص)

يمكن لعمود نصي أن يحدد الـ collation الذي تُقارن به قيمه وتُرتَّب. `Collation.BINARY` هو collation المقارنة بالبايتات، وهو قابل للنقل بين قواعد البيانات. تكتبه PostgreSQL على هيئة `"C"` وتكتبه SQLite على هيئة `BINARY`، فيعطي migration واحد الترتيب نفسه على الاثنتين.

```java
table.string("code").collation(Collation.BINARY);
table.string("name").collation("nb_NO.utf8");    // the database's own name, written as given
schema.table("codes", table -> table.string("code").collation(Collation.BINARY).change());
```

الاسم المعطى نصًا يُكتب كما هو، فيجب أن يكون collation تعرفه قاعدة البيانات. ولا يجوز أن يحوي علامة اقتباس أو حرف تحكم. على SQLite تحتفظ إعادة بناء الجدول بالـ collation الخاص بالعمود. أما `COLLATE` داخل قيد جدول، مثل `unique (email collate nocase)`، فما زال مرفوضًا.

### تغيير عمود

`change()` تعيد تعريف العمود. كما في Laravel 11 وما بعدها، التعريف الجديد يحل محل القديم بالكامل، فأعد ذكر كل معدّل تريد الإبقاء عليه.

```java
schema.table("posts", table -> table.string("title", 500).nullable().change());
```

تغيير عمود auto-increment (ترقيم تلقائي) غير مدعوم. على SQLite، أعد تسمية أو احذف عمودًا تشير إليه جداول أخرى في استدعاء `schema.table` منفصل عن `change()`. العمود الذي ما زال index أو مفتاح يستخدمه لا يمكن حذفه، فاحذف الـ index أو المفتاح أولًا، وفي الاستدعاء نفسه إن شئت.

## الفهارس (Indexes)

```java
table.index("user_id", "title");                  // columns in order
table.index(List.of("state", "next_fire_at"), "alarms_state_next");   // named index
table.unique(List.of("slug", "tenant_id"), "posts_slug_tenant");
table.primary("a", "b");
table.dropIndex("posts_user_id_title_index");
table.dropUnique(List.of("slug"));
table.renameIndex("old_name", "new_name");
```

## المفاتيح الأجنبية (Foreign keys)

```java
table.foreignId("user_id").constrained().cascadeOnDelete();     // points at users.id
table.foreignId("editor_id").nullable().constrained("users").nullOnDelete();

table.foreign("order_id").references("id").on("orders").onDelete(ForeignKeyAction.CASCADE);
table.dropForeign(List.of("order_id"));
table.dropConstrainedForeignId("user_id");                       // key, index and column
```

إجراءات الحذف والتحديث هي `cascade` و`restrict` و`set null` و`no action`، ولكل منها دالة تبدأ بـ `on...`.

تحدد PostgreSQL طول الاسم بـ 63 بايتًا، وقد يتجاوز الاسم الافتراضي لمفتاح على جدول طويل الاسم هذا الحد. سمِّ المفتاح بنفسك بالوسيط الثالث لـ `constrained`، أو بالوسيط الثاني لـ `references`:

```java
table.foreignId("attribute_id").constrained("product_attribute_values", "id", "pav_attribute_fk");
table.foreignId("attribute_id").references("id", "pav_attribute_fk").on("product_attribute_values");
```

## قيود check والأعمدة المولَّدة وSQL الخام

```java
schema.create("lines", table -> {
    table.id();
    table.integer("qty").check("qty > 0");
    table.integer("price");
    table.integer("total").storedAs("qty * price");
    table.check("lines_price_check", "price >= 0");
});
schema.statement("create index lines_total on lines (total)");
```

الـ SQL الذي تعطيه لـ `check` و`storedAs` و`virtualAs` و`rawColumn` و`statement` يدخل الجملة كما كُتب. ابنِه من ثوابت، لا من مدخلات المستخدم. أسماء الجداول والأعمدة حالة مختلفة: علامات الاقتباس داخل الاسم تُهرَّب، ولا يُرفض إلا الاسم الفارغ والاسم الذي فيه محارف تحكم. استخدم `schema.driverName()` (تعيد `"sqlite"` أو `"pgsql"`) حين يختلف الـ SQL الخام بين القواعد.

## إعادة بناء الجدول على SQLite

SQLite لا تستطيع إضافة primary key (مفتاح أساسي) أو foreign key (مفتاح أجنبي) إلى جدول موجود أو حذفه منه. لذلك يعيد Diwan بناء الجدول ويحتفظ بصفوفه وفهارسه وعدّاد auto-increment. إذا خالف صف المفتاح الجديد، لا يتغير شيء وتذكر `ForeignKeyCheckException` الجداول وعدد الصفوف.

داخل transaction فتحتها بنفسك، لا يُعاد بناء جدول تشير إليه جداول أخرى (`ForeignKeysOffRequiredException`). نفّذ هذا التغيير في [migration](migrations.md) أو داخل `schema.withoutForeignKeyConstraints(s -> ...)`.

## فحص ما هو موجود

```java
boolean hasUsers = schema.hasTable("users");
boolean hasBio = schema.hasColumn("users", "bio");

for (IndexInfo index : schema.indexes("posts")) {
    System.out.println(index.name() + " " + index.columns() + " unique=" + index.isUnique());
}
for (ForeignKeyInfo key : schema.foreignKeys("posts")) {
    System.out.println(key.columns() + " -> " + key.foreignTable() + key.foreignColumns());
}
```

### سرد كل شيء وحذفه

```java
List<TableInfo> tables = schema.getTables();        // name and schema, ordered by schema, then name
List<String> names = schema.getTableListing();      // names only
List<ViewInfo> views = schema.getViews();

schema.dropAllViews();
schema.dropAllTables();
```

الصنفان `TableInfo` و`ViewInfo` قيمتان غير قابلتين للتعديل فيهما `name()` و`schema()`. الجداول الداخلية لا تُسرد: جداول `sqlite_` و`android_metadata` وجداول FTS المساعدة على SQLite وAndroid، و`spatial_ref_sys` على PostgreSQL. يعيد السرد أسماء الجداول الحقيقية بما فيها بادئة الجداول (table prefix) في الاتصال، كما في Laravel. وعلى SQLite الأقدم من 3.37 تُخفى أيضًا الجداول المساعدة لـ FTS3-5 وR-Tree.

- **PostgreSQL:** جداول الـ schemas الموجودة في `search_path`، وتُحذف بعبارة واحدة `drop table ... cascade`. يبقى `spatial_ref_sys`. وإن لم يكن هناك ما يُحذف فلا تُنفَّذ أي عبارة. الأنواع (types) والـ sequences والدوال لا تُحذف.
- **SQLite وAndroid:** يُحذف كل جدول، الأبناء أولًا، فلا تمنع المفاتيح الأجنبية الحذف. تُتخطى جداول FTS المساعدة، ويبقى `android_metadata`.

الدالة `Migrator.fresh()` تستعمل هذه الاستدعاءات: انظر [الـ Migrations](migrations.md#start-from-scratch).

## معاينة الـ SQL

```java
List<LoggedQuery> plan = schema.pretend(s -> s.create("t", table -> table.id()));
```

`pretend` تسرد الجمل ولا تغير شيئًا. هي تقرأ الجداول الحية، فتعرض إعادة البناء بجملها الحقيقية، لكن الجدول الذي أُنشئ قبلها في نفس تشغيل pretend (وضع المعاينة دون تنفيذ) لا يكون موجودًا بالنسبة لها. و`hasTable` و`hasColumn` تعيدان `false` في وضع pretend.

داخل transaction (معاملة) استدعِ `schema.on(tx)` حتى يعمل العمل على المعاملة: `schema.on(tx).create(...)`.

التالي: [Migrations](migrations.md).

## مرجع الدوال

الدوال العامة التي لا تغطيها الأقسام السابقة، بصف واحد لكل اسم دالة (الـ overloads في صف واحد).

| الدالة | على | ماذا تفعل | مثال |
|---|---|---|---|
| `connection` `grammar` | `Schema` | على `Schema`: الاتصال الذي يعمل عليه والـ grammar الذي يبني الـ SQL. | `schema.connection()` |
| `commands` `isCreating` | `Blueprint` | على `Blueprint`: الأوامر بالترتيب الذي يبنيه الـ grammar، وهل ينشئ الـ blueprint جدوله. | `table.isCreating()` |
| `tinyIncrements` `smallIncrements` `mediumIncrements` `integerIncrements` | `Blueprint` | مفاتيح أساسية صحيحة موجبة ذاتية الزيادة بحجم 8 و16 و24 و32 بت. | `table.smallIncrements("id")` |
| `unsignedTinyInteger` `unsignedSmallInteger` `unsignedMediumInteger` `unsignedInteger` `unsignedBigInteger` | `Blueprint` | أعمدة أعداد صحيحة موجبة بحجم 8 و16 و24 و32 و64 بت. | `table.unsignedInteger("views")` |
| `tinyText` | `Blueprint` | تضيف عمود نص قصير. | `table.tinyText("note")` |
| `timeTz` `timestampTz` `dateTimeTz` | `Blueprint` | أعمدة وقت من اليوم وطابع زمني وتاريخ ووقت مع المنطقة الزمنية. | `table.timestampTz("seen_at")` |
| `nullableTimestamps` `datetimes` `timestampsTz` | `Blueprint` | عمودا `created_at` و`updated_at` القابلان لـ null: مثل `timestamps()` (`nullableTimestamps`)، أو كأعمدة تاريخ ووقت (`datetimes`)، أو مع المنطقة الزمنية (`timestampsTz`). | `table.timestampsTz()` |
| `softDeletesTz` `softDeletesDatetime` | `Blueprint` | عمود `deleted_at` القابل لـ null للحذف الناعم، مع المنطقة الزمنية أو كعمود تاريخ ووقت. | `table.softDeletesTz()` |
| `numericMorphs` `nullableNumericMorphs` `nullableMorphs` `uuidMorphs` `nullableUuidMorphs` `ulidMorphs` `nullableUlidMorphs` | `Blueprint` | أعمدة علاقة polymorphic: `_type` و`_id` بمعرّف رقمي أو UUID أو ULID وفهرس عليهما. صيغ `nullable` تسمح بـ null. | `table.nullableMorphs("taggable")` |
| `dropColumn` `renameColumn` | `Blueprint` | حذف أعمدة، أو إعادة تسمية عمود. | `table.renameColumn("a", "b")` |
| `dropPrimary` `dropCheck` | `Blueprint` | حذف المفتاح الأساسي، أو قيد CHECK مسمّى. | `table.dropCheck("age_check")` |
| `dropMorphs` `dropRememberToken` `dropSoftDeletes` `dropSoftDeletesTz` `dropTimestamps` `dropTimestampsTz` | `Blueprint` | حذف ما أضافته الدالة المقابلة: علاقة polymorphic (الفهرس ثم العمودان)، أو `remember_token`، أو `deleted_at`، أو `created_at` و`updated_at`. | `table.dropTimestamps()` |
| `type` `length` `places` `precision` `total` `allowed` `checks` `rawDefinition` | `ColumnDefinition`, `ForeignIdColumnDefinition` | قراءة تعريف عمود: نوعه، وطول النص، والخانات بعد الفاصلة والدقة أو إجمالي الخانات للعشري، والقيم التي يسمح بها enum أو set، وشروط CHECK، وSQL النوع الخام. | `column.type()` |
| `isNullable` `isNotNullStated` `isUnsigned` `isAutoIncrement` `isPrimary` `isIndexed` `isChange` `isGenerated` `usesCurrent` | `ColumnDefinition`, `ForeignIdColumnDefinition` | قراءة علامات عمود: يسمح بـ NULL، أو استُدعيت `nullable(false)`، وهل هو unsigned، وهل يزداد تلقائيًا، وهل هو المفتاح الأساسي وحده، وهل له فهرس عادي، وهل يعيد تعريف عمود موجود (`change()`)، وهل تحسبه قاعدة البيانات، وهل استُدعيت `useCurrent()`. | `column.isNullable()` |
| `onUpdate` `cascadeOnUpdate` `restrictOnUpdate` `noActionOnUpdate` `nullOnUpdate` `restrictOnDelete` `noActionOnDelete` | `ForeignKeyDefinition` | إجراءات المفتاح الأجنبي: `onUpdate` تحدد ما يحدث عند تغيّر المفتاح المرجعي، والاختصارات تعمل cascade أو restrict (الرفض) أو الرفض في نهاية الجملة (`noAction...`) أو ضبط NULL. | `fk.restrictOnDelete()` |
| `deleteAction` `updateAction` `referencedTable` `referencedColumns` | `ForeignKeyDefinition` | قراءة تعريف مفتاح أجنبي: إجراء الحذف والتحديث إن ضُبط، والجدول المرجعي، والأعمدة المرجعية. | `fk.referencedTable()` |
| `on` | `Schema` | تعيد باني الـ schema هذا مربوطًا باتصال آخر لقاعدة البيانات نفسها، مثل اتصال معاملة. وترمي `IllegalArgumentException` مع نوع آخر من قواعد البيانات. | `schema.on(tx)` |
| `collation` | `ColumnDefinition` و`ForeignIdColumnDefinition` | تضبط الـ collation لعمود نصي، يُعطى على هيئة `Collation` أو اسم collation في قاعدة البيانات. وعلى `ColumnDefinition` تعيده `collation()` بلا وسيط على هيئة `Optional`. | `column.collation(Collation.BINARY)` |
| `of` `name` `isPortable` | `Collation` | `of` تنشئ collation تعرفه قاعدة البيانات باسمه. و`name` تعيد الاسم، و`isPortable` تبيّن هل القيمة هي `Collation.BINARY`. | `Collation.of("nb_NO.utf8")` |
