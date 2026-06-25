# AWS Glue Data Catalog

The Glue Data Catalog is a managed Hive-compatible metastore. It stores
databases, tables, partitions, and column statistics for data sitting in
S3, JDBC sources, and other connectors. Any AWS analytics service that
speaks Hive metastore (Athena, EMR, Redshift Spectrum, Glue) can read from
the catalog.

## Databases, tables, partitions

The catalog is organised as databases > tables > partitions. A table points
at a storage location (`s3://bucket/prefix`) and a serde (Parquet, ORC,
CSV, JSON, etc.). Partitions add subdirectories that act like predicates
when queried.

A common layout is one database per business domain and one table per
logical dataset, with partitions for date and (optionally) tenant or region.
For example:

- `analytics.orders` partitioned by `event_date`, located at
  `s3://my-lake/analytics/orders/`.

## Catalog metadata vs storage

The catalog stores only metadata; it does not move or copy data. Deleting a
table from the catalog does not delete the underlying S3 objects. This
separation is what makes lakehouse patterns possible: the same files can
serve multiple engines (Athena, Spark, Trino) by registering them in the
catalog with different table definitions.

## Cross-account access

The catalog supports resource-based policies. To share a database with
another account, attach a Glue resource policy granting the consumer's IAM
principals `glue:GetTable`, `glue:GetPartitions`, and S3 read access to the
underlying bucket. For finer-grained sharing (column-level, row-level), use
Lake Formation on top of the Glue catalog.

## Partition projection

For very high-cardinality partition schemes (millions of partitions),
listing partitions from the catalog becomes a bottleneck. Athena supports
partition projection, where the partition values are derived from a
template at query time instead of from the catalog. This eliminates the
metadata lookup and scales to arbitrarily many partitions, at the cost of
losing the ability to query partitions that do not follow the template.
