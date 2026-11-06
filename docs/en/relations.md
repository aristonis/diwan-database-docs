# Relations

A relation is a typed method on the model plus a name in `relations()`. The map is how a name such
as `"posts"` reaches the method without reflection, so R8 cannot break it. Diwan checks the map
once per class on first use, and a mistake fails with `InvalidRelationException` naming the model
and the relation.

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

```java
ModelCollection<Post> posts = user.relatedMany("posts");   // select * from posts where user_id = ?
User author = post.related("author");                      // null when there is none
ModelCollection<Post> recent = user.posts().where("published", true).latest().get();
```

`withDefault()` on a `hasOne` or `belongsTo` returns an empty model when nothing is found.

## Eager loading

Eager load to avoid one query per model. Paths nest with dots, `name:col,...` selects columns (the
matching key is added), and a constraint narrows the related query:

```java
ModelCollection<User> all = users.with("posts.comments").get();   // three queries in all
users.with("posts", q -> q.where("published", true)).get();
users.query().with("posts:id,title").paginate(20, 1);

all.load("posts.author");        // on a collection already read
user.loadMissing("posts");       // only what is not loaded yet
```

Null keys are dropped, and long key lists are split to stay under the parameter limit of SQLite and
PostgreSQL. An eager constraint runs once per key chunk plus once, so keep it free of side effects.
It may not set `limit` or `offset`. `cursor()` refuses eager loads; `lazy()` loads them per page.

To catch N+1 queries in development, refuse lazy reads on models that came from a multi-row
result. It is a process-wide setting; call it once at startup:

```java
ModelQuery.preventLazyLoading(true);
users.query().get().get(0).relatedMany("posts");   // LazyLoadingViolationException
```

## has, whereHas and aggregates

```java
users.query().has("posts").get();
users.query().has("posts", ">=", 3).get();
users.query().whereHas("posts", q -> q.where("title", "like", "Java%")).get();
users.query().doesntHave("posts.comments").get();
users.query().whereRelation("posts", "published", true).get();
```

These compile to `exists` subqueries. Count, sum or check related rows without loading them. Each
call adds one subselect to the query, named `<relation>_<function>_<column>`, or by `as`:

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

```java
public HasManyThrough<Post> posts() {
    return hasManyThrough(Post.class, User.class);   // posts of the users of this country
}

public MorphMany<Comment> comments() { return morphMany(Comment.class, "commentable"); }
public MorphTo<Model> commentable()  { return morphTo("commentable"); }
public HasOne<Order> latestOrder()   { return hasOne(Order.class).latestOfMany(); }
```

A through relation creates its far row without linking it to the middle row; create the middle
row yourself. Use the through relation's finders, pages and iterators like any other.

A morph relation stores an alias in `commentable_type`. Register every parent once at startup:

```java
Map<String, Class<? extends Model>> map = new LinkedHashMap<>();
map.put("post", Post.class);
map.put("video", Video.class);
MorphMap.morphMap(map);
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

```java
Post post = user.posts().create(Map.of("title", "Hello"));   // user_id set
user.posts().saveMany(List.of(draftA, draftB));             // no transaction
post.author().associate(otherUser);                         // sets user_id and the relation
post.author().dissociate();
```

## Pivot writes

`belongsToMany` reads through a joining table, `role_user` by default with `user_id` and `role_id`.
Each related row carries its joining row as `pivot`.

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

`ids` can be an id, a related model, a collection of either, or a map from id to pivot attributes.
Index the joining table on a unique (`user_id`, `role_id`) and on `role_id`. A chain of `or` clauses
on a many-to-many read is not grouped, so group it with the relation's `where(q -> ...)`. A related
column named `pivot_x` moves into the joining row. A `morphToMany` pivot always carries the
relation's type; a different type value in the attributes throws `IllegalArgumentException`.

## Touch parent timestamps

Name relations in `touches()` to update a parent's `updated_at` when a child changes:

```java
public final class Comment extends Model {
    @Override
    protected Set<String> touches() { return Collections.singleton("post"); }
}

comment.save();    // then: update posts set updated_at = ? where posts.id = ?
Model.withoutTouching(Post.class, () -> importComments(rows));   // this thread only
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
