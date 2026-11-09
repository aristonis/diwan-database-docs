# Schema builder

`Schema` creates and changes tables. You describe the table in a callback on a `Blueprint`, and the
grammar of your database turns it into SQL.

=== "Java"

    ```java
    Schema schema = manager.schema();      // the default connection; manager.schema("cache") for another
    ```

=== "Kotlin"

    ```kotlin
    val schema = manager.schema()      // the default connection; manager.schema("cache") for another
    ```

`manager` is the `DatabaseManager` from [Connections and transactions](connections.md). The schema is built from the connection's configuration, so your code never names a driver class. Without a manager, use the grammar module: `SQLiteSchema.of(connection)`, or `PostgresSchema.of(connection)` on PostgreSQL.

## Create, alter and drop

=== "Java"

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

=== "Kotlin"

    ```kotlin
    schema.create("users") { table ->
        table.id()
        table.string("email").unique()
        table.booleanColumn("active").defaultValue(true)
        table.enumColumn("role", listOf("admin", "member")).defaultValue("member")
        table.rememberToken()
        table.softDeletes()
        table.timestamps()
    }

    schema.table("users") { table -> table.text("bio").nullable() }   // add a column
    schema.rename("users", "people")
    schema.dropIfExists("people")                                     // drop(...) fails if it is missing
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

`instant` stores whole microseconds on SQLite and `timestamptz` on PostgreSQL; convert with
`Instants.toMicros` and `Instants.read`. SQLite has nothing like `set`, so it refuses that type.
On a model, write an `instant` column through `Casts.instant()`. For timestamp columns
(`created_at`, `updated_at`, `deleted_at`), set `TimestampFormat.INSTANT` on the model instead. See
[Models](models.md#attributes-accessors-and-casts).

## Modifiers

=== "Java"

    ```java
    table.string("slug", 120).nullable().unique();
    table.timestamp("seen_at").useCurrent();
    table.integer("qty").check("qty > 0");
    table.integer("total").storedAs("qty * price");
    ```

=== "Kotlin"

    ```kotlin
    table.string("slug", 120).nullable().unique()
    table.timestamp("seen_at").useCurrent()
    table.integer("qty").check("qty > 0")
    table.integer("total").storedAs("qty * price")
    ```

The common ones are `nullable`, `defaultValue`, `useCurrent`, `unique`, `index`, `primary`,
`autoIncrement`, `unsigned`, `comment`, `virtualAs` and `storedAs`. SQLite ignores `unsigned` and
`comment`. It adds a not-null column without a default only while the table is empty. An SQLite
enum refuses any value outside its list, and keeps that rule through later table rebuilds.

### Collations

A text column can say how its values compare and sort. `Collation.BINARY` is the portable byte
order. PostgreSQL writes it as `"C"` and SQLite as `BINARY`, so one migration gives the same order
on both.

=== "Java"

    ```java
    table.string("code").collation(Collation.BINARY);
    table.string("name").collation("nb_NO.utf8");    // the database's own name, written as given
    schema.table("codes", table -> table.string("code").collation(Collation.BINARY).change());
    ```

=== "Kotlin"

    ```kotlin
    table.string("code").collation(Collation.BINARY)
    table.string("name").collation("nb_NO.utf8")    // the database's own name, written as given
    schema.table("codes") { t -> t.string("code").collation(Collation.BINARY).change() }
    ```

A name given as text is written as is, so it must be a collation the database knows. It cannot hold
a quote or a control character. On SQLite a table rebuild keeps a column's collation. A `COLLATE`
inside a table constraint, such as `unique (email collate nocase)`, is still refused.

### Changing a column

`change()` redefines a column. As in Laravel 11 and later, the new definition replaces the old one
in full, so restate every modifier you want to keep.

=== "Java"

    ```java
    schema.table("posts", table -> table.string("title", 500).nullable().change());
    ```

=== "Kotlin"

    ```kotlin
    schema.table("posts") { table -> table.string("title", 500).nullable().change() }
    ```

Changing an auto-increment column is not supported. On SQLite, rename or drop a column that another
table references in a separate `schema.table` call from a `change()`. A column that an index or key
still uses cannot be dropped, so drop the index or key first, in the same call if you like.

## Indexes

=== "Java"

    ```java
    table.index("user_id", "title");                  // columns in order
    table.index(List.of("state", "next_fire_at"), "alarms_state_next");   // named index
    table.unique(List.of("slug", "tenant_id"), "posts_slug_tenant");
    table.primary("a", "b");
    table.dropIndex("posts_user_id_title_index");
    table.dropUnique(List.of("slug"));
    table.renameIndex("old_name", "new_name");
    ```

=== "Kotlin"

    ```kotlin
    table.index("user_id", "title")                  // columns in order
    table.index(listOf("state", "next_fire_at"), "alarms_state_next")   // named index
    table.unique(listOf("slug", "tenant_id"), "posts_slug_tenant")
    table.primary("a", "b")
    table.dropIndex("posts_user_id_title_index")
    table.dropUnique(listOf("slug"))
    table.renameIndex("old_name", "new_name")
    ```

### Partial indexes

`index` and `unique` return an `IndexDefinition`. Call `where`, `whereNull` or `whereNotNull` on it to
index only the rows that match. Several conditions are joined with `and`.

=== "Java"

    ```java
    table.index(List.of("id"), "attempts_started").where("outcome", "STARTED");
    table.unique(List.of("email"), "users_email_live").whereNull("deleted_at");
    ```

=== "Kotlin"

    ```kotlin
    table.index(listOf("id"), "attempts_started").where("outcome", "STARTED")
    table.unique(listOf("email"), "users_email_live").whereNull("deleted_at")
    ```

`where(column, value)` compares a column with a value. The value can be text, a boolean, a finite
number or `null`, and `null` means `whereNull`. Any other type is refused when you make the call. The
column in a condition need not be one of the index's columns. Column-level `.index()` and `.unique()`
take no condition.

On PostgreSQL a partial unique index is a unique index, not a unique constraint. `dropUnique(name)`
drops whichever of the two exists under that name. On SQLite a table rebuild keeps each partial index
with its condition.

### Index order and collation

`asc`, `desc` and `collate` on an `IndexDefinition` set how an indexed column is sorted and compared.
The column must be one of the index's columns, or the call throws `IllegalArgumentException`. The
default index name still uses only the column names.

=== "Java"

    ```java
    table.index(List.of("module_id", "id"), "latest_per_module").desc("id");
    ```

=== "Kotlin"

    ```kotlin
    table.index(listOf("module_id", "id"), "latest_per_module").desc("id")
    ```

`collate(column, name)` takes a collation name the database knows, such as `NOCASE` on SQLite, and
writes it as given. Chain the calls: `table.index(...).where(...).desc(...)`. A SQLite table rebuild
keeps descending order and collations.

## Foreign keys

=== "Java"

    ```java
    table.foreignId("user_id").constrained().cascadeOnDelete();     // points at users.id
    table.foreignId("editor_id").nullable().constrained("users").nullOnDelete();

    table.foreign("order_id").references("id").on("orders").onDelete(ForeignKeyAction.CASCADE);
    table.dropForeign(List.of("order_id"));
    table.dropConstrainedForeignId("user_id");                       // key, index and column
    ```

=== "Kotlin"

    ```kotlin
    table.foreignId("user_id").constrained().cascadeOnDelete()     // points at users.id
    table.foreignId("editor_id").nullable().constrained("users").nullOnDelete()

    table.foreign("order_id").references("id").on("orders").onDelete(ForeignKeyAction.CASCADE)
    table.dropForeign(listOf("order_id"))
    table.dropConstrainedForeignId("user_id")                       // key, index and column
    ```

The delete and update actions are `cascade`, `restrict`, `set null` and `no action`, each with an
`on...` method.

PostgreSQL limits a name to 63 bytes, and the default name of a key on a long table can pass that.
Name the key yourself with the third argument of `constrained`, or with the second argument of
`references`:

=== "Java"

    ```java
    table.foreignId("attribute_id").constrained("product_attribute_values", "id", "pav_attribute_fk");
    table.foreignId("attribute_id").references("id", "pav_attribute_fk").on("product_attribute_values");
    ```

=== "Kotlin"

    ```kotlin
    table.foreignId("attribute_id").constrained("product_attribute_values", "id", "pav_attribute_fk")
    table.foreignId("attribute_id").references("id", "pav_attribute_fk").on("product_attribute_values")
    ```

## Check constraints, generated columns and raw SQL

=== "Java"

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

=== "Kotlin"

    ```kotlin
    schema.create("lines") { table ->
        table.id()
        table.integer("qty").check("qty > 0")
        table.integer("price")
        table.integer("total").storedAs("qty * price")
        table.check("lines_price_check", "price >= 0")
    }
    schema.statement("create index lines_total on lines (total)")
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

=== "Java"

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

=== "Kotlin"

    ```kotlin
    val hasUsers = schema.hasTable("users")
    val hasBio = schema.hasColumn("users", "bio")

    for (index in schema.indexes("posts")) {
        println("${index.name()} ${index.columns()} unique=${index.isUnique()}")
    }
    for (key in schema.foreignKeys("posts")) {
        println("${key.columns()} -> ${key.foreignTable()}${key.foreignColumns()}")
    }
    ```

`IndexInfo` also reports `orders()` (`asc` or `desc` for each column), `collations()` (an empty string
for the default) and `where()`, an `Optional` with the condition's SQL text. The text is the
database's own, and PostgreSQL rewrites it, so compare it within one database.

### List and drop everything

=== "Java"

    ```java
    List<TableInfo> tables = schema.getTables();        // name and schema, ordered by schema, then name
    List<String> names = schema.getTableListing();      // names only
    List<ViewInfo> views = schema.getViews();

    schema.dropAllViews();
    schema.dropAllTables();
    ```

=== "Kotlin"

    ```kotlin
    val tables = schema.tables              // name and schema, ordered by schema, then name
    val names = schema.tableListing         // names only
    val views = schema.views

    schema.dropAllViews()
    schema.dropAllTables()
    ```

`TableInfo` and `ViewInfo` are immutable values with `name()` and `schema()`. Internal tables are not listed: `sqlite_` tables, `android_metadata` and FTS shadow tables on SQLite and Android, and `spatial_ref_sys` on PostgreSQL. The listing returns real table names, including the connection's table prefix, as Laravel does. On SQLite older than 3.37, FTS3-5 and R-Tree shadow tables are hidden too.

- **PostgreSQL:** the tables of the schemas in `search_path`, dropped with one `drop table ... cascade` statement. `spatial_ref_sys` is kept. With nothing to drop, no statement runs. Types, sequences and functions are not dropped.
- **SQLite and Android:** each table is dropped, children first, so foreign keys do not block the drop. FTS shadow tables are skipped, and `android_metadata` is kept.

`Migrator.fresh()` uses these calls: see [Migrations](migrations.md#start-from-scratch).

## Preview the SQL

=== "Java"

    ```java
    List<LoggedQuery> plan = schema.pretend(s -> s.create("t", table -> table.id()));
    ```

=== "Kotlin"

    ```kotlin
    val plan = schema.pretend { s -> s.create("t") { table -> table.id() } }
    ```

`pretend` lists the statements and changes nothing. It reads the live tables, so a rebuild shows its
real statements, but a table made earlier in the same pretend run does not exist for it.
`hasTable` and `hasColumn` return `false` in pretend mode.

Inside a transaction, call `schema.on(tx)` so the work runs on the transaction: `schema.on(tx).create(...)`.

Next: [Migrations](migrations.md).

## Method reference

Public methods that the sections above do not cover, one row per method name (overloads share a row).

| Method | On | What it does | Example |
|---|---|---|---|
| `connection` `grammar` | `Schema` | On `Schema`: the connection it works on and the grammar that compiles its SQL. | `schema.connection()` |
| `commands` `isCreating` | `Blueprint` | On `Blueprint`: the commands in the order a grammar compiles them, and whether the blueprint creates its table. | `table.isCreating()` |
| `tinyIncrements` `smallIncrements` `mediumIncrements` `integerIncrements` | `Blueprint` | Auto-increment unsigned integer primary keys of 8, 16, 24 and 32 bits. | `table.smallIncrements("id")` |
| `unsignedTinyInteger` `unsignedSmallInteger` `unsignedMediumInteger` `unsignedInteger` `unsignedBigInteger` | `Blueprint` | Unsigned integer columns of 8, 16, 24, 32 and 64 bits. | `table.unsignedInteger("views")` |
| `tinyText` | `Blueprint` | Adds a short text column. | `table.tinyText("note")` |
| `timeTz` `timestampTz` `dateTimeTz` | `Blueprint` | Time of day, timestamp and date and time columns with a time zone. | `table.timestampTz("seen_at")` |
| `nullableTimestamps` `datetimes` `timestampsTz` | `Blueprint` | Nullable `created_at` and `updated_at` columns: as `timestamps()` does (`nullableTimestamps`), as date and time columns (`datetimes`) or with a time zone (`timestampsTz`). | `table.timestampsTz()` |
| `softDeletesTz` `softDeletesDatetime` | `Blueprint` | Nullable `deleted_at` column for soft deletes, with a time zone or as a date and time column. | `table.softDeletesTz()` |
| `numericMorphs` `nullableNumericMorphs` `nullableMorphs` `uuidMorphs` `nullableUuidMorphs` `ulidMorphs` `nullableUlidMorphs` | `Blueprint` | Polymorphic relation columns: `_type` and `_id` with a numeric, UUID or ULID id and an index on both. The `nullable` forms allow null. | `table.nullableMorphs("taggable")` |
| `dropColumn` `renameColumn` | `Blueprint` | Drop columns, or rename one. | `table.renameColumn("a", "b")` |
| `dropPrimary` `dropCheck` | `Blueprint` | Drop the primary key, or a named CHECK constraint. | `table.dropCheck("age_check")` |
| `dropMorphs` `dropRememberToken` `dropSoftDeletes` `dropSoftDeletesTz` `dropTimestamps` `dropTimestampsTz` | `Blueprint` | Drop what the matching helper added: a polymorphic relation (index, then both columns), `remember_token`, `deleted_at`, or `created_at` and `updated_at`. | `table.dropTimestamps()` |
| `type` `length` `places` `precision` `total` `allowed` `checks` `rawDefinition` | `ColumnDefinition`, `ForeignIdColumnDefinition` | Read a column definition: its type, the string length, the digits after the point and the precision or total digits of a decimal, the values an enum or set allows, its CHECK conditions and the SQL of a raw type. | `column.type()` |
| `isNullable` `isNotNullStated` `isUnsigned` `isAutoIncrement` `isPrimary` `isIndexed` `isChange` `isGenerated` `usesCurrent` | `ColumnDefinition`, `ForeignIdColumnDefinition` | Read a column's flags: allows NULL, `nullable(false)` was called, unsigned, counts up by itself, is the primary key on its own, has a plain index of its own, redefines an existing column (`change()`), is computed by the database, and `useCurrent()` was called. | `column.isNullable()` |
| `onUpdate` `cascadeOnUpdate` `restrictOnUpdate` `noActionOnUpdate` `nullOnUpdate` `restrictOnDelete` `noActionOnDelete` | `ForeignKeyDefinition` | Foreign key actions: `onUpdate` sets what happens when the referenced key changes, and the shortcuts cascade, restrict (refuse), refuse at the end of the statement (`noAction...`) or set NULL. | `fk.restrictOnDelete()` |
| `deleteAction` `updateAction` `referencedTable` `referencedColumns` | `ForeignKeyDefinition` | Read a foreign key definition: the delete and update action if one was set, the referenced table and the referenced columns. | `fk.referencedTable()` |
| `on` | `Schema` | Returns this schema builder bound to another connection of the same database, such as a transaction's. It throws `IllegalArgumentException` for another kind of database. | `schema.on(tx)` |
| `collation` | `ColumnDefinition`, `ForeignIdColumnDefinition` | Sets the collation of a text column, given as a `Collation` or as a database collation name. On `ColumnDefinition`, `collation()` with no argument returns it as an `Optional`. | `column.collation(Collation.BINARY)` |
| `of` `name` `isPortable` | `Collation` | `of` makes a collation the database knows by name. `name` returns the name, and `isPortable` tells whether the value is `Collation.BINARY`. | `Collation.of("nb_NO.utf8")` |
