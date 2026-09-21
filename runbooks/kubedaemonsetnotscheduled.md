---
title: "KubeDaemonSetNotScheduled: runbook and fix"
description: "KubeDaemonSetNotScheduled means some nodes that should run a DaemonSet pod do not have one. How to find those nodes and get the agent placed."
permalink: /runbooks/kubedaemonsetnotscheduled/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes workloads
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeDaemonSetNotScheduled comes with promtool unit tests and a full runbook, as do the other 12 workload alerts in the pack of 179."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubedaemonsetnotscheduled
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeDaemonSetNotScheduled

A DaemonSet should be running on more nodes than it currently is, so some nodes are missing their agent.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metrics | `kube_daemonset_status_desired_number_scheduled`, `kube_daemonset_status_current_number_scheduled` |

## What it means

The DaemonSet controller calculates which nodes match the pod's node selector, affinity and tolerations (the *desired* count) and how many of those actually run a daemon pod (the *current* count). The alert fires when desired stays above current for several minutes.

The affected nodes are running without the agent. For a CNI or CSI DaemonSet that breaks pods on those nodes. For logging or security agents it creates silent blind spots.

## Common causes

- **Not enough resources** on the node: the daemon pod stays Pending with `Insufficient cpu` or `Insufficient memory`.
- **Pod creation rejected**: a ResourceQuota in the namespace, a LimitRange, or an admission webhook refuses the pod (`FailedCreate` events on the DaemonSet).
- **Node pod limit reached**, so no room for one more pod.
- **hostPort already taken** on that node.
- **Newly joined nodes** where the pod is still being created, if autoscaling is very active.

## First checks

1. Read the DaemonSet's events for creation failures:
   ```bash
   kubectl -n <namespace> describe ds <daemonset> | sed -n '/Events:/,$p'
   ```
2. Find daemon pods stuck Pending and why:
   ```bash
   kubectl -n <namespace> get pods -l <selector> --field-selector=status.phase=Pending -o wide
   kubectl -n <namespace> describe pod <pending-pod> | grep -A5 FailedScheduling
   ```
3. List nodes without a daemon pod (includes nodes the DaemonSet deliberately skips, so compare against its selector and tolerations):
   ```bash
   comm -23 \
     <(kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort) \
     <(kubectl -n <namespace> get pods -l <selector> -o jsonpath='{range .items[*]}{.spec.nodeName}{"\n"}{end}' | sort)
   ```
4. Find Pending daemon pods across the whole cluster, with the DaemonSet that owns them:
   ```promql
   (kube_pod_status_phase{phase="Pending"} == 1)
     * on (namespace, pod) group_left (owner_name)
     kube_pod_owner{owner_kind="DaemonSet"}
   ```
5. Check free capacity on a suspect node: `kubectl describe node <node> | grep -A8 "Allocated resources"`.

## Fixing it

Node agents should win scheduling contests: give them a `priorityClassName` (such as `system-node-critical` for truly critical agents) so they can preempt ordinary pods, and keep their requests modest. Adjust or exempt quotas and webhooks that block the namespace. If nodes are simply full, add capacity.

## Related alerts

- [KubeDaemonSetRolloutStuck](/runbooks/kubedaemonsetrolloutstuck/): pods exist but are not ready or updating.
- [KubeDaemonSetMisScheduled](/runbooks/kubedaemonsetmisscheduled/): the opposite problem, pods on the wrong nodes.
- [KubeletTooManyPods](/runbooks/kubelettoomanypods/): a full node cannot accept the daemon pod.
