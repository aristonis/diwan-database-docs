# Factory relations

A factory can build a whole graph of models: an author with posts, a post with an author, a post
with tags. You name a relation of the model, hand over the factory of the other side, and Diwan
fills the key columns for you.

This page continues [Factories](factories.md) and uses the same package,
`org.aristonis.diwan.database.eloquent.factory`. The one public type it adds is `RecycleMode`.

The examples use these models. Each factory is built as on the Factories page:

| Model | Relations |
|---|---|
| `Author` | `posts` (`HasMany`), `profile` (`HasOne`), `comments` (`MorphMany`) |
| `Post` | `author` (`BelongsTo`), `comments` (`MorphMany`), `tags` (`BelongsToMany`) |
| `Comment` | `commentable` (`MorphTo`) |
| `Tag` | none |

`authors`, `posts`, `comments` and `tags` are the factories of those models.

## Related models

`has(child, relation)` creates the children of every model the factory creates. The relation is
looked up by name on the model and may be `HasOne`, `HasMany`, `MorphOne` or `MorphMany`. The count
of the child factory is the number of children for each parent:

=== "Java"
    ```java
    Author ada = authors.has(posts.count(3), "posts").create();   // one author, three posts

    List<Author> team = authors.has(posts.count(2), "posts").createMany(2);   // two authors, two posts each
    ```
=== "Kotlin"
    ```kotlin
    val ada: Author = authors.has(posts.count(3), "posts").create()   // one author, three posts

    val team: List<Author> = authors.has(posts.count(2), "posts").createMany(2)   // two authors, two posts each
    ```

The parent is saved first. Then each child is created with the relation columns set: the foreign
key, and for a morph relation the type column too. These columns win over the child's own
definition and states, because the key is the relation's job.

Every parent gets its own batch of children. A `Sequence` on the child continues inside one batch
and starts again for the next parent. A child goes through all its own create steps: its states,
its hooks and its own `has` and `hasAttached` links.

A child can read its parent in a state or hook, see
[Parent-aware states and hooks](#parent-aware-states-and-hooks).

## Attach related models

`hasAttached` fills a many-to-many relation (`BelongsToMany` or `MorphToMany`). It creates the
related models and writes the pivot rows. A `MorphToMany` writes its type column itself.

=== "Java"
    ```java
    List<Tag> existingTags = tags.createMany(2);

    // five forms
    posts.hasAttached(tags.count(2), "tags");
    posts.hasAttached(tags.count(2), Map.of("weight", 1), "tags");
    posts.hasAttached(tags.count(2), p -> Map.of("note", "for " + p.getKey()), "tags");
    posts.hasAttached(tags.count(3), List.of(Map.of("weight", 1), Map.of("weight", 2)), "tags");
    posts.hasAttached(existingTags, Map.of("weight", 1), "tags");   // no tag is created

    Post post = posts.hasAttached(tags.count(2), "tags").create();
    ```
=== "Kotlin"
    ```kotlin
    val existingTags: List<Tag> = tags.createMany(2)

    // five forms
    posts.hasAttached(tags.count(2), "tags")
    posts.hasAttached(tags.count(2), mapOf("weight" to 1), "tags")
    posts.hasAttached(tags.count(2), { p: Model -> mapOf("note" to "for ${p.key}") }, "tags")
    posts.hasAttached(tags.count(3), listOf(mapOf("weight" to 1), mapOf("weight" to 2)), "tags")
    posts.hasAttached(existingTags, mapOf("weight" to 1), "tags")   // no tag is created

    val post: Post = posts.hasAttached(tags.count(2), "tags").create()
    ```

| Form | Pivot values |
|---|---|
| `hasAttached(factory, relation)` | none |
| `hasAttached(factory, Map, relation)` | the same map for every related model |
| `hasAttached(factory, Function<Model, Map>, relation)` | the function receives the saved parent and is called once for each related model |
| `hasAttached(factory, List<Map>, relation)` | entry `i % size` for related model `i`; when the related factory has no count, it is set to the list size; an empty list is an error |
| `hasAttached(List<Model>, Map, relation)` | the same map for each saved model in the list; nothing is created |

Pivot values are written as you give them. To cast them, give the relation a pivot class with
`using`. A model in the list must be saved.

The related factory is built like a child of `has`: it inherits the connection, goes through its
own create steps and may read the parent.

## Owners

`forParent(parent, relation)` sets the owner of a `BelongsTo` or `MorphTo` relation. The parent is
a factory or a saved model. The method is `forParent` because `for` is a Java keyword.

=== "Java"
    ```java
    Post fresh = posts.forParent(authors, "author").create();   // creates an author, then the post

    Author ada = authors.create();
    List<Post> hers = posts.forParent(ada, "author").createMany(3);

    Comment note = comments.forParent(posts, "commentable").create();   // sets the id and the type
    ```
=== "Kotlin"
    ```kotlin
    val fresh: Post = posts.forParent(authors, "author").create()   // creates an author, then the post

    val ada: Author = authors.create()
    val hers: List<Post> = posts.forParent(ada, "author").createMany(3)

    val note: Comment = comments.forParent(posts, "commentable").create()   // sets the id and the type
    ```

A factory parent is created once for each terminal call, so `count(3).forParent(authors, "author")`
gives three posts with one author. Two terminal calls create two authors. A model parent that is not
saved throws `IllegalStateException`.

For a `MorphTo` relation the parent's morph class is written to the type column. The key and type
columns come before the states, so `state`, `set` or a `Sequence` can still replace the key.

## Parent-aware states and hooks

A state or hook can take a second argument, the parent. For a child made by `has` or `hasAttached`
it is the saved parent. At the top level it is `null`:

=== "Java"
    ```java
    Factory<Post> titled = posts.state((soFar, parent) -> {
        Map<String, Object> out = new LinkedHashMap<>();
        if (parent != null) {
            out.put("title", "By " + parent.getAttribute("name"));
        }
        return out;
    });

    List<String> audit = new ArrayList<>();
    Factory<Author> logged = authors.has(
        posts.afterCreating((post, author) -> audit.add(post.getKey() + " by " + author.getKey())),
        "posts");
    ```
=== "Kotlin"
    ```kotlin
    val titled: Factory<Post> = posts.state { soFar, parent ->
        if (parent == null) mapOf<String, Any>() else mapOf("title" to "By ${parent.getAttribute("name")}")
    }

    val audit = mutableListOf<String>()
    val logged: Factory<Author> = authors.has(
        posts.afterCreating { post, author -> audit.add("${post.key} by ${author.key}") },
        "posts",
    )
    ```

| Method | Receives |
|---|---|
| `state(BiFunction<Map, Model, Map>)` | the attributes so far, the parent |
| `afterMaking(BiConsumer<M, Model>)` | the new model, the parent |
| `afterCreating(BiConsumer<M, Model>)` | the saved model, the parent |

The one-argument forms are unchanged. A `Sequence` still receives the index only.

## Nested values

A value in a definition may be a `Factory` or a `Model`. It is replaced by a key after all states
have run:

- a `Factory` creates a model and its key is used. When the recycle pool holds a model of that
  class, the pooled model is used instead and nothing is created.
- a saved `Model` gives its key.
- `null` stays `null`.

=== "Java"
    ```java
    Factory<Post> posts = Factory.of(Post.query.on(manager.query()), () -> {
        Map<String, Object> attrs = new LinkedHashMap<>();
        attrs.put("title", "Hello");
        attrs.put("author_id", authors);   // a Factory: an author is created for each post
        return attrs;
    });

    Author ada = authors.create();
    Post post = posts.create();
    Post other = posts.set("author_id", ada).create();   // a Model: its key is used
    ```
=== "Kotlin"
    ```kotlin
    val posts: Factory<Post> = Factory.of(Post.query.on(manager.query())) {
        linkedMapOf<String, Any>(
            "title" to "Hello",
            "author_id" to authors,   // a Factory: an author is created for each post
        )
    }

    val ada: Author = authors.create()
    val post: Post = posts.create()
    val other: Post = posts.set("author_id", ada).create()   // a Model: its key is used
    ```

A `Supplier` or `Function` may return a `Factory` or a `Model` as well. A `Factory` value that a
later state replaces creates no row. The nested factory inherits the connection and goes through
its own create steps.

## Recycle

By default every nested factory creates its own model. `recycle(models...)` gives the call a pool of
saved models, and a nested factory takes one of the right class from the pool instead of creating
one. The pool serves `forParent` factories and nested `Factory` values, at any depth of the call.

=== "Java"
    ```java
    Author ada = authors.create();
    Author grace = authors.create();

    List<Post> posts3 = posts.recycle(ada, grace).count(3).createMany();   // ada, grace, ada
    ```
=== "Kotlin"
    ```kotlin
    val ada: Author = authors.create()
    val grace: Author = authors.create()

    val posts3: List<Post> = posts.recycle(ada, grace).count(3).createMany()   // ada, grace, ada
    ```

`recycle(List)` takes a list. Calls add to the pool, and the same instance is kept once. Models are
grouped by their exact class. A class with no model in the pool is created as usual.

`RecycleMode` says how a model is picked:

| Mode | Pick |
|---|---|
| `IN_TURN` (default) | the models of the class in order, and back to the first after the last |
| `RANDOM` | a random model for each pick |
| `FIRST` | always the first model |

Set it with `recycleMode(mode)`. `recycleRandom()` is `RANDOM` without a seed.

=== "Java"
    ```java
    posts.recycle(ada, grace).recycleMode(RecycleMode.FIRST).count(3).createMany();   // ada, ada, ada
    posts.recycle(ada, grace).recycleRandom().count(3).createMany();
    ```
=== "Kotlin"
    ```kotlin
    posts.recycle(ada, grace).recycleMode(RecycleMode.FIRST).count(3).createMany()   // ada, ada, ada
    posts.recycle(ada, grace).recycleRandom().count(3).createMany()
    ```

### Repeat a random run

An unseeded `recycleRandom()` picks differently on each call. To repeat a run, give it a seed with
`recycleRandom(long seed)`. The same seed and the same pool give the same picks on every call, so a
test that failed once can be run again. Log the seed you chose, and pass it back to reproduce:

=== "Java"
    ```java
    long seed = 20260101L;
    List<Post> first = posts.recycle(ada, grace).recycleRandom(seed).count(5).createMany();
    List<Post> again = posts.recycle(ada, grace).recycleRandom(seed).count(5).createMany();   // same authors in the same order
    ```
=== "Kotlin"
    ```kotlin
    val seed = 20260101L
    val first: List<Post> = posts.recycle(ada, grace).recycleRandom(seed).count(5).createMany()
    val again: List<Post> = posts.recycle(ada, grace).recycleRandom(seed).count(5).createMany()   // same authors in the same order
    ```

`recycleMode(RecycleMode.RANDOM)` keeps a seed that was already set. `recycleRandom()` clears it.

The pool lives for one terminal call. `IN_TURN` starts at the first model again on the next call, and
a seeded run starts again from its seed. Only the pool of the factory you call the terminal on is
used. A `recycle` on a nested factory is ignored. A model taken from the pool must be saved, or
`IllegalStateException` follows.

## Without parents

`withoutParents` turns nested `Factory` values into `null`, so no parent row is created. It applies
to the factory it is called on:

=== "Java"
    ```java
    posts.withoutParents().create();                         // every Factory value is null
    posts.withoutParents(Author.class).create();             // Factory values of Author are null
    posts.withoutParents("author_id").create();              // the Factory value of author_id is null
    ```
=== "Kotlin"
    ```kotlin
    posts.withoutParents().create()                          // every Factory value is null
    posts.withoutParents(Author::class.java).create()        // Factory values of Author are null
    posts.withoutParents("author_id").create()               // the Factory value of author_id is null
    ```

Repeated calls add together. A nested factory brings its own settings: `withoutParents` on the outer
factory does not reach into it. The column must allow null.

## What each terminal does

| Terminal | Parents (`forParent` factory, nested `Factory` values) | `has` and `hasAttached` | Hooks |
|---|---|---|---|
| `make`, `makeMany` | created and saved | never run | `afterMaking` |
| `create`, `createMany` | created and saved | run, after the model is saved | `afterMaking`, `afterCreating` |
| `createQuietly`, `createManyQuietly` | as `create`, with model events muted | as `create` | as `create` |
| `insert` | created and saved | skipped | none |
| `raw`, `rawMany` | never created | never run | none |

`raw` never touches the database. A `Model` value or a `forParent(Model)` gives its key. A `Factory`
value or a `forParent(Factory)` throws `IllegalStateException`, even when the recycle pool holds a
model of that class.

Relation names and kinds are checked before the first row is written, so a wrong name or kind
writes nothing. `make`, `insert` and `raw` check `forParent` only; `has` and `hasAttached` are
checked by the terminals that run them.

## Connection

A nested factory (a child, a related model, a parent or a nested value) builds and saves on the
connection of the factory that created it, unless it was given its own with `connection(connection)`.
A model you pass to `forParent` or to `hasAttached(List, ...)` keeps its own connection.

=== "Java"
    ```java
    authors.connection(reporting).has(posts, "posts").create();   // the posts use `reporting` too
    ```
=== "Kotlin"
    ```kotlin
    authors.connection(reporting).has(posts, "posts").create()   // the posts use `reporting` too
    ```

## Depth guard

Factories that create each other, an author whose posts create an author, would never end. The
guard stops a call that nests more than 32 levels deep and throws `IllegalStateException`.

There is no transaction around a tree. Rows written before the error stay in the database. When you
need all or nothing, run the terminal call inside your own transaction.

## Load relations

A factory needs no method to load relations after create. Use a hook:

=== "Java"
    ```java
    Author loaded = authors.has(posts.count(2), "posts").afterCreating(a -> a.load("posts")).create();
    ```
=== "Kotlin"
    ```kotlin
    val loaded: Author = authors.has(posts.count(2), "posts").afterCreating { a -> a.load("posts") }.create()
    ```

Hooks run after the children are created, so the loaded relation holds them.

## Errors

Messages name a class or a relation, and never a value.

| When | Exception |
|---|---|
| `has` on a relation that is not `HasOne`, `HasMany`, `MorphOne` or `MorphMany` | `IllegalArgumentException` |
| `hasAttached` on a relation that is not `BelongsToMany` | `IllegalArgumentException` |
| `forParent` on a relation that is not `BelongsTo` or `MorphTo` | `IllegalArgumentException` |
| an unknown relation name, or a bad `relations()` map | `RelationNotFoundException`, `InvalidRelationException` |
| `forParent(Model)` with a model that is not saved | `IllegalStateException` |
| `has` when the parent has no value for the local key | `IllegalStateException` |
| `hasAttached` with an empty pivot list | `IllegalArgumentException` |
| `hasAttached` with an unsaved model in the list | `IllegalArgumentException` |
| `raw` with a `Factory` value or a `forParent(Factory)` | `IllegalStateException` |
| a recycled model that is not saved | `IllegalStateException` |
| nesting deeper than 32 levels | `IllegalStateException` |
| a `null` argument | `NullPointerException` |
