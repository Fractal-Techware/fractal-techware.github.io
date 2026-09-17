---
title: "PostgresqlCacheHitRatioLow: runbook and fix"
description: "PostgresqlCacheHitRatioLow means PostgreSQL reads many blocks from disk instead of shared buffers. How to find the queries and size memory correctly."
permalink: /runbooks/postgresqlcachehitratiolow/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: PostgreSQL (postgres_exporter)
severity: info
cta:
  title: Get this alert, tested
  text: "PostgresqlCacheHitRatioLow is included with 9 other PostgreSQL alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=postgresqlcachehitratiolow
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PostgresqlCacheHitRatioLow

PostgreSQL has been reading an unusually large share of data blocks from disk rather than from its shared buffer cache.

| | |
|---|---|
| Severity | info |
| Source | prometheus-community/postgres_exporter 0.15+ |
| Key metrics | `pg_stat_database_blks_hit`, `pg_stat_database_blks_read` (label `datname`) |

## What it means

`blks_hit` counts block requests served from `shared_buffers`; `blks_read` counts blocks PostgreSQL had to fetch from the OS (which may still come from the OS page cache). The alert fires when the hit ratio for a database stays below what a healthy OLTP workload normally achieves for a long stretch.

It is informational: nothing is broken, but latency is likely higher and disk IO busier than it needs to be. Analytics workloads that scan large tables naturally have lower ratios.

## Common causes

- Working set has grown beyond `shared_buffers` and available RAM.
- Missing indexes causing sequential scans over large tables.
- A new report, export or batch job reading cold data.
- Table and index bloat inflating the number of pages to read.
- Restart or failover emptied the cache (temporary; it warms up).

## First checks

1. See which database is reading from disk and since when:
   ```promql
   sum by (instance, datname) (rate(pg_stat_database_blks_read[5m]))
   ```
2. Find the tables doing the reads and whether they are sequentially scanned:
   ```sql
   SELECT s.schemaname, s.relname, io.heap_blks_read, io.heap_blks_hit,
          io.idx_blks_read, s.seq_scan, s.idx_scan
   FROM pg_statio_user_tables io JOIN pg_stat_user_tables s USING (relid)
   ORDER BY io.heap_blks_read DESC
   LIMIT 10;
   ```
3. If `pg_stat_statements` is installed, find the queries responsible:
   ```sql
   SELECT left(query, 80), calls, shared_blks_read, shared_blks_hit
   FROM pg_stat_statements ORDER BY shared_blks_read DESC LIMIT 10;
   ```
4. Check memory settings against host RAM:
   ```sql
   SHOW shared_buffers;
   SHOW effective_cache_size;
   ```

## Fixing it

Add indexes for queries doing large sequential scans, and move reporting to a replica. If the working set simply outgrew memory, raise `shared_buffers` (commonly around a quarter of RAM, restart required) or give the host more memory. After a restart, the ratio recovers on its own; `pg_prewarm` can speed that up.

## Related alerts

- [PostgresqlHighDeadTuples](/runbooks/postgresqlhighdeadtuples/): bloat means more pages to read.
- [PostgresqlRestarted](/runbooks/postgresqlrestarted/): a cold cache after restart lowers the ratio temporarily.
- [PostgresqlLongRunningTransaction](/runbooks/postgresqllongrunningtransaction/): large scans often show up as long transactions.
