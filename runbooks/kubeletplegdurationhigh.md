---
title: "KubeletPlegDurationHigh: runbook and fix"
description: "KubeletPlegDurationHigh means a kubelet's PLEG relist is slow, the precursor to PLEG is not healthy and NotReady. Check the container runtime and load."
permalink: /runbooks/kubeletplegdurationhigh/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes control plane & kubelet
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeletPlegDurationHigh is one of 12 Kubernetes control plane and kubelet alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeletplegdurationhigh
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeletPlegDurationHigh

The kubelet on a node is taking far too long to get container state from the container runtime.

| | |
|---|---|
| Severity | warning |
| Source | kubelet `/metrics` |
| Key metric | `kubelet_pleg_relist_duration_seconds_bucket` |

## What it means

The Pod Lifecycle Event Generator (PLEG) periodically relists all containers from the runtime (containerd or CRI-O) to detect state changes. The alert fires when the slowest relists on a node take many seconds for several minutes.

This is an early warning. If relisting keeps getting slower, the kubelet logs "PLEG is not healthy" and marks the node `NotReady`, which leads to evictions. Before that, pod starts, stops and status updates on the node are delayed.

## Common causes

- Too many containers on the node, including exited ones that were never garbage collected.
- The container runtime is hung or slow (containerd deadlock, a stuck shim, a hung storage mount).
- Disk I/O saturation on the runtime's root directory.
- Node CPU starvation, often from pods without limits or a kernel issue.
- Pods with very many or stuck volumes (NFS mounts that hang).

## First checks

1. Find the affected nodes and how bad it is:
   ```promql
   topk(10, histogram_quantile(0.99, sum by (instance, le) (rate(kubelet_pleg_relist_duration_seconds_bucket{job="kubelet"}[5m]))))
   ```
2. Check container count on the node:
   ```promql
   kubelet_running_containers{job="kubelet", instance="<instance>"}
   ```
3. On the node, test the runtime directly. A slow `crictl ps` confirms the runtime is the bottleneck:
   ```bash
   time sudo crictl ps -a | wc -l
   sudo systemctl status containerd
   journalctl -u kubelet --since "1 hour ago" | grep -i pleg
   ```
4. Look for I/O and CPU pressure:
   ```bash
   top -b -n1 | head -20
   iostat -x 5 3
   ```
5. Look for hung mounts: `mount | grep nfs` and processes stuck in `D` state (`ps -eo stat,pid,cmd | grep '^D'`).

## Fixing it

Drain the node to move workloads off. Remove exited containers (`crictl rm` on stopped ones) and restart the container runtime, then the kubelet. If a hung NFS mount or kernel issue is involved, reboot the node. Longer term, cap pods per node, give the runtime faster disks and set CPU reservations for system daemons.

## Related alerts

- [KubeletPodStartUpLatencyHigh](/runbooks/kubeletpodstartuplatencyhigh/): the same slowness shows up as slow pod starts.
- [KubeNodeNotReady](/runbooks/kubenodenotready/): what happens if PLEG stops entirely.
- [KubeletTooManyPods](/runbooks/kubelettoomanypods/): a common contributing factor.
