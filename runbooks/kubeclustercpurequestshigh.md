---
title: "KubeClusterCPURequestsHigh: runbook and fix"
description: "KubeClusterCPURequestsHigh means pod CPU requests are close to total allocatable CPU, so new pods will stay Pending. How to find and free headroom."
permalink: /runbooks/kubeclustercpurequestshigh/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes nodes & capacity
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeClusterCPURequestsHigh is one of 8 capacity and node alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeclustercpurequestshigh
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeClusterCPURequestsHigh

The CPU that pods have reserved is close to all the CPU the cluster's nodes can offer, so there is little room left to schedule anything new.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metrics | `kube_pod_container_resource_requests` (resource `cpu`), `kube_node_status_allocatable`, `kube_pod_status_phase` |

## What it means

The scheduler places pods by **requests**, not by actual usage. This alert adds up CPU requests of running and pending pods and compares them with total allocatable CPU across nodes. It fires when that share stays near the top for several minutes.

Actual CPU may be low. What matters is that new pods, HPA scale-outs and rescheduled pods after a node failure will sit in `Pending` with `Insufficient cpu`.

## Common causes

- **Over-requesting**: requests copied from templates or set for peak load, far above real usage.
- **Growth** without adding nodes, or the cluster autoscaler has reached its maximum node count.
- **Large Pending pods** whose requests count against capacity even though they cannot run.
- **Capacity removed**: nodes deleted, or a node pool scaled down.

## First checks

1. Which namespaces reserve the most CPU (the metric can also include finished pods, so cross-check with step 3):
   ```promql
   topk(10, sum by (namespace) (kube_pod_container_resource_requests{resource="cpu"}))
   ```
2. Compare with what they actually use, to spot the biggest over-requesters:
   ```promql
   topk(10, sum by (namespace) (rate(container_cpu_usage_seconds_total{container!=""}[5m])))
   ```
3. See per-node allocation as the scheduler sees it:
   ```bash
   kubectl describe nodes | grep -A6 "Allocated resources"
   ```
4. Find pods that cannot be placed:
   ```bash
   kubectl get pods -A --field-selector=status.phase=Pending
   kubectl get events -A --field-selector reason=FailedScheduling | grep -i "insufficient cpu"
   ```
5. If you run the cluster autoscaler, check whether it is blocked:
   ```bash
   kubectl -n kube-system get configmap cluster-autoscaler-status -o yaml
   ```

## Fixing it

Add capacity now if pods are already Pending: scale the node pool or raise the autoscaler's maximum. Then reclaim headroom by right-sizing requests for the namespaces with the widest gap between requested and used CPU (VPA recommendations help here). Use ResourceQuotas per namespace so one team cannot reserve the rest of the cluster.

## Related alerts

- [KubeClusterMemoryRequestsHigh](/runbooks/kubeclustermemoryrequestshigh/): the same check for memory, which usually runs out first.
- [KubeletTooManyPods](/runbooks/kubelettoomanypods/): nodes can also fill up on pod count.
- [KubeNodeCordoned](/runbooks/kubenodecordoned/): cordoned nodes still count as capacity but take no pods.
- [KubeHpaMaxedOut](/runbooks/kubehpamaxedout/): autoscalers that need room to grow.
