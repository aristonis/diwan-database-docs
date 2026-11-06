# Upgrade guide

`0.1.0` is the first release, so there is nothing to upgrade from. Start from
[Getting started](getting-started.md).

## Databases created by a pre-release build

If you ran Diwan from a snapshot or a local build before `0.1.0`, your migrations table may lack the
`checksum` column that `0.1.0` uses to detect edited migrations. Diwan never alters the table at
runtime. The first migrator call that needs the column fails with a message that names the one
statement to run. Run it once, on SQLite or PostgreSQL:

```sql
alter table migrations add column checksum varchar(64);
```

Use your own table name if you changed it. Databases created by `0.1.0` already have the column.

## SQLite dates

Pre-release builds wrote some SQLite dates as `2026-01-02T03:04` or with a local offset. `0.1.0`
writes `yyyy-MM-dd HH:mm:ss`, with a fraction only when there is one, and an `Instant` as UTC with
`+00:00`. Old text does not sort or compare with the new text. Rewrite the old values before you
compare them.

## Removed in 0.1.0

The money helpers (`Blueprint.money`, `Money`, `MoneyAmount`) are gone. Use `decimal` or an integer
column of minor units. A pre-release money column keeps its generated check as an ordinary check.

## Later releases

Changes between versions will appear here, with the steps to take. The full list of changes is in
the changelog of the repository.
