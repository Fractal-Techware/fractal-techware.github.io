---
title: "KubeNodeReadinessFlapping: runbook and fix"
description: "KubeNodeReadinessFlapping means a node keeps switching between Ready and NotReady. How to find the unstable kubelet, runtime or network path."
permalink: /runbooks/kubenodereadinessflapping/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes nodes & capacity
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeNodeReadinessFlapping is one of 8 Kubernetes node alerts in the pack of 179, with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubenodereadinessflapping
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeNodeReadinessFlapping

A node is going Ready, NotReady, Ready again, several times in a short window, and has kept doing so.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metric | `kube_node_status_condition` (condition `Ready`) |

## What it means

The Ready condition reflects whether the kubelet is healthy and reporting on time. A node that flips repeatedly is unstable rather than dead, which can be worse: pods get marked not ready, endpoints are pulled from Services and added back, and the scheduler keeps placing new work on a node that will drop out again.

The alert fires when the Ready status changes more than a couple of times within a short window and the pattern persists.

## Common causes

- **Container runtime stalls**: containerd or CRI-O stops responding, the kubelet reports `PLEG is not healthy` and marks the node NotReady until the runtime recovers.
- **kubelet restarting**: killed by the OOM killer, a systemd restart loop, or a config management tool reapplying settings.
- **Intermittent network** to the API server: packet loss, conntrack table full, overloaded NAT gateway.
- **CPU or IO starvation**: the kubelet cannot post status in time on an overloaded node.

## First checks

1. Graph the node's readiness over a few hours to see the rhythm (regular intervals suggest a timer or restart loop):
   ```promql
   kube_node_status_condition{node="<node>", condition="Ready", status="true"}
   ```
2. Look at the kubelet's reasons for going NotReady:
   ```bash
   journalctl -u kubelet --since "2 hours ago" | grep -iE "PLEG|NodeNotReady|not ready|failed to update node" | tail -30
   ```
3. Check for kubelet and runtime restarts or OOM kills:
   ```bash
   systemctl show kubelet -p NRestarts
   systemctl status containerd
   dmesg -T | grep -iE "oom|killed process" | tail
   ```
4. Check PLEG relist latency on that node:
   ```promql
   histogram_quantile(0.99, sum by (le) (rate(kubelet_pleg_relist_duration_seconds_bucket{instance=~"<node-ip>:.*"}[5m])))
   ```
5. Check load and conntrack: `uptime`, `cat /proc/sys/net/netfilter/nf_conntrack_count /proc/sys/net/netfilter/nf_conntrack_max`.

## Fixing it

Cordon the node while you investigate so new pods stop landing there: `kubectl cordon <node>`. Then fix the underlying instability: restart or upgrade the container runtime, reserve memory and CPU for system daemons so the kubelet is not starved, raise the conntrack limit, or fix the network path. If the cause is unclear and the node is replaceable, drain and replace it.

## Related alerts

- [KubeNodeNotReady](/runbooks/kubenodenotready/): the node stays not ready instead of bouncing.
- [KubeNodeUnreachable](/runbooks/kubenodeunreachable/): the kubelet has stopped reporting entirely.
- [KubeNodePressure](/runbooks/kubenodepressure/): resource pressure often precedes flapping.
- [KubeletPlegDurationHigh](/runbooks/kubeletplegdurationhigh/): slow runtime relists, a frequent root cause.
