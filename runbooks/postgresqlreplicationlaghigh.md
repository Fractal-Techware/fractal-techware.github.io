---
title: "PostgresqlReplicationLagHigh: runbook and fix"
description: "PostgresqlReplicationLagHigh means a PostgreSQL standby is replaying WAL well behind the primary. Find whether network, IO or conflicts cause the lag."
permalink: /runbooks/postgresqlreplicationlaghigh/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: PostgreSQL (postgres_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "PostgresqlReplicationLagHigh is part of the 10-alert PostgreSQL set in a pack of 179 rules, each shipped with promtool unit tests and a runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=postgresqlreplicationlaghigh
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PostgresqlReplicationLagHigh

A PostgreSQL standby has been noticeably behind its primary for several minutes, so reads from it are stale and a failover would lose or delay recent data.

| | |
|---|---|
| Severity | warning |
| Source | prometheus-community/postgres_exporter 0.15+ (replication collector) |
| Key metrics | `pg_replication_lag_seconds`, `pg_replication_is_replica` |

## What it means

On a standby, the exporter reports lag as the time since the last replayed transaction. The alert fires only on instances that are replicas, when that lag stays high rather than spiking briefly.

One caveat: this measure is time based. If the primary receives no writes, there is nothing to replay and the lag grows even though the standby is fully caught up. Check LSNs before assuming a real problem.

## Common causes

- Heavy write bursts on the primary (bulk loads, index builds, large `UPDATE`/`DELETE`).
- Standby disk or CPU too slow to replay WAL at the primary's rate.
- Network saturation or packet loss between primary and standby.
- Replay paused by query conflicts because `max_standby_streaming_delay` lets long queries on the standby block replay.
- The WAL receiver disconnected and the standby is catching up from archive.

## First checks

1. On the primary, look at each standby's position and lag columns:
   ```sql
   SELECT application_name, client_addr, state, sync_state,
          pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS replay_bytes_behind,
          write_lag, flush_lag, replay_lag
   FROM pg_stat_replication;
   ```
2. On the standby, compare received and replayed WAL:
   ```sql
   SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn(),
          pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn()) AS replay_backlog_bytes,
          now() - pg_last_xact_replay_timestamp() AS since_last_replay,
          pg_is_wal_replay_paused();
   ```
   A large gap between receive and replay points to replay (IO, conflicts); no gap but high `replay_bytes_behind` on the primary points to the network or WAL receiver.
3. Confirm the WAL receiver is streaming:
   ```sql
   SELECT status, sender_host, last_msg_receipt_time FROM pg_stat_wal_receiver;
   ```
4. Graph lag across replicas:
   ```promql
   max by (instance) (pg_replication_lag_seconds)
   ```

## Fixing it

If replay is blocked by standby queries, cancel them or lower `max_standby_streaming_delay`. If the standby is IO bound, move it to faster storage or spread bulk writes on the primary into smaller batches. Resume replay if someone paused it with `SELECT pg_wal_replay_resume();`. Use replication slots so the primary keeps WAL for a standby that falls far behind, while watching primary disk usage.

## Related alerts

- [PostgresqlLongRunningTransaction](/runbooks/postgresqllongrunningtransaction/): long standby queries can hold up replay.
- [PostgresqlRestarted](/runbooks/postgresqlrestarted/): a restarted standby starts out behind.
- [PostgresqlDown](/runbooks/postgresqldown/): a lagging replica is often noticed right after its primary fails.
