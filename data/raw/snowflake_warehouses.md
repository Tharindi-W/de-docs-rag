# Snowflake Virtual Warehouses

A virtual warehouse in Snowflake is a cluster of compute resources that runs
queries, loads data, and performs DML operations. Warehouses are independent
of storage, which is one of the defining properties of the Snowflake
architecture: storage scales independently of compute.

## Sizing

Warehouse sizes range from X-Small (1 node) up to 6X-Large (512 nodes). Each
size doubles the compute and roughly doubles the credit consumption per hour.
A query that takes 60 seconds on an X-Small will typically take about 30
seconds on a Small, with the same credit cost, because credits are billed per
second with a 60-second minimum.

## Multi-cluster warehouses

For workloads with concurrent users (BI dashboards, ad-hoc analyst queries),
a multi-cluster warehouse can scale out horizontally. You configure a minimum
and maximum number of clusters. Snowflake spawns additional clusters when
queries start queueing and suspends them when load drops.

There are two scaling policies:

- STANDARD: Aggressive scale-out, prioritises latency.
- ECONOMY: Conservative scale-out, prioritises credit efficiency. Queries may
  queue for up to six minutes before another cluster spins up.

## Auto-suspend and auto-resume

Set `AUTO_SUSPEND` to release credits when a warehouse is idle. A common
default is 60 seconds for ad-hoc warehouses and longer (e.g. 600 seconds) for
warehouses that serve dashboards with frequent cache hits, because suspending
clears the local SSD cache.

`AUTO_RESUME = TRUE` makes the warehouse start automatically on the next
query, so users do not need to manage state manually.

## Cost levers

- Right-size the warehouse to the workload. Use query history to find the
  smallest size that meets your latency SLA.
- Use separate warehouses per workload (ingest, BI, ad-hoc) so noisy
  neighbours do not affect each other and you can attribute spend.
- Watch the `WAREHOUSE_METERING_HISTORY` view to find under-utilised
  warehouses.
