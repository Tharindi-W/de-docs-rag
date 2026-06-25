# Apache Airflow DAG Basics

A DAG (Directed Acyclic Graph) is the unit of orchestration in Airflow. It
defines a set of tasks and the dependencies between them. Airflow schedules
each DAG independently and tracks task instances per logical date.

## Anatomy of a DAG file

A DAG is just a Python module that constructs a DAG object and a set of
operators. The simplest form uses the `@dag` and `@task` decorators
(TaskFlow API), which keep boilerplate low:

```python
from airflow.decorators import dag, task
from pendulum import datetime

@dag(start_date=datetime(2025, 1, 1), schedule="@daily", catchup=False)
def daily_etl():
    @task
    def extract():
        return {"rows": 100}

    @task
    def load(payload: dict):
        print(payload)

    load(extract())

daily_etl()
```

## Schedule and logical date

The `schedule` parameter accepts cron strings, timedeltas, presets like
`@daily`, or dataset triggers. Airflow uses the *logical date* (formerly
`execution_date`) of the run, which is the start of the data interval the
run covers, not the wall-clock time when the run starts.

For an `@daily` DAG run on 2025-03-04, the logical date is 2025-03-03 and
the data interval covers all of 2025-03-03 to 2025-03-04. This convention
makes backfills idempotent: rerunning the run for logical date 2025-03-03
processes exactly the same window of data.

## Catchup

`catchup=False` tells Airflow not to backfill missed runs when a DAG is
unpaused. For a DAG that has not been running for a week, catchup=True will
queue seven runs to fill the gap; catchup=False only schedules the next one.
Use catchup=False unless your pipeline genuinely needs to reprocess history.

## Dependencies between tasks

Outside the TaskFlow API, dependencies are usually expressed with the bit-shift
operators `>>` and `<<` between operators, or with `set_upstream` /
`set_downstream`. The TaskFlow API derives the same graph from how the return
value of one task is passed into another.
