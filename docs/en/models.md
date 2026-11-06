# Models

A model is a class per table, with Eloquent's method names. It keeps its attributes, knows which
ones changed, and writes only those. Every query goes through the [query builder](query-builder.md),
so the SQL is the SQL you would get from `table(...)`.

Models live in `diwan-database-eloquent`:

```kotlin
implementation("org.aristonis:diwan-database-eloquent:0.1.0")
```

## Define a model

A model needs one static entry. It uses no reflection, annotations or build plugin, so the same
class runs on Android.

```java
public final class User extends Model {
    public static final ModelQuery<User> query = ModelQuery.of(User.class, User::new);

    @Override
    protected List<String> fillable() {
        return List.of("name", "email");   // nothing is mass assignable until listed
    }
}

ModelQuery<User> users = User.query.on(SQLiteQuery.of(db));
```

`on(...)` binds the entry to a query factory. Inside a transaction, bind to the transaction's
connection with `users.on(c)` so every statement runs in it.

## Configure a model

Override these methods to change the defaults:

| Method | Default |
|---|---|
| `table()` | snake-case plural of the class name (`BlogPost` gives `blog_posts`) |
| `primaryKey()`, `keyType()`, `incrementing()` | `id`, `int`, `true` |
| `connectionName()` | the default connection |
| `timestamps()`, `createdAtColumn()`, `updatedAtColumn()` | on, `created_at`, `updated_at` |
| `timestampFormat()`, `dateFormat()` | UTC text `yyyy-MM-dd HH:mm:ss`; `TimestampFormat.INSTANT` for instant columns |
| `uniqueIdKind()` | `UniqueIdKind.NONE`; `UUID` (version 7) or `ULID` generates the key on insert |
| `perPage()` | the page size for `paginate()` with no argument |
| `softDeletes()`, `deletedAtColumn()` | off, `deleted_at` |

The plural comes from a short English rule set. Override `table()` when it guesses wrong.

## Mass assignment

`fill` sets only the keys in `fillable()` and drops the rest. With the default guards (`guarded()`
is `*` and `fillable()` is empty), `fill` throws `MassAssignmentException`. `forceFill` and
`Model.unguarded(...)` bypass the guards.

```java
User user = users.make(request);   // fills; "is_admin" in request is dropped
user.save();
```

## Attributes, accessors and casts

```java
found.setAttribute("name", "Ada L.");
found.isDirty("name");      // true
found.getDirty();           // {name=Ada L.}
found.save();               // writes name and updated_at only
found.save();               // clean: runs nothing
```

Declare casts in `casts()` with Laravel's string form or the typed factories in `Casts`:

```java
@Override
protected Map<String, Cast<?>> casts() {
    return CastMap.create()
            .put("price", "decimal:2")                      // BigDecimal, scale 2
            .put("is_admin", "bool")                        // Boolean
            .put("options", "json")                         // Map or List
            .put("born_on", "date")                         // LocalDate
            .put("paid_at", Casts.datetime("dd/MM/yyyy"))   // Instant
            .put("status", Casts.enumOf(Status.class))      // the enum constant
            .build();
}
```

```java
Order order = orders.findOrFail(1);
BigDecimal price = (BigDecimal) order.getAttribute("price");
order.getAttributes().get("price");   // the stored form, "12.50"
```

Bad stored data, such as broken JSON or `"abc"` under `int`, throws `InvalidCastException`.
Laravel reads `null` or `0` there. The dirty check compares by meaning: JSON by structure, moments
as instants, dates as dates. Reading a cast value never makes a model dirty, but changing a map a
`json` cast returned does. For a cast of your own, implement `Cast<T>` (`get` and `set`).

Date formats are Java `DateTimeFormatter` patterns. Write `yyyy-MM-dd`, not PHP's `Y-m-d`: the PHP
form compiles in Java and means something else.

Accessors and mutators are registered in `accessors()`, not discovered by name:

```java
@Override
protected Map<String, Attribute<?>> accessors() {
    Map<String, Attribute<?>> map = new LinkedHashMap<>();
    map.put("display_name", Attribute.get((model, value, attrs) -> attrs.get("first") + " " + attrs.get("last")));
    map.put("email", Attribute.set((model, value, attrs) -> value.toString().toLowerCase(Locale.ROOT)));
    return map;
}
```

`casts()` and `accessors()` are read once per class, so they must not depend on instance state.

## Save, create and find

```java
User ada = users.create(Map.of("name", "Ada", "email", "ada@example.com"));  // id, timestamps set
User found = users.findOrFail(ada.getKey());
Optional<User> maybe = users.find(42);
Optional<User> first = users.query().where("email", "ada@example.com").first();

found.update(Map.of("name", "Ada Lovelace"));
found.increment("logins");
found.delete();            // false when the model is not in the database
```

`saveOrFail()` saves, and runs its touches, in one transaction. It throws `IllegalStateException`
when a model with a non-incrementing key has nothing to insert. Plain `save()` returns `true` there,
as in Laravel.

Find or make a row:

```java
User sam = users.firstOrCreate(Map.of("email", "sam@example.com"), Map.of("name", "Sam"));
users.updateOrCreate(Map.of("email", "sam@example.com"), Map.of("name", "Samuel"));
users.firstOrNew(Map.of("email", "new@example.com"), Map.of("name", "New"));   // not saved
```

`upsert` and `insertOrIgnore` write many rows in one statement. They skip model events and casts,
but fill unique ids and timestamps:

```java
users.query().upsert(rows, List.of("email"));          // needs a unique index on email
users.query().upsert(rows, List.of("email"), List.of("name"));
users.query().insertOrIgnore(rows);
```

`upsert` needs SQLite 3.24 or later, which means Android API 30 or later. See [Android](android.md).

## Scopes

A global scope adds a constraint to every query of a model, including eager loads and `whereHas`.
Register it once at start-up, with a name:

```java
posts.addGlobalScope("tenant", q -> q.where("tenant_id", 7));

posts.query().withoutGlobalScope("tenant").get();   // one query without it
posts.query().withoutGlobalScopes().get();
```

A scope may add query clauses only. It must be stateless and must not run a query itself. A class
that implements `Scope` registers through `addGlobalScope(Scope)`; a lambda needs a name. A local
scope is a reusable step you apply to one query:

```java
posts.query().scope(q -> q.where("published", true)).get();
```

## Soft deletes

Turn them on with `softDeletes()` returning `true`. Then:

| You want to | Use |
|---|---|
| Soft delete | `delete()` sets `deleted_at` (and `updated_at`) |
| Remove the row for good | `forceDelete()` |
| Restore | `restore()` |
| Check | `trashed()` |
| Read with trashed rows, or only those | `query().withTrashed()`, `query().onlyTrashed()` |
| Find a trashed row or create it | `restoreOrCreate(attributes)`, `createOrRestore(attributes)` on the query |

A unique index also covers trashed rows, so a plain `create` that reuses a key held by a trashed
row fails. `restoreOrCreate` finds the trashed row and restores it. `forceDelete()` on a query skips
only the soft-delete scope, so a tenant scope still applies.

## Events and observers

Register listeners once, at start-up, on the model's `ModelQuery`:

```java
posts.events()
        .saving(post -> {                       // return false to stop the save
            if (post.getString("slug") == null) {
                post.setAttribute("slug", slugOf(post.getString("title")));
            }
            return true;
        })
        .created(post -> auditLog.record("post created", post.getKey()));

posts.events().observe(new PostObserver());     // a ModelObserver<Post>
```

The events are `retrieved`, `saving`, `saved`, `creating`, `created`, `updating`, `updated`,
`deleting`, `deleted`, `softDeleted`, `restoring`, `restored`, `forceDeleting`, `forceDeleted` and
`replicating`. The six that run before a write can halt it by returning `false`. Only `false`
halts; `true` lets the next listener run.

`events().afterCommit()` and `ModelObserver.afterCommit()` hold a listener until the outermost
transaction commits. A rollback drops it. Skip events with `Model.withoutEvents(() -> ...)` (this
thread only) or `saveQuietly()`, `deleteQuietly()`. A listener that saves its own model must use
`saveQuietly()`, or it calls itself again. Builder writes such as `query().update(...)` load no
model and fire no event.

## Serialization

`toMap()` and `toJson()` apply `visible()`, then `hidden()`, then `appends()`. Moments come out as
ISO-8601 UTC with microseconds. Loaded relations follow the attributes, and a cycle ends.

```java
@Override
protected List<String> hidden() { return List.of("password"); }

String json = user.toJson();
```

The built-in JSON codec is strict RFC 8259 and the library adds no JSON dependency. To use Jackson
or Gson, implement `JsonCodec` and return it from `jsonCodec()`.

## Chunks, lazy reads, cursors and pages

```java
users.query().orderBy("id").chunk(500, batch -> { batch.forEach(this::sync); return true; });
users.query().chunkById(500, batch -> { /* rows may change here */ return true; });

for (User u : users.query().orderBy("id").lazy(1000)) { /* one page at a time */ }

try (QueryCursor<User> cursor = users.query().orderBy("id").cursor()) {
    for (User u : cursor) { /* streams one row at a time */ }
}

ModelPage<User> page = users.query().orderBy("name").paginate(20, 2);
page.items();   // ModelCollection<User>
page.total();
```

`chunk` pages by offset, so use `chunkById` when rows change during the loop. Always close a
`cursor()`: an open one keeps its connection. A cursor refuses eager loads; `lazy()` loads them per
page. `simplePaginate` and `cursorPaginate` work as on the query builder.

## Limits

- Models are not thread-safe. Share the `ModelQuery`; give each thread its own instances.
- Without a `bool` cast, a `Boolean` set on a SQLite column reads back as `1` and stays dirty
  against `true`.
- Listeners and scopes belong to the class registered with `ModelQuery.of`; a subclass registered
  separately has its own list.

See [Relations](relations.md) for relations, [Differences from Laravel](differences.md) and
[Errors](errors.md).
