# Models

A model is a class per table, with Eloquent's method names. It keeps its attributes, knows which
ones changed, and writes only those. Every query goes through the [query builder](query-builder.md),
so the SQL is the SQL you would get from `table(...)`.

Models live in `diwan-database-eloquent`:

=== "Gradle (Kotlin)"
    ```kotlin
    implementation("org.aristonis:diwan-database-eloquent:0.4.0")
    ```
=== "Gradle (Groovy)"
    ```groovy
    implementation 'org.aristonis:diwan-database-eloquent:0.4.0'
    ```
=== "Maven"
    ```xml
    <dependency>
        <groupId>org.aristonis</groupId>
        <artifactId>diwan-database-eloquent</artifactId>
        <version>0.4.0</version>
    </dependency>
    ```

## Define a model

A model needs one static entry. It uses no reflection, annotations or build plugin, so the same
class runs on Android.

=== "Java"
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
=== "Kotlin"
    ```kotlin
    class User : Model() {
        override fun fillable(): List<String> {
            return listOf("name", "email")   // nothing is mass assignable until listed
        }

        companion object {
            val query: ModelQuery<User> = ModelQuery.of(User::class.java, ::User)
        }
    }

    val users: ModelQuery<User> = User.query.on(manager.query())
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
| `attributeEncrypter()` | no encrypter (an `encrypted` cast on a non-null value then fails) |
| `attributeHasher()` | no hasher (a `hashed` cast on a non-null value then fails) |

The plural comes from a short English rule set. Override `table()` when it guesses wrong.

## Mass assignment

`fill` sets only the keys in `fillable()` and drops the rest. With the default guards (`guarded()`
is `*` and `fillable()` is empty), `fill` throws `MassAssignmentException`. `forceFill` and
`Model.unguarded(...)` bypass the guards.

=== "Java"
    ```java
    User user = users.make(request);   // fills; "is_admin" in request is dropped
    user.save();
    ```
=== "Kotlin"
    ```kotlin
    val user = users.make(request)   // fills; "is_admin" in request is dropped
    user.save()
    ```

## Attributes, accessors and casts

=== "Java"
    ```java
    found.setAttribute("name", "Ada L.");
    found.isDirty("name");      // true
    found.getDirty();           // {name=Ada L.}
    found.save();               // writes name and updated_at only
    found.save();               // clean: runs nothing
    ```
=== "Kotlin"
    ```kotlin
    found.setAttribute("name", "Ada L.")
    found.isDirty("name")      // true
    found.dirty                // {name=Ada L.}
    found.save()               // writes name and updated_at only
    found.save()               // clean: runs nothing
    ```

Declare casts in `casts()` with Laravel's string form or the typed factories in `Casts`:

=== "Java"
    ```java
    @Override
    protected Map<String, Cast<?>> casts() {
        return CastMap.create()
                .put("price", "decimal:2")                      // BigDecimal, scale 2
                .put("is_admin", "bool")                        // Boolean
                .put("options", "json")                         // Map or List
                .put("tags", "collection")                      // List
                .put("settings", "object")                      // Map
                .put("secret", "encrypted")                     // String, encrypted
                .put("payload", "encrypted:json")               // Map or List, encrypted
                .put("password", "hashed")                      // String, hashed
                .put("token", "binary:uuid")                    // UUID, 16 bytes
                .put("born_on", "date")                         // LocalDate
                .put("paid_at", Casts.datetime("dd/MM/yyyy"))   // Instant
                .put("status", Casts.enumOf(Status.class))      // the enum constant
                .build();
    }
    ```
=== "Kotlin"
    ```kotlin
    override fun casts(): Map<String, Cast<*>> {
        return CastMap.create()
            .put("price", "decimal:2")                      // BigDecimal, scale 2
            .put("is_admin", "bool")                        // Boolean
            .put("options", "json")                         // Map or List
            .put("tags", "collection")                      // List
            .put("settings", "object")                      // Map
            .put("born_on", "date")                         // LocalDate
            .put("paid_at", Casts.datetime("dd/MM/yyyy"))   // Instant
            .put("status", Casts.enumOf(Status::class.java))      // the enum constant
            .build()
    }
    ```

=== "Java"
    ```java
    Order order = orders.findOrFail(1);
    BigDecimal price = (BigDecimal) order.getAttribute("price");
    order.getAttributes().get("price");   // the stored form, "12.50"
    ```
=== "Kotlin"
    ```kotlin
    val order = orders.findOrFail(1)
    val price = order.getAttribute("price") as BigDecimal
    order.attributes["price"]   // the stored form, "12.50"
    ```

Bad stored data, such as broken JSON or `"abc"` under `int`, throws `InvalidCastException`.
Laravel reads `null` or `0` there. The dirty check compares by meaning: JSON by structure, moments
as instants, dates as dates. Reading a cast value never makes a model dirty, but changing a map a
`json` cast returned does. For a cast of your own, implement `Cast<T>` (`get` and `set`).

The `collection` cast reads a JSON array as a `List` and the `object` cast reads a JSON object as a
`Map` that keeps the stored key order. A stored value of the other shape throws
`InvalidCastException`, and so does writing a value of the wrong type; neither message holds the
value. A null column, an empty string and the JSON text `null` read as `null`, and writing `null`
stores SQL NULL. Both results can be changed in place like a `json` result, and writes encode as
`json` does. For typed elements, a typed map or a DTO, implement `Cast<T>` yourself, as described above.

An `encrypted` cast stores its value as text that an encrypter produces. The cast strings are
`encrypted` (a `String`), `encrypted:array` and `encrypted:json` (a `Map` or `List`),
`encrypted:collection` (a `List`) and `encrypted:object` (a `Map`); `Casts.encrypted()` and
`Casts.encrypted(Cast)` are the typed forms. Diwan does no cryptography. You supply an
`AttributeEncrypter` by overriding `attributeEncrypter()` on the model, and it holds your own cipher
and keys:

=== "Java"
    ```java
    public final class MyEncrypter implements AttributeEncrypter {
        @Override
        public String encrypt(String plain) { return yourOwnCipher.seal(plain); }

        @Override
        public String decrypt(String cipher) { return yourOwnCipher.open(cipher); }
    }

    // in the model
    private static final AttributeEncrypter ENCRYPTER = new MyEncrypter();

    @Override
    protected AttributeEncrypter attributeEncrypter() { return ENCRYPTER; }
    ```
=== "Kotlin"
    ```kotlin
    class MyEncrypter : AttributeEncrypter {
        override fun encrypt(plain: String): String = yourOwnCipher.seal(plain)

        override fun decrypt(cipher: String): String = yourOwnCipher.open(cipher)
    }

    private val ENCRYPTER = MyEncrypter()  // one shared instance

    // in the model
    override fun attributeEncrypter(): AttributeEncrypter = ENCRYPTER
    ```

Keep these limits in mind:

- The column must be a text type, not `jsonb`.
- An encrypted column cannot be used in a `where` clause, because the database holds only the
  encrypter's output.
- A null value stores SQL NULL and reads as `null` without calling the encrypter.
- An exception from `encrypt` or `decrypt`, or a non-null value with no encrypter, reaches you as an
  `InvalidCastException` whose cause is the original exception.
- If `hasPreviousKeys()` returns `true`, an encrypted attribute whose stored text changed is dirty
  even when the decrypted value is the same, so the next save re-encrypts it under the current key.
  An encrypted JSON value that you only read also turns dirty.
- `toMap()` and `toJson()` return the decrypted value. List encrypted attributes in `hidden()`
  unless you mean to expose them.
- Only `setAttribute` and `fill` encrypt. Raw attribute writes and query builder inserts or
  updates store what you pass.
- Diwan calls `attributeEncrypter()` on every read, write and dirty check, so return one shared,
  thread-safe instance. Use an authenticated cipher with a fresh nonce per value, load keys from
  the environment or a key store, and keep plaintext and keys out of exception messages.

A `hashed` cast stores a one-way hash of a `String` in a text column. The cast string is `hashed`;
`Casts.hashed()` is the typed form. Diwan does no hashing. You supply an `AttributeHasher` by
overriding `attributeHasher()` on the model, and it wraps your own hash library. Use a proper
password hash, bcrypt or argon2, and return one shared, thread-safe instance:

=== "Java"
    ```java
    public final class MyHasher implements AttributeHasher {
        @Override
        public String hash(String plain) { return yourOwnHash.make(plain); }

        @Override
        public boolean isHashed(String value) { return yourOwnHash.isHash(value); }

        @Override
        public boolean isCurrent(String hashed) { return yourOwnHash.isUpToDate(hashed); }  // override to refuse hashes below your minimum cost
    }

    // in the model
    private static final AttributeHasher HASHER = new MyHasher();

    @Override
    protected AttributeHasher attributeHasher() { return HASHER; }
    ```
=== "Kotlin"
    ```kotlin
    class MyHasher : AttributeHasher {
        override fun hash(plain: String): String = yourOwnHash.make(plain)

        override fun isHashed(value: String): Boolean = yourOwnHash.isHash(value)

        override fun isCurrent(hashed: String): Boolean = yourOwnHash.isUpToDate(hashed)  // override to refuse hashes below your minimum cost
    }

    private val HASHER = MyHasher()  // one shared instance

    // in the model
    override fun attributeHasher(): AttributeHasher = HASHER
    ```

Keep these limits in mind:

- The cast is write-only. A read returns the stored hash, and verifying a password is your hasher's
  job.
- The cast takes a `String` only. Any other value reaches you as an `InvalidCastException`.
- A value that `isHashed` accepts is already a hash. It is kept as given if `isCurrent` returns
  `true` and refused otherwise. So a request that sends a hash-shaped value skips your hasher and
  your password rules. Validate untrusted input as plain text first, or keep the attribute out of
  `fillable()` and set it yourself. Make `isHashed` match the full format and length, and override
  `isCurrent` to refuse hashes below your minimum cost.
- Verifying, constant-time comparison and input limits (bcrypt reads only the first 72 bytes) are
  your hash library's job. Cap the input length before you set it.
- A null value stays SQL NULL and the hasher is not called.
- An exception from the hasher, or a non-null value with no hasher, reaches you as an
  `InvalidCastException` whose cause is the original exception.
- Setting the same plain value again is dirty when your hasher's output differs, as a salted hash
  does.
- `toMap()` and `toJson()` return the hash. List hashed attributes in `hidden()`.
- Use a text column wide enough for the hash.
- Only `setAttribute` and `fill` hash. Raw attribute writes and query builder inserts or updates
  store what you pass.

A binary cast stores a UUID or a ULID as 16 bytes. The cast strings are `binary:uuid` and
`binary:ulid`; `Casts.binaryUuid()` and `Casts.binaryUlid()` are the typed forms. Use a `binary()`
column, not `uuid()`:

=== "Java"
    ```java
    @Override
    protected Map<String, Cast<?>> casts() {
        return CastMap.create()
                .put("token", "binary:uuid")    // java.util.UUID
                .put("ref", "binary:ulid")      // String, 26 lower-case characters
                .build();
    }

    // a where clause on a binary column takes the bytes
    Optional<Device> found = devices.query().where("token", BinaryIds.uuidBytes(uuid)).first();
    ```
=== "Kotlin"
    ```kotlin
    override fun casts(): Map<String, Cast<*>> {
        return CastMap.create()
            .put("token", "binary:uuid")    // java.util.UUID
            .put("ref", "binary:ulid")      // String, 26 lower-case characters
            .build()
    }

    // a where clause on a binary column takes the bytes
    val found = devices.query().where("token", BinaryIds.uuidBytes(uuid)).first()
    ```

Keep these limits in mind:

- `binary:uuid` reads and writes a `java.util.UUID`, and a write takes a `UUID` only.
- `binary:ulid` reads a lower-case 26-character `String` and writes a strict 26-character ULID in
  any case: digits 0-9 and letters A-Z without I, L, O and U, the first character 0 to 7. Any other
  text fails as `InvalidCastException`.
- Any other value type fails as `InvalidCastException`.
- A `where` clause on such a column compares bytes. Pass `BinaryIds.uuidBytes(uuid)` or
  `BinaryIds.ulidBytes(text)`; a `UUID` or text does not match.
- `toMap()` and `toJson()` give the text form.
- A null value stays SQL NULL.
- A stored value that is not exactly 16 bytes fails as `InvalidCastException`.
- The key of a model with a binary key is not generated as bytes. This is not supported.

Date formats are Java `DateTimeFormatter` patterns. Write `yyyy-MM-dd`, not PHP's `Y-m-d`: the PHP
form compiles in Java and means something else.

`Casts.instant()` stores an `Instant` whatever the model's `timestampFormat()`. Use it for
`Blueprint.instant` columns. `created_at`, `updated_at` and `deleted_at` are also written directly
by soft delete, bulk update and touch, always in the model's format. So when those columns are
`instant`, the model needs `TimestampFormat.INSTANT`. A model on the TEXT format that puts the
instant cast on one of them fails at first use, and the message names the column.

=== "Java"
    ```java
    @Override
    protected TimestampFormat timestampFormat() { return TimestampFormat.INSTANT; }

    @Override
    protected Map<String, Cast<?>> casts() {
        return CastMap.create().put("sent_at", Casts.instant()).build();   // any other instant column
    }
    ```
=== "Kotlin"
    ```kotlin
    override fun timestampFormat(): TimestampFormat = TimestampFormat.INSTANT

    override fun casts(): Map<String, Cast<*>> {
        return CastMap.create().put("sent_at", Casts.instant()).build()   // any other instant column
    }
    ```

Accessors and mutators are registered in `accessors()`, not discovered by name:

=== "Java"
    ```java
    @Override
    protected Map<String, Attribute<?>> accessors() {
        Map<String, Attribute<?>> map = new LinkedHashMap<>();
        map.put("display_name", Attribute.get((model, value, attrs) -> attrs.get("first") + " " + attrs.get("last")));
        map.put("email", Attribute.set((model, value, attrs) -> value.toString().toLowerCase(Locale.ROOT)));
        return map;
    }
    ```
=== "Kotlin"
    ```kotlin
    override fun accessors(): Map<String, Attribute<*>> {
        val map = LinkedHashMap<String, Attribute<*>>()
        map["display_name"] = Attribute.get<Any> { model, value, attrs -> "${attrs["first"]} ${attrs["last"]}" }
        map["email"] = Attribute.set<Any> { model, value, attrs -> value.toString().lowercase(Locale.ROOT) }
        return map
    }
    ```

`casts()` and `accessors()` are read once per class, so they must not depend on instance state.

### Strict decimals for money

`decimal:2` reads and writes any number with two decimals and rounds extra decimals half up, as
Laravel does. For money, declare the column with the same numbers as its migration, so the cast
checks what the column can hold:

=== "Java"
    ```java
    // migration: table.decimal("total", 6, 2)   -- 6 digits in all, 2 after the point
    @Override
    protected Map<String, Cast<?>> casts() {
        return CastMap.create()
                .put("total", Casts.decimal(6, 2))                          // decimal:6,2
                .put("tax", Casts.decimal(6, 2, RoundingMode.HALF_EVEN))    // decimal:6,2,HALF_EVEN
                .build();
    }
    ```
=== "Kotlin"
    ```kotlin
    // migration: table.decimal("total", 6, 2)   -- 6 digits in all, 2 after the point
    override fun casts(): Map<String, Cast<*>> {
        return CastMap.create()
            .put("total", Casts.decimal(6, 2))                          // decimal:6,2
            .put("tax", Casts.decimal(6, 2, RoundingMode.HALF_EVEN))    // decimal:6,2,HALF_EVEN
            .build()
    }
    ```

The spec strings work too: `decimal:6,2` and `decimal:6,2,HALF_EVEN` (the mode name in any
case). The first number is the total digits and the second the digits after the point. Both must
satisfy `0 <= scale <= precision`, and a bad declaration throws `IllegalArgumentException`.

When a value is set:

- More decimals than the scale are refused by default. The mode decides what happens to them
  instead: `Casts.decimal(6, 2)` refuses `10.125`, and `Casts.decimal(6, 2, HALF_UP)` stores
  `10.13`.
- More integer digits than `precision - scale` are always refused, whatever the mode. With
  `decimal:6,2`, `10000.00` is refused, and so is `9999.999` under `HALF_UP`, because rounding
  carries it to `10000.00`.
- A refused value throws `InvalidCastException`. The message names the model, the attribute and the
  rule it broke. It never contains the value.

Reading returns a `BigDecimal` at the declared scale, so `12.5` comes back as `12.50`.

| Mode | Rule | Example, `decimal:6,2,MODE` | Stored |
|---|---|---|---|
| `UNNECESSARY` (default) | Refuses any extra decimal. | `10.12` stays `10.12`; `10.125` throws | `10.12` |
| `HALF_UP` | Rounds to the nearest, a tie away from zero. | `10.125` | `10.13` |
| `HALF_EVEN` | Rounds to the nearest, a tie to the even digit (banker's rounding). | `10.125` | `10.12` |
| `DOWN` | Cuts toward zero. | `10.129` | `10.12` |
| `UP` | Rounds away from zero. | `10.121` | `10.13` |
| `FLOOR` | Rounds toward negative infinity. | `-10.121` | `-10.13` |
| `CEILING` | Rounds toward positive infinity. | `-10.129` | `-10.12` |

### The 15-digit rule on SQLite

SQLite keeps a decimal column as a double, which holds about 15 significant digits. The strict cast
therefore refuses a value with more than 15 significant digits on SQLite. The `InvalidCastException`
names the column, never the value. PostgreSQL stores exact decimals and is unchanged.

This is a behavior change for upgraders: a value that was accepted before and carries more than 15
digits now throws. To keep longer exact values on SQLite, use a text column with
`Casts.decimalText(precision, scale)`, which keeps the strict precision and scale rules but skips the 15-digit limit:

=== "Java"
    ```java
    // migration: table.string("rate")   -- text column, exact digits
    .put("rate", Casts.decimalText(30, 15))
    ```
=== "Kotlin"
    ```kotlin
    // migration: table.string("rate")   -- text column, exact digits
    .put("rate", Casts.decimalText(30, 15))
    ```

`Casts.decimal(scale)` (`decimal:2`) is unchanged: it has no precision limit and rounds half up.
Use the strict form for money, so that a stored value always fits its column.

## Save, create and find

=== "Java"
    ```java
    User ada = users.create(Map.of("name", "Ada", "email", "ada@example.com"));  // id, timestamps set
    User found = users.findOrFail(ada.getKey());
    Optional<User> maybe = users.find(42);
    Optional<User> first = users.query().where("email", "ada@example.com").first();

    found.update(Map.of("name", "Ada Lovelace"));
    found.increment("logins");
    found.delete();            // false when the model is not in the database
    ```
=== "Kotlin"
    ```kotlin
    val ada = users.create(mapOf("name" to "Ada", "email" to "ada@example.com"))  // id, timestamps set
    val found = users.findOrFail(ada.key)
    val maybe: Optional<User> = users.find(42)
    val first: Optional<User> = users.query().where("email", "ada@example.com").first()

    found.update(mapOf("name" to "Ada Lovelace"))
    found.increment("logins")
    found.delete()            // false when the model is not in the database
    ```

`saveOrFail()` saves, and runs its touches, in one transaction. It throws `IllegalStateException`
when a model with a non-incrementing key has nothing to insert. Plain `save()` returns `true` there,
as in Laravel.

Find or make a row:

=== "Java"
    ```java
    User sam = users.firstOrCreate(Map.of("email", "sam@example.com"), Map.of("name", "Sam"));
    users.updateOrCreate(Map.of("email", "sam@example.com"), Map.of("name", "Samuel"));
    users.firstOrNew(Map.of("email", "new@example.com"), Map.of("name", "New"));   // not saved
    ```
=== "Kotlin"
    ```kotlin
    val sam = users.firstOrCreate(mapOf("email" to "sam@example.com"), mapOf("name" to "Sam"))
    users.updateOrCreate(mapOf("email" to "sam@example.com"), mapOf("name" to "Samuel"))
    users.firstOrNew(mapOf("email" to "new@example.com"), mapOf("name" to "New"))   // not saved
    ```

`upsert` and `insertOrIgnore` write many rows in one statement. They skip model events and casts,
but fill unique ids and timestamps:

=== "Java"
    ```java
    users.query().upsert(rows, List.of("email"));          // needs a unique index on email
    users.query().upsert(rows, List.of("email"), List.of("name"));
    users.query().insertOrIgnore(rows);
    ```
=== "Kotlin"
    ```kotlin
    users.query().upsert(rows, listOf("email"))          // needs a unique index on email
    users.query().upsert(rows, listOf("email"), listOf("name"))
    users.query().insertOrIgnore(rows)
    ```

`upsert` needs SQLite 3.24 or later, which means Android API 30 or later. See [Android](android.md).

`fillAndInsert`, `fillAndInsertOrIgnore` and `fillAndInsertGetId` fill each row as `fill` does, then
insert it. They are called on the model builder, not on `ModelQuery`:

=== "Java"
    ```java
    Member.query.on(db).query().fillAndInsert(rows);
    int added = Member.query.on(db).query().fillAndInsertOrIgnore(rows);
    Object id = Member.query.on(db).query().fillAndInsertGetId(row);
    ```
=== "Kotlin"
    ```kotlin
    Member.query.on(db).query().fillAndInsert(rows)
    val added = Member.query.on(db).query().fillAndInsertOrIgnore(rows)
    val id = Member.query.on(db).query().fillAndInsertGetId(row)
    ```

The fill skips the fillable guard, so never pass request data to these methods unchecked. Casts
apply, unique ids and timestamps are set, and a `created_at` or `updated_at` the row already has is
kept. `beforeWrite()` runs on each row, but no model event fires. The list forms write every row in
one statement, so all rows need the same columns, and a large batch must stay under the binding
limit (999 on SQLite before 3.32).

To build models for tests and seeding, see [factories](factories.md): `Factory` makes, creates or inserts
models from a definition you write.

## Query shortcuts

`whereBelongsTo` filters the children of a parent through the `belongsTo` relation the child
declares. Without a name it uses the parent's class name in camel case, so `user` for `User`. Under
R8 or other renaming, pass the relation name:

=== "Java"
    ```java
    ModelQuery<Post> posts = Post.query.on(db);
    posts.query().whereBelongsTo(ada).get();                          // relation "user"
    posts.query().whereBelongsTo(ada, "author").get();
    posts.query().whereBelongsTo(List.of(ada, sam), "author").get();  // one in clause
    posts.query().where("pinned", true).orWhereBelongsTo(ada, "author").get();
    ```
=== "Kotlin"
    ```kotlin
    val posts = Post.query.on(db)
    posts.query().whereBelongsTo(ada).get()                          // relation "user"
    posts.query().whereBelongsTo(ada, "author").get()
    posts.query().whereBelongsTo(listOf(ada, sam), "author").get()  // one in clause
    posts.query().where("pinned", true).orWhereBelongsTo(ada, "author").get()
    ```

The methods refuse an empty collection, a parent of the wrong class and a parent without a key
value.

`pluck(column, key)` returns a map from the key column to the column, with raw values as
`pluck(column)` gives them:

=== "Java"
    ```java
    Map<Object, Object> ids = Member.query.on(db).query().pluck("id", "code");   // code -> id
    ```
=== "Kotlin"
    ```kotlin
    val ids = Member.query.on(db).query().pluck("id", "code")   // code -> id
    ```

## Scopes

A global scope adds a constraint to every query of a model, including eager loads and `whereHas`.
Register it once at start-up, with a name:

=== "Java"
    ```java
    posts.addGlobalScope("tenant", q -> q.where("tenant_id", 7));

    posts.query().withoutGlobalScope("tenant").get();   // one query without it
    posts.query().withoutGlobalScopes().get();
    ```
=== "Kotlin"
    ```kotlin
    posts.addGlobalScope("tenant", Consumer<EloquentBuilder<*>> { q -> q.where("tenant_id", 7) })

    posts.query().withoutGlobalScope("tenant").get()   // one query without it
    posts.query().withoutGlobalScopes().get()
    ```

A scope may add query clauses only. It must be stateless and must not run a query itself. A class
that implements `Scope` registers through `addGlobalScope(Scope)`; a lambda needs a name. A local
scope is a reusable step you apply to one query:

=== "Java"
    ```java
    posts.query().scope(q -> q.where("published", true)).get();
    ```
=== "Kotlin"
    ```kotlin
    posts.query().scope { q -> q.where("published", true) }.get()
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

=== "Java"
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
=== "Kotlin"
    ```kotlin
    posts.events()
        .saving { post ->                       // return false to stop the save
            if (post.getString("slug") == null) {
                post.setAttribute("slug", slugOf(post.getString("title")))
            }
            true
        }
        .created { post -> auditLog.record("post created", post.key) }

    posts.events().observe(PostObserver())     // a ModelObserver<Post>
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

=== "Java"
    ```java
    @Override
    protected List<String> hidden() { return List.of("password"); }

    String json = user.toJson();
    ```
=== "Kotlin"
    ```kotlin
    override fun hidden(): List<String> = listOf("password")

    val json = user.toJson()
    ```

The built-in JSON codec is strict RFC 8259 and the library adds no JSON dependency. To use Jackson
or Gson, implement `JsonCodec` and return it from `jsonCodec()`.

## Chunks, lazy reads, cursors and pages

=== "Java"
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
=== "Kotlin"
    ```kotlin
    users.query().orderBy("id").chunk(500) { batch -> batch.forEach { sync(it) }; true }
    users.query().chunkById(500) { batch -> /* rows may change here */ true }

    for (u in users.query().orderBy("id").lazy(1000)) { /* one page at a time */ }

    users.query().orderBy("id").cursor().use { cursor ->
        for (u in cursor) { /* streams one row at a time */ }
    }

    val page = users.query().orderBy("name").paginate(20, 2)
    page.items()   // ModelCollection<User>
    page.total()
    ```

`chunk` pages by offset, so use `chunkById` when rows change during the loop. Always close a
`cursor()`: an open one keeps its connection. A cursor refuses eager loads; `lazy()` loads them per
page. `simplePaginate` and `cursorPaginate` work as on the query builder.

## Limits

- Models are not thread-safe. Share the `ModelQuery`; give each thread its own instances.
- Without a `bool` cast, a `Boolean` set on a SQLite column reads back as `1` and stays dirty
  against `true`.
- Diwan does no cryptography. An encrypted column must be text, cannot be used in a `where`
  clause, and an encrypter failure surfaces as `InvalidCastException`.
- Diwan does no hashing. A hashed column must be text, a `hashed` cast takes a `String` only,
  and a hasher failure surfaces as `InvalidCastException`.
- A `binary:uuid` or `binary:ulid` column must be `binary()`, a `where` clause on it takes the bytes from `BinaryIds`, and a stored value that is not 16 bytes surfaces as `InvalidCastException`.
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
| `Casts.encrypted` | `Casts` | The `encrypted` cast: `encrypted()` stores a string as the encrypter's text, `encrypted(Cast)` wraps another cast (`Casts.json()`, `Casts.jsonUnicode()`, `Casts.collection()`, `Casts.object()`). The model needs an `attributeEncrypter()`. | `.put("secret", Casts.encrypted())` |
| `Casts.hashed` | `Casts` | The `hashed` cast: stores a `String` as the hasher's hash and takes a `String` only. The model needs an `attributeHasher()`. | `.put("password", Casts.hashed())` |
| `Casts.binaryUuid` `Casts.binaryUlid` `BinaryIds` | `Casts` | The `binary:uuid` and `binary:ulid` casts: store a `UUID` or a ULID `String` as 16 bytes in a `binary()` column. `BinaryIds.uuidBytes` and `BinaryIds.ulidBytes` give the bytes for a `where` clause. | `.put("token", Casts.binaryUuid())` |
| `attributeEncrypter` `getAttributeEncrypter` | `Model` | The encrypter the model's `encrypted` casts use: override `attributeEncrypter()` to return your `AttributeEncrypter`, and `getAttributeEncrypter()` reads it. None by default. | `post.getAttributeEncrypter()` |
| `attributeHasher` `getAttributeHasher` | `Model` | The hasher the model's `hashed` casts use: override `attributeHasher()` to return your `AttributeHasher`, and `getAttributeHasher()` reads it. None by default. | `user.getAttributeHasher()` |
| `Casts.decimal` | `Casts` | `decimal(scale)` is the rounding `decimal:N` cast. `decimal(precision, scale[, mode])` is the strict cast: precision and scale as in `Blueprint.decimal`, extra decimals refused unless a rounding mode is given. | `.put("total", Casts.decimal(6, 2))` |
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
