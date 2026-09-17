---
title: "KubePodDisruptionBudgetViolated: runbook and fix"
description: "KubePodDisruptionBudgetViolated means fewer pods are healthy than a PodDisruptionBudget requires. How to find the unhealthy pods and restore them."
permalink: /runbooks/kubepoddisruptionbudgetviolated/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes quotas, limits & disruption budgets
severity: warning
cta:
  title: Get this alert, tested
  text: "KubePodDisruptionBudgetViolated is in the pack of 179 alerts alongside the other PDB and quota rules, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubepoddisruptionbudgetviolated
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubePodDisruptionBudgetViolated

A PodDisruptionBudget has fewer healthy pods than it promises to keep, so the application is already below its minimum safe availability.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metrics | `kube_poddisruptionbudget_status_current_healthy`, `kube_poddisruptionbudget_status_desired_healthy` |

## What it means

A PDB states how many matching pods must stay available (`minAvailable`) or how many may be down (`maxUnavailable`). The disruption controller turns that into a desired healthy count. This alert fires when the number of Ready pods has stayed below that count for a sustained period.

A PDB only blocks voluntary evictions such as drains. It cannot stop crashes, OOM kills or node failures, and those are what usually cause this. The service is running with less redundancy than intended, and further disruption could cause an outage.

## Common causes

- Pods crash looping, failing readiness probes or stuck on image pulls.
- A node failure took out several replicas at once (poor spreading across nodes or zones).
- Replicas scaled down below `minAvailable` by a person, GitOps sync or HPA minimum.
- New pods `Pending` because of capacity, quota or unbound volumes.
- PDB selector matching more pods than intended, raising the required count.

## First checks

1. List affected PDBs and the gap:
   ```promql
   kube_poddisruptionbudget_status_desired_healthy - kube_poddisruptionbudget_status_current_healthy > 0
   ```
   ```bash
   kubectl get pdb -A
   ```
2. See the selector and status:
   ```bash
   kubectl -n <ns> describe pdb <pdb>
   ```
3. List matching pods that are not Ready:
   ```bash
   kubectl -n <ns> get pods -l <selector> -o wide
   ```
4. Find out why they are unhealthy:
   ```bash
   kubectl -n <ns> describe pod <pod> | sed -n '/Conditions/,$p'
   kubectl -n <ns> logs <pod> --previous --tail=50
   ```
5. Check whether the unhealthy pods share a node or zone.

## Fixing it

Fix whatever keeps pods from being Ready, following the pod-level alert that is almost certainly also firing. Pause node drains and cluster upgrades until the budget is met again. If replicas were scaled below the budget on purpose, adjust `minAvailable` to match, and add topology spread constraints so one node failure cannot violate it.

## Related alerts

- [KubePodDisruptionBudgetBlocksEviction](/runbooks/kubepoddisruptionbudgetblockseviction/): the budget has no room left for evictions.
- [KubePodCrashLooping](/runbooks/kubepodcrashlooping/): a frequent root cause.
- [KubePodNotReady](/runbooks/kubepodnotready/): pods counted as unhealthy.
