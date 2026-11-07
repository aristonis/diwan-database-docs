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

ModelQuery<User> users = User.query.on(manager.query());
```

`on(...)` binds the entry to a query factory, normally `manager.query()`, so the model never names a driver class. Inside a transaction, bind with `User.query.on(db.on(tx))` so every statement runs on the transaction.

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

`Casts.instant()` stores an `Instant` whatever the model's `timestampFormat()`. Use it for
`Blueprint.instant` columns. `created_at`, `updated_at` and `deleted_at` are also written directly
by soft delete, bulk update and touch, always in the model's format. So when those columns are
`instant`, the model needs `TimestampFormat.INSTANT`. A model on the TEXT format that puts the
instant cast on one of them fails at first use, and the message names the column.

```java
@Override
protected TimestampFormat timestampFormat() { return TimestampFormat.INSTANT; }

@Override
protected Map<String, Cast<?>> casts() {
    return CastMap.create().put("sent_at", Casts.instant()).build();   // any other instant column
}
```

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

`fillAndInsert`, `fillAndInsertOrIgnore` and `fillAndInsertGetId` fill each row as `fill` does, then
insert it. They are called on the model builder, not on `ModelQuery`:

```java
Member.query.on(db).query().fillAndInsert(rows);
int added = Member.query.on(db).query().fillAndInsertOrIgnore(rows);
Object id = Member.query.on(db).query().fillAndInsertGetId(row);
```

The fill skips the fillable guard, so never pass request data to these methods unchecked. Casts
apply, unique ids and timestamps are set, and a `created_at` or `updated_at` the row already has is
kept. `beforeWrite()` runs on each row, but no model event fires. The list forms write every row in
one statement, so all rows need the same columns, and a large batch must stay under the binding
limit (999 on SQLite before 3.32).

## Query shortcuts

`whereBelongsTo` filters the children of a parent through the `belongsTo` relation the child
declares. Without a name it uses the parent's class name in camel case, so `user` for `User`. Under
R8 or other renaming, pass the relation name:

```java
ModelQuery<Post> posts = Post.query.on(db);
posts.query().whereBelongsTo(ada).get();                          // relation "user"
posts.query().whereBelongsTo(ada, "author").get();
posts.query().whereBelongsTo(List.of(ada, sam), "author").get();  // one in clause
posts.query().where("pinned", true).orWhereBelongsTo(ada, "author").get();
```

The methods refuse an empty collection, a parent of the wrong class and a parent without a key
value.

`pluck(column, key)` returns a map from the key column to the column, with raw values as
`pluck(column)` gives them:

```java
Map<Object, Object> ids = Member.query.on(db).query().pluck("id", "code");   // code -> id
```

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

## Method reference

Public methods that the sections above do not cover, one row per method name (overloads share a row).

| Method | On | What it does | Example |
|---|---|---|---|
| `getInteger` `getLong` `getDouble` `getBigDecimal` `getBoolean` `getInstant` | `Model` | Typed reads of an attribute: from any whole number or numeric text (`getInteger`, `getLong`), a number (`getDouble`), an exact decimal (`getBigDecimal`), a boolean (`getBoolean`: non-zero or `1`/`true`) or a moment (`getInstant`). | `post.getInteger("views")` |
| `hasAttribute` | `Model` | Returns whether the model holds an attribute, even a null one. | `post.hasAttribute("title")` |
| `hasCast` `getCasts` `mergeCasts` `withCasts` | `Model`, `EloquentBuilder` | Casts: `hasCast` tells whether an attribute has one, `getCasts` returns the resolved casts, `mergeCasts` adds casts to one instance and `withCasts` (on a query) casts columns of every model it reads. | `post.mergeCasts(Map.of("meta", "json"))` |
| `getOriginal` `getRawOriginal` `originalIsEquivalent` | `Model` | `getOriginal` returns an attribute's original value through its accessor or cast, `getRawOriginal` as stored with no cast, and `originalIsEquivalent` tells whether the current value equals the original. | `post.getRawOriginal("title")` |
| `isClean` `wasChanged` `getChanges` `getPrevious` | `Model` | Dirty tracking: `isClean` (no given attribute differs from its original), `wasChanged` and `getChanges` (what the last save changed) and `getPrevious` (the values it replaced). | `post.wasChanged("title")` |
| `syncOriginal` `syncOriginalAttribute` `syncOriginalAttributes` `syncChanges` `discardChanges` `setRawAttributes` | `Model` | Reset the change baseline: make current values the originals (all, one or several), record the last save's changes (`syncChanges`), put every attribute back to its original (`discardChanges`), or replace every attribute raw (`setRawAttributes`). | `post.discardChanges()` |
| `preventSilentlyDiscardingAttributes` | `Model` | Sets, for every model in the process, whether `fill` throws for keys it would otherwise drop silently. | `Model.preventSilentlyDiscardingAttributes(true)` |
| `getFillable` `getGuarded` `isFillable` `isGuarded` `isUnguarded` `totallyGuarded` | `Model` | Mass assignment settings: the fillable and guarded keys, whether one key may be set, whether guarding is off on this thread, and whether the model allows no mass assignment at all. | `post.isFillable("title")` |
| `getHidden` `getVisible` `setHidden` `setVisible` `makeHidden` `makeVisible` `getAppends` `setAppends` `append` `withoutAppends` | `Model` | Serialization lists: read or replace the hidden, visible and appended (computed) attributes, add to them (`makeHidden`, `append`), show hidden ones (`makeVisible`) or remove every appended one (`withoutAppends`). | `post.makeHidden("secret")` |
| `getTable` `getKeyName` `getKeyType` `getIncrementing` `getQualifiedKeyName` `qualifyColumn` `getForeignKey` `getPerPage` `getUniqueIdKind` | `Model` | Model settings as the model resolves them: table, primary key name and type, whether the database assigns the key, the key qualified by table (`users.id`), a column qualified by table, the foreign key name other tables use for this model, the default page size and the unique id kind. | `post.getQualifiedKeyName()` |
| `getConnection` `getConnectionName` `setConnection` `getQueryFactory` `newBaseQuery` | `Model` | Connection access: the model's connection and its name, binding the model to a query factory (`setConnection`), the factory it uses, and a new base query builder on the model's table. | `post.newBaseQuery().where("id", 1)` |
| `Casts.instant` | `Casts` | A cast that stores an `Instant` whatever the model's timestamp format, for `Blueprint.instant` columns. Timestamp columns also need `TimestampFormat.INSTANT`. | `.put("sent_at", Casts.instant())` |
| `getJsonCodec` `getDateFormat` `getTimestampFormat` `setClock` | `Model` | Time and JSON settings: the codec behind JSON casts and the JSON form, the pattern of text timestamps, how timestamps are written, and the clock the model reads timestamps from. | `post.setClock(clock)` |
| `getCreatedAtColumn` `getUpdatedAtColumn` `getDeletedAtColumn` `getQualifiedDeletedAtColumn` `usesTimestamps` | `Model` | Timestamp columns: the created-at, updated-at and deleted-at column names (the last one also qualified by table), and whether the model writes timestamps now. | `post.usesTimestamps()` |
| `freshTimestamp` `freshTimestampValue` `fromDateTime` `updateTimestamps` | `Model` | Timestamp helpers: the current moment from the model's clock, in the form the model stores, converting a moment to that form, and setting `updated_at` (and `created_at` on a new model) unless already dirty. | `post.updateTimestamps()` |
| `withoutTimestamps` `withoutTouchingOn` `touch` `touchQuietly` `touchOwners` | `Model` | Touching: `touch` updates the timestamps and saves, `touchQuietly` does it with listeners silenced, `touchOwners` sets `updated_at` on the relations named in `touches()`, `withoutTimestamps` and `withoutTouchingOn` run a callback with timestamps or owner touches off on this thread. | `post.touch()` |
| `decrement` | `Model`, `EloquentBuilder` | Subtracts an amount (1 by default) from a column of this model's row, as `increment` does for adding; returns the affected rows. | `post.decrement("stock")` |
| `is` `isNot` | `Model` | Tell whether another model is the same row (same key, table and connection name), or not. | `a.is(b)` |
| `fresh` | `Model`, `ModelCollection` | Returns a new instance loaded from the database by the key as last read (a collection returns the fresh list). | `post.fresh()` |
| `newInstance` `withoutRelations` `replicate` `replicateQuietly` | `Model` | Copies: `newInstance` makes an empty instance bound to the same connection and clock, `withoutRelations` copies the model without loaded relations, `replicate` makes an unsaved copy without the key and timestamps, and `replicateQuietly` copies with the registered listeners silenced. | `post.replicate()` |
| `forceDeleteQuietly` `restoreQuietly` `updateQuietly` | `Model` | Delete for good, restore or update a model with the registered listeners silenced. | `post.updateQuietly(Map.of("title", "x"))` |
| `isForceDeleting` `isSoftDeletable` `wasRecentlyCreated` | `Model` | State checks: a `forceDelete()` is running, the model opts in to soft deletes, the last save inserted the row. | `post.wasRecentlyCreated()` |
| `getMorphClass` | `Model` | Returns the name stored in a morph type column for this model. | `post.getMorphClass()` |
| `relation` `getRelation` `getRelationValue` `getRelations` `relationLoaded` `setRelation` `setRelations` `unsetRelation` | `Model` | Relation state: build a relation by name (`relation`), read a loaded one without loading (`getRelation`), read it or load it lazily (`getRelationValue`), read all loaded relations, test whether one is loaded, and set, replace or forget loaded relations. | `post.relationLoaded("user")` |
| `loadAggregate` `loadAvg` `loadMax` `loadMin` `loadSum` `loadMorph` `loadMorphCount` | `Model`, `ModelCollection` | Load aggregates of a related column onto the model (`loadSum`, `loadAvg`, `loadMax`, `loadMin`, `loadAggregate`), and load relations or counts onto the owner a morph-to relation has loaded, chosen by the owner's class (`loadMorph`, `loadMorphCount`). They also exist on `ModelCollection`. | `post.loadSum("comments", "votes")` |
| `count` | `EloquentBuilder` | Counts the matching rows (the aggregate forms `sum`, `avg`, `min` and `max` work the same way). | `Post.query().where("published", true).count()` |
| `all` | `ModelQuery` | Returns every model of the table. | `Post.query().all()` |
| `destroy` `forceDestroy` | `ModelQuery` | Load the models with the given keys and delete each one, so each runs its hooks (`forceDestroy` includes trashed ones and deletes them for good). | `Post.query().destroy(1, 2)` |
| `forceCreate` | `EloquentBuilder`, `ModelQuery` | Fills a new model from a map ignoring the guards, and saves it. | `Post.query().forceCreate(attrs)` |
| `createOrFirst` | `EloquentBuilder` | Creates a model; when a unique index refuses it, returns the existing match instead. | `Post.query().createOrFirst(attrs)` |
| `findMany` `findOr` `findOrNew` `firstOr` `firstOrFail` `firstWhere` `sole` | `EloquentBuilder`, `ModelQuery` | More finders: `findMany` (several keys, no query for an empty list), `findOr`/`firstOr` (callback result when none), `findOrNew` (a new unsaved model), `firstOrFail`, `firstWhere` (column equals value) and `sole` (the only match, reading at most two rows). | `Post.query().firstWhere("slug", s)` |
| `each` `lazyById` | `EloquentBuilder` | Read in bulk: `each` hands every model to a predicate (until it returns false); `lazyById` returns the models as a lazy sequence read in chunks by primary key. | See [Chunks, lazy reads, cursors and pages](#chunks-lazy-reads-cursors-and-pages) |
| `hydrate` | `EloquentBuilder`, `ModelQuery` | Builds models from raw rows without running a query. | `Post.query().hydrate(rows)` |
| `getModel` `getModelClass` `newModel` | `EloquentBuilder`, `ModelQuery` | The model the query is built on: an instance of it (`getModel`), its class (`getModelClass`), or a new empty model bound to the entry's connection and clock (`newModel`). | `Post.query().newModel()` |
| `using` `withClock` | `ModelQuery` | Return an entry whose models find their factory by connection name in a resolver (`using`), or read timestamps from a given clock (`withClock`). | `Post.query().withClock(clock)` |
| `preventsLazyLoading` | `ModelQuery` | Returns whether lazy loading is prevented, as set by `preventLazyLoading(boolean)`. | `Post.query().preventsLazyLoading()` |
| `addGlobalScopes` `clearGlobalScopes` `getGlobalScope` `getGlobalScopes` `hasGlobalScope` `removeGlobalScope` `withGlobalScope` `withoutGlobalScopesExcept` `removedScopes` `scopes` | `ModelQuery`, `EloquentBuilder` | Scope registry: add several global scopes at once, clear, get, list, test or remove them by name, add one to a single query, drop every scope but the named ones, list the removed names, and apply several local scopes in order (`scopes`). | `Post.query().withoutGlobalScopesExcept("tenant")` |
| `withoutTrashed` | `EloquentBuilder` | Excludes soft-deleted rows, also after `withTrashed()`. | `Post.query().withoutTrashed()` |
| `withOnly` `without` `getEagerLoads` | `EloquentBuilder` | Eager loads: `withOnly` replaces every eager load, `without` removes eager loads by exact path (`without("posts")` keeps `posts.comments`), `getEagerLoads` returns the current set. | `Post.query().withOnly("user")` |
| `toBase` `getBindings` `toSql` `lock` `lockForUpdate` `sharedLock` | `EloquentBuilder` | Reach the SQL layer: a copy of the wrapped query builder with global scopes applied (`toBase`), the select's bindings and SQL (`getBindings`, `toSql`), and row locks (`lock`, `lockForUpdate`, `sharedLock`). | `Post.query().lockForUpdate()` |
| `forPage` `skip` `take` `reorder` `inRandomOrder` `oldest` `orderByDesc` `orderByRaw` `pluck` `value` `selectRaw` `leftJoin` | `EloquentBuilder` | Query builder methods that `EloquentBuilder` forwards, with the same meaning as on the query builder: paging (`forPage`, `skip`, `take`), ordering (`reorder`, `inRandomOrder`, `oldest`, `orderByDesc`, `orderByRaw`), reads (`pluck`, which also takes a key column as `pluck(column, key)` and returns a map, and `value`), `selectRaw` and `leftJoin`. | See [Query builder](query-builder.md) |
| `whereBelongsTo` `orWhereBelongsTo` | `EloquentBuilder` | Filters children by a parent through the `belongsTo` relation: by default the parent's class name in camel case, or the relation name given second. A collection gives one `in` clause. The `or` form joins with OR. | `posts.query().whereBelongsTo(ada, "author")` |
| `fillAndInsert` `fillAndInsertOrIgnore` `fillAndInsertGetId` | `EloquentBuilder` | Fill each row as `fill` does, without the fillable guard, then insert the rows in one statement (`fillAndInsertGetId` inserts one row and returns its key). | `Member.query.on(db).query().fillAndInsert(rows)` |
| `whereKey` `whereKeyNot` | `EloquentBuilder` | Constrain the qualified primary key: `users.id = ?`, or `in` for a collection (`whereKeyNot` excludes). | `Post.query().whereKey(ids)` |
| `whereGroup` `orWhereGroup` | `EloquentBuilder` | Add a parenthesised group of clauses built on an Eloquent builder for the same model (`orWhereGroup` joins with OR), as Laravel's `where(Closure)`. | `q.whereGroup(g -> g.where("a", 1).orWhere("b", 2))` |
| `whereInstantBetween` | `EloquentBuilder` | Adds a clause for moments in a half-open range. | `q.whereInstantBetween("created_at", from, to)` |
| `whereBetween` `whereNotBetween` `orWhereBetween` `whereColumn` `orWhereColumn` `whereDate` `whereDay` `whereMonth` `whereYear` `whereTime` `whereExists` `whereNotExists` `whereIn` `whereNotIn` `orWhereIn` `orWhereNotIn` `whereLike` `whereNotLike` `orWhereLike` `whereNot` `orWhereNot` `whereNull` `orWhereNull` `whereNotNull` `orWhereNotNull` `whereRaw` `orWhereRaw` | `EloquentBuilder` | The query builder's `where` family, also available on `EloquentBuilder` with the same meaning (`or...` forms join with OR). | See [Query builder](query-builder.md) |
| `whereDoesntHave` `orWhereDoesntHave` `orDoesntHave` `orHas` `orWhereHas` `orWhereRelation` | `EloquentBuilder` | Relation existence with `OR` and negation: no related model matching a constraint (`whereDoesntHave`), the `or` forms, and an or condition on a related model's column (`orWhereRelation`). | `Post.query().whereDoesntHave("comments")` |
| `whereDoesntHaveMorph` `doesntHaveMorph` `orDoesntHaveMorph` `orHasMorph` `orWhereDoesntHaveMorph` `orWhereHasMorph` `whereMorphRelation` `whereMorphDoesntHaveRelation` `orWhereMorphRelation` `orWhereMorphDoesntHaveRelation` `whereNotMorphedTo` `orWhereMorphedTo` `orWhereNotMorphedTo` | `EloquentBuilder` | Morph-to existence queries: an owner of one of the given types (or none), with a constraint or a column comparison, and whether a morph-to points at a target. The `or` forms join with OR. | `q.orHasMorph("imageable", Post.class)` |
| `contains` `modelKeys` `size` | `ModelCollection` | Collection basics: whether the list holds a model (the same row, or a model with a primary key), the primary keys in list order, and the number of models. | `posts.modelKeys()` |
| `hasMorePages` | `ModelPage`, `SimpleModelPage` | Returns whether a page follows this one. | `page.hasMorePages()` |
| `currentPage` `lastPage` | `ModelPage`, `SimpleModelPage` | Page numbers on a page object: the current page from 1, and the last page. | `page.lastPage()` |
| `nextCursor` `previousCursor` | `CursorModelPage` | Return the cursor of the page after, or before, this one. | `page.nextCursor()` |
