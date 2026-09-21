---
title: "KubePodDisruptionBudgetBlocksEviction: runbook and fix"
description: "KubePodDisruptionBudgetBlocksEviction means a PDB allows zero disruptions, so node drains and upgrades will hang. How to find and fix it."
permalink: /runbooks/kubepoddisruptionbudgetblockseviction/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes quotas, limits & disruption budgets
severity: info
cta:
  title: Get this alert, tested
  text: "KubePodDisruptionBudgetBlocksEviction is one of the disruption budget alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubepoddisruptionbudgetblockseviction
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubePodDisruptionBudgetBlocksEviction

A PodDisruptionBudget has allowed zero voluntary disruptions for a long time, so any `kubectl drain`, node upgrade or cluster autoscaler scale-down touching its pods will stall.

| | |
|---|---|
| Severity | info |
| Source | kube-state-metrics v2.x |
| Key metrics | `kube_poddisruptionbudget_status_pod_disruptions_allowed`, `kube_poddisruptionbudget_status_expected_pods` |

## What it means

`disruptionsAllowed` is how many matching pods may be evicted right now. When it stays at zero for a PDB that actually covers pods, the eviction API refuses every request with a "would violate the pod's disruption budget" error. The alert is informational: nothing is down, but maintenance is blocked.

It tends to surface at the worst time, during a node pool upgrade that hangs for hours.

## Common causes

- Single-replica workload with `minAvailable: 1` or `maxUnavailable: 0`.
- `minAvailable` equal to the replica count (for example 3 of 3).
- A replica is unhealthy, using up the only allowed disruption.
- A Helm chart default PDB applied to a workload scaled down to one pod.
- Percentage values that round to no allowed disruptions on small replica counts.

## First checks

1. List PDBs with no disruptions allowed:
   ```bash
   kubectl get pdb -A | awk 'NR==1 || $5==0'
   ```
   ```promql
   kube_poddisruptionbudget_status_pod_disruptions_allowed == 0
   ```
2. Compare the budget with the replica count:
   ```bash
   kubectl -n <ns> get pdb <pdb> -o yaml | grep -E 'minAvailable|maxUnavailable|currentHealthy|desiredHealthy|expectedPods'
   kubectl -n <ns> get deploy,statefulset -l <selector>
   ```
3. Check whether a drain is already stuck on it:
   ```bash
   kubectl get nodes | grep SchedulingDisabled
   ```
4. Look for unhealthy pods consuming the budget:
   ```bash
   kubectl -n <ns> get pods -l <selector>
   ```

## Fixing it

Give the workload room: run at least two replicas, or switch to `maxUnavailable: 1`. If a pod is unhealthy, fix it first. On Kubernetes 1.31+ (beta since 1.27), `unhealthyPodEvictionPolicy: AlwaysAllow` lets drains evict pods that are already not Ready. For a truly single-instance workload, accept the PDB and plan a manual failover before draining, rather than deleting the PDB mid-upgrade.

## Related alerts

- [KubePodDisruptionBudgetViolated](/runbooks/kubepoddisruptionbudgetviolated/): the budget is not even met.
- [KubeNodeCordoned](/runbooks/kubenodecordoned/): a node left cordoned by a stalled drain.
- [KubeDeploymentReplicasMismatch](/runbooks/kubedeploymentreplicasmismatch/): missing replicas that use up the budget.
