---
title: "KubeletTooManyPods: runbook and fix"
description: "KubeletTooManyPods means a node is running close to its maximum pod count and will soon reject new pods. How to check max-pods and rebalance."
permalink: /runbooks/kubelettoomanypods/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes nodes & capacity
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeletTooManyPods is one of 179 alerts in the pack, each with promtool unit tests and a full runbook, 8 of them for nodes and capacity."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubelettoomanypods
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeletTooManyPods

A node is almost at its pod limit, so the scheduler will soon stop placing pods there no matter how much CPU and memory is free.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metrics | `kube_node_status_capacity` (resource `pods`), `kube_pod_info`, `kube_pod_status_phase` |

## What it means

Every node advertises a pod capacity, set by the kubelet's `maxPods` (110 by default, often lower on managed clusters where it is tied to available pod IPs). The alert fires when the running pods on a node stay very close to that capacity.

Once the limit is hit, new pods fail to schedule there with `Too many pods`, DaemonSet pods for new agents cannot land, and a rollout that needs surge capacity can stall.

## Common causes

- **Low `maxPods` from the CNI**: on EKS with the VPC CNI the limit depends on the instance's network interfaces and IPs, so small instances hold few pods.
- **Many small pods** (sidecars split into pods, per-tenant workers) packed onto large nodes.
- **Uneven scheduling**: no topology spread or anti-affinity, so one node attracts most replicas.
- **DaemonSet sprawl**: many agents using a fixed share of every node's slots.

## First checks

1. Find the fullest nodes and compare with their capacity:
   ```promql
   topk(10, count by (node) (kube_pod_info{node!=""}))
   ```
   ```promql
   kube_node_status_capacity{resource="pods"}
   ```
2. Confirm on the node itself:
   ```bash
   kubectl get node <node> -o jsonpath='{.status.capacity.pods}{"\n"}'
   kubectl get pods -A --field-selector spec.nodeName=<node>,status.phase=Running --no-headers | wc -l
   ```
3. See which namespaces dominate that node:
   ```bash
   kubectl get pods -A --field-selector spec.nodeName=<node> --no-headers | awk '{print $1}' | sort | uniq -c | sort -rn | head
   ```
4. Look for pods failing to schedule because of the limit:
   ```bash
   kubectl get events -A --field-selector reason=FailedScheduling | grep -i "too many pods"
   ```

## Fixing it

Short term, add nodes (or let the cluster autoscaler do it) and spread workloads with `topologySpreadConstraints`. Longer term, raise `maxPods` in the kubelet configuration where the pod CIDR and CNI allow it; on EKS, enable prefix delegation to get more IPs per node. Alternatively consolidate tiny pods, or use larger instance types when the CNI ties pod count to instance size.

## Related alerts

- [KubeDaemonSetNotScheduled](/runbooks/kubedaemonsetnotscheduled/): a full node cannot take a DaemonSet pod.
- [KubeClusterCPURequestsHigh](/runbooks/kubeclustercpurequestshigh/): cluster-wide CPU headroom, the other capacity limit.
- [KubeNodeCordoned](/runbooks/kubenodecordoned/): cordoned nodes push more pods onto the rest.
