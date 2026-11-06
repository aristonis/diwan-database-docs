# Schema builder

`Schema` creates and changes tables. You describe the table in a callback on a `Blueprint`, and the
grammar of your database turns it into SQL.

```java
import org.aristonis.diwan.database.schema.Schema;
import org.aristonis.diwan.database.sqlite.SQLiteSchema;     // PostgresSchema.of(db) on PostgreSQL

Schema schema = SQLiteSchema.of(db);
```

## Create, alter and drop

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

`create` and `table` take a `Consumer<Blueprint>`. When one call needs several statements (a table
and its unique index), SQLite runs them in one transaction, so a failure leaves nothing behind. The
connection's table prefix goes in front of every table and generated index name.

## Column types

Names that clash with Java keywords carry a suffix: `booleanColumn`, `floatColumn`, `doubleColumn`,
`charColumn`, `enumColumn`. Laravel's `default` is `defaultValue`.

| Group | Methods |
|---|---|
| Keys | `id`, `increments`, `bigIncrements`, `foreignId`, `foreignUuid`, `foreignUlid` |
| Integers | `tinyInteger`, `smallInteger`, `mediumInteger`, `integer`, `bigInteger` and the `unsigned*` forms |
| Numbers | `decimal(column, total, places)`, `floatColumn`, `doubleColumn` |
| Text | `string(column[, length])`, `charColumn`, `text`, `mediumText`, `longText` |
| Dates and times | `date`, `dateTime`, `time`, `timestamp`, the `*Tz` forms, `year`, `instant` |
| Other | `booleanColumn`, `json`, `jsonb`, `binary`, `uuid`, `ulid`, `ipAddress`, `macAddress`, `enumColumn`, `set` |
| Shortcuts | `timestamps`, `softDeletes`, `rememberToken`, the `morphs` family |

Diwan has no money type. Use `decimal("amount", 12, 2)` or an integer column of minor units.
`instant` stores whole microseconds on SQLite and `timestamptz` on PostgreSQL; convert with
`Instants.toMicros` and `Instants.read`. SQLite has nothing like `set`, so it refuses that type.

## Modifiers

```java
table.string("slug", 120).nullable().unique();
table.timestamp("seen_at").useCurrent();
table.integer("qty").check("qty > 0");
table.integer("total").storedAs("qty * price");
```

The common ones are `nullable`, `defaultValue`, `useCurrent`, `unique`, `index`, `primary`,
`autoIncrement`, `unsigned`, `comment`, `virtualAs` and `storedAs`. SQLite ignores `unsigned` and
`comment`. It adds a not-null column without a default only while the table is empty. An SQLite
enum refuses any value outside its list, and keeps that rule through later table rebuilds.

### Changing a column

`change()` redefines a column. As in Laravel 11 and later, the new definition replaces the old one
in full, so restate every modifier you want to keep.

```java
schema.table("posts", table -> table.string("title", 500).nullable().change());
```

Changing an auto-increment column is not supported. On SQLite, rename or drop a column that another
table references in a separate `schema.table` call from a `change()`. A column that an index or key
still uses cannot be dropped, so drop the index or key first, in the same call if you like.

## Indexes

```java
table.index("user_id", "title");                  // columns in order
table.unique(List.of("slug", "tenant_id"), "posts_slug_tenant");
table.primary("a", "b");
table.dropIndex("posts_user_id_title_index");
table.dropUnique(List.of("slug"));
table.renameIndex("old_name", "new_name");
```

## Foreign keys

```java
table.foreignId("user_id").constrained().cascadeOnDelete();     // points at users.id
table.foreignId("editor_id").nullable().constrained("users").nullOnDelete();

table.foreign("order_id").references("id").on("orders").onDelete(ForeignKeyAction.CASCADE);
table.dropForeign(List.of("order_id"));
table.dropConstrainedForeignId("user_id");                       // key, index and column
```

The delete and update actions are `cascade`, `restrict`, `set null` and `no action`, each with an
`on...` method.

## Check constraints, generated columns and raw SQL

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

The SQL you give to `check`, `storedAs`, `virtualAs`, `rawColumn` and `statement` goes into the
statement as written. Build it from constants, never from user input. Table and column names are
different: quotes inside a name are escaped, and only empty names and names with control characters
are refused. Use `schema.driverName()` (`"sqlite"` or `"pgsql"`) when raw SQL differs by database.

## SQLite table rebuilds

SQLite cannot add or drop a primary or foreign key on an existing table. Diwan rebuilds the table
instead and keeps its rows, indexes and auto-increment counter. If a row breaks the new key,
nothing changes and `ForeignKeyCheckException` names the tables and the row count.

Inside a transaction you opened yourself, a table that other tables point at is not rebuilt
(`ForeignKeysOffRequiredException`). Run that change in a [migration](migrations.md) or inside
`schema.withoutForeignKeyConstraints(s -> ...)`.

## Inspect what exists

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

## Preview the SQL

```java
List<LoggedQuery> plan = schema.pretend(s -> s.create("t", table -> table.id()));
```

`pretend` lists the statements and changes nothing. It reads the live tables, so a rebuild shows its
real statements, but a table made earlier in the same pretend run does not exist for it.
`hasTable` and `hasColumn` return `false` in pretend mode.

Next: [Migrations](migrations.md).
