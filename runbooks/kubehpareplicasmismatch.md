---
title: "KubeHpaReplicasMismatch: runbook and fix"
description: "KubeHpaReplicasMismatch means an HPA wants more or fewer pods than it has and is not getting there. How to find what blocks the scale."
permalink: /runbooks/kubehpareplicasmismatch/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes autoscaling (HPA)
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeHpaReplicasMismatch is one of 4 HPA alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubehpareplicasmismatch
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeHpaReplicasMismatch

A HorizontalPodAutoscaler has decided on a replica count, but the workload has been stuck at a different number for a while.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x (autoscaling/v2) |
| Key metrics | `kube_horizontalpodautoscaler_status_desired_replicas`, `kube_horizontalpodautoscaler_status_current_replicas` |

## What it means

The HPA computes a desired replica count from its metrics. Normally the current count catches up within a minute or two. This alert fires when desired and current differ, the HPA is somewhere between its min and max, and the current count has not changed at all for a sustained period. In other words: scaling was requested and nothing happened.

The usual impact is under-provisioning during a load spike: latency rises while the autoscaler "thinks" it has already reacted.

## Common causes

- New pods are `Pending`: not enough node capacity, or the cluster autoscaler cannot add nodes.
- A namespace ResourceQuota blocks new pods.
- Pods start but never become Ready (failing probes, crash loops, image pull errors).
- Another controller or a GitOps tool keeps resetting `spec.replicas` on the Deployment.
- Scale-down is held back by a `behavior` stabilization window or policy (expected, but long windows can trigger this).

## First checks

1. Compare desired and current across HPAs:
   ```promql
   kube_horizontalpodautoscaler_status_desired_replicas - kube_horizontalpodautoscaler_status_current_replicas != 0
   ```
2. Read the HPA's conditions and events:
   ```bash
   kubectl -n <ns> describe hpa <hpa>
   ```
3. Look for pods that are not running and why:
   ```bash
   kubectl -n <ns> get pods -l <selector> --field-selector=status.phase=Pending
   kubectl -n <ns> describe pod <pending-pod> | sed -n '/Events/,$p'
   ```
4. Check the ReplicaSet for quota or admission errors:
   ```bash
   kubectl -n <ns> describe rs <replicaset> | grep -iE 'FailedCreate|quota|forbidden'
   ```
5. Check whether something else is writing replicas (look at `managedFields` managers):
   ```bash
   kubectl -n <ns> get deploy <name> --show-managed-fields -o yaml | grep -E 'manager:|replicas'
   ```

## Fixing it

Unblock the thing new pods are waiting on: add node capacity or fix the cluster autoscaler, raise the quota, or fix the readiness problem. If a GitOps tool owns `spec.replicas`, remove that field from the manifest (or ignore it in the sync diff) so the HPA is the single owner.

## Related alerts

- [KubeHpaMaxedOut](/runbooks/kubehpamaxedout/): the HPA has hit its ceiling instead.
- [KubeHpaUnableToScale](/runbooks/kubehpaunabletoscale/): the HPA cannot even update the scale subresource.
- [KubeQuotaFullyUsed](/runbooks/kubequotafullyused/): a full quota is a common blocker.
- [KubeDeploymentReplicasMismatch](/runbooks/kubedeploymentreplicasmismatch/): the Deployment side of the same gap.
