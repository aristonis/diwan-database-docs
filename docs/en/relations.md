# Relations

A relation is a typed method on the model plus a name in `relations()`. The map is how a name such
as `"posts"` reaches the method without reflection, so R8 cannot break it. Diwan checks the map
once per class on first use, and a mistake fails with `InvalidRelationException` naming the model
and the relation.

=== "Java"
    ```java
    public final class User extends Model {
        public static final ModelQuery<User> query = ModelQuery.of(User.class, User::new);

        @Override
        protected RelationMap<?> relations() {
            return RelationMap.of(User.class).add("posts", User::posts);
        }

        public HasMany<Post> posts() {
            return hasMany(Post.class, "user_id");      // hasOne works the same way
        }
    }

    public final class Post extends Model {
        public static final ModelQuery<Post> query = ModelQuery.of(Post.class, Post::new);

        @Override
        protected RelationMap<?> relations() {
            return RelationMap.of(Post.class).add("author", Post::author);
        }

        public BelongsTo<User> author() {
            return belongsTo(User.class, "user_id");    // the foreign key is required
        }
    }
    ```
=== "Kotlin"
    ```kotlin
    class User : Model() {
        override fun relations(): RelationMap<*> {
            return RelationMap.of(User::class.java).add("posts", User::posts)
        }

        fun posts(): HasMany<Post> {
            return hasMany(Post::class.java, "user_id")      // hasOne works the same way
        }

        companion object {
            val query: ModelQuery<User> = ModelQuery.of(User::class.java, ::User)
        }
    }

    class Post : Model() {
        override fun relations(): RelationMap<*> {
            return RelationMap.of(Post::class.java).add("author", Post::author)
        }

        fun author(): BelongsTo<User> {
            return belongsTo(User::class.java, "user_id")    // the foreign key is required
        }

        companion object {
            val query: ModelQuery<Post> = ModelQuery.of(Post::class.java, ::Post)
        }
    }
    ```

## Relation types

| Type | Declare with |
|---|---|
| One to one, one to many | `hasOne`, `hasMany`, `belongsTo` |
| Many to many | `belongsToMany` |
| Through another table | `hasOneThrough`, `hasManyThrough` |
| Polymorphic | `morphOne`, `morphMany`, `morphTo`, `morphToMany`, `morphedByMany` |
| One row picked from many | `latestOfMany`, `oldestOfMany`, `ofMany`, `one()` |

## Read a relation

A lazy read runs once and keeps the result on the model. `getAttribute("posts")` never loads a
relation.

=== "Java"
    ```java
    ModelCollection<Post> posts = user.relatedMany("posts");   // select * from posts where user_id = ?
    User author = post.related("author");                      // null when there is none
    ModelCollection<Post> recent = user.posts().where("published", true).latest().get();
    ```
=== "Kotlin"
    ```kotlin
    val posts: ModelCollection<Post> = user.relatedMany("posts")   // select * from posts where user_id = ?
    val author: User? = post.related("author")                     // null when there is none
    val recent: ModelCollection<Post> = user.posts().where("published", true).latest().get()
    ```

`withDefault()` on a `hasOne` or `belongsTo` returns an empty model when nothing is found.

## Eager loading

Eager load to avoid one query per model. Paths nest with dots, `name:col,...` selects columns (the
matching key is added), and a constraint narrows the related query:

=== "Java"
    ```java
    ModelCollection<User> all = users.with("posts.comments").get();   // three queries in all
    users.with("posts", q -> q.where("published", true)).get();
    users.query().with("posts:id,title").paginate(20, 1);

    all.load("posts.author");        // on a collection already read
    user.loadMissing("posts");       // only what is not loaded yet
    ```
=== "Kotlin"
    ```kotlin
    val all: ModelCollection<User> = users.with("posts.comments").get()   // three queries in all
    users.with("posts") { q -> q.where("published", true) }.get()
    users.query().with("posts:id,title").paginate(20, 1)

    all.load("posts.author")        // on a collection already read
    user.loadMissing("posts")       // only what is not loaded yet
    ```

Null keys are dropped, and long key lists are split to stay under the parameter limit of SQLite and
PostgreSQL. An eager constraint runs once per key chunk plus once, so keep it free of side effects.
It may not set `limit` or `offset`. `cursor()` refuses eager loads; `lazy()` loads them per page.

To catch N+1 queries in development, refuse lazy reads on models that came from a multi-row
result. It is a process-wide setting; call it once at startup:

=== "Java"
    ```java
    ModelQuery.preventLazyLoading(true);
    users.query().get().get(0).relatedMany("posts");   // LazyLoadingViolationException
    ```
=== "Kotlin"
    ```kotlin
    ModelQuery.preventLazyLoading(true)
    users.query().get()[0].relatedMany<Post>("posts")   // LazyLoadingViolationException
    ```

## has, whereHas and aggregates

=== "Java"
    ```java
    users.query().has("posts").get();
    users.query().has("posts", ">=", 3).get();
    users.query().whereHas("posts", q -> q.where("title", "like", "Java%")).get();
    users.query().doesntHave("posts.comments").get();
    users.query().whereRelation("posts", "published", true).get();
    ```
=== "Kotlin"
    ```kotlin
    users.query().has("posts").get()
    users.query().has("posts", ">=", 3).get()
    users.query().whereHas("posts") { q -> q.where("title", "like", "Java%") }.get()
    users.query().doesntHave("posts.comments").get()
    users.query().whereRelation("posts", "published", true).get()
    ```

These compile to `exists` subqueries. Count, sum or check related rows without loading them. Each
call adds one subselect to the query, named `<relation>_<function>_<column>`, or by `as`:

=== "Java"
    ```java
    users.query()
            .withCount("posts")                                        // posts_count
            .withCount(Map.of("posts as published", q -> q.where("published", true)))
            .withSum("orders", "total")                                // orders_sum_total
            .withExists("posts")                                       // posts_exists, a Boolean
            .get();

    all.loadCount("posts");              // the same aggregates on models already read
    user.loadExists(Map.of("posts", q -> q.where("published", true)));
    ```
=== "Kotlin"
    ```kotlin
    users.query()
        .withCount("posts")                                        // posts_count
        .withCount(mapOf("posts as published" to Consumer<EloquentBuilder<*>> { q -> q.where("published", true) }))
        .withSum("orders", "total")                                // orders_sum_total
        .withExists("posts")                                       // posts_exists, a Boolean
        .get()

    all.loadCount("posts")              // the same aggregates on models already read
    user.loadExists(mapOf("posts" to Consumer<EloquentBuilder<*>> { q -> q.where("published", true) }))
    ```

`withMin`, `withMax`, `withAvg` and `withAggregate(relation, column, function)` work the same way.
After `withCount`, call `addSelect`, not `select`: `select` replaces the columns and drops the
aggregate.

What a constraint closure may contain:

- In `has`, `whereHas` and `whereRelation`, the closure runs on the `exists` subquery. It may add
  `join`, `orderBy`, `limit`, `offset`, `groupBy` and `having`. Its `where` clauses form one
  group when they hold an `or`, so an `orWhere` cannot widen the relation's own match.
- With a count (`whereHas("posts", q -> ..., ">", 2)`), orders, limit and offset are dropped, and
  `groupBy` or `having` throw `IllegalArgumentException`.
- In `withCount` and the other aggregates, joins and `where` clauses work. `select`, `orderBy`,
  `limit` and `offset` are cleared. `groupBy`, `having`, `distinct` and unions throw
  `IllegalArgumentException`.

## Through, morph and one-of-many

=== "Java"
    ```java
    public HasManyThrough<Post> posts() {
        return hasManyThrough(Post.class, User.class);   // posts of the users of this country
    }

    public MorphMany<Comment> comments() { return morphMany(Comment.class, "commentable"); }
    public MorphTo<Model> commentable()  { return morphTo("commentable"); }
    public HasOne<Order> latestOrder()   { return hasOne(Order.class).latestOfMany(); }
    ```
=== "Kotlin"
    ```kotlin
    fun posts(): HasManyThrough<Post> {
        return hasManyThrough(Post::class.java, User::class.java)   // posts of the users of this country
    }

    fun comments(): MorphMany<Comment> = morphMany(Comment::class.java, "commentable")
    fun commentable(): MorphTo<Model> = morphTo("commentable")
    fun latestOrder(): HasOne<Order> = hasOne(Order::class.java).latestOfMany()
    ```

A through relation creates its far row without linking it to the middle row; create the middle
row yourself. Use the through relation's finders, pages and iterators like any other.

A morph relation stores an alias in `commentable_type`. Register every parent once at startup:

=== "Java"
    ```java
    Map<String, Class<? extends Model>> map = new LinkedHashMap<>();
    map.put("post", Post.class);
    map.put("video", Video.class);
    MorphMap.morphMap(map);
    ```
=== "Kotlin"
    ```kotlin
    val map = LinkedHashMap<String, Class<out Model>>()
    map["post"] = Post::class.java
    map["video"] = Video::class.java
    MorphMap.morphMap(map)
    ```

Without an alias, Diwan throws `ClassMorphViolationException`, unless you opt out with
`MorphMap.requireMorphMap(false)`. Filter on a `morphTo` with `whereHasMorph`, `hasMorph` and
`whereMorphedTo`, and eager load per parent class with `withMorph`. `has` and `whereHas` are
refused on a `morphTo`.

`latestOfMany`, `oldestOfMany` and `ofMany(column, "min" | "max")` pick one row per parent.
`hasMany(...).one()` turns a many relation into one. Conditions on the relation filter the picked
row afterwards. Put the condition in the `ofMany` constraint to pick the latest paid order.

## Write through a relation

The foreign key is set for you. A parent with no key yet throws `IllegalStateException` before any
SQL.

=== "Java"
    ```java
    Post post = user.posts().create(Map.of("title", "Hello"));   // user_id set
    user.posts().saveMany(List.of(draftA, draftB));             // no transaction
    post.author().associate(otherUser);                         // sets user_id and the relation
    post.author().dissociate();
    ```
=== "Kotlin"
    ```kotlin
    val post = user.posts().create(mapOf("title" to "Hello"))   // user_id set
    user.posts().saveMany(listOf(draftA, draftB))              // no transaction
    post.author().associate(otherUser)                         // sets user_id and the relation
    post.author().dissociate()
    ```

## Pivot writes

`belongsToMany` reads through a joining table, `role_user` by default with `user_id` and `role_id`.
Each related row carries its joining row as `pivot`.

=== "Java"
    ```java
    public BelongsToMany<Role> roles() {
        return belongsToMany(Role.class).withPivot("status").withTimestamps();
    }

    user.roles().attach(5, Map.of("status", "active"));
    user.roles().detach(5);
    SyncResult changes = user.roles().sync(List.of(1, 2, 3));
    changes.getAttached();   // ids added
    changes.getDetached();   // ids removed
    user.roles().syncWithoutDetaching(List.of(4));
    user.roles().toggle(List.of(1, 9));
    user.roles().updateExistingPivot(1, Map.of("status", "paused"));

    Pivot.of(user.roles().first().orElseThrow()).getString("status");   // read the joining row
    user.roles().wherePivot("status", "active").get();
    ```
=== "Kotlin"
    ```kotlin
    fun roles(): BelongsToMany<Role> {
        return belongsToMany(Role::class.java).withPivot("status").withTimestamps()
    }

    user.roles().attach(5, mapOf("status" to "active"))
    user.roles().detach(5)
    val changes: SyncResult = user.roles().sync(listOf(1, 2, 3))
    changes.attached   // ids added
    changes.detached   // ids removed
    user.roles().syncWithoutDetaching(listOf(4))
    user.roles().toggle(listOf(1, 9))
    user.roles().updateExistingPivot(1, mapOf("status" to "paused"))

    Pivot.of(user.roles().first().orElseThrow()).getString("status")   // read the joining row
    user.roles().wherePivot("status", "active").get()
    ```

`ids` can be an id, a related model, a collection of either, or a map from id to pivot attributes.
Index the joining table on a unique (`user_id`, `role_id`) and on `role_id`. A chain of `or` clauses
on a many-to-many read is not grouped, so group it with the relation's `where(q -> ...)`. A related
column named `pivot_x` moves into the joining row. A `morphToMany` pivot always carries the
relation's type; a different type value in the attributes throws `IllegalArgumentException`.

## Touch parent timestamps

Name relations in `touches()` to update a parent's `updated_at` when a child changes:

=== "Java"
    ```java
    public final class Comment extends Model {
        @Override
        protected Set<String> touches() { return Collections.singleton("post"); }
    }

    comment.save();    // then: update posts set updated_at = ? where posts.id = ?
    Model.withoutTouching(Post.class, () -> importComments(rows));   // this thread only
    ```
=== "Kotlin"
    ```kotlin
    class Comment : Model() {
        override fun touches(): Set<String> = Collections.singleton("post")
    }

    comment.save()    // then: update posts set updated_at = ? where posts.id = ?
    Model.withoutTouching(Post::class.java) { importComments(rows) }   // this thread only
    ```

A save that changed something, and a delete, each run one raw `UPDATE` per touched owner, with no
events and no `SELECT`. The owner object in memory keeps its old `updated_at`; call `refresh()` to
reload it. Wrap bulk imports in `withoutTouching`.

## Save a graph and link children

`push()` saves a model, then every loaded relation under it, depth first. It returns `false` at the
first failed save and runs no transaction. `chaperone("post")` on a `hasMany` sets the parent on
each child with no query.

## Performance and R8

- Index each child foreign key that `has`, `whereHas`, `withCount` and `load*` use. Each runs a
  correlated subquery per outer row.
- Touch a hot parent from many children and you create lock waits (`SQLITE_BUSY` on SQLite).
- A class literal such as `Post.class` does not run the class's static initializer. Touch each
  model's `query` entry at startup, before a relation names it.
- R8 renames classes, and Diwan derives the default foreign key, table, pivot table and
  `chaperone` guess from the class name. On Android, pass the keys, tables and names explicitly,
  as the examples here do. See [Android](android.md).

## Method reference

Public methods that the sections above do not cover, one row per method name (overloads share a row).

| Method | On | What it does | Example |
|---|---|---|---|
| `getParent` `getRelated` `getQuery` `getResults` `getRelationName` | all relations | Inspect a relation: the model it was built on, the related model instance, the relation query with the lazy constraints applied, its result in the relation's shape (one model or null for a single relation, a collection for a many relation), and its name. | `post.relation("comments").getResults()` |
| `oldest` `orderByDesc` `take` `whereColumn` `whereIn` `whereNotIn` `whereNull` `whereNotNull` `scopes` `withoutTrashed` `withoutGlobalScopesExcept` | all relations | Query methods a relation forwards to its related query, with the meaning they have on `EloquentBuilder`: `oldest`, `orderByDesc`, `take`, `whereColumn`, `whereIn`, `whereNotIn`, `whereNull`, `whereNotNull`, `scopes`, `withoutTrashed`, `withoutGlobalScopesExcept`. | `post.relation("comments").oldest()` |
| `rawUpdate` | all relations | Runs an UPDATE of the given columns over the lazy query, with the clauses added to the relation. | `rel.rawUpdate(Map.of("seen", true))` |
| `touch` | all relations | Sets the update timestamp of every related row the relation reads to now, in one raw `UPDATE`: no select, no events, no casts. | `rel.touch()` |
| `createMany` | `HasOne`, `HasMany`, `BelongsToMany`, `MorphOne`, `MorphMany`, `MorphToMany` | Creates one related model per record, in order, as `create` does. | `user.posts().createMany(List.of(a, b))` |
| `getForeignKeyName` `getLocalKeyName` `getParentKey` `getQualifiedForeignKeyName` `getMorphType` `getMorphTypeName` `getMorphClass` | `HasOne`, `HasMany`, `BelongsTo`, `MorphOne`, `MorphMany`, `MorphTo`, `HasOneThrough`, `HasManyThrough`, `MorphPivot`, `MorphToMany` | Key names of has-one/has-many (and morph) relations: the foreign key column on the related table (plain or qualified), the parent's column it points at, the parent's value of that key, the morph type column and the parent's morph class stored in it. | `user.posts().getForeignKeyName()` |
| `inverse` `withoutChaperone` `withoutInverse` | `HasOne`, `HasMany`, `MorphOne`, `MorphMany`, `BelongsToMany`, `MorphToMany` | Child-to-parent linking: `inverse` sets the parent on every child under the guessed inverse name (same as `chaperone`); `withoutChaperone` and `withoutInverse` stop that linking. | `user.posts().inverse()` |
| `isOneOfMany` `ofManyAs` | `HasOne`, `MorphOne`, `HasOneThrough` | One-of-many: whether the relation was turned into one, and naming its joined subquery. | See [Through, morph and one-of-many](#through-morph-and-one-of-many) |
| `getChild` `getOwnerKeyName` `getQualifiedOwnerKeyName` | `BelongsTo`, `MorphTo` | Belongs-to key names: the model holding the foreign key (same as `getParent`), the owner's key column, and that column qualified by the owner's table. | `post.relation("user").getOwnerKeyName()` |
| `createOrFirst` `findMany` `findOr` `findOrNew` `firstOr` `firstOrFail` `firstWhere` `sole` `each` `lazyById` | `BelongsToMany`, `MorphToMany`, `HasOneThrough`, `HasManyThrough` | Finders and readers on many-style relations, with the meaning they have on `EloquentBuilder`, limited to the relation's rows. | `user.posts().firstOrFail()` |
| `findSole` | `HasOneThrough`, `HasManyThrough` | Finds the only related model with the given key, reading at most two rows, so a key that joins to several through rows is refused. | `country.posts().findSole(5)` |
| `getForeignPivotKeyName` `getRelatedPivotKeyName` `getParentKeyName` `getRelatedKeyName` `getQualifiedForeignPivotKeyName` `getQualifiedRelatedPivotKeyName` `getQualifiedParentKeyName` `getQualifiedRelatedKeyName` `getTable` | `Pivot`, `BelongsToMany`, `MorphToMany` | Key and table names of a many-to-many relation: the pivot columns that hold the parent's and the related model's keys, the parent's and related model's columns they point at (plain or qualified), and the pivot table. | `rel.getTable()` |
| `getPivotAccessor` `getPivotClass` `getPivotColumns` `createdAt` `updatedAt` `using` | `BelongsToMany`, `MorphToMany` | Pivot settings: the name the pivot is stored under on each related model, its class, the extra pivot columns, the timestamp columns when the relation keeps them, and `using` to build pivots as a custom class. | `rel.getPivotColumns()` |
| `newPivot` `newExistingPivot` `newPivotQuery` `newPivotStatement` | `BelongsToMany`, `MorphToMany` | Build pivot objects and queries: `newPivot` for one row, `newExistingPivot` for a row already in the database, `newPivotQuery` for a query on the pivot table scoped to the parent, `newPivotStatement` for one with no condition at all. | `rel.newPivotQuery()` |
| `wherePivotBetween` `wherePivotNotBetween` `wherePivotIn` `wherePivotNotIn` `wherePivotNull` `wherePivotNotNull` `orWherePivot` `orWherePivotBetween` `orWherePivotNotBetween` `orWherePivotIn` `orWherePivotNotIn` `orWherePivotNull` `orWherePivotNotNull` | `BelongsToMany`, `MorphToMany` | Constrain the relation on a pivot column: between, not between, in, not in, null and not null. The `orWherePivot...` forms join with OR. | `rel.wherePivotIn("role", roles)` |
| `orderByPivot` `orderByPivotDesc` | `BelongsToMany`, `MorphToMany` | Order the query by a pivot column, ascending or descending. | `rel.orderByPivot("position")` |
| `withPivotValue` | `BelongsToMany`, `MorphToMany` | Filters the pivot table on `column = value` and records the pair, so the pivot's value for that column is known. | `rel.withPivotValue("type", "admin")` |
| `syncWithPivotValues` | `BelongsToMany`, `MorphToMany` | Syncs the ids and writes the same pivot attributes for every one of them; a shared value wins over a per-id value of the same column. | `rel.syncWithPivotValues(ids, Map.of("active", true))` |
| `isInverse` `getQualifiedMorphTypeName` | `MorphToMany` | Morph many-to-many: whether this is the inverse side (`morphedByMany`), and the type column of the pivot table qualified by that table. | `rel.isInverse()` |
| `getFirstKeyName` `getSecondLocalKeyName` `getQualifiedFirstKeyName` `getQualifiedSecondLocalKeyName` `getQualifiedLocalKeyName` `getQualifiedFarKeyName` | `HasOneThrough`, `HasManyThrough` | Key names of a through relation: the through table's column that holds the far parent's key, the column the second key points at, and the far parent's and related table's columns, qualified by their tables where the name says so. | `rel.getQualifiedFirstKeyName()` |
| `throughParentSoftDeletes` `withTrashedParents` | `HasOneThrough`, `HasManyThrough` | Through relations and soft deletes: whether the through model soft-deletes (so trashed through parents are left out), and `withTrashedParents` keeps them. | `rel.withTrashedParents()` |
| `fromAttributes` `fromRawAttributes` `setPivotKeys` `setRelatedModel` `getRelatedModel` `getPivotParent` | `Pivot` | Build and wire a `Pivot`: `fromAttributes` and `fromRawAttributes` build one for a row read through a parent model (the second sets attributes raw), `setPivotKeys` sets the parent and related key columns, `setRelatedModel`/`getRelatedModel` set and read the related model, `getPivotParent` returns the parent it was read through. | `pivot.getPivotParent()` |
| `getCreatedAtColumn` `getUpdatedAtColumn` `fresh` `decrement` | `Pivot` | `Pivot` as a model: its creation and update timestamp columns, a fresh copy from the database, and decrementing a numeric column. | `pivot.fresh()` |
| `empty` `modelClass` `names` `resolve` | `RelationMap` | `RelationMap`: `empty` returns the map of a model with no relations, `modelClass` the class it was built for, `names` the relation names in the order they were added, and `resolve` builds a relation by name for a model. | `model.relations().names()` |
