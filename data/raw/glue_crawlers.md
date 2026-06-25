# AWS Glue Crawlers

A Glue crawler inspects a data source (most often an S3 prefix) and writes
table definitions into the Glue Data Catalog. Athena, Redshift Spectrum,
EMR, and Glue jobs can then query the data as if it were a regular table.

## What a crawler does

1. Walks the configured S3 prefix(es).
2. Samples a subset of files to infer schema and detect partition structure.
3. Picks a classifier (JSON, CSV, Parquet, ORC, Avro, or a custom Grok
   pattern).
4. Creates or updates a table in the configured Glue database.
5. Optionally creates partitions for any new partition keys found.

## Scheduling

Crawlers can run on demand, on a cron-like schedule, or be triggered from a
Glue workflow. For event-driven ingestion, prefer S3 event notifications or
the `crawl_new_folders_only` setting over a fixed schedule, since
re-crawling a large prefix is expensive.

## Schema evolution policy

When the crawler detects a column or type change, the configured update
behaviour controls what happens:

- **UPDATE_IN_DATABASE**: replace the existing schema in the catalog.
- **LOG**: write a log entry and leave the schema unchanged.
- **DELETE_FROM_DATABASE**: drop tables whose underlying data is gone.

Pick UPDATE_IN_DATABASE for trusted upstreams that only add columns. Pick
LOG for shared catalogs where ad-hoc schema changes could break downstream
queries.

## When you might skip a crawler

Crawlers are convenient but they cost money and can be slow for large
prefixes. Alternatives:

- Define the table manually with a `CREATE EXTERNAL TABLE` DDL. Best when
  you control the schema and partition layout.
- Use `MSCK REPAIR TABLE` (Athena) or `ALTER TABLE ADD PARTITION` to
  register new partitions without re-inferring schema.
- Use a Glue job that registers schemas programmatically via the
  `glueContext.getCatalogSource` and `getCatalogSink` APIs.
