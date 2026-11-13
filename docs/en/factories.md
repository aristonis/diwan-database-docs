# Factories

A factory builds models for tests and seeding. You write one definition, the attributes of a
typical row, and ask for one model or many, saved or not. States change the definition for one
call, and sequences vary it from row to row.

Factories live in `diwan-database-eloquent`, in the package
`org.aristonis.diwan.database.eloquent.factory`. They have two public types: `Factory` and `Sequence`. Related models, owners and recycling are on [Factory relations](factory-relations.md); that page adds a third type, `RecycleMode`.

Diwan has no fake or random data. The definition is your own lambda: a fixed value, a counter, or
any data library you already use. Nothing on this page needs a library.

## Define a factory

`Factory.of` takes the model entry and a `Supplier` of the attributes:

=== "Java"
    ```java
    Factory<User> users = Factory.of(User.query.on(manager.query()), () -> Map.of(
        "name", "Ada",
        "email", "ada@example.com",
        "role", "member"));

    User ada = users.create();   // saved, with id and timestamps
    ```
=== "Kotlin"
    ```kotlin
    val users: Factory<User> = Factory.of(User.query.on(manager.query())) {
        mapOf(
            "name" to "Ada",
            "email" to "ada@example.com",
            "role" to "member",
        )
    }

    val ada: User = users.create()   // saved, with id and timestamps
    ```

A factory never changes. Every method below returns a new factory, so one factory can be shared by
many tests, and a state added in one test never leaks into another.

A factory also fills attributes the model does not list in `fillable()`, so the definition may set
any column.

### A subclass

For a model you build often, extend `Factory` and put the definition in `definition()`. Name each
state in a method that returns `Factory<M>`:

=== "Java"
    ```java
    public final class UserFactory extends Factory<User> {
        public UserFactory(QueryFactory db) {
            super(User.query.on(db));
        }

        @Override
        protected Map<String, Object> definition() {
            return Map.of("name", "Ada", "email", "ada@example.com", "role", "member");
        }

        public Factory<User> admin() {
            return set("role", "admin");
        }
    }

    List<User> admins = new UserFactory(manager.query()).admin().count(3).createMany();
    ```
=== "Kotlin"
    ```kotlin
    class UserFactory(db: QueryFactory) : Factory<User>(User.query.on(db)) {
        override fun definition(): Map<String, Any> {
            return mapOf("name" to "Ada", "email" to "ada@example.com", "role" to "member")
        }

        fun admin(): Factory<User> {
            return set("role", "admin")
        }
    }

    val admins: List<User> = UserFactory(manager.query()).admin().count(3).createMany()
    ```

The state method returns `Factory<User>`, not `UserFactory`, so the named states of a subclass are
reached first and the fluent calls follow: `new UserFactory(db).admin().count(3)`.

## States and set

A state changes the attributes for the calls that follow. `state(Map)` replaces the keys it names.
`set(name, value)` replaces one key. `state(UnaryOperator)` receives a read-only copy of the
attributes built so far and returns the keys to replace:

=== "Java"
    ```java
    Factory<User> admins = users.state(Map.of("role", "admin"));
    Factory<User> renamed = users.set("name", "Grace");
    Factory<User> derived = users.state(soFar -> Map.of("email", soFar.get("name") + "@example.org"));
    ```
=== "Kotlin"
    ```kotlin
    val admins: Factory<User> = users.state(mapOf("role" to "admin"))
    val renamed: Factory<User> = users.set("name", "Grace")
    val derived: Factory<User> = users.state { soFar -> mapOf("email" to "${soFar["name"]}@example.org") }
    ```

States and `set` fill the model through `forceFill`, which skips `fillable` and `guarded`, so never
pass request data to them. `state(Map)` copies the map shallowly, so mutable values inside it are
shared between factories.

States apply in the order you add them. A later state wins over an earlier one and over the
definition. A key keeps its place when it is replaced.

## Values

Each value in a definition, a state or `set` is one of three things:

| Value | Meaning |
|---|---|
| a plain object | used as it is |
| a `Supplier` | called with no argument, once for each model |
| a `Function<Map<String, Object>, Object>` | called with a copy of the attributes resolved so far |

A result is used as it is: a `Supplier` that returns a function stores that function. A `Supplier`
is tested before a `Function`.

A lambda in a map needs a target type, so declare it first:

=== "Java"
    ```java
    AtomicInteger counter = new AtomicInteger();
    Supplier<Object> number = () -> counter.incrementAndGet();
    Function<Map<String, Object>, Object> email =
        soFar -> soFar.get("name").toString().toLowerCase() + "@example.com";

    Factory<User> numbered = Factory.of(User.query.on(manager.query()), () -> {
        Map<String, Object> attrs = new LinkedHashMap<>();
        attrs.put("name", "User");
        attrs.put("email", email);   // sees name, resolved first
        attrs.put("badge", number);  // a new number for each model
        return attrs;
    });
    ```
=== "Kotlin"
    ```kotlin
    val counter = AtomicInteger()
    val number = Supplier<Any> { counter.incrementAndGet() }
    val email = Function<Map<String, Any?>, Any> { soFar ->
        soFar["name"].toString().lowercase() + "@example.com"
    }

    val numbered: Factory<User> = Factory.of(User.query.on(manager.query())) {
        linkedMapOf("name" to "User", "email" to email, "badge" to number)
    }
    ```

A `Function` sees the keys that come before it in the same map, so use a map with a stable key
order (`LinkedHashMap`, `linkedMapOf`) when one value depends on another. `Map.of` has no stable
order; for a dependent value put it in a later state instead.

If a `Function` expects another input type, its `ClassCastException` is rethrown as an
`IllegalArgumentException` that names the attribute and the model class, never the value. The
original is the cause.

### Your own data

To get names, addresses or random numbers, pass a lambda that calls the library you prefer. Here
is one with Datafaker, added to your own build:

=== "Java"
    ```java
    Faker faker = new Faker();
    Supplier<Object> name = () -> faker.name().fullName();
    Supplier<Object> email = () -> faker.internet().emailAddress();

    Factory<User> users = Factory.of(User.query.on(manager.query()), () -> Map.of(
        "name", name,
        "email", email));
    ```
=== "Kotlin"
    ```kotlin
    val faker = Faker()

    val users: Factory<User> = Factory.of(User.query.on(manager.query())) {
        mapOf(
            "name" to Supplier<Any> { faker.name().fullName() },
            "email" to Supplier<Any> { faker.internet().emailAddress() },
        )
    }
    ```

## Count

`count(n)` sets how many models the plural methods build. It is read by `makeMany()`,
`createMany()`, `createManyQuietly()`, `rawMany()` and `insert()`. The last `count` wins. Without
it, they build one.

The singular methods `make()`, `create()`, `createQuietly()` and `raw()` always build exactly one
and ignore `count`. The forms that take a number, such as `makeMany(5)`, use that number and ignore
`count`. A count below one builds nothing and returns an empty list.

## Make and create

`make()` builds a model in memory and does not save it. `makeMany()` builds a list.

=== "Java"
    ```java
    User draft = users.make();                       // not saved: draft.exists() is false
    List<User> drafts = users.makeMany(5);
    ```
=== "Kotlin"
    ```kotlin
    val draft: User = users.make()                   // not saved: draft.exists() is false
    val drafts: List<User> = users.makeMany(5)
    ```

`create()` builds, saves and returns the model. `createMany()` does the same for a list, one save
for each model. `createQuietly()` and `createManyQuietly()` save without firing model events, one
mute for the whole batch.

=== "Java"
    ```java
    User ada = users.create();
    List<User> five = users.count(5).createMany();
    List<User> silent = users.createManyQuietly(3);   // no model event fires
    ```
=== "Kotlin"
    ```kotlin
    val ada: User = users.create()
    val five: List<User> = users.count(5).createMany()
    val silent: List<User> = users.createManyQuietly(3)   // no model event fires
    ```

`create()` throws `IllegalStateException` when a model event hook stops the save or when no row was
stored. The message names the model class. An error from the save itself reaches you unchanged, and
the `afterCreating` hooks do not run for that model.

## Raw attributes

`raw()` returns the resolved attributes as a map and builds no model. `rawMany()` returns a list of
maps. Use it for request bodies and fixtures.

=== "Java"
    ```java
    Map<String, Object> body = users.set("role", "admin").raw();
    List<Map<String, Object>> bodies = users.rawMany(3);
    ```
=== "Kotlin"
    ```kotlin
    val body: Map<String, Any> = users.set("role", "admin").raw()
    val bodies: List<Map<String, Any>> = users.rawMany(3)
    ```

Each map is new and yours to change.

## Insert

`insert()` writes every row in one statement and returns nothing:

=== "Java"
    ```java
    users.insert(1000);
    users.count(1000).insert();
    ```
=== "Kotlin"
    ```kotlin
    users.insert(1000)
    users.count(1000).insert()
    ```

The statement goes through the model's insert path, so casts and timestamps apply. No model is
built, so no `afterMaking` or `afterCreating` hook runs and no model event fires, though
`beforeWrite()` still runs on each row. With a count below one, nothing is written.

One statement has a binding limit (999 on SQLite before 3.32), so split a very large insert into
batches. Every row must have the same keys. A state that adds a key to some rows only (a
sequence with different keys in each entry) fails with `IllegalArgumentException`.

## Hooks

`afterMaking(hook)` runs for each model after it is built, by `make`, `makeMany`, `create` and
`createMany`. `afterCreating(hook)` runs for each model after it is saved, by `create`,
`createMany` and the quiet forms. Hooks run in the order you add them.

=== "Java"
    ```java
    Factory<User> withPosts = users
        .afterMaking(user -> user.setAttribute("name", "Ada Lovelace"))
        .afterCreating(user -> posts.create(Map.of("user_id", user.getKey(), "title", "Hello")));
    ```
=== "Kotlin"
    ```kotlin
    val withPosts: Factory<User> = users
        .afterMaking { user -> user.setAttribute("name", "Ada Lovelace") }
        .afterCreating { user -> posts.create(mapOf("user_id" to user.key, "title" to "Hello")) }
    ```

`withoutAfterMaking()` and `withoutAfterCreating()` drop the hooks added so far. A hook added after
them still runs. `insert` and `raw` run no hook.

## Connection

`connection(connection)` builds and saves on another connection. Without it, the factory uses the
connection the model entry was bound to:

=== "Java"
    ```java
    User report = users.connection(reportingConnection).create();
    ```
=== "Kotlin"
    ```kotlin
    val report: User = users.connection(reportingConnection).create()
    ```

## Trashed

`trashed()` marks the model as soft deleted: it sets the deleted-at column, one day before now by
default. `trashed(Instant)` sets that moment. The column comes from the model, so a model that
renames it works too.

=== "Java"
    ```java
    Post old = postFactory.trashed().create();
    Post gone = postFactory.trashed(Instant.parse("2026-01-01T00:00:00Z")).create();
    ```
=== "Kotlin"
    ```kotlin
    val old: Post = postFactory.trashed().create()
    val gone: Post = postFactory.trashed(Instant.parse("2026-01-01T00:00:00Z")).create()
    ```

On a model without soft deletes, `trashed()` throws `IllegalStateException` when the rows are
built (by `make`, `create`, `raw` or `insert`), never silently. Building the factory itself runs nothing.

## Sequences

A sequence gives each model its own entry. The entries repeat when there are more models than
entries. `sequence(...)` takes maps; `forEachSequence(...)` also sets the count to the number of
entries:

=== "Java"
    ```java
    List<User> mixed = users
        .sequence(Map.of("role", "admin"), Map.of("role", "member"))
        .count(5)
        .createMany();                // admin, member, admin, member, admin

    List<User> pair = users
        .forEachSequence(Map.of("role", "admin"), Map.of("role", "member"))
        .createMany();                // exactly two models
    ```
=== "Kotlin"
    ```kotlin
    val mixed: List<User> = users
        .sequence(mapOf("role" to "admin"), mapOf("role" to "member"))
        .count(5)
        .createMany()                 // admin, member, admin, member, admin

    val pair: List<User> = users
        .forEachSequence(mapOf("role" to "admin"), mapOf("role" to "member"))
        .createMany()                 // exactly two models
    ```

A sequence restarts on each call. Two `createMany` calls on the same factory both start at the
first entry, because the position is the loop position of the call and nothing is kept between
calls. `make()`, `create()` and `raw()` always use the first entry.

### Sequence

For more control, build a `Sequence` and pass it to `sequence(Sequence)`:

| Method | What it does |
|---|---|
| `Sequence.of(maps...)` | entries from maps |
| `Sequence.byIndex(functions...)` | entries from `IntFunction` that receive the model position, counted from 0 |
| `and(map)`, `and(function)` | a new sequence with one more entry |
| `Sequence.crossJoin(lists...)` | every combination of one entry from each list; the first list changes slowest, a later key wins |
| `size()` | the number of entries |

A `Sequence` is immutable and safe to share. An `IntFunction` entry receives the model position
itself, not its place in the cycle, so it can number rows:

=== "Java"
    ```java
    Sequence numbered = Sequence.byIndex(i -> Map.of("name", "User " + i));

    Sequence grid = Sequence.crossJoin(
        List.of(Map.of("role", "admin"), Map.of("role", "member")),
        List.of(Map.of("active", true), Map.of("active", false)));

    List<User> all = users.sequence(grid).count(4).createMany();
    ```
=== "Kotlin"
    ```kotlin
    val numbered: Sequence = Sequence.byIndex(IntFunction { i -> mapOf("name" to "User $i") })

    val grid: Sequence = Sequence.crossJoin(
        listOf(mapOf("role" to "admin"), mapOf("role" to "member")),
        listOf(mapOf("active" to true), mapOf("active" to false)),
    )

    val all: List<User> = users.sequence(grid).count(4).createMany()
    ```

## Errors

Messages name a class, a position or an attribute, and never a value.

| When | Exception |
|---|---|
| `create` and the save is stopped by a hook or stores no row | `IllegalStateException` |
| `trashed` on a model without soft deletes | `IllegalStateException` |
| a `ClassCastException` while resolving a value | `IllegalArgumentException` naming the attribute and the model class, original as cause |
| `Sequence.of()` or `byIndex()` with no entry | `IllegalArgumentException` |
| `crossJoin` with no list, an empty list, or a result too large | `IllegalArgumentException` |
| `insert` with rows that have different keys | `IllegalArgumentException` |
| a `null` argument, a `null` key or a `null` sequence entry | `NullPointerException` |

## Related models

To build related models with `has`, `hasAttached` and `forParent`, to share parents with `recycle`, or to use a
parent in a state or hook, see [Factory relations](factory-relations.md).
