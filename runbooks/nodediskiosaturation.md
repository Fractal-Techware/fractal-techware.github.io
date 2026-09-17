---
title: "NodeDiskIOSaturation: runbook and fix"
description: "NodeDiskIOSaturation means a disk has a long I/O queue for a sustained time, so reads and writes wait. How to find the device, the workload and fix it."
permalink: /runbooks/nodediskiosaturation/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeDiskIOSaturation is one of 25 node_exporter alerts in a pack of 179, each tested with promtool and paired with a runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodediskiosaturation
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeDiskIOSaturation

A block device on this host has had a deep queue of pending I/O for a long time, so everything that touches it is waiting.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `diskstats` collector |
| Key metric | `node_disk_io_time_weighted_seconds_total` (label `device`) |

## What it means

The weighted I/O time counter grows by the number of in-flight requests for every second the device is busy, so its rate approximates the average queue depth. `%util` alone can hit 100% on fast SSDs that still have capacity; a large, sustained queue is the more reliable sign that the device cannot keep up. The alert fires when the queue on a real disk (sd, nvme, vd, xvd, dm, md and similar) stays high for an extended period.

Expect higher latency for databases, slow container starts, timeouts, and a rising load average and iowait on the host.

## Common causes

- Cloud volume throttled at its provisioned IOPS or throughput, or out of burst credits.
- Database compaction, vacuum, reindex, or a large backup/restore.
- Log-heavy workloads or a debug log level left on.
- Swapping onto the same disk.
- A failing disk retrying I/O, or a RAID rebuild.

## First checks

1. Rank devices by queue depth and utilisation:
   ```promql
   topk(5, rate(node_disk_io_time_weighted_seconds_total{instance="<instance>"}[5m]))
   rate(node_disk_io_time_seconds_total{instance="<instance>", device="<device>"}[5m])
   ```
2. Check read and write volume, and average latency per operation:
   ```promql
   rate(node_disk_written_bytes_total{instance="<instance>", device="<device>"}[5m])
   rate(node_disk_write_time_seconds_total{instance="<instance>", device="<device>"}[5m]) / rate(node_disk_writes_completed_total{instance="<instance>", device="<device>"}[5m])
   ```
3. Confirm on the host (`aqu-sz`, `r_await`, `w_await`):
   ```bash
   iostat -xz 2 5
   ```
4. Find the processes responsible:
   ```bash
   sudo iotop -oPa -d 2
   ```
5. Map `dm-N` devices to volumes, and check for hardware errors:
   ```bash
   lsblk -o NAME,KNAME,MOUNTPOINT,SIZE
   sudo dmesg -T | grep -iE "i/o error|reset|timeout" | tail
   ```

## Fixing it

Throttle or reschedule the heavy job, or lower its priority with `ionice`. If the volume is simply undersized, raise its IOPS/throughput tier or move hot data to a separate, faster disk. Stop swapping by fixing memory pressure. Replace disks showing errors.

## Related alerts

- [NodeCPUHighIOWait](/runbooks/nodecpuhighiowait/): the CPU side of the same bottleneck.
- [NodeLoadHigh](/runbooks/nodeloadhigh/): blocked tasks inflate load average.
- [NodeRAIDDegraded](/runbooks/noderaiddegraded/): a rebuild can saturate member disks.
