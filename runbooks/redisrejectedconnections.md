---
title: "RedisRejectedConnections: runbook and fix"
description: "RedisRejectedConnections means Redis is refusing new clients because maxclients is reached. Find what exhausted the limit and restore capacity."
permalink: /runbooks/redisrejectedconnections/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Redis (redis_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "RedisRejectedConnections is one of the Redis alerts in a 179-alert pack where every rule has promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=redisrejectedconnections
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# RedisRejectedConnections

Redis has been turning away new client connections over the last several minutes.

| | |
|---|---|
| Severity | warning |
| Source | oliver006/redis_exporter 1.50+ |
| Key metric | `redis_rejected_connections_total` (from `rejected_connections` in `INFO stats`) |

## What it means

Redis increments `rejected_connections` each time it refuses a client because `maxclients` has been reached. The alert fires when that counter keeps increasing, meaning clients are actively failing to connect right now, not just at some point in the past.

Unlike the connection-count warning, this one is user-visible: some requests are already getting `ERR max number of clients reached`.

## Common causes

- A connection leak or retry storm filling every slot.
- A traffic spike or scale-out multiplying connection pools.
- Idle connections piling up with no server-side `timeout`.
- `maxclients` silently reduced at startup because of a low open file limit.
- Redis slowed by a blocking command, so clients time out, reconnect and never release the old sockets.

## First checks

1. Confirm the rejections and how close the client count is to the limit:
   ```bash
   redis-cli -h <host> INFO stats | grep rejected_connections
   redis-cli -h <host> INFO clients | grep connected_clients
   redis-cli -h <host> CONFIG GET maxclients
   ```
   If you cannot connect at all, retry a few times; one slot frees up quickly under churn.
2. Find the client sources holding the most connections:
   ```bash
   redis-cli -h <host> CLIENT LIST | grep -o 'addr=[^ ]*' | cut -d= -f2 | cut -d: -f1 | sort | uniq -c | sort -rn | head
   ```
3. See the rate and when it started:
   ```promql
   sum by (instance) (rate(redis_rejected_connections_total[5m]))
   ```
4. Check the startup log for a lowered limit:
   ```bash
   kubectl -n <ns> logs <redis-pod> | grep -i 'maxclients'
   ```
5. Look for slow commands causing reconnect storms: `redis-cli -h <host> SLOWLOG GET 10`.

## Fixing it

Relieve pressure first: kill idle connections from the offending host with `CLIENT KILL ADDR <ip:port>` or restart the leaking application. Set a server `timeout`, reduce client pool sizes, and add backoff to client retries. If legitimate demand exceeds the limit, raise `maxclients` together with the file descriptor limit, or put a proxy in front of Redis.

## Related alerts

- [RedisTooManyConnections](/runbooks/redistoomanyconnections/): the earlier warning before rejections begin.
- [RedisDown](/runbooks/redisdown/): the exporter may also be locked out.
- [RedisMemoryHigh](/runbooks/redismemoryhigh/): large client buffers use memory too.
