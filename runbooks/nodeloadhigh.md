---
title: "NodeLoadHigh: runbook and fix"
description: "NodeLoadHigh means the host load average is well above its CPU count for a long time. How to tell CPU contention from blocked I/O and fix it."
permalink: /runbooks/nodeloadhigh/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeLoadHigh is one of 25 host alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodeloadhigh
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeLoadHigh

The host's long-term load average has been far above the number of CPUs it has, so work is queuing up.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `loadavg` and `cpu` collectors |
| Key metrics | `node_load15`, `node_cpu_seconds_total` (used to count CPUs) |

## What it means

On Linux, load average counts tasks that are running, waiting for a CPU, or in uninterruptible sleep (usually waiting for disk or NFS). The alert compares the 15-minute load to the host's CPU count and fires when load has been a clear multiple of it for a long period, so a short spike will not page you.

High load is a symptom, not a diagnosis. It can mean "not enough CPU" or "everything is stuck waiting on storage", and the fixes are different.

## Common causes

- CPU-bound workload larger than the host: traffic growth, a runaway process, a busy-looping thread.
- Tasks stuck in D state on a slow disk or hung NFS mount.
- Noisy neighbours or CPU steal on an oversubscribed VM.
- Heavy swapping due to memory pressure.
- Kubernetes node packed with pods that have no CPU limits.

## First checks

1. Compare short and long load to see if it is getting better or worse:
   ```promql
   node_load1{instance="<instance>"}
   node_load15{instance="<instance>"}
   count by (instance) (node_cpu_seconds_total{mode="idle", instance="<instance>"})
   ```
2. Break CPU time down by mode. High `user`/`system` means CPU contention; high `iowait` means blocked I/O; high `steal` means the hypervisor:
   ```promql
   sum by (mode) (rate(node_cpu_seconds_total{instance="<instance>", mode!="idle"}[5m]))
   ```
3. On the host, find the top consumers:
   ```bash
   top -b -n1 -o %CPU | head -20
   ```
4. Count processes in uninterruptible sleep and what they wait on:
   ```bash
   ps -eo state,pid,wchan:32,cmd | awk '$1=="D"'
   ```
5. Check run queue and swap activity:
   ```bash
   vmstat 2 5   # r = runnable, b = blocked, si/so = swap
   ```

## Fixing it

For CPU contention, stop or throttle the runaway process, scale out, or move to a larger instance; on Kubernetes, set CPU requests and limits and rebalance pods. For D-state tasks, fix the underlying storage or remount the hung filesystem. For steal, move the VM or change instance type. For swapping, address memory first.

## Related alerts

- [NodeHighCPUUsage](/runbooks/nodehighcpuusage/): confirms the load is real CPU work.
- [NodeCPUHighIOWait](/runbooks/nodecpuhighiowait/): load driven by tasks waiting on I/O.
- [NodeDiskIOSaturation](/runbooks/nodediskiosaturation/): the disk those tasks are waiting on.
