---
title: "KubeQuotaExceeded: runbook and fix"
description: "KubeQuotaExceeded means a namespace is using more than its ResourceQuota hard limit, usually after the quota was lowered. How to reconcile it."
permalink: /runbooks/kubequotaexceeded/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes quotas, limits & disruption budgets
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeQuotaExceeded is one of 179 alerts in the pack, grouped with the Kubernetes quota and disruption budget rules and backed by promtool unit tests and a runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubequotaexceeded
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeQuotaExceeded

A namespace is consuming more of a resource than its ResourceQuota allows, which the admission check should normally make impossible.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metric | `kube_resourcequota` (labels `namespace`, `resourcequota`, `resource`, `type`) |

## What it means

Kubernetes enforces quotas only when objects are created or updated. Existing objects are never removed to satisfy a quota. So usage above the hard limit means the limit changed after the fact, or objects got in without going through quota admission. The alert fires when this state persists.

Consequences: every new pod or object for that resource is rejected until usage falls back below the limit, which can freeze deployments, scale-ups and Jobs for the whole namespace.

## Common causes

- The quota's `spec.hard` was reduced (by a platform team, a GitOps sync or a policy controller) below current usage.
- A ResourceQuota was created in a namespace that already had workloads.
- A quota with a new `scopes` or `scopeSelector` suddenly started counting existing pods.
- Objects created while the quota controller or admission plugin was unavailable.

## First checks

1. Show used and hard values for the namespace and spot the resource where used is higher:
   ```promql
   sum by (resourcequota, resource, type) (kube_resourcequota{namespace="<ns>"})
   ```
2. Inspect the quota and when it changed:
   ```bash
   kubectl -n <ns> describe resourcequota <quota>
   kubectl -n <ns> get resourcequota <quota> -o yaml --show-managed-fields | grep -E 'manager:|time:'
   ```
3. Check whether new pods are being rejected:
   ```bash
   kubectl -n <ns> get events --field-selector reason=FailedCreate
   ```
4. List the largest consumers of the exceeded resource:
   ```bash
   kubectl -n <ns> top pods --sort-by=cpu
   kubectl -n <ns> get pods -o custom-columns='POD:.metadata.name,REQ_CPU:.spec.containers[*].resources.requests.cpu,REQ_MEM:.spec.containers[*].resources.requests.memory'
   ```
5. Check your GitOps repository history for the quota change.

## Fixing it

Decide which side is wrong. If the new limit is intentional, bring the namespace under it by scaling down or right-sizing requests, then confirm new pods can be created. If the change was accidental, restore the previous `spec.hard` in its source of truth, so a sync does not revert your fix.

## Related alerts

- [KubeQuotaFullyUsed](/runbooks/kubequotafullyused/): at the limit rather than over it.
- [KubeQuotaAlmostFull](/runbooks/kubequotaalmostfull/): approaching the limit.
- [KubeHpaReplicasMismatch](/runbooks/kubehpareplicasmismatch/): autoscalers cannot add pods while the quota is exceeded.
