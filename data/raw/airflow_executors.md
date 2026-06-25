# Airflow Executors

The executor is the component that runs task instances. The choice of
executor determines how tasks are distributed, how isolation works, and how
the deployment scales.

## SequentialExecutor

Runs one task at a time in the scheduler process. Useful only for local
debugging on SQLite. Not suitable for production.

## LocalExecutor

Runs tasks in subprocesses on the scheduler host. Supports parallelism within
a single machine and pairs well with PostgreSQL or MySQL as the metadata DB.
A reasonable choice for small teams running on a single beefy box.

## CeleryExecutor

Distributes tasks to a fleet of worker processes via a Celery broker
(typically Redis or RabbitMQ). The scheduler enqueues tasks; workers pull
them and report status back through the result backend. Good fit when you
need to scale horizontally to many concurrent tasks but want long-lived
workers.

Operational considerations:

- Workers all share the same Python environment, so library upgrades require
  rolling the whole fleet.
- The broker is a critical dependency; size and monitor it.
- Use queues to route heavy tasks (e.g. Spark submits) to dedicated workers.

## KubernetesExecutor

Spawns a pod per task instance, using the cluster's scheduler for resource
allocation. Each task gets its own ephemeral environment, which avoids the
shared-environment problem of Celery. The tradeoff is per-task pod startup
overhead (typically 5-15 seconds) and more complex configuration.

KubernetesExecutor shines when:

- Tasks vary widely in resource needs (CPU, memory, GPU) and you want
  per-task resource requests.
- You already operate Kubernetes for other services.
- Library or image isolation per task is required.

## CeleryKubernetesExecutor

A hybrid that routes lightweight tasks to a persistent Celery pool and heavy
or specialised tasks to Kubernetes pods. Lets teams keep the latency of
Celery for normal work and only pay the pod startup cost when isolation or
custom resources are needed.
