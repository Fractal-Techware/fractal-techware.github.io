---
title: "NodeRAIDDegraded: runbook and fix"
description: "NodeRAIDDegraded means a Linux software RAID (mdadm) array is running with fewer active disks than it needs. How to check it and rebuild."
permalink: /runbooks/noderaiddegraded/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: critical
cta:
  title: Get this alert, tested
  text: "NodeRAIDDegraded is one of 179 alerts in the pack, including 25 for hosts, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=noderaiddegraded
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeRAIDDegraded

A software RAID array has lost redundancy: it is still serving data, but one more failure could lose it.

| | |
|---|---|
| Severity | critical |
| Source | node_exporter 1.x, `mdadm` collector (reads `/proc/mdstat`) |
| Key metrics | `node_md_disks_required`, `node_md_disks{state="active"}` |

## What it means

For every md array, node_exporter reports how many member disks the array is designed to have and how many are currently active. The alert fires when the active count stays below the required count for several minutes, meaning a member is missing, failed, or still being rebuilt.

It is critical because a degraded RAID1, RAID5 or RAID10 has no margin left. A second disk error, or a read error hit during rebuild, can take the array and its filesystem down. Performance is usually worse too, since reads must be reconstructed.

## Common causes

- A disk failed and was kicked out of the array (see [NodeRAIDDiskFailure](/runbooks/noderaiddiskfailure/)).
- A disk disappeared from the bus: loose cable, backplane or controller issue, NVMe dropping off.
- The array was assembled at boot without one member, for example after a disk was slow to appear.
- A disk was replaced but never added back to the array.
- A resync or recovery is in progress after an unclean shutdown.

## First checks

1. See which arrays are short and by how much:
   ```promql
   node_md_disks_required - ignoring(state) node_md_disks{state="active"}
   ```
2. Check the kernel's view, including rebuild progress:
   ```bash
   cat /proc/mdstat
   ```
3. Get the detailed state and which slot is missing or faulty:
   ```bash
   sudo mdadm --detail /dev/md<N>
   ```
4. Check the health of the remaining and missing disks:
   ```bash
   sudo smartctl -H -a /dev/<disk>
   dmesg -T | grep -iE "md/|ata|nvme|I/O error"
   ```
5. Verify your backups of this host are recent before touching anything.

## Fixing it

If a rebuild is already running, let it finish and avoid heavy I/O. If a disk dropped out but SMART is clean, re-add it with `mdadm --manage /dev/md<N> --re-add /dev/<part>` (or `--add`). If the disk is bad, remove it (`--fail` then `--remove`), replace the hardware, copy the partition table from a healthy member, and `--add` the new partition. Keep a hot spare on important arrays so recovery starts automatically.

## Related alerts

- [NodeRAIDDiskFailure](/runbooks/noderaiddiskfailure/): a member is explicitly marked failed.
- [NodeFilesystemDeviceError](/runbooks/nodefilesystemdeviceerror/): the filesystem on the array can no longer be read.
- [NodeDiskIOSaturation](/runbooks/nodediskiosaturation/): rebuilds and degraded reads saturate disks.
