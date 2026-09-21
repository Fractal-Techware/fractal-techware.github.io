---
title: "NodeMemoryMajorPagesFaults: runbook and fix"
description: "NodeMemoryMajorPagesFaults means a host is constantly reading pages back from disk, a sign of memory pressure or swapping. How to confirm and fix it."
permalink: /runbooks/nodememorymajorpagesfaults/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeMemoryMajorPagesFaults is part of a pack of 179 Prometheus alerts, 25 of them for node_exporter hosts, each unit tested and documented."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodememorymajorpagesfaults
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeMemoryMajorPagesFaults

The host is taking a high rate of major page faults for a sustained period, meaning it keeps going to disk for memory it recently had to drop.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `vmstat` collector |
| Key metric | `node_vmstat_pgmajfault` |

## What it means

A minor page fault is cheap: the page is already in RAM. A major fault means the kernel had to read the page from disk, either from swap or from a file (program code, mmapped data) that was evicted from the page cache. A few are normal after startup. A steady high rate means the working set does not fit in memory and the host is thrashing.

Each major fault costs milliseconds instead of nanoseconds, so latency climbs across everything on the host, and disk I/O and iowait rise with it. Left alone, this often ends in the OOM killer.

## Common causes

- Processes whose combined working set exceeds RAM (a memory leak, or too many pods/services on one host).
- Swap enabled on a host that is overcommitted.
- A large mmapped dataset (search indexes, databases) bigger than available page cache.
- A cgroup memory limit set close to a container's real usage, forcing it to reclaim its own file pages.

## First checks

1. Look at the trend and when it started:
   ```promql
   increase(node_vmstat_pgmajfault{instance="<instance>"}[1h])
   ```
2. Check available memory and swap activity:
   ```promql
   node_memory_MemAvailable_bytes{instance="<instance>"} / node_memory_MemTotal_bytes{instance="<instance>"}
   rate(node_vmstat_pswpin{instance="<instance>"}[5m])
   ```
3. Find which processes are faulting (the `majflt/s` column):
   ```bash
   pidstat -r 2 5
   ```
4. Check the biggest memory users and swap usage:
   ```bash
   ps -eo pid,rss,cmd --sort=-rss | head -15
   free -h
   ```
5. On Kubernetes, see which pods use the most memory on the node:
   ```bash
   kubectl top pods -A --sort-by=memory | head -15
   ```

## Fixing it

Reduce memory demand: restart or fix the leaking process, move workloads off the host, or lower caches in the application. Add RAM or resize the instance if the load is legitimate. On Kubernetes, set realistic memory requests so the scheduler stops overpacking the node, and raise limits for containers reclaiming against their own ceiling.

## Related alerts

- [NodeMemoryHighUtilization](/runbooks/nodememoryhighutilization/): usually fires before or alongside heavy faulting.
- [NodeOOMKillDetected](/runbooks/nodeoomkilldetected/): what often happens next.
- [NodeCPUHighIOWait](/runbooks/nodecpuhighiowait/): faults show up as I/O wait.
