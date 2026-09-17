---
title: "RedisReplicaLinkDown: runbook and fix"
description: "RedisReplicaLinkDown means a Redis replica has lost its link to the master and is serving stale data. How to find why sync keeps failing."
permalink: /runbooks/redisreplicalinkdown/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Redis (redis_exporter)
severity: critical
cta:
  title: Get this alert, tested
  text: "RedisReplicaLinkDown is one of the 9 Redis rules in a 179-alert pack, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=redisreplicalinkdown
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# RedisReplicaLinkDown

A Redis replica has been disconnected from its master for several minutes and is no longer receiving updates.

| | |
|---|---|
| Severity | critical |
| Source | oliver006/redis_exporter 1.50+ |
| Key metric | `redis_master_link_up` (1 = `master_link_status:up`) |

## What it means

On a replica, `INFO replication` reports whether the link to the master is up. The alert fires when it has stayed down for several minutes, longer than a normal reconnect or short resync.

While the link is down, the replica serves increasingly stale reads, and it is not a safe failover target: promoting it would lose everything written since the link dropped. If this replica is your only one, you have no redundancy.

## Common causes

- The master is down or was replaced, and the replica still points at the old address.
- A full resync loops: the replica requests a full sync, the RDB transfer takes too long, and the master drops it because `client-output-buffer-limit replica` is exceeded.
- The replication backlog (`repl-backlog-size`) is too small, so every short disconnect forces a full sync.
- Wrong `masterauth` after a password or ACL change.
- Network policy, firewall or DNS change between replica and master.

## First checks

1. On the replica, look at link state and how long it has been down:
   ```bash
   redis-cli -h <replica> INFO replication | grep -E '^(role|master_host|master_port|master_link_status|master_link_down_since_seconds|master_sync_in_progress)'
   ```
2. On the master, check whether it sees the replica:
   ```bash
   redis-cli -h <master> INFO replication
   ```
3. Read the replica log for the reason sync fails (auth errors, timeouts, "MASTER aborted replication"):
   ```bash
   kubectl -n <ns> logs <replica-pod> --tail=100 | grep -iE 'master|sync|replica'
   ```
4. Check the master log for output buffer disconnects:
   ```bash
   kubectl -n <ns> logs <master-pod> --tail=200 | grep -i 'scheduled to be closed ASAP for overcoming of output buffer limits'
   ```
5. Find all affected replicas:
   ```promql
   redis_master_link_up == 0
   ```

## Fixing it

If the master moved, run `REPLICAOF <new-master> <port>` (or let Sentinel reconfigure it). If full syncs keep failing, raise the replica output buffer limit and `repl-backlog-size` on the master with `CONFIG SET`, and persist the change to the config. Fix `masterauth` after credential changes, and check connectivity with `redis-cli -h <master> PING` from the replica host.

## Related alerts

- [RedisReplicasDisconnected](/runbooks/redisreplicasdisconnected/): the master's view of lost replicas.
- [RedisMissingMaster](/runbooks/redismissingmaster/): the link may be down because there is no master.
- [RedisDown](/runbooks/redisdown/): check whether the master itself is unreachable.
