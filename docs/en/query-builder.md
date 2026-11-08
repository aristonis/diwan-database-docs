# Query builder

The query builder reads and writes rows through a chain of method calls. Every value you pass is
bound as a parameter, so the builder never puts your data into the SQL text.

## Get a builder

Ask the `DatabaseManager` for a `QueryFactory`. It is built from the connection's configuration, so your code never names a driver class and switching the database is a configuration change. Call `table(...)` on it to start a query.

```java
import org.aristonis.diwan.database.query.QueryFactory;

QueryFactory query = manager.query();            // the default connection
QueryFactory cache = manager.query("cache");     // a named connection
```

`manager` is the `DatabaseManager` from [Connections and transactions](connections.md). A builder is not thread-safe. `clone()` gives an independent copy. The examples on this page call the factory `query`.

Without a manager, take the factory from the grammar module of your database:

```java
QueryFactory query = SQLiteQuery.of(connection);       // SQLite, and Android through the same grammar
// QueryFactory query = PostgresQuery.of(connection);  // PostgreSQL
```

Inside a transaction, call `query.on(c)` so the work runs on the transaction, as the row locks example below does. On Android, see [Android](android.md).

## Select and filter

```java
List<Map<String, Object>> rows = query.table("orders")
        .select("id", "total")
        .where("status", "open")
        .where("total", ">", 1000)
        .orWhere("priority", true)
        .whereIn("region", List.of("eu", "us"))
        .whereNotNull("customer_id")
        .orderByDesc("id")
        .limit(10)
        .get();

Optional<Map<String, Object>> one = query.table("users").find(7);
Optional<Object> email = query.table("users").where("id", 7).value("email");
boolean any = query.table("orders").where("status", "open").exists();
```

Rows are `Map<String, Object>`. Other filters include `whereBetween`, `whereLike`,
`whereContains` (see below), `whereColumn`, `whereAny`, `whereAll`, `whereNone`, grouped conditions
with `where(q -> ...)`, and `groupBy` with `having`. `toSql()` and `getBindings()` show what a builder will run.

`where(column, operator, value)` accepts the builder's operators (`=`, `<`, `>`, `<=`, `>=`, `<>`,
`!=`, `like`, `not like`, `ilike` and others) plus the grammar's own. An unknown operator is taken
as the value, so `where("total", "=>", 10)` compares `total` with the text `=>`, as in Laravel.

### Empty lists

An empty `whereIn` list matches no row (`0 = 1`). An empty `whereNotIn` list matches every row
(`1 = 1`), as in Laravel. That is the right answer for "every row except none", but in a delete it
removes everything the other conditions select. Make sure an empty list really means "none" and not
"not loaded":

```java
// "delete the task's alarms except these": with keep empty, every alarm of the task goes
query.table("alarms").where("task_id", taskId).whereNotIn("id", keep).delete();
```

Date wheres (`whereDate`, `whereMonth` and the others) are for text date columns. On an instant
column use `whereInstantBetween(column, from, to)`.

## Searching user input

`whereContains`, `whereStartsWith` and `whereEndsWith` find text that a user typed. They always
treat the text as literal: `%`, `_` and `!` match themselves, never as wildcards.

```java
List<Map<String, Object>> rows = query.table("users")
        .whereContains("name", userInput)            // the name holds the input, as typed
        .orWhereStartsWith("email", prefix)
        .whereNotEndsWith("email", ".test", true)    // case-sensitive
        .get();
```

Each method takes `(column, value)` or `(column, value, caseSensitive)`. The flag defaults to
`false`, as on `whereLike`. Each anchor has four forms: `whereContains`, `orWhereContains`,
`whereNotContains` and `orWhereNotContains`, and the same for `StartsWith` and `EndsWith`.

- A `null` value throws `IllegalArgumentException`.
- An empty value matches every row whose column is not null, because every text starts and ends
  with the empty text. A null column never matches.

The value is bound as one parameter. Diwan escapes it first, with `!` as the escape character:
`!` becomes `!!`, then `%` and `_` gain a `!` in front. The SQL depends on the database:

| Database | Default (`caseSensitive` false) | `caseSensitive` true |
|---|---|---|
| PostgreSQL | `col::text ilike ? escape '!'` | `col::text like ? escape '!'` |
| SQLite | `col like ? escape '!'` | `col glob ?` |

SQLite's GLOB has no escape character, so the case-sensitive form wraps `*`, `?` and `[` in
brackets, which makes each one match itself.

Notes:

- SQLite's default match folds case for ASCII letters only, so `É` does not match `é` there.
- SQLite does not use an index for `LIKE` with an `ESCAPE` clause. A case-sensitive
  `whereStartsWith` uses `GLOB` instead, which can use an index on a column with the `BINARY`
  collation.
- On PostgreSQL, a case-sensitive `whereStartsWith` can use a `text_pattern_ops` index on a text
  column. `ilike` cannot use a plain B-tree index; on a large table, a `pg_trgm` GIN index
  (`create index ... using gin (col gin_trgm_ops)`) serves contains, starts-with and ends-with in
  both case modes. The column is compared as `col::text`, so an index on a non-text column does not
  match.

### whereLike stays raw

`whereLike` works as in Laravel: the pattern is raw LIKE syntax, so `%` and `_` are wildcards and
nothing is escaped. Use it for patterns that you write yourself. Do not pass user input to
`whereLike`, not even with `%` added around it. Use `whereContains`, `whereStartsWith` or
`whereEndsWith` for that.

```java
query.table("users").whereLike("name", "A%");   // names that start with A, as written
```

## Joins, subqueries and unions

```java
List<Map<String, Object>> rows = query.table("orders")
        .join("customers", "customers.id", "=", "orders.customer_id")
        .leftJoinSub(query.table("payments").selectRaw("order_id, sum(amount) as paid")
                .groupBy("order_id"), "p", "p.order_id", "=", "orders.id")
        .whereExists(q -> q.from("notes").whereColumn("notes.order_id", "orders.id"))
        .select("orders.id", "customers.name", "p.paid")
        .get();

List<Object> ids = query.table("orders").select("id").where("status", "open")
        .union(query.table("archived_orders").select("id"))
        .orderByDesc("id")
        .limit(20)
        .pluck("id");
```

A subquery is copied when you attach it, so changing it afterward does not change the outer query.
A right join needs SQLite 3.39 or later, which Android 14 (API 34) and later ship. Older Android
SQLite reports its own error as a `QueryException`.

## Aggregates

```java
long total = query.table("orders").count();
Number revenue = query.table("orders").sum("total");          // 0 when there are no rows
Optional<Object> biggest = query.table("orders").max("total");
Optional<Number> mean = query.table("orders").avg("total");
```

### Exact decimal sums

`sum` returns a `Number`. For money, use `sumDecimal`, which returns a `BigDecimal` at the scale you give:

```java
BigDecimal paid = query.table("payments").sumDecimal("amount", 2);                       // HALF_UP
BigDecimal net = query.table("payments").sumDecimal("amount", 2, RoundingMode.HALF_EVEN);
```

- On PostgreSQL the sum is exact.
- On SQLite `SUM` is a double that Diwan rounds back to the scale. That is fine for normal totals and approximate for very large ones (millions of large values).
- No rows gives zero at the scale (`0.00`).
- The Eloquent builder has the same methods through `query()`.

## Insert, update and delete

```java
Object id = query.table("users").insertGetId(Map.of("email", "ada@example.com"));
query.table("users").insert(List.of(Map.of("email", "a@x"), Map.of("email", "b@x")));
query.table("users").where("id", id).update(Map.of("email", "ada@example.org"));
query.table("posts").where("id", 3).increment("views");
query.table("users").where("id", id).delete();
query.table("archive").insertUsing(List.of("id", "total"),
        q -> q.from("orders").select("id", "total").where("status", "closed"));
```

An update or delete may join other tables. On SQLite that needs a table with a rowid. Writes need a
table, not a subquery or raw `from`.

### insertOrIgnore, upsert and updateOrInsert

```java
query.table("users").insertOrIgnore(rows);                       // skips rows that break a unique key
query.table("users").upsert(rows, List.of("email"));             // updates every column of the first row
query.table("users").upsert(rows, List.of("email"), List.of("name"));
query.table("users").upsert(rows, List.of("email"),
        Map.of("votes", Expression.raw("users.votes + 1")));
query.table("users").updateOrInsert(Map.of("email", "a@x"), Map.of("name", "A"));
```

- `insertOrIgnore` returns the number of rows inserted. On SQLite it also skips a row that fails a
  `not null` or `check` constraint, not only a unique one.
- `upsert` needs a unique index on exactly the columns in `uniqueBy`, or the database refuses it.
  It needs SQLite 3.24 or later (Android API 30 and up). Older versions throw
  `UnsupportedOperationException` before any SQL runs.
- With two rows that share a unique key, SQLite applies them in order and the last wins. PostgreSQL
  refuses the statement. Remove duplicates first.
- An empty update list leaves a conflicting row as it is. Laravel runs a plain insert there, which
  fails.
- `updateOrInsert` reads, then writes, so it is not atomic. Two callers can both insert. Use
  `upsert` on a unique index when that matters.
- `insertOrIgnore` and `upsert` send all rows in one statement. Rows times columns must stay under
  the driver's binding limit: 999 on SQLite before 3.32, 32766 on SQLite 3.32 and later, 65535 on
  PostgreSQL. Split larger batches yourself, inside a transaction when they must succeed together.

## Row locks

```java
connection.transaction(c -> {
    var accounts = query.on(c).table("accounts").where("id", 1).lockForUpdate().get();
    var jobs = query.on(c).table("jobs")
            .lock(LockStrength.UPDATE, LockWait.SKIP_LOCKED).limit(10).get();
    return null;
});
```

`lockForUpdate()` and `sharedLock()` are shortcuts for `lock(LockStrength.UPDATE)` and
`lock(LockStrength.SHARE)`. There is no raw string lock as in Laravel.

- PostgreSQL needs a transaction for a locked select and throws `IllegalStateException` outside one.
  Run the query on the connection the `transaction(...)` callback gives you.
- SQLite has no row locks. Every strength (`UPDATE`, `SHARE`, `NO_KEY_UPDATE` and `KEY_SHARE`) writes
  nothing there: SQLite locks the whole database, and only at a transaction's first write. `NOWAIT` and
  `SKIP_LOCKED` throw `UnsupportedOperationException`. Code that relies on a lock for mutual
  exclusion is safe only on PostgreSQL.
- Aggregates, `exists` and the count behind `paginate` leave the lock out. A union with a lock is
  refused.

### Timed lock

```java
connection.transaction(c -> {
    var row = query.on(c).table("accounts").where("id", 1)
            .lock(LockStrength.UPDATE, Duration.ofSeconds(2)).first();
    return row;
});
```

`lock(strength, Duration)` waits at most that long for the row lock, then throws a `QueryException` with `isConcurrencyFailure()` true.

- PostgreSQL only. It needs an open transaction and throws `IllegalStateException` outside one. SQLite and Android throw `UnsupportedOperationException`.
- It applies to that statement only. Diwan restores the earlier `lock_timeout` after the statement.
- On a locking cursor the limit holds only while the cursor opens. Later fetches are not bounded.
- A statement limit wins over a transaction `lockWait` and the `lock_wait` configuration key. See [Connections](connections.md#lock-wait).

## Pagination

```java
LengthAwarePage page = query.table("orders").orderBy("id").paginate(20, 3);   // per page, page number
long total = page.total();
SimplePage simple = query.table("orders").orderBy("id").simplePaginate(20, 3);
boolean more = simple.hasMorePages();

CursorPage first = query.table("orders").orderByDesc("created_at").orderBy("id").cursorPaginate(20);
String token = first.nextCursor().map(Cursor::encode).orElse(null);           // send to the client
CursorPage next = query.table("orders").orderByDesc("created_at").orderBy("id")
        .cursorPaginate(20, Cursor.decode(token));
```

`cursorPaginate` needs an `orderBy` and should order by columns that are never null, since a null
can make it skip rows. Cursor tokens are not signed. A forged token cannot inject SQL, but it can
ask for any rows the query already allows.

When a sort column comes from a user, check it against a fixed list before it reaches the builder:

```java
private static final Set<String> SORTABLE = Set.of("created_at", "total", "id");

String column = SORTABLE.contains(requested) ? requested : "id";
query.table("orders").orderBy(column).orderBy("id").cursorPaginate(20);
```

Column and direction names are quoted as identifiers, not bound as values, so an allowlist is your
job.

## Reading large tables

```java
// Offset batches. Return false to stop. Needs an order.
query.table("orders").orderBy("id").chunk(500, rows -> { rows.forEach(this::recalculate); return true; });

// Key batches. Safe when rows change during the loop.
query.table("orders").where("status", "open").chunkById(500, rows -> { /* ... */ return true; });

// One page per step, no connection held between pages.
for (Map<String, Object> row : query.table("orders").orderBy("id").lazy(1000)) {
    export(row);
}

// Streams rows from one open statement.
try (QueryCursor<Map<String, Object>> rows = query.table("orders").orderBy("id").cursor()) {
    for (Map<String, Object> row : rows) {
        export(row);
    }
}
```

`chunk` pages by offset, so rows inserted or deleted during the loop can be skipped or read twice.
Use `chunkById` or `lazyById` for a table that changes. On Android the cursor refills its window by
running the query again, so prefer those two there too.

Always open a `QueryCursor` in try-with-resources. One that is neither read to the end nor closed
keeps its pooled connection for good, and a few of them can exhaust the pool. On PostgreSQL it also
leaves the server session idle in a transaction, which blocks vacuum. On SQLite it holds a read
lock, so another connection's write waits or fails as busy. Inside a transaction no other
statement runs on the connection until the cursor closes.

`iterator()` and `stream()` share one single use, and a second call throws
`IllegalStateException`. Closing the stream closes the cursor, so keep it in try-with-resources:

```java
try (Stream<Map<String, Object>> rows = query.table("orders").orderBy("id").cursor().stream()) {
    rows.limit(10).forEach(this::export);
}
```

On Android a cursor works only on the thread that opened it.

## Raw expressions

`selectRaw`, `whereRaw`, `orderByRaw`, `groupByRaw`, `havingRaw`, `fromRaw` and `Expression.raw` write
SQL exactly as you give it. Put values in the bindings list, never in the string.

```java
query.table("orders").whereRaw("total > ? and status = ?", List.of(100, status)).get();
// Never: whereRaw("status = '" + status + "'")
```

Build raw SQL from constants. The SQL text itself must never come from user input.

Next: [Schema builder](schema.md), [Models](models.md), [Differences from Laravel](differences.md).

## Method reference

Public methods that the sections above do not cover, one row per method name (overloads share a row).

| Method | On | What it does | Example |
|---|---|---|---|
| `addBinding` `addBindings` `setBindings` `getRawBindings` | `Builder` | Reads or changes the bound values by bucket (`select`, `where`, `having`, and so on). `addBinding` and `addBindings` append, `setBindings` replaces a bucket, `getRawBindings` returns all buckets. | `q.addBinding("where", 5)` |
| `addSelect` `selectSub` | `Builder` | Adds to the select list: a subquery under an alias (`addSelect`, `selectSub`). | `q.selectSub(sub, "post_count")` |
| `distinct` | `Builder` | Makes the query return only distinct rows. | `q.distinct().select("city")` |
| `average` `min` | `Builder` | `average` is an alias of `avg`. `min` returns the smallest value of a column. | `q.min("price")` |
| `first` | `Builder` | Runs the query limited to one row, on a copy, and returns that row. | `q.where("id", 1).first()` |
| `doesntExist` | `Builder` | Returns whether no row matches. | `q.where("email", e).doesntExist()` |
| `each` `eachById` `chunkMap` | `Builder` | Hand rows to a callback or map them page by page: `each` reads 1000 rows per page, `eachById` pages by id, `chunkMap` maps every row and returns the results. | See [Reading large tables](#reading-large-tables) |
| `chunkByIdDesc` `lazyByIdDesc` | `Builder` | Read id pages from the highest id down, as a chunk callback (`chunkByIdDesc`) or a lazy iterable (`lazyByIdDesc`). | See [Reading large tables](#reading-large-tables) |
| `forPage` `forPageAfterId` `forPageBeforeId` | `Builder` | Select one page of rows. `forPage` uses offset and limit, `forPageAfterId` takes ids above the last one (lowest first), `forPageBeforeId` takes ids below it (highest first). | `q.forPage(2, 15)` |
| `getCountForPagination` | `Builder` | Counts the rows all pages would show together, on a copy so the builder is unchanged. | See [Pagination](#pagination) |
| `crossJoin` `crossJoinSub` `leftJoin` `leftJoinWhere` `rightJoin` `rightJoinSub` `rightJoinWhere` `joinSub` `joinWhere` | `Builder` | More join forms: `crossJoin` without conditions, `leftJoin` and `rightJoin` on two columns, the `...Sub` forms on a subquery, and the `...Where` forms compare a column with a bound value. | `q.leftJoin("posts", "users.id", "posts.user_id")` |
| `fromSub` `getFrom` | `Builder` | `fromSub` reads from a subquery under an alias. `getFrom` returns the table. | `q.fromSub(sub, "recent")` |
| `unionAll` | `Builder` | Joins a query with `union all`, which keeps duplicate rows. | See [Joins, subqueries and unions](#joins-subqueries-and-unions) |
| `hasJoins` `newQuery` | `Builder`, `JoinClause` | `hasJoins` tells whether the query has joins. `newQuery` returns a new empty builder on the same connection, grammar and processor. | `q.newQuery().table("posts")` |
| `getConnection` `connection` `grammar` `getGrammar` `processor` `getProcessor` | `Builder`, `QueryFactory` | Return the parts a query runs on: the connection, the grammar that compiles SQL, and the processor that shapes results. On `QueryFactory` they are the factory's own. | `q.getGrammar()` |
| `query` | `QueryFactory` | Starts a query without a table, for example for `selectRaw("1")`. | `factory.query().selectRaw("1")` |
| `decrement` `decrementEach` `incrementEach` | `Builder` | `decrement` subtracts 1 (or an amount) from a column of the matching rows. `incrementEach` and `decrementEach` change several columns at once. | `q.where("id", 1).decrement("stock")` |
| `insertOrIgnoreUsing` | `Builder` | Inserts the rows a subquery returns and skips rows that break a unique or primary key constraint. | See [insertOrIgnore, upsert and updateOrInsert](#insertorignore-upsert-and-updateorinsert) |
| `truncate` | `Builder` | Empties the table. | `q.table("logs").truncate()` |
| `latest` `oldest` | `Builder` | Order by `created_at`, newest first (`latest`) or oldest first (`oldest`). | `q.latest()` |
| `inRandomOrder` | `Builder` | Orders randomly. | `q.inRandomOrder().limit(1)` |
| `reorder` `reorderDesc` | `Builder` | `reorder` removes every order and its bindings, including the orders of a union. `reorderDesc` replaces every order with one column, descending. | `q.reorder("id")` |
| `offset` `skip` `take` | `Builder` | `offset` skips rows (a negative value means zero). `skip` is an alias of `offset`, and `take` is an alias of `limit`. | `q.skip(10).take(5)` |
| `toRawSql` | `Builder` | `toRawSql` compiles the query with its bindings written in as literals, for display and logging only. | `q.where("id", 1).toRawSql()` |
| `whereNot` `orWhereNot` | `Builder` | A negated condition comparing a column with a value using `=` (`orWhereNot` joins with OR). | `q.whereNot("status", "draft")` |
| `whereNull` `orWhereNull` | `Builder`, `JoinClause` | Condition that each column is null (`orWhereNull` joins with OR). | `q.whereNull("deleted_at")` |
| `whereNotNull` `orWhereNotNull` | `Builder` | Condition that each column is not null (`orWhereNotNull` joins with OR). | `q.whereNotNull("email")` |
| `whereNotIn` `orWhereIn` `orWhereNotIn` | `Builder` | IN and NOT IN conditions, here on the rows of a subquery, with the `or` forms. | `q.orWhereIn("id", sub)` |
| `whereNotBetween` `orWhereBetween` `orWhereNotBetween` | `Builder` | BETWEEN and NOT BETWEEN a pair of values, with the `or` forms. | `q.whereNotBetween("age", 18, 65)` |
| `whereBetweenColumns` `whereNotBetweenColumns` `orWhereBetweenColumns` `orWhereNotBetweenColumns` | `Builder` | A column is (or is not) between two other columns, with the `or` forms. | `q.whereBetweenColumns("price", "min", "max")` |
| `whereValueBetween` `whereValueNotBetween` `orWhereValueBetween` `orWhereValueNotBetween` | `Builder` | A value is (or is not) between two columns, with the `or` forms. | `q.whereValueBetween(5, "low", "high")` |
| `orWhereColumn` | `Builder` | Compares two columns for equality (`orWhereColumn` joins with OR). | `q.orWhereColumn("a", "b")` |
| `whereNotExists` `orWhereExists` `orWhereNotExists` | `Builder` | Subquery EXISTS and NOT EXISTS conditions, with the `or` forms. | `q.whereNotExists(sub -> ...)` |
| `whereNotLike` `orWhereLike` `orWhereNotLike` | `Builder` | Case-insensitive LIKE and NOT LIKE conditions, with the `or` forms. | `q.whereNotLike("name", "a%")` |
| `whereContains` `whereStartsWith` `whereEndsWith`, with `or`, `Not` and `orNot` forms | `Builder` | Text search for user input, with the value always literal and an optional `caseSensitive` flag. | `q.whereContains("name", input)` |
| `orWhereAll` `orWhereAny` `orWhereNone` | `Builder` | `or` groups over several columns: every column equals the value (`All`), at least one (`Any`), or none (`None`). | `q.orWhereAny(cols, "x")` |
| `whereDay` `whereYear` `whereTime` `orWhereDate` `orWhereDay` `orWhereMonth` `orWhereYear` `orWhereTime` | `Builder` | Conditions on one part of a text date or time column: day, month, year or time (and the date part with `orWhereDate`), compared with `=`. The `or` forms join with OR. | `q.whereYear("created_at", 2026)` |
| `whereIntegerInRaw` | `Builder` | A column is in a list of integers written into the SQL, not bound; an empty list matches no row. | `q.whereIntegerInRaw("id", List.of(1, 2))` |
| `whereNullSafeEquals` `orWhereNullSafeEquals` | `Builder` | A comparison that treats two nulls as equal, with the `or` form. | `q.whereNullSafeEquals("a", null)` |
| `whereRowValues` `orWhereRowValues` | `Builder` | Compares a row of columns with a row of values: `(a, b) < (?, ?)`. | `q.whereRowValues(cols, "<", vals)` |
| `orWhereRaw` `orHavingRaw` | `Builder` | Trusted SQL joined to the earlier conditions with OR, in `where` or `having`. | `q.orWhereRaw("a > b")` |
| `groupWheresAt` | `Builder` | Regroups the where conditions around an index. | - |
| `orHaving` `orHavingBetween` `orHavingNotBetween` `orHavingNull` `orHavingNotNull` `orHavingNested` `havingBetween` `havingNotBetween` `havingNull` `havingNotNull` `havingNested` | `Builder` | Having conditions: between and not between, null and not null, and a nested group in parentheses. The `orHaving...` forms join with OR. | `q.havingNotNull("total")` |
| `on` `orOn` | `JoinClause` | Inside a join, adds a condition comparing two columns with `=` (`orOn` joins with OR). | `join.on("a.id", "b.a_id")` |
| `getTable` `getType` | `JoinClause` | On a `JoinClause`, return the joined table and the join type. | `join.getType()` |
| `close` `isClosed` | `QueryCursor` | Release the statement and everything the cursor holds (a second call does nothing), and tell whether the cursor is closed. | `try (var c = q.cursor()) { ... }` |
| `currentPage` `lastPage` `perPage` `items` | `LengthAwarePage`, `SimplePage`, `CursorPage` | Read a page object: the page number from 1, the last page number (1 when no row matches), the page size, and the rows. | `page.items()` |
| `previousCursor` | `CursorPage` | Returns the cursor of the page before this one. | `page.previousCursor()` |
| `encode` | `Cursor` | Writes a cursor as URL-safe text (base64url without padding). | `cursor.encode()` |
| `parameter` `parameters` | `Cursor` | Return the value of one order column, or every order value of the cursor. | `cursor.parameter("id")` |
| `pointsToNextItems` `pointsToPreviousItems` | `Cursor` | Tell whether the cursor leads to the rows after, or before, its position. | `cursor.pointsToNextItems()` |
| `toString` `equals` `hashCode` | `LengthAwarePage`, `SimplePage`, `CursorPage`, `Cursor` | Standard text, equality and hash for page and cursor values. | - |
| `on` | `QueryFactory` | Returns this factory bound to another connection of the same database, such as the one a transaction gives you. It throws `IllegalArgumentException` for another kind of database. | `query.on(tx)` |
