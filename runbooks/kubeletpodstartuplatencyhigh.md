---
title: "KubeletPodStartUpLatencyHigh: runbook and fix"
description: "KubeletPodStartUpLatencyHigh means pods on a node take very long to start. Check image pulls, volume mounts, CNI and container runtime health."
permalink: /runbooks/kubeletpodstartuplatencyhigh/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes control plane & kubelet
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeletPodStartUpLatencyHigh is part of a pack of 179 tested Prometheus alerts, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeletpodstartuplatencyhigh
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeletPodStartUpLatencyHigh

The kubelet on a node is taking an unusually long time to process pods, so new pods there start slowly.

| | |
|---|---|
| Severity | warning |
| Source | kubelet `/metrics` |
| Key metric | `kubelet_pod_worker_duration_seconds_bucket` |

## What it means

For every pod sync, a kubelet pod worker sets up volumes, the network sandbox and containers. The alert watches the slowest of those syncs per node and fires when they stay far above normal for a sustained period.

The visible effect is pods sitting in `ContainerCreating` or `Init` for a long time on that node. Rollouts slow down, autoscaling reacts late, and readiness-based traffic shifting lags.

## Common causes

- Large images pulled over a slow or rate-limited registry connection.
- Slow volume attach and mount (cloud disks, CSI driver issues, NFS).
- CNI plugin delays or IP address exhaustion in the subnet.
- An overloaded container runtime or node, often seen together with slow PLEG.
- Many secrets or configmaps projected into pods on an overloaded API server.

## First checks

1. Find the slow nodes and which operation dominates:
   ```promql
   topk(10, histogram_quantile(0.99, sum by (instance, operation_type, le) (rate(kubelet_pod_worker_duration_seconds_bucket{job="kubelet"}[5m]))))
   ```
2. Compare end-to-end start times:
   ```promql
   histogram_quantile(0.99, sum by (instance, le) (rate(kubelet_pod_start_duration_seconds_bucket{job="kubelet"}[15m])))
   ```
3. Check slow runtime operations such as image pulls:
   ```promql
   topk(5, histogram_quantile(0.99, sum by (instance, operation_type, le) (rate(kubelet_runtime_operations_duration_seconds_bucket{job="kubelet"}[15m]))))
   ```
4. Look at events for a slow pod on that node:
   ```bash
   kubectl get pods -A --field-selector spec.nodeName=<node> | grep -v Running
   kubectl describe pod <pod> -n <namespace> | sed -n '/Events/,$p'
   ```
   Long gaps between `Pulling` and `Pulled`, or `FailedMount` and `FailedCreatePodSandBox` events, point to the cause.

## Fixing it

Use smaller images, a pull-through registry cache or pre-pulled images. Fix the CSI driver or storage backend if mounts are slow. Free IPs or enlarge the pod subnet for CNI failures. If the runtime itself is slow, drain the node and restart containerd and the kubelet.

## Related alerts

- [KubeletPlegDurationHigh](/runbooks/kubeletplegdurationhigh/): runtime slowness on the same node.
- [KubeClientErrors](/runbooks/kubeclienterrors/): kubelet failing to fetch secrets or configmaps.
- [KubeImagePullBackOff](/runbooks/kubeimagepullbackoff/): image pulls that fail outright.
