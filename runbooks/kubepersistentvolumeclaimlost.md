---
title: "KubePersistentVolumeClaimLost: runbook and fix"
description: "KubePersistentVolumeClaimLost means a PVC points to a PersistentVolume that no longer exists. How to confirm, protect the data and rebind."
permalink: /runbooks/kubepersistentvolumeclaimlost/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes persistent volumes
severity: critical
cta:
  title: Get this alert, tested
  text: "KubePersistentVolumeClaimLost is included with the other Kubernetes storage alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubepersistentvolumeclaimlost
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubePersistentVolumeClaimLost

A PersistentVolumeClaim is in the `Lost` phase: it was bound to a volume, and that PersistentVolume object is gone.

| | |
|---|---|
| Severity | critical |
| Source | kube-state-metrics v2.x |
| Key metric | `kube_persistentvolumeclaim_status_phase` (labels `namespace`, `persistentvolumeclaim`, `phase`) |

## What it means

The claim still records a `volumeName`, but Kubernetes cannot find a PV with that name. Pods already running may keep their mount until they restart; any new pod using the claim will fail to start.

It is critical because this often means data is missing from Kubernetes' point of view. The backend disk may still exist, and the goal is to reconnect it before anyone recreates the claim and provisions an empty volume.

## Common causes

- Someone deleted the PV object manually (for example while cleaning up `Released` volumes).
- A cluster restore or migration brought back PVCs without their PVs.
- A PV was recreated under a different name.
- The backend volume was deleted outside Kubernetes and a controller or operator removed the PV.

## First checks

1. List lost claims:
   ```bash
   kubectl get pvc -A | grep Lost
   ```
2. Note the volume the claim expects:
   ```bash
   kubectl -n <ns> get pvc <pvc> -o jsonpath='{.spec.volumeName}{"\n"}'
   kubectl get pv <volume-name>
   ```
3. Check the audit log or events for who deleted it and when:
   ```bash
   kubectl get events -A --field-selector involvedObject.name=<volume-name>
   ```
4. Find the backend volume in your storage system or cloud console, using the CSI volume handle from a backup of the PV manifest, GitOps history or Velero backup.
5. Identify pods that still mount the claim and avoid restarting them:
   ```bash
   kubectl -n <ns> get pods -o wide
   ```

## Fixing it

If the backend volume still exists, recreate the PV with the same name, the original `csi.volumeHandle`, `persistentVolumeReclaimPolicy: Retain` and a `claimRef` pointing at the claim's namespace, name and UID. The claim should return to `Bound`. If the backend is gone, restore from backup into a new claim. Protect against repeats by using `Retain` for important data and restricting who may delete PVs.

## Related alerts

- [KubePersistentVolumeErrors](/runbooks/kubepersistentvolumeerrors/): a failed reclaim that often precedes cleanup mistakes.
- [KubePersistentVolumeClaimPending](/runbooks/kubepersistentvolumeclaimpending/): a recreated claim waiting for a volume.
- [KubePodCrashLooping](/runbooks/kubepodcrashlooping/): workloads that restart without their data.
