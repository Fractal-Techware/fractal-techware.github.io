---
title: "KubeQuotaFullyUsed: runbook and fix"
description: "KubeQuotaFullyUsed means a namespace has used 100% of a ResourceQuota, so new pods or objects are rejected. How to find the consumer and free room."
permalink: /runbooks/kubequotafullyused/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes quotas, limits & disruption budgets
severity: info
cta:
  title: Get this alert, tested
  text: "KubeQuotaFullyUsed comes with the other ResourceQuota and PDB alerts in the pack of 179, every one with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubequotafullyused
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeQuotaFullyUsed

A namespace has used exactly all of one ResourceQuota limit. Any new object that needs that resource will be rejected by the API server.

| | |
|---|---|
| Severity | info |
| Source | kube-state-metrics v2.x |
| Key metric | `kube_resourcequota` (labels `namespace`, `resourcequota`, `resource`, `type`) |

## What it means

Usage equals the hard limit and has stayed there. The alert is informational because some teams size quotas tightly on purpose. Still, the namespace has zero headroom: a rolling update cannot create its surge pod, an HPA cannot add replicas, and a CronJob's next pod may fail to create.

The failure is quiet. Pods are not evicted; instead the ReplicaSet or Job controller logs `FailedCreate` events with "exceeded quota", and the Deployment simply stalls.

## Common causes

- A rollout with `maxSurge` needing one more pod than the quota allows.
- HPA scale-out consuming all remaining CPU or memory quota.
- Object-count quotas (pods, PVCs, services, secrets) reached by accumulated leftovers.
- Quota recently lowered to match the current usage.

## First checks

1. Show used and hard values side by side for the namespace (table view):
   ```promql
   sort(kube_resourcequota{namespace="<ns>"})
   ```
2. Confirm and see the numbers:
   ```bash
   kubectl -n <ns> describe resourcequota
   ```
3. Look for creations that are already failing:
   ```bash
   kubectl -n <ns> get events --field-selector reason=FailedCreate
   ```
4. Check for stalled rollouts in the namespace:
   ```bash
   kubectl -n <ns> get deploy
   kubectl -n <ns> rollout status deploy/<name> --timeout=10s
   ```
5. Identify what can be freed (finished pods, idle workloads, unused PVCs):
   ```bash
   kubectl -n <ns> get pods --field-selector=status.phase!=Running
   ```

## Fixing it

Free capacity by deleting completed pods, scaling down idle workloads or removing unused PVCs and services. Lower inflated requests so the same workload fits. If the namespace genuinely needs more, raise the quota's `spec.hard` value. For rollouts, a `maxSurge: 0` strategy avoids needing extra quota, at the cost of reduced capacity during the update.

## Related alerts

- [KubeQuotaAlmostFull](/runbooks/kubequotaalmostfull/): the earlier warning sign.
- [KubeQuotaExceeded](/runbooks/kubequotaexceeded/): usage is already above the limit.
- [KubeDeploymentRolloutStuck](/runbooks/kubedeploymentrolloutstuck/): the usual visible effect of a full quota.
