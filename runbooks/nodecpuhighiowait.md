---
title: "NodeCPUHighIOWait: runbook and fix"
description: "NodeCPUHighIOWait means host CPUs spend a large share of time waiting on disk or network I/O. How to find the slow device and the process behind it."
permalink: /runbooks/nodecpuhighiowait/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeCPUHighIOWait ships in the pack of 179 alerts, alongside 24 other node_exporter host alerts, each with promtool unit tests and a runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodecpuhighiowait
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeCPUHighIOWait

The host's CPUs have spent a large share of their time idle but blocked on I/O for a sustained period, which means storage (or a network filesystem) is the bottleneck.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `cpu` collector |
| Key metric | `node_cpu_seconds_total{mode="iowait"}` |

## What it means

iowait is time a CPU had nothing else to run while at least one task was waiting for I/O to complete. It is not CPU work: the machine is waiting on disks. The alert fires when the average iowait share across all CPUs stays high for a long stretch, filtering out short bursts like a nightly backup.

Users feel this as slow requests, database latency, stalled deploys and a rising load average, even though CPU "usage" looks moderate.

## Common causes

- A disk at its IOPS or throughput limit (cloud volumes with burst credits exhausted are a classic).
- A heavy batch job: backup, `rsync`, compaction, reindexing, log shipping.
- Memory pressure forcing constant page cache eviction or swapping.
- A slow or unhealthy NFS/iSCSI backend.
- A degraded RAID array rebuilding.

## First checks

1. See how iowait is spread over time on this host:
   ```promql
   sum by (instance) (rate(node_cpu_seconds_total{mode="iowait", instance="<instance>"}[5m]))
   ```
2. Find the busiest devices:
   ```promql
   topk(5, rate(node_disk_io_time_seconds_total{instance="<instance>"}[5m]))
   ```
3. Confirm on the host and watch `await`, `aqu-sz` and `%util` per device:
   ```bash
   iostat -xz 2 5
   ```
4. Find the processes doing the I/O:
   ```bash
   sudo iotop -oPa -d 2
   # or, without iotop:
   pidstat -d 2 5
   ```
5. Rule out memory pressure and swap:
   ```bash
   vmstat 2 5   # watch si/so and wa columns
   ```

## Fixing it

Throttle or reschedule the heavy job (`ionice -c3 -p <pid>` lowers its I/O priority). If the volume is simply too small for the workload, raise its provisioned IOPS/throughput or move hot data to faster storage. If swapping shows up, fix the memory problem first. For network storage, check the server and the path to it.

## Related alerts

- [NodeDiskIOSaturation](/runbooks/nodediskiosaturation/): pinpoints which device has a growing queue.
- [NodeLoadHigh](/runbooks/nodeloadhigh/): tasks blocked on I/O count toward load average.
- [NodeMemoryMajorPagesFaults](/runbooks/nodememorymajorpagesfaults/): memory pressure that turns into disk reads.
- [NodeHighCPUUsage](/runbooks/nodehighcpuusage/): distinguishes real CPU saturation from waiting.
