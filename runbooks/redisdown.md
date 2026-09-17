---
title: "RedisDown: runbook and fix"
description: "RedisDown means redis_exporter cannot reach the Redis instance. How to check whether Redis crashed, is overloaded or the exporter is misconfigured."
permalink: /runbooks/redisdown/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Redis (redis_exporter)
severity: critical
cta:
  title: Get this alert, tested
  text: "RedisDown is one of 9 Redis alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=redisdown
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# RedisDown

redis_exporter has failed to talk to its Redis instance for a couple of minutes, so Redis is down or unreachable.

| | |
|---|---|
| Severity | critical |
| Source | oliver006/redis_exporter 1.50+ |
| Key metric | `redis_up` (1 = last scrape reached Redis, 0 = failed) |

## What it means

On each scrape the exporter connects to Redis and runs `INFO`. If that fails, `redis_up` is 0. The alert fires when this persists beyond a short grace period. The exporter process itself is running (its own `up` series is 1), so the problem is between the exporter and Redis, or Redis itself.

Applications using Redis as a cache usually degrade (slower, more database load); applications using it for sessions, queues or locks usually fail outright.

## Common causes

- Redis crashed or was OOM killed (container memory limit below actual usage).
- Redis is blocked by a slow command (`KEYS *`, big `DEL`, long Lua script), so connections time out.
- A `requirepass`/ACL change and the exporter's password is now wrong.
- The instance moved (failover, new pod IP) and the exporter points at a stale address.
- `maxclients` reached, so new connections are refused.

## First checks

1. Try to reach it from where the exporter runs:
   ```bash
   redis-cli -h <host> -p 6379 -a '<password>' --no-auth-warning PING
   ```
2. Read the exporter log for the exact error (timeout, auth, connection refused):
   ```bash
   kubectl -n <ns> logs deploy/<redis-exporter> --tail=50
   ```
3. Check the Redis process or pod and its last termination reason:
   ```bash
   kubectl -n <ns> get pod <redis-pod> -o jsonpath='{.status.containerStatuses[*].lastState.terminated.reason}'
   kubectl -n <ns> logs <redis-pod> --previous --tail=50
   ```
4. If Redis answers but slowly, look for blocking commands:
   ```bash
   redis-cli -h <host> SLOWLOG GET 10
   redis-cli -h <host> INFO clients
   ```
5. Check the scope:
   ```promql
   count by (job) (redis_up == 0)
   ```

## Fixing it

Restart a crashed instance and check the log for the reason before it happens again; for OOM, set `maxmemory` below the container limit with headroom for fork and buffers. Fix exporter credentials or address after a password rotation or failover (point it at the Sentinel-managed master or a stable Service). Ban `KEYS` in favour of `SCAN` if blocking commands caused it.

## Related alerts

- [RedisMissingMaster](/runbooks/redismissingmaster/): the down instance may have been the only master.
- [RedisReplicaLinkDown](/runbooks/redisreplicalinkdown/): replicas notice when their master disappears.
- [RedisRejectedConnections](/runbooks/redisrejectedconnections/): a full client table can look like an outage.
