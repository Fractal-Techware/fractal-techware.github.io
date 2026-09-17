---
title: "PostgresqlHighRollbackRate: runbook and fix"
description: "PostgresqlHighRollbackRate means a large share of PostgreSQL transactions roll back. How to find the failing statements and the client behind them."
permalink: /runbooks/postgresqlhighrollbackrate/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: PostgreSQL (postgres_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "PostgresqlHighRollbackRate is one of 10 PostgreSQL alerts in the pack of 179, each tested with promtool and paired with a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=postgresqlhighrollbackrate
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PostgresqlHighRollbackRate

A meaningful fraction of transactions in a PostgreSQL database are ending in rollback instead of commit, usually because statements are failing.

| | |
|---|---|
| Severity | warning |
| Source | prometheus-community/postgres_exporter 0.15+ |
| Key metrics | `pg_stat_database_xact_rollback`, `pg_stat_database_xact_commit` (label `datname`) |

## What it means

`pg_stat_database` counts committed and rolled-back transactions per database. The alert compares the two rates and fires when rollbacks make up a significant share of traffic for a sustained period. Databases with almost no traffic are ignored, so a few failures on an idle database do not page anyone.

Rollbacks are not always errors: some frameworks roll back read-only transactions on purpose, and tests do it constantly. A sudden change from the usual ratio is the signal to chase.

## Common causes

- Application errors: constraint violations, bad input, type errors after a schema migration.
- Serialization failures (`40001`) under `REPEATABLE READ`/`SERIALIZABLE` and deadlock victims (`40P01`).
- `statement_timeout` or `lock_timeout` cancelling statements, which aborts the transaction.
- An ORM or pooler that issues `ROLLBACK` at the end of every read.
- A retry loop hammering the same failing statement.

## First checks

1. Find the database and when the rollback rate changed:
   ```promql
   sum by (instance, datname) (rate(pg_stat_database_xact_rollback[5m]))
   ```
   Graph it next to `rate(pg_stat_database_xact_commit[5m])` and line it up with deploys.
2. Read the errors that caused the rollbacks:
   ```bash
   grep -E 'ERROR|FATAL' /var/log/postgresql/postgresql-*.log \
     | sed -E 's/^.*(ERROR|FATAL)/\1/' | sort | uniq -c | sort -rn | head -20
   ```
3. Confirm the per-database counters directly:
   ```sql
   SELECT datname, xact_commit, xact_rollback, deadlocks, conflicts
   FROM pg_stat_database
   WHERE datname NOT LIKE 'template%';
   ```
4. Identify which clients are active in that database:
   ```sql
   SELECT usename, application_name, client_addr, count(*)
   FROM pg_stat_activity WHERE datname = '<datname>'
   GROUP BY 1, 2, 3 ORDER BY 4 DESC;
   ```
   If errors are not logged, set `log_min_error_statement = error` temporarily.

## Fixing it

Fix the error, not the metric. Roll back a bad deploy or migration if the timing matches. For serialization failures or deadlocks, add retries and shorten transactions. If the rollbacks are intentional read-only rollbacks from a framework, confirm that, then tune the threshold or exclude that database.

## Related alerts

- [PostgresqlDeadlocks](/runbooks/postgresqldeadlocks/): deadlock victims are counted as rollbacks.
- [PostgresqlLongRunningTransaction](/runbooks/postgresqllongrunningtransaction/): timeouts on long work abort transactions.
- [PostgresqlTooManyConnections](/runbooks/postgresqltoomanyconnections/): failing retries can also exhaust connections.
