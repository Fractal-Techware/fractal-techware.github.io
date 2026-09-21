---
title: "KubePersistentVolumeClaimPending: runbook and fix"
description: "KubePersistentVolumeClaimPending means a PVC has stayed unbound, so its pod cannot start. How to find the provisioning error and get it bound."
permalink: /runbooks/kubepersistentvolumeclaimpending/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes persistent volumes
severity: warning
cta:
  title: Get this alert, tested
  text: "KubePersistentVolumeClaimPending is one of the persistent volume alerts in the pack of 179, all with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubepersistentvolumeclaimpending
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubePersistentVolumeClaimPending

A PersistentVolumeClaim has been waiting for a volume for a long time, and any pod that mounts it is stuck in `Pending` too.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metric | `kube_persistentvolumeclaim_status_phase` (labels `namespace`, `persistentvolumeclaim`, `phase`) |

## What it means

A claim is `Pending` until it is bound to a PersistentVolume, either a pre-created one or one a provisioner creates. A few seconds is normal. This alert fires only when the claim has stayed unbound well beyond that, so something is blocking provisioning or matching.

Typical impact: a new StatefulSet replica never starts, a Helm release hangs, or a scale-up does nothing.

## Common causes

- No StorageClass given and no default StorageClass in the cluster.
- The StorageClass uses `volumeBindingMode: WaitForFirstConsumer` and no pod using the claim has been scheduled yet (by design, but it looks stuck).
- The CSI provisioner is down or failing (cloud quota, IAM, wrong zone).
- Static provisioning: no available PV matches the requested size, access mode, StorageClass or selector.
- Requested access mode not supported by the driver (for example `ReadWriteMany` on a block-storage driver).

## First checks

1. List every pending claim:
   ```bash
   kubectl get pvc -A | grep Pending
   ```
2. Read the claim's events; the provisioner reason is usually right there:
   ```bash
   kubectl -n <ns> describe pvc <pvc>
   ```
3. Check the StorageClass exists and see its binding mode:
   ```bash
   kubectl get storageclass
   kubectl get storageclass <class> -o yaml | grep -E 'provisioner|volumeBindingMode|allowedTopologies'
   ```
4. If the mode is `WaitForFirstConsumer`, look at the consuming pod instead; a scheduling problem is the real blocker:
   ```bash
   kubectl -n <ns> describe pod <pod> | sed -n '/Events/,$p'
   ```
5. Check the provisioner logs:
   ```bash
   kubectl -n <csi-namespace> logs <csi-controller-pod> -c csi-provisioner --tail=100
   ```

## Fixing it

Set `storageClassName` explicitly or mark a default class (`storageclass.kubernetes.io/is-default-class: "true"`). Fix the provisioner error (quota, permissions, zone). For static PVs, create one that matches the claim. `storageClassName` and access modes cannot be edited on an existing claim, so delete and recreate it if they are wrong.

## Related alerts

- [KubePersistentVolumeErrors](/runbooks/kubepersistentvolumeerrors/): the same broken provisioner often leaves failed PVs.
- [KubePersistentVolumeClaimLost](/runbooks/kubepersistentvolumeclaimlost/): a claim that was bound and then lost its volume.
- [KubeStatefulSetReplicasMismatch](/runbooks/kubestatefulsetreplicasmismatch/): replicas waiting on these claims.
