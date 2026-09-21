---
title: "NodeFilesystemDeviceError: runbook and fix"
description: "NodeFilesystemDeviceError means node_exporter cannot stat a mounted filesystem, often a hung NFS mount or failing disk. How to diagnose and fix it."
permalink: /runbooks/nodefilesystemdeviceerror/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeFilesystemDeviceError is one of 25 node_exporter host alerts in the pack of 179 alerts, all unit tested with promtool and shipped with runbooks."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodefilesystemdeviceerror
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeFilesystemDeviceError

node_exporter has been unable to read the size and usage of a mounted filesystem for a while, which usually means the mount is hung, gone, or broken.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `filesystem` collector |
| Key metric | `node_filesystem_device_error` (labels `device`, `mountpoint`, `fstype`) |

## What it means

For each mount, node_exporter calls `statfs()`. If that call errors or does not return in time, it sets `node_filesystem_device_error` to 1 for that mount and stops exporting its size metrics. The alert fires when this persists, not on a single failed scrape.

The side effect matters as much as the error: your space and inode alerts for that mount are now blind. And if the cause is a hung network mount, any process touching that path (including backups and shells) will block.

## Common causes

- A stale NFS or CIFS mount after the server went away or the export changed.
- A FUSE mount whose daemon crashed (sshfs, s3fs, rclone).
- A failing disk or a filesystem the kernel remounted or shut down after I/O errors.
- Permission problems when node_exporter runs in a container without the host root mounted correctly.

## First checks

1. List affected mounts:
   ```promql
   count by (instance, mountpoint, fstype, device) (node_filesystem_device_error > 0)
   ```
2. Test the mount on the host with a timeout, so your shell does not hang:
   ```bash
   timeout 5 stat -f <mountpoint>; echo "exit=$?"
   ```
3. Look for kernel-level trouble:
   ```bash
   sudo dmesg -T | grep -iE "nfs|i/o error|ext4|xfs|blk_update_request" | tail -30
   ```
4. Check the mount table and the remote server:
   ```bash
   findmnt <mountpoint>
   showmount -e <nfs-server>
   ```
5. Check node_exporter's logs for statfs errors or stale mount messages (some are only visible with `--log.level=debug`):
   ```bash
   journalctl -u node_exporter --since "1 hour ago" | grep -iE "statfs|stale"
   ```

## Fixing it

For a dead network or FUSE mount, restore the server or daemon, then remount; if it is stuck, `umount -l <mountpoint>` detaches it lazily. For disk errors, check SMART data (`smartctl -a /dev/<disk>`), run `fsck` from maintenance mode and plan a replacement. If the mount is intentionally unreachable, exclude it with `--collector.filesystem.mount-points-exclude`. For slow but healthy mounts, `--collector.filesystem.mount-timeout` controls how long node_exporter waits.

## Related alerts

- [NodeFilesystemAlmostOutOfSpace](/runbooks/nodefilesystemalmostoutofspace/): cannot evaluate while this mount is erroring.
- [NodeFilesystemAlmostOutOfFiles](/runbooks/nodefilesystemalmostoutoffiles/): same blind spot for inodes.
- [NodeRAIDDegraded](/runbooks/noderaiddegraded/): the underlying array may be losing disks.
- [NodeExporterDown](/runbooks/nodeexporterdown/): a hung mount can make scrapes time out entirely.
