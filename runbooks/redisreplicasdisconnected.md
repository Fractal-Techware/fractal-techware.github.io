---
title: "RedisReplicasDisconnected: runbook and fix"
description: "RedisReplicasDisconnected means a Redis master recently lost one or more connected replicas. How to find which replica dropped and why."
permalink: /runbooks/redisreplicasdisconnected/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Redis (redis_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "RedisReplicasDisconnected is part of the Redis set of 9 alerts in the pack of 179, all with promtool unit tests and runbooks."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=redisreplicasdisconnected
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# RedisReplicasDisconnected

The number of replicas connected to a Redis master has just dropped.

| | |
|---|---|
| Severity | warning |
| Source | oliver006/redis_exporter 1.50+ |
| Key metric | `redis_connected_slaves` (from `connected_slaves` in `INFO replication`) |

## What it means

The alert watches the master's replica count and fires when it goes down within a short window. It stays active for a while afterwards so a brief drop is not missed between notifications. It does not fire if a replica was never connected; it detects losses.

Fewer replicas means less redundancy and fewer failover candidates. If you use `min-replicas-to-write`, the master may start rejecting writes when too many replicas go away.

## Common causes

- A replica pod or host was restarted, rescheduled or scaled down.
- Replica disconnected for exceeding the replica output buffer limit during a large write burst or full sync.
- Network interruption between master and a replica.
- A failover reconfigured replicas to follow a different master.
- The replica process was OOM killed while loading a large RDB.

## First checks

1. See which master lost replicas and when:
   ```promql
   redis_connected_slaves
   ```
2. List the replicas the master currently sees, with their offsets:
   ```bash
   redis-cli -h <master> INFO replication
   ```
   Lines like `slave0:ip=...,port=...,state=online,offset=...,lag=...` show each connected replica.
3. Compare with the replicas you expect, and check each missing one:
   ```bash
   redis-cli -h <replica> INFO replication | grep -E '^(role|master_host|master_link_status)'
   kubectl -n <ns> get pods -l <redis-selector> -o wide
   ```
4. Look in the master log for why the connection closed:
   ```bash
   kubectl -n <ns> logs <master-pod> --since=30m | grep -iE 'replica|output buffer|connection lost'
   ```
5. Check whether an ongoing full sync is involved: `INFO persistence` on the master shows `rdb_bgsave_in_progress`.

## Fixing it

If the replica is restarting, it usually reconnects on its own; confirm `state=online` on the master. For output buffer disconnects, raise `client-output-buffer-limit replica` and `repl-backlog-size`. If a failover moved the replica elsewhere, that is expected; confirm the topology matches what Sentinel reports. Replace or repair a replica that is repeatedly OOM killed.

## Related alerts

- [RedisReplicaLinkDown](/runbooks/redisreplicalinkdown/): the replica-side alert for a lasting disconnect.
- [RedisMissingMaster](/runbooks/redismissingmaster/): check the group still has a master.
- [RedisMemoryHigh](/runbooks/redismemoryhigh/): memory pressure during sync often kills replicas.
