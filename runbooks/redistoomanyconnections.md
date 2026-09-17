---
title: "RedisTooManyConnections: runbook and fix"
description: "RedisTooManyConnections warns that Redis connected clients are near maxclients. Find the clients holding connections before Redis rejects new ones."
permalink: /runbooks/redistoomanyconnections/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Redis (redis_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "RedisTooManyConnections comes in the pack of 179 alerts alongside 8 other Redis rules, each with promtool unit tests and a runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=redistoomanyconnections
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# RedisTooManyConnections

The number of clients connected to Redis is approaching the `maxclients` limit.

| | |
|---|---|
| Severity | warning |
| Source | oliver006/redis_exporter 1.50+ |
| Key metrics | `redis_connected_clients`, `redis_config_maxclients` |

## What it means

The alert fires when connected clients have stayed at a large fraction of `maxclients` for several minutes. Once the limit is reached, Redis accepts the TCP connection and immediately closes it with `ERR max number of clients reached`, which applications see as intermittent connection failures.

The effective `maxclients` can also be lower than configured: Redis lowers it at startup if the process file descriptor limit is too small, and logs a warning when it does.

## Common causes

- Connection leaks: clients that create a new connection per request and never close it.
- Many application replicas, each with a large connection pool.
- Idle connections never reaped because `timeout` is 0 (the default).
- Blocked clients (`BLPOP`, `XREAD BLOCK`) holding connections for a long time.
- A low file descriptor limit shrinking the usable `maxclients`.

## First checks

1. Current count and limit:
   ```bash
   redis-cli -h <host> INFO clients | grep -E '^(connected_clients|blocked_clients)'
   redis-cli -h <host> CONFIG GET maxclients
   redis-cli -h <host> CONFIG GET timeout
   ```
2. Group connections by source IP to find the heavy client:
   ```bash
   redis-cli -h <host> CLIENT LIST | awk '{print $2}' | cut -d= -f2 | cut -d: -f1 | sort | uniq -c | sort -rn | head
   ```
3. Look for long-idle connections (the `idle=` field is seconds since last command):
   ```bash
   redis-cli -h <host> CLIENT LIST | awk '{for(i=1;i<=NF;i++) if ($i ~ /^idle=/) {split($i,a,"="); if (a[2] > 3600) print}}' | head
   ```
4. Check whether growth follows a deploy or scale-out:
   ```promql
   redis_connected_clients
   ```

## Fixing it

Fix the leaking client or reduce pool sizes per replica. Set `CONFIG SET timeout <seconds>` so idle connections are closed (do not do this if clients rely on long-lived idle Pub/Sub connections). Kill specific offenders with `CLIENT KILL ADDR <ip:port>`. Raise `maxclients` only after checking `ulimit -n` for the Redis process allows it.

## Related alerts

- [RedisRejectedConnections](/runbooks/redisrejectedconnections/): fires once the limit is actually hit.
- [RedisMemoryHigh](/runbooks/redismemoryhigh/): each client adds buffer memory.
- [RedisDown](/runbooks/redisdown/): a full client table can lock out the exporter.
