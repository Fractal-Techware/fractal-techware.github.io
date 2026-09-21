---
title: "PostgresqlTooManyConnections: runbook and fix"
description: "PostgresqlTooManyConnections warns that PostgreSQL is nearing max_connections. Find who holds the connections and free them before logins fail."
permalink: /runbooks/postgresqltoomanyconnections/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: PostgreSQL (postgres_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "PostgresqlTooManyConnections ships in the pack of 179 alerts, alongside 9 other PostgreSQL rules, all unit tested with promtool and documented."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=postgresqltoomanyconnections
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PostgresqlTooManyConnections

PostgreSQL is using most of its `max_connections` slots, and new clients will soon get "sorry, too many clients already".

| | |
|---|---|
| Severity | warning |
| Source | prometheus-community/postgres_exporter 0.15+ |
| Key metrics | `pg_stat_activity_count` (labels `datname`, `state`), `pg_settings_max_connections` |

## What it means

The exporter counts backends in `pg_stat_activity` and reads the `max_connections` setting. The alert fires when the total has stayed close to the limit for several minutes. Once the limit is hit, only superusers can use the few `superuser_reserved_connections`; every application login fails.

Each PostgreSQL connection is a full OS process with its own memory, so raising the limit is rarely the right first move.

## Common causes

- Connection leaks: code that opens connections and never returns them to the pool.
- Many application replicas each with a generous pool size (after a scale-out, pools multiply).
- Sessions stuck `idle in transaction`, holding a slot and often locks.
- Slow queries or lock waits making every request hold its connection longer.
- No pooler (PgBouncer, pgcat, RDS Proxy) in front of a large fleet.

## First checks

1. Break the connections down by database, user, application and state:
   ```sql
   SELECT datname, usename, application_name, state, count(*)
   FROM pg_stat_activity
   GROUP BY 1, 2, 3, 4
   ORDER BY count(*) DESC
   LIMIT 20;
   ```
2. Compare with the limits:
   ```sql
   SHOW max_connections;
   SHOW superuser_reserved_connections;
   ```
3. Find long idle and idle-in-transaction sessions:
   ```sql
   SELECT pid, usename, client_addr, state, now() - state_change AS in_state_for
   FROM pg_stat_activity
   WHERE state IN ('idle', 'idle in transaction')
   ORDER BY state_change
   LIMIT 20;
   ```
4. See when the growth started and which database drives it:
   ```promql
   sum by (instance, datname, state) (pg_stat_activity_count)
   ```

## Fixing it

For immediate relief, terminate clearly abandoned sessions: `SELECT pg_terminate_backend(<pid>);` (target old `idle in transaction` sessions first). Then fix the source: lower per-replica pool sizes, set `idle_in_transaction_session_timeout`, and put a transaction-mode pooler in front of the database. Raise `max_connections` only with a matching memory budget; it requires a restart.

## Related alerts

- [PostgresqlLongRunningTransaction](/runbooks/postgresqllongrunningtransaction/): stuck transactions are a common reason slots never free up.
- [PostgresqlDown](/runbooks/postgresqldown/): at the limit, the exporter itself may fail to connect.
- [PostgresqlDeadlocks](/runbooks/postgresqldeadlocks/): lock contention makes connections pile up.
