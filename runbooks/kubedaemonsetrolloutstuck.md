---
title: "KubeDaemonSetRolloutStuck: runbook and fix"
description: "KubeDaemonSetRolloutStuck means DaemonSet pods are not ready and the rollout has stopped progressing. How to find the broken nodes and roll back."
permalink: /runbooks/kubedaemonsetrolloutstuck/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes workloads
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeDaemonSetRolloutStuck is one of 13 Kubernetes workload alerts in the pack of 179, each backed by promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubedaemonsetrolloutstuck
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeDaemonSetRolloutStuck

Some pods of a DaemonSet are not ready and the rollout has stopped moving forward.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metrics | `kube_daemonset_status_desired_number_scheduled`, `kube_daemonset_status_number_ready`, `kube_daemonset_status_updated_number_scheduled` |

## What it means

A DaemonSet wants one ready pod per eligible node. The alert fires when fewer pods are ready than desired *and* the number of updated pods has not changed for a while. With the default `RollingUpdate` strategy and `maxUnavailable: 1`, a single pod that never becomes ready halts the update on every remaining node.

DaemonSets usually run node agents: CNI, CSI drivers, log shippers, monitoring. A stuck one can mean nodes without networking, storage or observability.

## Common causes

- **New version crashes or fails readiness**, often only on some nodes (different kernel, OS image or GPU drivers).
- **Wrong architecture**: an amd64-only image landing on arm64 nodes.
- **hostPort or host path conflicts** with another agent on the node.
- **Pods Pending** on nodes without enough free CPU or memory for the agent.
- **`OnDelete` update strategy**: pods only update when deleted by hand.

## First checks

1. See the rollout state:
   ```bash
   kubectl -n <namespace> rollout status ds/<daemonset> --timeout=10s
   kubectl -n <namespace> get ds <daemonset> -o wide
   ```
2. List the pods that are not running, with their nodes:
   ```bash
   kubectl -n <namespace> get pods -l <selector> -o wide --field-selector=status.phase!=Running
   ```
   Also look for `Running` pods with `0/1` ready.
3. Track update progress per DaemonSet:
   ```promql
   kube_daemonset_status_updated_number_scheduled / kube_daemonset_status_desired_number_scheduled
   ```
4. Describe a failing pod and read its logs:
   ```bash
   kubectl -n <namespace> describe pod <pod>
   kubectl -n <namespace> logs <pod> --previous
   ```
5. Check whether failures correlate with a node property:
   ```bash
   kubectl get nodes -L kubernetes.io/arch,node.kubernetes.io/instance-type
   ```

## Fixing it

If the new version is bad, roll back with `kubectl -n <namespace> rollout undo ds/<daemonset>` and fix it before retrying. For architecture problems, publish a multi-arch image or restrict the DaemonSet with a node selector. Pending pods need room: lower the agent's requests or give it a high `priorityClassName` so it can preempt workloads. With `OnDelete`, delete the old pods node by node.

## Related alerts

- [KubeDaemonSetNotScheduled](/runbooks/kubedaemonsetnotscheduled/): pods are missing from nodes entirely.
- [KubeDaemonSetMisScheduled](/runbooks/kubedaemonsetmisscheduled/): pods are on nodes they should not be on.
- [KubePodCrashLooping](/runbooks/kubepodcrashlooping/): usually fires on the new pods that are failing.
