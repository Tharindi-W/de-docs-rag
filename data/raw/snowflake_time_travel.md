# Snowflake Time Travel and Fail-safe

Time Travel lets you query, clone, or restore data as it existed at a point in
the past, up to a per-table retention period. It is one of the simplest ways
to recover from an accidental UPDATE, DELETE, DROP, or TRUNCATE.

## Retention periods

- Standard edition: 1 day of Time Travel.
- Enterprise edition and above: up to 90 days for permanent tables.
- Transient and temporary tables: maximum of 1 day, and no Fail-safe.

Retention is configured per table via `DATA_RETENTION_TIME_IN_DAYS`. Setting
this to 0 disables Time Travel for the table and lets storage be released
immediately, which can reduce storage cost for staging tables that are
rebuilt on every run.

## Usage

You can read historical data with the AT or BEFORE clause:

```sql
SELECT * FROM orders AT (OFFSET => -60 * 5);   -- five minutes ago
SELECT * FROM orders BEFORE (STATEMENT => '019b...'); -- before a given query
```

To restore a dropped object, use UNDROP:

```sql
UNDROP TABLE orders;
```

To restore a table to a previous state without losing the current one, use
zero-copy cloning at a point in time:

```sql
CREATE TABLE orders_recovered CLONE orders AT (OFFSET => -3600);
```

## Fail-safe

Fail-safe is a 7-day period after Time Travel expires during which only
Snowflake support can recover the data. It applies only to permanent tables
and cannot be disabled or queried directly. It is a disaster-recovery
backstop, not a user-facing feature.

## Cost implications

Time Travel and Fail-safe both incur storage cost for retained micro-partitions.
For high-churn tables this can be a significant fraction of the total bill.
Tune `DATA_RETENTION_TIME_IN_DAYS` per table based on how recoverable the
data already is from upstream sources.
