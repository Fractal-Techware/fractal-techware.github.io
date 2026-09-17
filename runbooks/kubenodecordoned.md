---
title: "KubeNodeCordoned: runbook and fix"
description: "KubeNodeCordoned means a node has been marked unschedulable for a long time. How to find who cordoned it, finish maintenance, and uncordon."
permalink: /runbooks/kubenodecordoned/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes nodes & capacity
severity: info
cta:
  title: Get this alert, tested
  text: "KubeNodeCordoned is one of 8 node and capacity alerts in the pack of 179, all covered by promtool unit tests and full runbooks."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubenodecordoned
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeNodeCordoned

A node has been cordoned (no new pods allowed) for much longer than a normal maintenance window, most likely by accident.

| | |
|---|---|
| Severity | info |
| Source | kube-state-metrics v2.x |
| Key metric | `kube_node_spec_unschedulable` (label `node`) |

## What it means

`kubectl cordon` and `kubectl drain` set `spec.unschedulable` on a node. Existing pods keep running, but nothing new is scheduled there. The alert fires once a node has stayed cordoned for a long stretch.

It is informational because nothing is broken yet. The cost is quiet: you pay for capacity you cannot use, the remaining nodes run hotter, and the next node failure hurts more than it should.

## Common causes

- **Forgotten maintenance**: someone cordoned the node for a kernel update or debugging and never uncordoned it.
- **Drain stuck**: a PodDisruptionBudget or a pod without a controller blocked `kubectl drain`, so the automation that would uncordon never finished.
- **Upgrade or reboot tooling failed midway** (node upgrade jobs, reboot daemons like kured).
- **Deliberate quarantine** of a suspect node that nobody followed up on.

## First checks

1. See how much of the fleet is cordoned and since when (graph over a few days):
   ```promql
   sum(kube_node_spec_unschedulable) / count(kube_node_spec_unschedulable)
   ```
   That gives the share of nodes cordoned; to name them:
   ```bash
   kubectl get nodes | grep SchedulingDisabled
   ```
2. Find out who cordoned it. The field manager tells you whether it was kubectl, an upgrade tool or an autoscaler:
   ```bash
   kubectl get node <node> --show-managed-fields -o yaml | grep -B8 "f:unschedulable"
   ```
3. Check taints and annotations left by maintenance tooling:
   ```bash
   kubectl get node <node> -o jsonpath='{.spec.taints}{"\n"}{.metadata.annotations}{"\n"}'
   ```
4. See what is still running and whether a PodDisruptionBudget blocks eviction:
   ```bash
   kubectl get pods -A --field-selector spec.nodeName=<node> -o wide
   kubectl get pdb -A
   ```

## Fixing it

Ask the owner (from step 2) whether the work is done. If the node is healthy, `kubectl uncordon <node>`. If maintenance is still needed, finish the drain: resolve the blocking PodDisruptionBudget (scale the workload up so it tolerates one disruption), then complete the work and uncordon. If the node was quarantined for a hardware or kernel issue, drain it and replace it instead of leaving it half in service.

## Related alerts

- [KubeNodeUnreachable](/runbooks/kubenodeunreachable/): a node that is actually lost, not just cordoned.
- [KubeClusterCPURequestsHigh](/runbooks/kubeclustercpurequestshigh/): cordoned capacity leaves less room for everything else.
- [KubePodDisruptionBudgetBlocksEviction](/runbooks/kubepoddisruptionbudgetblockseviction/): the usual reason a drain never completes.
