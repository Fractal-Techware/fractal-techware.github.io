---
title: "PostgresqlLongRunningTransaction: runbook and fix"
description: "PostgresqlLongRunningTransaction means a PostgreSQL transaction has been open far too long. Find it, judge whether to kill it, and prevent repeats."
permalink: /runbooks/postgresqllongrunningtransaction/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: PostgreSQL (postgres_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "PostgresqlLongRunningTransaction comes with the pack of 179 alerts, including 10 for PostgreSQL, every one unit tested and backed by a runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=postgresqllongrunningtransaction
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PostgresqlLongRunningTransaction

A transaction in PostgreSQL has been open for a long time, either still working or sitting idle while holding locks and old snapshots.

| | |
|---|---|
| Severity | warning |
| Source | prometheus-community/postgres_exporter 0.15+ |
| Key metric | `pg_stat_activity_max_tx_duration` (labels `datname`, `state`) |

## What it means

The exporter reports the age of the oldest open transaction per database and state. The alert fires when a transaction that is `active` or `idle in transaction` has been open for a long time (tens of minutes) and stays that way.

Long transactions hurt in ways that are not obvious: they hold row and table locks that block other writers and DDL, and their snapshot prevents VACUUM from removing dead rows anywhere in the cluster, so tables and indexes bloat while it stays open.

## Common causes

- Application bug: a transaction opened, then the code waited on a network call or crashed without rolling back (`idle in transaction`).
- A person left a `BEGIN` open in psql or a GUI client.
- Reporting or analytics queries running on the primary.
- Migrations or bulk backfills done in a single transaction.
- `pg_dump` of a large database (holds one snapshot for the whole dump).

## First checks

1. List the oldest transactions:
   ```sql
   SELECT pid, usename, application_name, client_addr, state,
          now() - xact_start AS xact_age, now() - state_change AS in_state_for,
          wait_event_type, left(query, 100) AS last_query
   FROM pg_stat_activity
   WHERE xact_start IS NOT NULL
   ORDER BY xact_start
   LIMIT 10;
   ```
2. Check whether it is blocking anyone:
   ```sql
   SELECT pid, pg_blocking_pids(pid) AS blocked_by, left(query, 80)
   FROM pg_stat_activity
   WHERE cardinality(pg_blocking_pids(pid)) > 0;
   ```
3. See how long it has been growing:
   ```promql
   max by (instance, datname, state) (pg_stat_activity_max_tx_duration)
   ```
4. Also check forgotten prepared transactions, which do not appear as sessions:
   ```sql
   SELECT gid, prepared, owner, database FROM pg_prepared_xacts ORDER BY prepared;
   ```

## Fixing it

Ask the owner if it is a legitimate job. If it is abandoned or blocking production, cancel the query with `SELECT pg_cancel_backend(<pid>);` or end the session with `SELECT pg_terminate_backend(<pid>);`. Prevent repeats with `idle_in_transaction_session_timeout`, per-role `statement_timeout` for ad-hoc users, and by running reports on a replica.

## Related alerts

- [PostgresqlHighDeadTuples](/runbooks/postgresqlhighdeadtuples/): old snapshots stop VACUUM from cleaning up.
- [PostgresqlDeadlocks](/runbooks/postgresqldeadlocks/): long lock holders increase conflicts.
- [PostgresqlTooManyConnections](/runbooks/postgresqltoomanyconnections/): blocked sessions pile up behind the transaction.
