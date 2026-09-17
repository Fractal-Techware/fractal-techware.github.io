---
title: "KubeQuotaAlmostFull: runbook and fix"
description: "KubeQuotaAlmostFull means a namespace ResourceQuota is close to its hard limit, so new pods may soon be rejected. How to check usage and act early."
permalink: /runbooks/kubequotaalmostfull/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes quotas, limits & disruption budgets
severity: info
cta:
  title: Get this alert, tested
  text: "KubeQuotaAlmostFull is one of 7 quota, limit and disruption budget alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubequotaalmostfull
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeQuotaAlmostFull

A namespace is using most of one of its ResourceQuota limits. Nothing is broken yet, but the next deploy or scale-up may be refused.

| | |
|---|---|
| Severity | info |
| Source | kube-state-metrics v2.x |
| Key metric | `kube_resourcequota` (labels `namespace`, `resourcequota`, `resource`, `type="hard"` or `"used"`) |

## What it means

A ResourceQuota caps what a namespace can consume: CPU and memory requests or limits, pod count, PVCs, services, and so on. The alert fires when usage of one resource has sat just below its hard limit for a while. It is informational: a heads-up to the namespace owner, not a page.

The risk is timing. Rolling updates temporarily run extra pods (`maxSurge`), and HPAs add replicas under load, so a namespace that is "almost full" at rest can hit the wall exactly when it needs headroom.

## Common causes

- Organic growth: more services or replicas than when the quota was sized.
- Requests set far above real usage, consuming quota without using the resources.
- Leftover objects: completed Jobs' pods, old ReplicaSets, orphaned PVCs or LoadBalancer services.
- An HPA that has scaled out and stayed there.

## First checks

1. See which resources are close to their limit:
   ```promql
   sort_desc(
     kube_resourcequota{type="used"}
       / ignoring (type) kube_resourcequota{type="hard"}
   )
   ```
2. Read the quota as Kubernetes sees it:
   ```bash
   kubectl -n <ns> describe resourcequota
   ```
3. Find the biggest consumers of requests in the namespace:
   ```bash
   kubectl -n <ns> get pods -o custom-columns='POD:.metadata.name,CPU:.spec.containers[*].resources.requests.cpu,MEM:.spec.containers[*].resources.requests.memory'
   ```
4. Compare requests with actual usage to spot over-provisioning:
   ```bash
   kubectl -n <ns> top pods --sort-by=memory
   ```
5. Look for leftovers counted against object quotas:
   ```bash
   kubectl -n <ns> get pods --field-selector=status.phase=Succeeded
   kubectl -n <ns> get pvc,svc
   ```

## What to do

Right-size requests that are well above real usage, clean up finished pods and unused PVCs, or ask the platform team for a higher quota if the growth is legitimate. Make sure there is room for at least one rolling update's surge.

## Related alerts

- [KubeQuotaFullyUsed](/runbooks/kubequotafullyused/): the next stage, when the limit is reached.
- [KubeQuotaExceeded](/runbooks/kubequotaexceeded/): usage above the hard limit.
- [KubeHpaReplicasMismatch](/runbooks/kubehpareplicasmismatch/): what a full quota looks like to an autoscaler.
