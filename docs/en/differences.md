# Differences from Laravel

Diwan keeps Laravel's method names where they read well in Java. This page lists the places where
it behaves differently on purpose. Each row is a choice, not a missing feature.

## Language and return shapes

| Laravel | Diwan |
|---|---|
| `null` or `false` for "not found" | `Optional` from `find`, `first`, `selectOne` and `scalar`; `findOrFail` throws |
| PHP dates and format letters (`Y-m-d`) | `java.time` and `DateTimeFormatter` patterns (`yyyy-MM-dd`) |
| Rows are arrays | Rows are unmodifiable maps in select order |
| Lazy loading works from any attribute read | `getAttribute("posts")` never loads a relation; use `related` or `relatedMany` |
| Relations found by method name | A typed method plus a `RelationMap` entry, so R8 cannot break it |
| Morph and global-scope names guessed from the call stack or a closure | You pass the name |

## Connections and queries

| Laravel | Diwan |
|---|---|
| A transaction callback can use any connection | Strict transactions: the outer connection refuses calls from inside its own transaction; use the `tx` you are given |
| Binding values appear in error messages | Hidden by default; turn on `showBindingsInErrors` |
| `upsert` with an empty update list runs a plain insert | Leaves a conflicting row as it is |
| `lock('lock in share mode')` raw string | Typed `LockStrength` and `LockWait` only |
| `paginate` counts every row of a `distinct` query | Counts distinct rows |
| `cursor()` returns a lazy collection | `QueryCursor`, which you close; an unclosed one keeps its connection |
| Cursor and page tokens are your problem | Tokens are not signed; a forged one cannot inject SQL but can ask for other allowed rows |
| `chunk` on a growing table | Same offset paging, so use `chunkById` |

## Models

| Laravel | Diwan |
|---|---|
| Bad stored data reads as `null`, `0` or `true` | `InvalidCastException` naming the model, key and cast |
| JSON and float dirty checks compare loosely | JSON compares by structure, floats within 4 ULP, moments as instants |
| `delete()` on a model not in the database | Returns `false` |
| `increment` on a model not in the database | Refused |
| `saveOrFail` | Saves in its own transaction and throws when a non-incrementing model has nothing to insert |
| A write through a relation from a parent with no key writes a null key | `IllegalStateException` before any SQL |
| Eager loads read null keys as `0` | Null keys are dropped |
| `with` on the same relation twice keeps the last constraint | Runs both |
| An eager constraint may use `limit` | Refused, since it would cut all parents together |
| A listener returning `true` silences later listeners | Only `false` halts |
| `withoutEvents` mutes every thread | Mutes the calling thread only, and the model's own hooks still run |
| Global scopes are inherited by subclasses | Each class has the scopes registered on its own `ModelQuery` |
| `forceDelete()` on a builder skips every global scope | Skips only the soft-delete scope |
| The morph map is optional | Required unless you call `requireMorphMap(false)` |
| `oldestOfMany` can return the highest key among ties | Returns the lowest |

## Not in 0.1.0

- Custom event classes, string event names and wildcard listeners.
- `ObservedBy`; register an observer with `observe`.
- MySQL, SQL Server and other databases. SQLite, PostgreSQL and Android are supported.

See also [Models](models.md), [Relations](relations.md) and [Query builder](query-builder.md).
