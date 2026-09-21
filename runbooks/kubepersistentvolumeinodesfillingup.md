---
title: "KubePersistentVolumeInodesFillingUp: runbook and fix"
description: "KubePersistentVolumeInodesFillingUp means a PVC has almost no free inodes, so file creation fails even with free space. How to find and clean up."
permalink: /runbooks/kubepersistentvolumeinodesfillingup/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes persistent volumes
severity: critical
cta:
  title: Get this alert, tested
  text: "KubePersistentVolumeInodesFillingUp is one of the Kubernetes persistent volume alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubepersistentvolumeinodesfillingup
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubePersistentVolumeInodesFillingUp

A PersistentVolumeClaim has almost run out of inodes, so the application will soon be unable to create new files, no matter how many bytes are free.

| | |
|---|---|
| Severity | critical |
| Source | kubelet volume stats + kube-state-metrics v2.x |
| Key metrics | `kubelet_volume_stats_inodes`, `kubelet_volume_stats_inodes_free`, `kubelet_volume_stats_inodes_used` |

## What it means

Filesystems like ext4 allocate a fixed number of inodes when they are formatted. Every file, directory and symlink uses one. When the free inode count on a mounted claim drops to a tiny fraction of the total, this alert fires. Read-only volumes are ignored.

It is critical because the failure is confusing: `df -h` shows plenty of space, yet writes fail with "No space left on device". Caches, session stores and mail or queue spools usually break first.

## Common causes

- Millions of tiny files: cache directories, session files, thumbnails, per-message files.
- A cleanup job that stopped running, so temp files accumulate forever.
- Build or package caches (npm, pip, Maven) stored on a persistent volume.
- A small volume formatted with the default inode ratio but used for small files.

## First checks

1. List claims by inode usage:
   ```promql
   sort_desc(kubelet_volume_stats_inodes_used / kubelet_volume_stats_inodes)
   ```
2. Confirm inside the pod that inodes, not bytes, are the problem:
   ```bash
   kubectl -n <ns> exec <pod> -- df -i <mount-path>
   kubectl -n <ns> exec <pod> -- df -h <mount-path>
   ```
3. Find the directories with the most files:
   ```bash
   kubectl -n <ns> exec <pod> -- sh -c 'for d in <mount-path>/*; do echo "$(find "$d" -xdev | wc -l) $d"; done | sort -n | tail'
   ```
4. Check how fast the count is rising, to judge how long you have:
   ```promql
   deriv(kubelet_volume_stats_inodes_used{namespace="<ns>", persistentvolumeclaim="<pvc>"}[1h])
   ```

## Fixing it

Delete the stale small files (for example `find <dir> -type f -mtime +7 -delete` after confirming what they are) and restore the job that should have cleaned them. Expanding the PVC usually adds inodes on ext4 too, since resize2fs grows inode tables with the filesystem, so a resize is a valid stopgap. Long term, move caches to `emptyDir`, store small objects in a database or object store, or reformat with a lower bytes-per-inode ratio (XFS allocates inodes dynamically).

## Related alerts

- [KubePersistentVolumeFillingUp](/runbooks/kubepersistentvolumefillingup/): the byte-based version of the same problem.
- [KubePersistentVolumeErrors](/runbooks/kubepersistentvolumeerrors/): check it if a resize attempt fails.
- [KubePodCrashLooping](/runbooks/kubepodcrashlooping/): apps often crash once they cannot create files.
