---
title: "CPUThrottlingHigh: runbook and fix"
description: "CPUThrottlingHigh means a container is repeatedly hitting its CPU limit and being throttled by CFS. How to confirm the impact and fix limits."
permalink: /runbooks/cputhrottlinghigh/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes quotas, limits & disruption budgets
severity: info
cta:
  title: Get this alert, tested
  text: "CPUThrottlingHigh is one of the resource and limit alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=cputhrottlinghigh
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# CPUThrottlingHigh

A container spends a large share of its CPU scheduling periods throttled because it keeps hitting its CPU limit.

| | |
|---|---|
| Severity | info |
| Source | cAdvisor (kubelet `/metrics/cadvisor`) |
| Key metrics | `container_cpu_cfs_throttled_periods_total`, `container_cpu_cfs_periods_total` |

## What it means

A CPU limit is enforced by the Linux CFS quota: in each 100ms period a container can use only its allotted CPU time, and once it is used up the container waits for the next period. cAdvisor counts periods and throttled periods. This alert fires when a sizeable fraction of periods have been throttled for a sustained stretch.

It is informational because throttling is not always harmful. But it adds latency in bursts, even when average CPU usage looks low, and it often explains mysterious p99 spikes and slow health checks.

## Common causes

- CPU limit set too close to (or below) real peak usage.
- Multi-threaded runtimes (JVM, Go, Node worker pools) that burn the whole quota early in each period.
- Runtimes sizing thread pools from the node's CPU count rather than the container limit.
- Startup or JIT warm-up bursts, or periodic GC, cron-like work inside the process.
- A sidecar sharing the pod with a tight limit.

## First checks

1. Rank containers by throttled ratio:
   ```promql
   topk(10,
     sum by (namespace, pod, container) (rate(container_cpu_cfs_throttled_periods_total{container!=""}[5m]))
     / sum by (namespace, pod, container) (rate(container_cpu_cfs_periods_total{container!=""}[5m]))
   )
   ```
2. Compare actual usage with the limit:
   ```promql
   sum by (pod, container) (rate(container_cpu_usage_seconds_total{namespace="<ns>", container!=""}[5m]))
   ```
   ```bash
   kubectl -n <ns> get pod <pod> -o jsonpath='{range .spec.containers[*]}{.name}: {.resources}{"\n"}{end}'
   ```
3. Check how much time is lost to throttling:
   ```promql
   rate(container_cpu_cfs_throttled_seconds_total{namespace="<ns>", pod="<pod>"}[5m])
   ```
4. Correlate with latency or probe failures for the same pod:
   ```bash
   kubectl -n <ns> describe pod <pod> | grep -iE 'unhealthy|probe'
   ```

## Fixing it

Raise the CPU limit, or remove it and rely on requests for scheduling, which is a common choice for latency-sensitive services on clusters with sensible node sizing. Make the runtime limit-aware (for example set `GOMAXPROCS` to match the limit; modern JVMs detect container limits). If throttling is harmless for a batch job, silence or ignore it for that workload.

## Related alerts

- [KubeContainerMemoryNearLimit](/runbooks/kubecontainermemorynearlimit/): the memory side of limits that are too tight.
- [KubeHpaMaxedOut](/runbooks/kubehpamaxedout/): throttled pods can push CPU-based autoscaling to its ceiling.
- [KubePodNotReady](/runbooks/kubepodnotready/): throttling can make readiness probes time out.
