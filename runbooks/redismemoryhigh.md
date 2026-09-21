---
title: "RedisMemoryHigh: runbook and fix"
description: "RedisMemoryHigh means Redis memory use is close to maxmemory, so evictions or OOM write errors are near. Find big keys and choose a fix."
permalink: /runbooks/redismemoryhigh/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Redis (redis_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "RedisMemoryHigh is one of 9 Redis alerts in the pack of 179, each shipped with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=redismemoryhigh
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# RedisMemoryHigh

Redis is using nearly all of the memory allowed by its `maxmemory` setting.

| | |
|---|---|
| Severity | warning |
| Source | oliver006/redis_exporter 1.50+ |
| Key metrics | `redis_memory_used_bytes`, `redis_memory_max_bytes` |

## What it means

The alert compares used memory with the configured `maxmemory` and fires when usage has stayed close to the limit for several minutes. Instances without a `maxmemory` limit are ignored (they can still be killed by the OS or container limit, which this alert cannot see).

What happens at the limit depends on `maxmemory-policy`. With `noeviction`, writes fail with `OOM command not allowed when used memory > 'maxmemory'`. With an `allkeys-*` or `volatile-*` policy, Redis evicts keys, which is fine for a pure cache but data loss for anything else.

## Common causes

- Organic data growth without a matching capacity increase.
- Keys written without a TTL, or TTLs much longer than intended.
- A few very large keys: unbounded lists, sets or hashes used as queues or logs.
- Client output buffers growing (slow subscribers, `MONITOR`, big replies).
- High fragmentation after heavy churn.

## First checks

1. Read the memory breakdown and the policy:
   ```bash
   redis-cli -h <host> INFO memory | grep -E '^(used_memory_human|used_memory_rss_human|maxmemory_human|maxmemory_policy|mem_fragmentation_ratio|mem_clients_normal)'
   redis-cli -h <host> CONFIG GET maxmemory-policy
   ```
2. Ask Redis for its own diagnosis:
   ```bash
   redis-cli -h <host> MEMORY DOCTOR
   ```
3. Find the largest keys (uses `SCAN`, safe on production but adds some load):
   ```bash
   redis-cli -h <host> --bigkeys
   redis-cli -h <host> --memkeys
   ```
4. Check how many keys lack an expiry, per database:
   ```bash
   redis-cli -h <host> INFO keyspace
   ```
   Compare `keys=` with `expires=` for each `db`.
5. Look at the growth trend to estimate time to full:
   ```promql
   deriv(redis_memory_used_bytes[1h])
   ```

## Fixing it

Short term, raise `maxmemory` with `CONFIG SET maxmemory <bytes>` if the host or container has headroom (keep room for fork during persistence). Delete or trim unbounded keys with `UNLINK` rather than `DEL` to avoid blocking. Longer term, add TTLs, cap collections, choose a policy that matches the use case, and shard or scale up.

## Related alerts

- [RedisKeyEvictions](/runbooks/rediskeyevictions/): what happens next under an eviction policy.
- [RedisRdbLastSaveFailed](/runbooks/redisrdblastsavefailed/): fork for snapshots can fail when memory is tight.
- [RedisDown](/runbooks/redisdown/): an OOM kill takes the instance down.
