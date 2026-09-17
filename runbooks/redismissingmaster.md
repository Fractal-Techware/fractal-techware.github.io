---
title: "RedisMissingMaster: runbook and fix"
description: "RedisMissingMaster means no instance in a Redis replication group reports the master role, so writes fail. How to check Sentinel and restore a master."
permalink: /runbooks/redismissingmaster/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Redis (redis_exporter)
severity: critical
cta:
  title: Get this alert, tested
  text: "RedisMissingMaster ships with 8 other Redis alerts in the pack of 179, every one unit tested with promtool and documented in a runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=redismissingmaster
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# RedisMissingMaster

None of the Redis instances in a group currently report themselves as master, so there is nowhere for writes to go.

| | |
|---|---|
| Severity | critical |
| Source | oliver006/redis_exporter 1.50+ |
| Key metric | `redis_instance_info` (label `role` = `master` or `slave`) |

## What it means

Every scraped instance exposes its role. The alert groups instances by cluster and job and fires when that group has no master for a couple of minutes, including the case where the master's series has vanished entirely.

Replicas are read-only by default, so any write returns `READONLY You can't write against a read only replica`. Reads may continue from replicas, but they are serving data that will not change until a master returns.

## Common causes

- The master crashed or its pod was deleted, and failover did not complete.
- Sentinel has too few healthy Sentinels to reach quorum, so it will not promote a replica.
- All replicas are considered unfit (stale data beyond `down-after-milliseconds` rules, or `replica-priority 0`).
- Someone ran `REPLICAOF <host> <port>` on the master by mistake.
- The master is up but its exporter is down, so its role series is missing.

## First checks

1. See what each exporter currently reports:
   ```promql
   redis_instance_info
   ```
   Check whether a master series is missing, or a former master now shows `role="slave"`.
2. Ask each instance directly:
   ```bash
   redis-cli -h <host> INFO replication | grep -E '^(role|master_host|master_link_status|connected_slaves)'
   ```
3. If you use Sentinel, ask it what it believes:
   ```bash
   redis-cli -p 26379 SENTINEL get-master-addr-by-name <master-name>
   redis-cli -p 26379 SENTINEL ckquorum <master-name>
   redis-cli -p 26379 SENTINEL replicas <master-name>
   ```
4. Check the Sentinel logs for `+sdown`, `+odown`, `+failover-abort-*` or `-failover-abort-no-good-slave` events.
5. Confirm the exporter for the old master is up: `up{job="<redis-exporter-job>"}`.

## Fixing it

If the old master is healthy and just unmonitored, fix its exporter. If it is gone and Sentinel is stuck, restore Sentinel quorum (bring back the missing Sentinels) or force a promotion with `SENTINEL failover <master-name>`. Without Sentinel, pick the replica with the highest `master_repl_offset` and run `REPLICAOF NO ONE` on it, then repoint the other replicas and the application. Accept that writes after that offset are lost.

## Related alerts

- [RedisDown](/runbooks/redisdown/): usually fires for the old master at the same time.
- [RedisReplicaLinkDown](/runbooks/redisreplicalinkdown/): replicas lose their link when the master goes away.
- [RedisReplicasDisconnected](/runbooks/redisreplicasdisconnected/): the master side of the same story.
