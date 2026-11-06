# Query builder

The query builder reads and writes rows through a chain of method calls. Every value you pass is
bound as a parameter, so the builder never puts your data into the SQL text.

## Get a builder

Each database has one entry point that returns a `QueryFactory`. Call `table(...)` on it to start a
query.

```java
import org.aristonis.diwan.database.query.QueryFactory;
import org.aristonis.diwan.database.sqlite.SQLiteQuery;     // diwan-database-sqlite:0.1.0
import org.aristonis.diwan.database.pgsql.PostgresQuery;    // diwan-database-pgsql:0.1.0

QueryFactory query = SQLiteQuery.of(db);        // SQLite, and Android through the same grammar
// QueryFactory query = PostgresQuery.of(db);   // PostgreSQL
```

`db` is the `Connection` from [Connections and transactions](connections.md). On Android you pass
the two factories to `AndroidConnector`, see [Android](android.md). A builder is not thread-safe.
`clone()` gives an independent copy.

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

Rows are `Map<String, Object>`. Other filters include `whereBetween`, `whereLike`, `whereColumn`,
`whereAny`, `whereAll`, `whereNone`, grouped conditions with `where(q -> ...)`, and `groupBy` with
`having`. `toSql()` and `getBindings()` show what a builder will run.

Date wheres (`whereDate`, `whereMonth` and the others) are for text date columns. On an instant
column use `whereInstantBetween(column, from, to)`.

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
db.transaction(c -> {
    var accounts = PostgresQuery.of(c).table("accounts").where("id", 1).lockForUpdate().get();
    var jobs = PostgresQuery.of(c).table("jobs")
            .lock(LockStrength.UPDATE, LockWait.SKIP_LOCKED).limit(10).get();
    return null;
});
```

`lockForUpdate()` and `sharedLock()` are shortcuts for `lock(LockStrength.UPDATE)` and
`lock(LockStrength.SHARE)`. There is no raw string lock as in Laravel.

- PostgreSQL needs a transaction for a locked select and throws `IllegalStateException` outside one.
  Run the query on the connection the `transaction(...)` callback gives you.
- SQLite has no row locks. The plain `UPDATE` and `SHARE` locks write nothing, and the PostgreSQL-only
  ones (`NO_KEY_UPDATE`, `KEY_SHARE`, `NOWAIT`, `SKIP_LOCKED`) throw
  `UnsupportedOperationException`. Code that relies on a lock for mutual exclusion is safe only on
  PostgreSQL.
- Aggregates, `exists` and the count behind `paginate` leave the lock out. A union with a lock is
  refused.

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
