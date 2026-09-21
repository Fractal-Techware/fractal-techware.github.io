---
title: "KubeNodePressure: runbook and fix"
description: "KubeNodePressure means a node reports MemoryPressure, DiskPressure or PIDPressure and the kubelet may evict pods. How to find the cause and relieve it."
permalink: /runbooks/kubenodepressure/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes nodes & capacity
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeNodePressure ships in a pack of 179 Prometheus alerts with promtool unit tests and a full runbook for each one."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubenodepressure
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeNodePressure

A node is short on memory, disk or process IDs, and the kubelet is protecting itself by blocking new pods and evicting existing ones.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metric | `kube_node_status_condition` (condition `MemoryPressure`, `DiskPressure` or `PIDPressure`) |

## What it means

The kubelet compares node resources with its eviction thresholds. When one is crossed it sets a pressure condition, taints the node (for example `node.kubernetes.io/disk-pressure:NoSchedule`) and starts evicting pods, lowest priority and biggest overusers first. The alert fires when a pressure condition has stayed on for several minutes, the `condition` label tells you which one.

Expect evicted pods, workloads rescheduling onto other nodes (which can spread the pressure), and a node that accepts no new work.

## Common causes

- **MemoryPressure**: pods without memory limits, or limits that add up to far more than the node has.
- **DiskPressure**: container logs, `emptyDir` volumes or writable layers filling the root disk; unused images not garbage collected.
- **PIDPressure**: an application leaking threads or processes, or a fork loop.
- **System daemons** outside Kubernetes consuming resources with no `system-reserved` set aside for them.

## First checks

1. See which condition is active and the kubelet's own events:
   ```bash
   kubectl describe node <node> | sed -n '/Conditions:/,/Addresses:/p'
   kubectl get events -A --field-selector involvedObject.name=<node>
   ```
2. List recent evictions:
   ```bash
   kubectl get events -A --field-selector reason=Evicted --sort-by=.lastTimestamp | tail -20
   ```
3. Memory: find the biggest pods on that node (the `node` label on cAdvisor metrics is added by kube-prometheus-stack; adjust if your setup differs):
   ```promql
   topk(10, sum by (namespace, pod) (container_memory_working_set_bytes{node="<node>", container!=""}))
   ```
4. Disk: on the node, find what is using space:
   ```bash
   df -h / /var/lib/containerd
   du -sh /var/log/pods/* | sort -h | tail -10
   crictl images | wc -l
   ```
5. PIDs: count threads and find the offender:
   ```bash
   ps -eLf | wc -l
   ps -eo pid,nlwp,comm --sort=-nlwp | head
   ```

## Fixing it

For memory, set realistic requests and limits and move or restart the leaking workload. For disk, rotate or cap logs, set `ephemeral-storage` limits, and prune images with `crictl rmi --prune`. For PIDs, fix the leak and consider setting `podPidsLimit` in the kubelet config. Reserve capacity for the OS with `systemReserved` and `kubeReserved`.

## Related alerts

- [KubeNodeNotReady](/runbooks/kubenodenotready/): severe pressure can take the whole node down.
- [KubeContainerOOMKilled](/runbooks/kubecontaineroomkilled/): containers hitting their own memory limits.
- [KubeClusterMemoryRequestsHigh](/runbooks/kubeclustermemoryrequestshigh/): the cluster as a whole has little room left.
