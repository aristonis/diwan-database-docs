# مرجع الـ API

Javadoc (توثيق الواجهة المولَّد من تعليقات Java) لكل صنف عام موجود على javadoc.io، على العنوان
`https://javadoc.io/doc/org.aristonis/diwan-database/0.2.0` (صفحة لكل وحدة). ويمكنك أيضًا بناؤه من المستودع بالأمر `./gradlew javadoc`.

كل الوحدات (modules) تستعمل المجموعة `org.aristonis` والإصدار `0.2.0`. والحزم تحت `org.aristonis.diwan.database`.

| الوحدة (artifact) | أضفها حين | أهم الأصناف |
|---|---|---|
| `diwan-database` | دائمًا | `Connection` و`TransactionScope` و`Migrator` و`Migration` و`Schema` و`Blueprint` و`QueryFactory` و`Builder` و`QueryCursor` و`DatabaseManager` |
| `diwan-database-sqlite` | تستعمل SQLite أو Android | `SQLiteSchema.of(db)` و`SQLiteQuery.of(db)` |
| `diwan-database-pgsql` | تستعمل PostgreSQL | `PostgresSchema.of(db)` و`PostgresQuery.of(db)` و`PostgresMigrationLock` |
| `diwan-database-android` | تعمل على Android | `AndroidSqliteDriver` و`AndroidConnector` |
| `diwan-database-eloquent` | تستعمل النماذج | `Model` و`ModelQuery` و`EloquentBuilder` و`ModelCollection` و`Scope` و`ModelObserver` و`Casts` و`RelationMap` |

## الحزم

| الحزمة | المحتوى |
|---|---|
| `org.aristonis.diwan.database` | `Connection` و`ConnectionBuilder` و`TransactionScope` و`LoggedQuery` و`QueryException` |
| `...database.driver` و`...database.jdbc` | واجهة الـ driver (مشغّل) ومحوّل JDBC (واجهة Java للاتصال بقواعد البيانات) |
| `...database.schema` | `Schema` و`Blueprint` و`ColumnDefinition` و`ForeignKeyDefinition` |
| `...database.migrations` | `Migration` و`Migrator` و`MigrationChecksum` و`MigrationResult` |
| `...database.query` | `QueryFactory` و`Builder` و`JoinClause` و`LengthAwarePage` و`SimplePage` و`CursorPage` و`Cursor` |
| `...database.manager` و`...database.config` | `DatabaseManager` و`DatabaseConfig` ومصادر الإعداد |
| `...database.eloquent` | `Model` و`ModelQuery` و`EloquentBuilder` و`ModelCollection` و`ModelPage` |
| `...database.eloquent.casts` | `Cast` و`Casts` و`CastMap` |
| `...database.eloquent.json` | `JsonCodec` |
| `...database.eloquent.relations` | `HasOne` و`HasMany` و`BelongsTo` و`BelongsToMany` و`HasManyThrough` و`MorphTo` و`Pivot` و`MorphMap` |

الأصناف في الحزم المسمّاة `internal` ليست جزءًا من الـ API العام.

## أين يُشرح كل موضوع

- الاتصال والمعاملات: [الاتصالات](connections.md)
- الاستعلامات: [Query builder](query-builder.md)
- الجداول: [Schema builder](schema.md) و[التهجيرات](migrations.md)
- النماذج: [النماذج](models.md) و[العلاقات](relations.md)
- الإخفاقات: [الأخطاء](errors.md)
