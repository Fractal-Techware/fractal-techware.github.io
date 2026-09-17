---
title: "KubeStatefulSetReplicasMismatch: runbook and fix"
description: "KubeStatefulSetReplicasMismatch means a StatefulSet has had the wrong number of ready pods with no rollout progress. How to find the blocking pod."
permalink: /runbooks/kubestatefulsetreplicasmismatch/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes workloads
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeStatefulSetReplicasMismatch is one of 13 workload alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubestatefulsetreplicasmismatch
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeStatefulSetReplicasMismatch

A StatefulSet does not have the number of ready pods it asks for, and nothing is changing to fix that.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metrics | `kube_statefulset_replicas`, `kube_statefulset_status_replicas_ready`, `kube_statefulset_status_replicas_updated` |

## What it means

The ready replica count differs from the desired count, and the updated count has not moved recently, so this is not a rollout that is simply slow. The alert fires once the situation has persisted for a while.

StatefulSets are usually databases, queues and clustered services. One missing member can mean lost redundancy or lost quorum. And because pods are handled in order by default, one stuck ordinal blocks every pod after it.

## Common causes

- **Pod Pending on storage**: its PVC is bound to a volume in a zone with no schedulable node, or the StorageClass cannot provision.
- **Readiness probe failing**: the member cannot join the cluster, replay its log, or reach its peers.
- **Pod stuck Terminating on a dead node**: the controller will not create a replacement with the same identity until the old pod is gone.
- **OrderedReady policy** waiting on an unhealthy lower ordinal.
- **Quota or insufficient resources** for the next pod.

## First checks

1. List the StatefulSet's pods with their nodes and states:
   ```bash
   kubectl -n <namespace> get sts <statefulset>
   kubectl -n <namespace> get pods -l <selector> -o wide
   ```
2. Find unready pods owned by StatefulSets across the cluster:
   ```promql
   (kube_pod_status_ready{condition="false"} == 1)
     * on (namespace, pod) group_left (owner_name)
     kube_pod_owner{owner_kind="StatefulSet"}
   ```
3. Describe the lowest-numbered unhealthy pod; it is the one blocking the others:
   ```bash
   kubectl -n <namespace> describe pod <statefulset>-<ordinal>
   ```
4. Check its volume claim and where the volume lives:
   ```bash
   kubectl -n <namespace> get pvc -l <selector>
   kubectl get pv <pv-name> -o jsonpath='{.spec.nodeAffinity}{"\n"}'
   ```
5. For a failing probe, read the application log: `kubectl -n <namespace> logs <pod> --tail=100`.

## Fixing it

Fix the storage or scheduling constraint so the pending pod can land. For a pod stuck Terminating on a node that is truly gone, confirm the node is powered off first, then `kubectl delete pod <pod> --grace-period=0 --force`. Doing that while the old process might still run risks two members with the same identity. For readiness failures, fix the application (peer discovery, data corruption) rather than loosening the probe.

## Related alerts

- [KubeStatefulSetGenerationMismatch](/runbooks/kubestatefulsetgenerationmismatch/): the controller has not even seen the latest spec.
- [KubePodNotReady](/runbooks/kubepodnotready/): fires on the individual stuck pod.
- [KubePersistentVolumeClaimPending](/runbooks/kubepersistentvolumeclaimpending/): the claim for a new replica cannot bind.
