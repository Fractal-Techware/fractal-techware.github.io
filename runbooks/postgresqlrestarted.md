---
title: "PostgresqlRestarted: runbook and fix"
description: "PostgresqlRestarted means the PostgreSQL postmaster started recently. Confirm whether it was planned, a crash, an OOM kill or a failover."
permalink: /runbooks/postgresqlrestarted/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: PostgreSQL (postgres_exporter)
severity: info
cta:
  title: Get this alert, tested
  text: "PostgresqlRestarted is among the 10 PostgreSQL alerts in the pack of 179, each shipped with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=postgresqlrestarted
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PostgresqlRestarted

The PostgreSQL server process started only a few minutes ago. This is a notification to confirm the restart was expected.

| | |
|---|---|
| Severity | info |
| Source | prometheus-community/postgres_exporter 0.15+ |
| Key metric | `pg_postmaster_start_time_seconds` (Unix timestamp of postmaster start) |

## What it means

The exporter reports when the postmaster started. The alert fires briefly after that timestamp changes, then resolves on its own. A planned maintenance window explains it; an unexplained restart deserves a look, because every connection was dropped and caches are cold.

Also note that a backend crash (segfault, OOM kill of a single backend) makes PostgreSQL reinitialize all sessions and run crash recovery, but does not always change the postmaster start time. Check logs for that case too.

## Common causes

- Planned restart: config change needing restart, minor version upgrade, host reboot.
- Kubernetes pod rescheduled, evicted, or failed its liveness probe.
- OOM killer terminating the postmaster or the container hitting its memory limit.
- PANIC after the WAL or data volume filled.
- Failover managed by Patroni or a cloud provider promoting a new primary.

## First checks

1. Confirm the start time and role:
   ```sql
   SELECT pg_postmaster_start_time(), now() - pg_postmaster_start_time() AS uptime, pg_is_in_recovery();
   ```
2. Read the log around the restart for the shutdown reason:
   ```bash
   grep -E 'PANIC|FATAL|terminated by signal|shutting down|database system is ready' \
     /var/log/postgresql/postgresql-*.log | tail -30
   ```
3. On Kubernetes, check restart counts and the last termination reason:
   ```bash
   kubectl -n <ns> get pod <postgres-pod> -o jsonpath='{.status.containerStatuses[*].lastState.terminated}'
   kubectl -n <ns> get events --sort-by=.lastTimestamp | tail -20
   ```
4. On a VM, look for OOM kills and reboots:
   ```bash
   dmesg -T | grep -i 'killed process'
   last -x reboot | head -5
   ```
5. Check how often it happens:
   ```promql
   changes(pg_postmaster_start_time_seconds[24h])
   ```

## Fixing it

If it was planned, nothing to do. If memory was the cause, lower `shared_buffers`, `work_mem` or `max_connections`, or raise the container limit. For disk-full crashes, grow the volume and find what filled it (WAL retained by a stale slot is common). For repeated failovers, review the HA manager's logs and health checks.

## Related alerts

- [PostgresqlDown](/runbooks/postgresqldown/): fires if the restart takes longer than a couple of minutes.
- [PostgresqlReplicationLagHigh](/runbooks/postgresqlreplicationlaghigh/): standbys fall behind after a primary restart.
- [PostgresqlCacheHitRatioLow](/runbooks/postgresqlcachehitratiolow/): expected briefly while the cache warms.
