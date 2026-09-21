---
title: "NodeRAIDDiskFailure: runbook and fix"
description: "NodeRAIDDiskFailure means a disk in a Linux mdadm software RAID array is marked failed. How to confirm the disk and replace it safely."
permalink: /runbooks/noderaiddiskfailure/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeRAIDDiskFailure is one of 25 host alerts in the 179-alert pack, and every one comes with promtool unit tests and a runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=noderaiddiskfailure
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeRAIDDiskFailure

The kernel has marked at least one member of a software RAID array as faulty.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `mdadm` collector |
| Key metric | `node_md_disks{state="failed"}` (labels `device`, `instance`) |

## What it means

node_exporter counts the members of each md array by state (`active`, `failed`, `spare`, and others). This alert fires as soon as the failed count is above zero. The md driver sets a member faulty after I/O errors, or when an administrator fails it by hand.

On its own it is a warning: if a spare took over, or the array has extra redundancy (RAID6, three-way mirror), data is still protected. It becomes urgent when the array is also degraded, so check both.

## Common causes

- The disk is genuinely dying: reallocated or pending sectors, media errors.
- Transient bus problems: a bad SATA cable, backplane slot, or HBA reset that made the kernel give up on the device.
- NVMe or SSD firmware bugs causing the device to stop responding.
- Someone ran `mdadm --fail` during maintenance and did not finish the replacement.

## First checks

1. Find the array and host:
   ```promql
   node_md_disks{state="failed"} > 0
   ```
2. Identify the faulty member (`(F)` in mdstat):
   ```bash
   cat /proc/mdstat
   sudo mdadm --detail /dev/md<N>
   ```
3. Look at the disk's SMART data and error log:
   ```bash
   sudo smartctl -a /dev/<disk>
   ```
   For NVMe, `sudo nvme smart-log /dev/nvme<N>` gives media errors and wear.
4. Check kernel messages for the reason it was failed:
   ```bash
   dmesg -T | grep -iE "raid|md/|I/O error|reset" | tail -40
   ```
5. Map the device to a physical slot before pulling anything: `ls -l /dev/disk/by-id/` shows the serial number.

## Fixing it

If SMART shows real media errors, replace the disk. Remove it from the array first:

```bash
sudo mdadm --manage /dev/md<N> --remove /dev/<failed-part>
```

After swapping hardware, recreate the partition layout (for GPT, `sgdisk --replicate=/dev/<new> /dev/<healthy>` then `sgdisk -G /dev/<new>`), add it with `mdadm --manage /dev/md<N> --add /dev/<new-part>` and watch `/proc/mdstat` until recovery completes. If the disk looks healthy and the failure was a cable or controller glitch, fix that cause and re-add the member, but keep an eye on it.

## Related alerts

- [NodeRAIDDegraded](/runbooks/noderaiddegraded/): the array has lost redundancy, not just a member.
- [NodeFilesystemDeviceError](/runbooks/nodefilesystemdeviceerror/): errors have reached the filesystem layer.
- [NodeDiskIOSaturation](/runbooks/nodediskiosaturation/): expect heavy I/O during the rebuild.
