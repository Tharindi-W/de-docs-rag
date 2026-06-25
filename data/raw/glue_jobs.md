# AWS Glue Jobs

A Glue job is a serverless Spark or Python shell job that AWS Glue runs on
your behalf. You define the script (PySpark, Scala, or Python) and Glue
provisions workers, attaches the data catalog, runs the job, and tears the
cluster down.

## Job types

- **Spark**: Distributed PySpark or Scala job. Use for transformations over
  large datasets or anything that benefits from Spark.
- **Spark Streaming**: Structured Streaming for Kinesis or Kafka sources.
- **Python shell**: Single-node Python process. Cheap, simple, and a good
  fit for small orchestration scripts, calls to AWS APIs, or lightweight
  pandas-scale transforms.
- **Ray**: For Python ML workloads that benefit from Ray's actor model.

## Worker types and DPUs

For Spark jobs you choose a worker type (G.1X, G.2X, G.4X, G.8X) and a worker
count. A DPU (Data Processing Unit) is the billing unit: 4 vCPU and 16 GB of
memory. G.1X is 1 DPU per worker, G.2X is 2 DPUs, and so on. Billing is per
second with a 1-minute minimum.

A common starting point is G.1X with 10 workers for jobs reading tens of GB.
Scale worker type up when individual partitions are large (wide rows, complex
UDFs) and scale worker count up when partition counts are high.

## Bookmarks

Job bookmarks track which input data a Spark job has already processed, so
the next run only reads new files. Bookmarks are scoped per source (S3
prefix, JDBC table) and per job. Without bookmarks, each run re-reads the
entire source.

Bookmarks store state in Glue's internal metadata. They can be paused,
enabled, or reset from the console or via `glue:ResetJobBookmark`. Reset
bookmarks when reprocessing history or when changing the upstream schema in
a non-additive way.

## Spark configuration

Glue jobs accept Spark configuration via `--conf` job parameters. Common
tunings:

- `--enable-glue-datacatalog`: register Hive metastore against the Glue
  catalog.
- `--enable-metrics`: emit CloudWatch metrics for the job.
- `--enable-continuous-cloudwatch-log`: stream driver and executor logs.
- `spark.sql.shuffle.partitions`: default is 200; lower for small datasets,
  raise for skewed joins.
