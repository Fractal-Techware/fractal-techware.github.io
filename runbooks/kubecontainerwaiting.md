---
title: "KubeContainerWaiting: runbook and fix"
description: "KubeContainerWaiting means a container has sat in a Waiting state for a long time without starting. How to find the reason and unblock it."
permalink: /runbooks/kubecontainerwaiting/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes workloads
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeContainerWaiting is one of 13 Kubernetes workload alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubecontainerwaiting
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeContainerWaiting

A container was created in the pod spec but has been stuck before it ever started, for far longer than a normal startup.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metric | `kube_pod_container_status_waiting_reason` (labels `namespace`, `pod`, `container`, `reason`) |

## What it means

A container in the `Waiting` state has not been started by the kubelet yet. This alert covers the waiting reasons that are *not* crash loops or image pulls (those have their own alerts): typically `ContainerCreating`, `PodInitializing`, `CreateContainerConfigError` or `CreateContainerError`. It fires only after the container has stayed that way for a long stretch, so it is not a slow image or a busy node.

The workload is not serving from that pod, and if it is part of a rollout, the rollout is probably blocked behind it.

## Common causes

- **Missing ConfigMap or Secret** referenced in `env`, `envFrom` or a volume (`CreateContainerConfigError`).
- **Volume cannot attach or mount**: PVC bound in another zone, CSI driver errors, NFS server unreachable (`ContainerCreating`).
- **CNI failure**: the pod sandbox cannot get an IP, often because the node's IP pool is exhausted.
- **Init container never finishes**: waiting for a dependency that is down (`PodInitializing`).
- **Security context mismatch**: `runAsNonRoot` set on an image that runs as root.

## First checks

1. See which reasons are affected and where:
   ```promql
   count by (namespace, reason) (kube_pod_container_status_waiting_reason == 1)
   ```
2. Read the exact waiting message for the pod:
   ```bash
   kubectl -n <namespace> get pod <pod> \
     -o jsonpath='{range .status.containerStatuses[*]}{.name}: {.state.waiting.reason} {.state.waiting.message}{"\n"}{end}'
   ```
3. The events usually name the culprit (`FailedMount`, `FailedCreatePodSandBox`, missing key):
   ```bash
   kubectl -n <namespace> describe pod <pod> | sed -n '/Events:/,$p'
   ```
4. For `PodInitializing`, check the init containers:
   ```bash
   kubectl -n <namespace> logs <pod> -c <init-container>
   ```
5. If many pods on one node are affected, look at that node's kubelet and CNI logs:
   ```bash
   journalctl -u kubelet --since "1 hour ago" | grep -iE "mount|sandbox|cni"
   ```

## Fixing it

Create the missing ConfigMap or Secret (or fix the key name), then the kubelet retries on its own. For volume problems, fix the storage side or reschedule into the volume's zone. For CNI or node-local issues, cordon the node and delete the pod so it lands elsewhere. Fix the security context in the manifest rather than weakening policy.

## Related alerts

- [KubePodCrashLooping](/runbooks/kubepodcrashlooping/): the container starts but keeps exiting.
- [KubeImagePullBackOff](/runbooks/kubeimagepullbackoff/): the waiting reason is an image that cannot be pulled.
- [KubePodNotReady](/runbooks/kubepodnotready/): the pod-level view of the same stuck startup.
