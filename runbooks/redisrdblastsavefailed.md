---
title: "RedisRdbLastSaveFailed: runbook and fix"
description: "RedisRdbLastSaveFailed means the last Redis RDB background save failed, so snapshots are stale and writes may be refused. How to find and fix the cause."
permalink: /runbooks/redisrdblastsavefailed/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Redis (redis_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "RedisRdbLastSaveFailed is one of 9 Redis rules in the pack of 179 alerts, all tested with promtool and each paired with a runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=redisrdblastsavefailed
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# RedisRdbLastSaveFailed

Redis tried to write an RDB snapshot in the background and the attempt failed.

| | |
|---|---|
| Severity | warning |
| Source | oliver006/redis_exporter 1.50+ |
| Key metric | `redis_rdb_last_bgsave_status` (1 = ok, 0 = last `BGSAVE` failed) |

## What it means

`INFO persistence` reports whether the most recent background save succeeded. The alert fires when it has reported failure for several minutes, meaning Redis also has not managed a successful retry.

Two consequences. Your on-disk snapshot is getting older, so a restart loses more data. And with the default `stop-writes-on-bgsave-error yes`, Redis refuses write commands with `MISCONF Redis is configured to save RDB snapshots, but it's currently unable to persist to disk`, which is an application outage.

## Common causes

- Disk full or the data directory is not writable (wrong permissions, read-only volume).
- `fork()` failing with "Cannot allocate memory" because the host lacks memory and `vm.overcommit_memory` is 0.
- Container memory limit too close to dataset size; copy-on-write during the save pushes it over and the child is killed.
- `dir` changed via `CONFIG SET` to a path that does not exist.

## First checks

1. Read persistence status:
   ```bash
   redis-cli -h <host> INFO persistence | grep -E '^(rdb_last_bgsave_status|rdb_bgsave_in_progress|rdb_changes_since_last_save|rdb_last_bgsave_time_sec|rdb_last_cow_size)'
   redis-cli -h <host> LASTSAVE
   ```
   `LASTSAVE` is the Unix time of the last successful save; `date -d @<ts>` makes it readable.
2. Find the reason in the Redis log:
   ```bash
   kubectl -n <ns> logs <redis-pod> --since=1h | grep -iE 'background saving|fork|can.t save|error'
   ```
3. Check where it writes and whether there is space:
   ```bash
   redis-cli -h <host> CONFIG GET dir
   redis-cli -h <host> CONFIG GET dbfilename
   df -h <dir>
   ```
4. On the host, check memory overcommit and free memory:
   ```bash
   sysctl vm.overcommit_memory
   free -m
   ```
5. See how many writes are unsaved: `redis_rdb_changes_since_last_save`.

## Fixing it

Free or grow the disk, fix directory ownership, or reset `dir` to a valid path, then trigger `redis-cli BGSAVE` and confirm the status returns to ok. For fork failures, set `vm.overcommit_memory = 1` on the host (the Redis documentation recommends it) and leave memory headroom above the dataset. If writes are blocked and you need them back immediately, `CONFIG SET stop-writes-on-bgsave-error no` is a temporary bypass, not a fix.

## Related alerts

- [RedisMemoryHigh](/runbooks/redismemoryhigh/): tight memory is a common reason fork fails.
- [RedisDown](/runbooks/redisdown/): a child OOM kill can take the whole container down.
- [RedisReplicasDisconnected](/runbooks/redisreplicasdisconnected/): replica full syncs also depend on successful RDB saves.
