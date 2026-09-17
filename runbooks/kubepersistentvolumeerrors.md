---
title: "KubePersistentVolumeErrors: runbook and fix"
description: "KubePersistentVolumeErrors means a PersistentVolume is stuck in Failed or Pending. How to read the PV events, check the CSI driver and recover."
permalink: /runbooks/kubepersistentvolumeerrors/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes persistent volumes
severity: critical
cta:
  title: Get this alert, tested
  text: "KubePersistentVolumeErrors is part of the storage group in the pack of 179 alerts, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubepersistentvolumeerrors
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubePersistentVolumeErrors

A PersistentVolume has been stuck in the `Failed` or `Pending` phase for several minutes, so the storage behind it is not usable.

| | |
|---|---|
| Severity | critical |
| Source | kube-state-metrics v2.x |
| Key metric | `kube_persistentvolume_status_phase` (labels `persistentvolume`, `phase`) |

## What it means

A healthy PV is `Available` (not yet claimed) or `Bound`. `Released` means its claim was deleted. `Failed` means Kubernetes tried to reclaim it automatically and could not. `Pending` on a PV is rare and short-lived; seeing it persist points to a provisioner that never finished.

It is critical because the data on a `Failed` volume may still exist on the backend but is detached from Kubernetes, and any workload expecting it will not start.

## Common causes

- Reclaim policy `Delete` and the CSI driver or cloud API refused the delete (permissions, volume still attached, snapshot dependency).
- Legacy `Recycle` reclaim policy failing (it is deprecated; most drivers do not support it).
- The CSI controller or external-provisioner pod is down or crash looping.
- Cloud quota or IAM errors while creating or deleting disks.
- Manually created PV pointing at a backend path or volume ID that no longer exists.

## First checks

1. List the affected volumes:
   ```promql
   kube_persistentvolume_status_phase{phase=~"Failed|Pending"} == 1
   ```
   ```bash
   kubectl get pv | grep -Ev 'Bound|Available'
   ```
2. Read the PV and its events; the message usually states the backend error:
   ```bash
   kubectl describe pv <pv>
   kubectl get events -A --field-selector involvedObject.kind=PersistentVolume,involvedObject.name=<pv>
   ```
3. Check the CSI driver for this StorageClass is healthy:
   ```bash
   kubectl get csidrivers
   kubectl -n <csi-namespace> get pods
   kubectl -n <csi-namespace> logs <csi-controller-pod> -c csi-provisioner --tail=100
   ```
4. Verify the underlying disk in your cloud console or storage system: does it exist, and is it still attached to a node?

## Fixing it

Fix the root cause first (restart the CSI controller, restore IAM permissions, detach the disk). For a `Failed` PV whose data you still need, change `persistentReclaimPolicy` to `Retain`, back up or snapshot the backend volume, then clear `spec.claimRef` so it can be bound again. If the data is truly unneeded, delete the backend volume yourself and remove the PV object.

## Related alerts

- [KubePersistentVolumeClaimLost](/runbooks/kubepersistentvolumeclaimlost/): the claim side of a volume that disappeared.
- [KubePersistentVolumeClaimPending](/runbooks/kubepersistentvolumeclaimpending/): a broken provisioner also leaves new claims unbound.
