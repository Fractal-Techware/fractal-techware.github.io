---
title: "NodeFilesystemAlmostOutOfFiles: runbook and fix"
description: "NodeFilesystemAlmostOutOfFiles means a filesystem is running out of inodes, so new files fail even with free space. How to find and fix the culprit."
permalink: /runbooks/nodefilesystemalmostoutoffiles/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: "warning, critical"
cta:
  title: Get this alert, tested
  text: "NodeFilesystemAlmostOutOfFiles is one of 25 host alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodefilesystemalmostoutoffiles
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeFilesystemAlmostOutOfFiles

A writable filesystem on this host has almost no free inodes left, so creating files will soon fail with "No space left on device" even though `df -h` looks fine.

| | |
|---|---|
| Severity | warning, critical |
| Source | node_exporter 1.x, `filesystem` collector |
| Key metrics | `node_filesystem_files`, `node_filesystem_files_free`, `node_filesystem_readonly` |

## What it means

Every file, directory and symlink uses one inode, and most filesystems (ext4 in particular) fix the inode count when the filesystem is created. The alert fires when free inodes on a read-write mount have stayed low for a sustained period. Pseudo filesystems and container overlay mounts are excluded.

The **warning** means inodes are running low and you have time to clean up. **Critical** means the filesystem is close to exhausted: log rotation, package installs, sockets, lock files and databases can start failing at any moment.

## Common causes

- Millions of tiny files: session files, mail queues, cache directories, build artifacts.
- A cron job or application writing a temp file per request and never deleting it.
- Container image layers and old logs piling up under `/var/lib/containerd` or `/var/lib/docker`.
- A filesystem created with a large bytes-per-inode ratio, then used for small files.

## First checks

1. Find the most inode-starved filesystems across the fleet:
   ```promql
   bottomk(10, node_filesystem_files_free{fstype!~"tmpfs|overlay|squashfs"})
   ```
2. Confirm on the host:
   ```bash
   df -i
   ```
3. Find which directories hold the most inodes (stays on one filesystem):
   ```bash
   sudo du --inodes -x / 2>/dev/null | sort -n | tail -20
   ```
4. Drill into the top directory to find the exact producer:
   ```bash
   sudo find /var/<dir> -xdev -type f | cut -d/ -f1-5 | sort | uniq -c | sort -n | tail
   ```
5. Check whether usage is still growing, to judge urgency:
   ```promql
   deriv(node_filesystem_files_free{instance="<instance>", mountpoint="<mountpoint>"}[1h])
   ```

## Fixing it

Delete or archive the small files (for huge directories, `find <dir> -type f -mtime +7 -delete` is faster than `rm *`). Then stop the source: fix the application, add a `systemd-tmpfiles` or cron cleanup, or prune container images with `crictl rmi --prune` or `docker image prune`. If the workload legitimately needs many files, move it to a filesystem with more inodes (XFS allocates inodes dynamically) or recreate ext4 with a smaller `-i` ratio.

## Related alerts

- [NodeFilesystemAlmostOutOfSpace](/runbooks/nodefilesystemalmostoutofspace/): the same mount can run out of bytes instead of inodes.
- [NodeFilesystemSpaceFillingUp](/runbooks/nodefilesystemspacefillingup/): predicts space exhaustion before it happens.
- [NodeFilesystemDeviceError](/runbooks/nodefilesystemdeviceerror/): the filesystem cannot be read at all, so inode data is missing.
