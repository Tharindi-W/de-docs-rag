# Airflow XComs

XCom (short for cross-communication) is Airflow's mechanism for passing small
amounts of data between tasks. Every task instance can push and pull XCom
values, and the metadata DB stores them keyed by dag_id, run_id, task_id, and
key.

## Pushing and pulling

Classic operators push XComs by returning a value from `execute`, or
explicitly with `ti.xcom_push(key=..., value=...)`. The TaskFlow API
abstracts this away: the return value of a `@task` function is automatically
pushed as the `return_value` XCom, and any argument that receives another
task's return value triggers an `xcom_pull` for that key.

```python
@task
def compute() -> int:
    return 42

@task
def consume(x: int) -> None:
    print(x)

consume(compute())   # the int 42 flows via XCom
```

## Size and backend

The default XCom backend stores values in the metadata database, serialised
as JSON (or pickled, if `enable_xcom_pickling` is set). This makes XComs
unsuitable for large objects: a multi-megabyte payload will bloat the
metadata DB and slow scheduler queries.

For larger payloads use a custom XCom backend that stores the value in S3,
GCS, or another blob store and persists only a pointer in the metadata DB.
Airflow ships with an abstract `BaseXCom` class for this purpose. A common
pattern is `S3XComBackend` that writes the value as a JSON object under a
deterministic key and reads it back on pull.

## When not to use XCom

If a task only needs a value to pass through to a downstream operator's
template, prefer Jinja templating (`{{ ti.xcom_pull(...) }}`) or
`{{ params.x }}` over manual XCom manipulation. If two tasks need a large
shared dataset, write it to object storage and pass the URI through XCom,
not the data itself.
