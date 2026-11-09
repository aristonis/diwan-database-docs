# Upgrade guide

This page lists the changes between releases, with the steps to take.
Start from [Getting started](getting-started.md).

## 0.2.0 to 0.3.0

No code change is needed: 0.3.0 only adds API. One behaviour changed, in a way a test may notice:

- Every driver and query error message now ends with the Diwan error, for example
  `[DWN-CST-0001 unique violation: users_email_unique (email)]`. Nothing is replaced: the original
  text, `sqlState()`, `vendorCode()`, `kinds()` and `databaseMessage()` are unchanged. A test that
  compares the whole message fails; match the start, or read `error().code()` instead.

## 0.1.0 to 0.2.0

No code change is needed: 0.2.0 only adds API. Four behaviours changed, in ways a test may notice:

- On SQLite, `lock(LockStrength.NO_KEY_UPDATE)` and `lock(LockStrength.KEY_SHARE)` now run and
  write nothing, as the other strengths do; they no longer throw.
- A `DriverException` message keeps its old text and may add `: ` with the recognised kinds and,
  on SQLite, the result code name. Match the start of the message, not the whole of it.
- The `MigrationChecksumException` message now advises restoring the migration; repair is for
  recovery only.
- `busy_timeout`, when set, now also applies to SQLite file databases, so a busy writer waits that
  long instead of the driver's 3 seconds.
