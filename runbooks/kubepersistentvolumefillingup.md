---
title: "KubePersistentVolumeFillingUp: runbook and fix"
description: "KubePersistentVolumeFillingUp means a PVC is nearly out of space or will be soon. How to find what is filling it, and how to expand or clean up."
permalink: /runbooks/kubepersistentvolumefillingup/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes persistent volumes
severity: "warning, critical"
cta:
  title: Get this alert, tested
  text: "KubePersistentVolumeFillingUp ships in the pack of 179 alerts with both its warning and critical rules, promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubepersistentvolumefillingup
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubePersistentVolumeFillingUp

A PersistentVolumeClaim is running out of free space, and the application writing to it will start failing when it hits zero.

| | |
|---|---|
| Severity | warning, critical |
| Source | kubelet volume stats + kube-state-metrics v2.x |
| Key metrics | `kubelet_volume_stats_available_bytes`, `kubelet_volume_stats_capacity_bytes`, `kubelet_volume_stats_used_bytes` |

## What it means

The kubelet reports capacity and free bytes for every mounted PVC. The alert has two levels:

- **warning**: free space is already low and the recent trend says the volume will be full within a few days. You have time to plan.
- **critical**: only a sliver of space is left. Writes may start failing in minutes.

Read-only volumes are excluded. When a volume fills, databases crash or go read-only, queues stop accepting messages and log shippers drop data.

## Common causes

- Database growth, WAL or binlog retention, or a replication slot holding old segments.
- Application logs or temp files written to the data volume instead of stdout.
- Retention or compaction stopped (a failed cron, a broken Prometheus/Loki compactor).
- The volume was simply sized too small for normal growth.
- Backups or dumps written locally and never removed.

## First checks

1. Find the fullest volumes and how fast they are growing:
   ```promql
   sort_desc(kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes)
   ```
   ```promql
   deriv(kubelet_volume_stats_used_bytes{namespace="<ns>", persistentvolumeclaim="<pvc>"}[1h])
   ```
2. Find the pod that mounts the claim:
   ```bash
   kubectl -n <ns> get pods -o json | jq -r '.items[] | select(.spec.volumes[]?.persistentVolumeClaim.claimName=="<pvc>") | .metadata.name'
   ```
3. See what is using the space from inside the pod:
   ```bash
   kubectl -n <ns> exec <pod> -- df -h <mount-path>
   kubectl -n <ns> exec <pod> -- du -xh --max-depth=2 <mount-path> | sort -h | tail -20
   ```
4. Check whether the StorageClass allows online expansion:
   ```bash
   kubectl get storageclass <class> -o jsonpath='{.allowVolumeExpansion}'
   ```

## Fixing it

For a quick win, delete what should not be there (old dumps, rotated logs) or fix the retention job that stopped. If the growth is legitimate, expand the claim when the StorageClass supports it:

```bash
kubectl -n <ns> patch pvc <pvc> -p '{"spec":{"resources":{"requests":{"storage":"<new-size>"}}}}'
```

Watch `kubectl -n <ns> describe pvc <pvc>` for the resize conditions; some CSI drivers need a pod restart to grow the filesystem. For StatefulSets, also raise the size in the volumeClaimTemplate so new replicas match.

## Related alerts

- [KubePersistentVolumeInodesFillingUp](/runbooks/kubepersistentvolumeinodesfillingup/): the same volume can fail with free bytes but no inodes.
- [KubePersistentVolumeErrors](/runbooks/kubepersistentvolumeerrors/): an expansion or reprovision went wrong.
- [KubePodCrashLooping](/runbooks/kubepodcrashlooping/): the typical downstream symptom once writes fail.
