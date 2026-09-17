---
title: "KubeDaemonSetMisScheduled: runbook and fix"
description: "KubeDaemonSetMisScheduled means DaemonSet pods run on nodes that no longer match the DaemonSet. How to find why and clean them up safely."
permalink: /runbooks/kubedaemonsetmisscheduled/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes workloads
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeDaemonSetMisScheduled is part of a pack of 179 Prometheus alerts, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubedaemonsetmisscheduled
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeDaemonSetMisScheduled

Pods from a DaemonSet are running on nodes where, according to the DaemonSet's current rules, they should not be.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metric | `kube_daemonset_status_number_misscheduled` (labels `namespace`, `daemonset`) |

## What it means

The DaemonSet controller counts pods that sit on nodes no longer matching the DaemonSet's node selector, node affinity or taint tolerations. Normally it deletes such pods quickly. The alert fires when that count stays above zero for several minutes, which means the cleanup is not happening.

The direct impact is usually small (an agent running where it is not needed), but it points to either an unintended label change on nodes or a controller or node that cannot finish deleting pods.

## Common causes

- **Node labels changed**: a label the DaemonSet selects on was removed or renamed, by hand or by a node pool update.
- **DaemonSet selector or affinity edited** to exclude nodes that still run the old pods.
- **Pods cannot be deleted**: the node is unreachable, so the pod sits in `Terminating`, or a finalizer blocks removal.
- **Controller manager unhealthy**, so nobody removes the pods.

## First checks

1. See which DaemonSets are affected and when it started (graph it over the last day; a step change usually lines up with a node pool or manifest change):
   ```promql
   topk(10, kube_daemonset_status_number_misscheduled)
   ```
2. Compare the DaemonSet's placement rules with the node's labels:
   ```bash
   kubectl -n <namespace> get ds <daemonset> -o jsonpath='{.spec.template.spec.nodeSelector}{"\n"}{.spec.template.spec.affinity}{"\n"}'
   kubectl get node <node> --show-labels
   ```
3. Find the pods and whether they are already being deleted:
   ```bash
   kubectl -n <namespace> get pods -l <selector> -o wide
   kubectl -n <namespace> get pod <pod> -o jsonpath='{.metadata.deletionTimestamp} {.metadata.finalizers}{"\n"}'
   ```
4. Check the health of the node hosting them: `kubectl get node <node>`. `NotReady` or `Unknown` explains stuck deletions.
5. Check who last changed the node's labels:
   ```bash
   kubectl get node <node> --show-managed-fields -o yaml | grep -B2 -A10 "f:labels"
   ```

## Fixing it

Decide which side is correct. If the label change was a mistake, restore it (`kubectl label node <node> <key>=<value>`). If the DaemonSet should no longer run there, let the controller remove the pods; if they are stuck on a node that is gone, confirm it is down and force delete them. Remove orphaned finalizers only when you know what added them.

## Related alerts

- [KubeDaemonSetNotScheduled](/runbooks/kubedaemonsetnotscheduled/): the complement, eligible nodes without a pod.
- [KubeDaemonSetRolloutStuck](/runbooks/kubedaemonsetrolloutstuck/): a selector change often coincides with a rollout.
- [KubeNodeUnreachable](/runbooks/kubenodeunreachable/): a lost node keeps pods stuck in Terminating.
