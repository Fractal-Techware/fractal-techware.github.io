---
title: "KubeClusterMemoryRequestsHigh: runbook and fix"
description: "KubeClusterMemoryRequestsHigh means pod memory requests are near total allocatable memory, leaving no room to schedule. How to find and fix it."
permalink: /runbooks/kubeclustermemoryrequestshigh/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes nodes & capacity
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeClusterMemoryRequestsHigh ships with promtool unit tests and a full runbook, as part of a pack of 179 Prometheus alerts."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeclustermemoryrequestshigh
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeClusterMemoryRequestsHigh

Pods have reserved nearly all the memory the cluster's nodes can allocate, so the scheduler is running out of places to put new pods.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metrics | `kube_pod_container_resource_requests` (resource `memory`), `kube_node_status_allocatable`, `kube_pod_status_phase` |

## What it means

Memory requests are reservations: the scheduler only places a pod on a node with enough unreserved memory. This alert compares the requests of running and pending pods with the allocatable memory of all nodes, and fires when that ratio has stayed high for several minutes.

It is about reservations, not usage. The immediate effect is `Pending` pods with `Insufficient memory`. The bigger risk is losing a node: its pods need somewhere to go, and there is no room.

## Common causes

- **Generous requests**, often set equal to a high limit "to be safe", on workloads that use a fraction of it.
- **JVM and cache-heavy services** sized for worst case.
- **Workload growth** or new tenants without a matching node pool increase.
- **Autoscaler at its ceiling**, or node pools of the wrong instance size for large pods.
- **Pending pods** with large requests inflating the total.

## First checks

1. Top memory reservations by namespace (finished pods can still appear in this metric, so confirm with kubectl):
   ```promql
   topk(10, sum by (namespace) (kube_pod_container_resource_requests{resource="memory"}))
   ```
2. Actual working set per namespace, to find reservations that are mostly unused:
   ```promql
   topk(10, sum by (namespace) (container_memory_working_set_bytes{container!=""}))
   ```
3. Per-node picture:
   ```bash
   kubectl describe nodes | grep -A6 "Allocated resources"
   kubectl top nodes
   ```
4. Pods that cannot schedule because of memory:
   ```bash
   kubectl get events -A --field-selector reason=FailedScheduling | grep -i "insufficient memory"
   ```
5. Largest individual requests, often the ones that fragment capacity:
   ```bash
   kubectl get pods -A -o custom-columns='NS:.metadata.namespace,POD:.metadata.name,MEM:.spec.containers[*].resources.requests.memory' | sort -k3 -h | tail -15
   ```

## Fixing it

If pods are Pending, add nodes first. Then lower requests where the working set is consistently far below them; be more careful than with CPU, because a memory request set too low leads to evictions and OOM kills under pressure. Keep enough spare capacity to absorb the loss of your largest node, and set namespace quotas.

## Related alerts

- [KubeClusterCPURequestsHigh](/runbooks/kubeclustercpurequestshigh/): the CPU side of the same capacity question.
- [KubeNodePressure](/runbooks/kubenodepressure/): nodes whose real memory use, not requests, is too high.
- [KubeletTooManyPods](/runbooks/kubelettoomanypods/): nodes full by pod count.
