---
title: "KubeContainerMemoryNearLimit: runbook and fix"
description: "KubeContainerMemoryNearLimit means a container's working set is close to its memory limit and at risk of OOMKill. How to check for leaks and resize."
permalink: /runbooks/kubecontainermemorynearlimit/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes quotas, limits & disruption budgets
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeContainerMemoryNearLimit is one of 7 Kubernetes quota, limit and PDB alerts in the pack of 179, with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubecontainermemorynearlimit
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeContainerMemoryNearLimit

A container has been using almost all of its memory limit for a while, and the kernel will kill it if it grows any further.

| | |
|---|---|
| Severity | warning |
| Source | cAdvisor + kube-state-metrics v2.x |
| Key metrics | `container_memory_working_set_bytes`, `kube_pod_container_resource_limits{resource="memory"}` |

## What it means

The working set is the memory the kernel cannot easily reclaim, and it is the number compared against the limit when deciding on an OOM kill. When it stays very close to the limit for a sustained period, this alert fires. It is a warning ahead of an `OOMKilled` restart, not after one.

Beyond the kill itself, containers near their limit often slow down as the kernel reclaims page cache aggressively.

## Common causes

- A memory leak: usage climbs steadily and never drops.
- Runtime heap sized independently of the container limit (JVM `-Xmx`, Node `--max-old-space-size`) leaving no room for off-heap memory.
- Load growth or larger payloads, caches without a size bound.
- A memory limit copied from another service and never tuned.
- Page cache from heavy file I/O counted in the working set (active file pages).

## First checks

1. Rank containers by usage as a share of their limit:
   ```promql
   topk(10,
     max by (namespace, pod, container) (container_memory_working_set_bytes{container!=""})
     / on (namespace, pod, container) group_left
     max by (namespace, pod, container) (kube_pod_container_resource_limits{resource="memory"})
   )
   ```
2. Look at the trend over a day to tell a leak from a plateau:
   ```promql
   container_memory_working_set_bytes{namespace="<ns>", pod="<pod>", container="<container>"}
   ```
3. Check for recent OOM kills and restarts:
   ```bash
   kubectl -n <ns> get pod <pod> -o jsonpath='{range .status.containerStatuses[*]}{.name} restarts={.restartCount} last={.lastState.terminated.reason}{"\n"}{end}'
   ```
4. Compare runtime heap settings with the limit:
   ```bash
   kubectl -n <ns> get pod <pod> -o jsonpath='{.spec.containers[*].env}'
   kubectl -n <ns> exec <pod> -c <container> -- cat /sys/fs/cgroup/memory.max
   ```

## Fixing it

If usage is a stable plateau, raise the memory limit (and request) to give headroom. If it grows without bound, restart to buy time, then take a heap profile and fix the leak. Size runtime heaps as a fraction of the limit, for example `-XX:MaxRAMPercentage` on the JVM, so the container limit stays authoritative.

## Related alerts

- [KubeContainerOOMKilled](/runbooks/kubecontaineroomkilled/): what happens if this is ignored.
- [CPUThrottlingHigh](/runbooks/cputhrottlinghigh/): CPU limits that are too tight.
- [KubeQuotaAlmostFull](/runbooks/kubequotaalmostfull/): check quota headroom before raising limits.
