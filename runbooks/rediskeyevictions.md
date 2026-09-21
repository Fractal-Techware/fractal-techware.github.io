---
title: "RedisKeyEvictions: runbook and fix"
description: "RedisKeyEvictions means Redis has hit maxmemory and is deleting keys under its eviction policy. Decide whether that is acceptable and how to stop it."
permalink: /runbooks/rediskeyevictions/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Redis (redis_exporter)
severity: info
cta:
  title: Get this alert, tested
  text: "RedisKeyEvictions is included in the pack of 179 alerts with 8 other Redis rules, each backed by promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=rediskeyevictions
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# RedisKeyEvictions

Redis has been evicting keys for a sustained period because it keeps reaching its memory limit.

| | |
|---|---|
| Severity | info |
| Source | oliver006/redis_exporter 1.50+ |
| Key metric | `redis_evicted_keys_total` (from `evicted_keys` in `INFO stats`) |

## What it means

When used memory hits `maxmemory` and the policy is anything other than `noeviction`, Redis removes keys to make room for new writes. The alert fires when evictions continue over a longer window rather than a single burst.

It is informational because for a pure cache with `allkeys-lru` or `allkeys-lfu`, steady eviction is the design. It becomes a real problem when Redis also holds data that must not disappear (sessions, rate-limit counters, job queues, locks), or when eviction is so heavy that the cache hit rate collapses.

## Common causes

- The dataset has outgrown `maxmemory`.
- Keys stored without TTLs crowding out short-lived ones.
- A single large key or a new feature caching much more data.
- Cache and durable data mixed on the same instance.
- `maxmemory` set lower than intended (or lowered during an incident and never restored).

## First checks

1. Confirm the policy and how full memory is:
   ```bash
   redis-cli -h <host> CONFIG GET maxmemory-policy
   redis-cli -h <host> INFO memory | grep -E '^(used_memory_human|maxmemory_human)'
   ```
2. Check evictions against cache effectiveness:
   ```bash
   redis-cli -h <host> INFO stats | grep -E '^(evicted_keys|expired_keys|keyspace_hits|keyspace_misses)'
   ```
   A falling hit ratio alongside evictions means the cache is too small for the working set.
3. Graph eviction rate per instance:
   ```promql
   sum by (instance) (rate(redis_evicted_keys_total[5m]))
   ```
4. Find what is using the memory:
   ```bash
   redis-cli -h <host> --bigkeys
   redis-cli -h <host> INFO keyspace
   ```

## Fixing it

If this is a cache and hit rates are fine, you can accept it or lower the alert's priority for that instance. Otherwise give Redis more memory (`CONFIG SET maxmemory`, a larger node, or sharding), add TTLs to keys that lack them, and trim oversized keys. Move data that must not be evicted to a separate instance with `noeviction` and alert on its memory instead.

## Related alerts

- [RedisMemoryHigh](/runbooks/redismemoryhigh/): the memory pressure that leads to evictions.
- [RedisRdbLastSaveFailed](/runbooks/redisrdblastsavefailed/): memory pressure also breaks snapshots.
- [RedisTooManyConnections](/runbooks/redistoomanyconnections/): client buffers add to used memory.
