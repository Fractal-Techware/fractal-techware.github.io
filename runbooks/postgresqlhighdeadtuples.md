---
title: "PostgresqlHighDeadTuples: runbook and fix"
description: "PostgresqlHighDeadTuples means a PostgreSQL table holds a large share of dead rows. Find why autovacuum is not keeping up and clean the table."
permalink: /runbooks/postgresqlhighdeadtuples/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: PostgreSQL (postgres_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "PostgresqlHighDeadTuples is one of the 10 PostgreSQL rules in a pack of 179 alerts, all shipped with promtool unit tests and runbooks."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=postgresqlhighdeadtuples
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PostgresqlHighDeadTuples

A PostgreSQL table has accumulated a large number of dead row versions, and they have not been cleaned up for a long time.

| | |
|---|---|
| Severity | warning |
| Source | prometheus-community/postgres_exporter 0.15+ (stat_user_tables collector) |
| Key metrics | `pg_stat_user_tables_n_dead_tup`, `pg_stat_user_tables_n_live_tup` (labels `datname`, `schemaname`, `relname`) |

## What it means

Every `UPDATE` and `DELETE` leaves the old row version behind as a dead tuple until VACUUM reclaims it. The alert fires when a table has both a large absolute number of dead tuples and a high proportion relative to live rows, and that has persisted for an extended period. Small tables and short spikes after a batch job are ignored.

It matters because dead tuples bloat the table and its indexes, slow sequential and index scans, and waste disk. If VACUUM is blocked entirely, the same problem eventually threatens transaction ID wraparound.

## Common causes

- A long-running or `idle in transaction` session holding an old snapshot, so VACUUM cannot remove anything newer.
- An inactive replication slot or a standby with `hot_standby_feedback` holding back `xmin`.
- Autovacuum settings too conservative for a high-churn table (scale factor, cost limit).
- All autovacuum workers busy on other large tables.
- Queue-like tables with heavy insert/delete churn.

## First checks

1. List the worst tables and their vacuum history (run in the affected database):
   ```sql
   SELECT schemaname, relname, n_live_tup, n_dead_tup,
          last_autovacuum, last_vacuum, autovacuum_count
   FROM pg_stat_user_tables
   ORDER BY n_dead_tup DESC
   LIMIT 10;
   ```
2. Look for anything holding back cleanup:
   ```sql
   SELECT pid, state, backend_xmin, now() - xact_start AS xact_age
   FROM pg_stat_activity WHERE backend_xmin IS NOT NULL ORDER BY age(backend_xmin) DESC LIMIT 5;
   SELECT slot_name, active, xmin, catalog_xmin FROM pg_replication_slots;
   ```
3. Check whether autovacuum is running on it right now:
   ```sql
   SELECT pid, relid::regclass, phase, heap_blks_scanned, heap_blks_total
   FROM pg_stat_progress_vacuum;
   ```
4. Graph the trend per table:
   ```promql
   topk(10, pg_stat_user_tables_n_dead_tup)
   ```

## Fixing it

Remove the blocker first (end the old transaction, drop an unused replication slot), otherwise vacuum will not help. Then run `VACUUM (VERBOSE, ANALYZE) <schema>.<table>;` and check the output for "dead row versions cannot be removed yet". For chronic cases, lower `autovacuum_vacuum_scale_factor` on that table with `ALTER TABLE ... SET (...)` and raise the autovacuum cost limit.

## Related alerts

- [PostgresqlLongRunningTransaction](/runbooks/postgresqllongrunningtransaction/): the most common reason VACUUM cannot clean up.
- [PostgresqlCacheHitRatioLow](/runbooks/postgresqlcachehitratiolow/): bloated tables read more pages from disk.
- [PostgresqlReplicationLagHigh](/runbooks/postgresqlreplicationlaghigh/): standbys with feedback can hold back cleanup.
