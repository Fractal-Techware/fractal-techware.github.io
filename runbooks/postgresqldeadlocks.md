---
title: "PostgresqlDeadlocks: runbook and fix"
description: "PostgresqlDeadlocks fires when PostgreSQL keeps aborting transactions to break deadlocks. Find the conflicting queries and fix lock ordering."
permalink: /runbooks/postgresqldeadlocks/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: PostgreSQL (postgres_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "PostgresqlDeadlocks is one of the PostgreSQL rules in a 179-alert pack where every alert has promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=postgresqldeadlocks
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PostgresqlDeadlocks

PostgreSQL is repeatedly detecting deadlocks in a database and killing one transaction each time to break the cycle.

| | |
|---|---|
| Severity | warning |
| Source | prometheus-community/postgres_exporter 0.15+ |
| Key metric | `pg_stat_database_deadlocks` (counter, label `datname`) |

## What it means

A deadlock happens when two or more transactions each hold a lock the other needs. After `deadlock_timeout` PostgreSQL checks for cycles and aborts one participant with `ERROR: deadlock detected`. The alert fires when more than a handful of these occur in a short window; it keeps firing a little while after they stop so it does not flap.

The database protects itself, but the application sees failed transactions. Unless it retries, users see errors or lost writes.

## Common causes

- Two code paths updating the same rows or tables in opposite order.
- Batch jobs updating many rows without a deterministic `ORDER BY`, colliding with each other or with OLTP traffic.
- Foreign keys: inserts into child tables take share locks on parent rows that another transaction is updating.
- `SELECT ... FOR UPDATE` over overlapping ranges taken in different orders.
- A new deploy that changed transaction boundaries.

## First checks

1. Find the database and when it started:
   ```promql
   sum by (instance, datname) (increase(pg_stat_database_deadlocks[1h]))
   ```
2. Read the server log. Each deadlock logs both processes, their queries and the locks involved:
   ```bash
   grep -A 8 'deadlock detected' /var/log/postgresql/postgresql-*.log | tail -60
   ```
3. Check current blocking chains (they often precede deadlocks):
   ```sql
   SELECT pid, pg_blocking_pids(pid) AS blocked_by, state,
          now() - xact_start AS xact_age, left(query, 80) AS query
   FROM pg_stat_activity
   WHERE cardinality(pg_blocking_pids(pid)) > 0;
   ```
4. Inspect the lock types involved:
   ```sql
   SELECT l.pid, l.locktype, l.relation::regclass, l.mode, l.granted
   FROM pg_locks l JOIN pg_stat_activity a USING (pid)
   WHERE a.datname = '<datname>' AND NOT l.granted;
   ```
5. Make sure lock waits get logged: `SHOW log_lock_waits;` (turn it on if off).

## Fixing it

Correlate the queries in the log with a recent deploy or job schedule. The durable fix is consistent lock ordering: always touch tables and rows in the same order, and sort keys before bulk updates. Keep transactions short, add retry-on-`40P01` logic in the application, and index foreign key columns so lock scopes stay narrow.

## Related alerts

- [PostgresqlHighRollbackRate](/runbooks/postgresqlhighrollbackrate/): aborted deadlock victims show up as rollbacks.
- [PostgresqlLongRunningTransaction](/runbooks/postgresqllongrunningtransaction/): long transactions widen the window for lock conflicts.
- [PostgresqlTooManyConnections](/runbooks/postgresqltoomanyconnections/): waiting sessions accumulate connections.
