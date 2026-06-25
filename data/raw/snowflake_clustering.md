# Snowflake Automatic Clustering

Snowflake automatic clustering is a background service that maintains the
clustering of large tables defined with a CLUSTER BY expression. Instead of
running a manual RECLUSTER statement, the service monitors clustering depth
and re-organises micro-partitions when partitions become heavily overlapping
on the clustering keys.

## When to define a clustering key

A clustering key is worthwhile when:

- The table is large (multi-terabyte) and queries filter or join on a small
  number of columns most of the time.
- The natural ingestion order does not align with how the table is queried.
- Query profiles show a high number of micro-partitions scanned relative to
  the number returned.

Small tables (under roughly one terabyte) usually do not benefit from
clustering. Snowflake's default micro-partition pruning already removes
unneeded partitions for these cases.

## How automatic clustering works

The service computes a clustering depth metric per table. When depth crosses
a threshold, Snowflake schedules background reclustering jobs. These jobs run
on Snowflake-managed compute (not your warehouse) and are billed under the
automatic clustering line item on the account usage view
`AUTOMATIC_CLUSTERING_HISTORY`.

Reclustering is incremental. The service rewrites overlapping micro-partitions
into new, better-organised ones and marks the originals for cleanup. Time
Travel still works against the previous state.

## Operational notes

- Clustering keys are most effective on low-cardinality, frequently filtered
  columns such as event_date or region_id.
- Avoid using highly unique columns (like a primary key) as the sole
  clustering key, because every insert creates a new micro-partition that
  cannot be co-located with anything.
- Monitor `SYSTEM$CLUSTERING_INFORMATION('my_table')` to inspect the current
  clustering ratio and depth.
- You can suspend automatic clustering on a table with
  `ALTER TABLE ... SUSPEND RECLUSTER` while you investigate cost spikes.
