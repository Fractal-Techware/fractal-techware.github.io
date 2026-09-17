---
title: "KubeVersionMismatch: runbook and fix"
description: "KubeVersionMismatch means Kubernetes components run different minor versions. How to find the lagging nodes or components and finish the upgrade."
permalink: /runbooks/kubeversionmismatch/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes control plane & kubelet
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeVersionMismatch is one of 12 Kubernetes control plane and kubelet alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeversionmismatch
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeVersionMismatch

Kubernetes components in this cluster report more than one minor version.

| | |
|---|---|
| Severity | warning |
| Source | `/metrics` of API server, kubelets, scheduler, controller manager |
| Key metric | `kubernetes_build_info` (label `git_version`) |

## What it means

Every Kubernetes binary exposes its version. The alert groups them by minor version (patch differences are ignored) and fires when more than one minor version has been running for a while.

During an upgrade this is expected. Left in place, it is a risk: Kubernetes only supports a limited version skew (kubelets may lag the API server by a few minors but must never be newer), and the next upgrade can push old nodes outside the supported range.

## Common causes

- An upgrade is in progress or was abandoned halfway.
- A node pool or autoscaling group still uses an old node image or launch template.
- Nodes that were cordoned and forgotten during a previous upgrade.
- A managed control plane auto-upgraded while self-managed node groups did not.

## First checks

1. List versions per component and instance:
   ```promql
   count by (git_version, job) (kubernetes_build_info)
   ```
2. Find the nodes that are behind:
   ```bash
   kubectl get nodes -o custom-columns=NAME:.metadata.name,KUBELET:.status.nodeInfo.kubeletVersion --sort-by=.status.nodeInfo.kubeletVersion
   ```
3. Confirm the API server version:
   ```bash
   kubectl version
   ```
4. Check control plane static pods on each control plane node:
   ```bash
   kubectl -n kube-system get pods -l tier=control-plane -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image
   ```

## Fixing it

Finish the upgrade in the supported order: control plane first, then nodes. For node pools, update the image or template and roll nodes with drain and replace. With kubeadm, run `kubeadm upgrade node` and upgrade the kubelet package on the remaining nodes. If an upgrade is deliberately staged, silence the alert with an expiry rather than ignoring it.

## Related alerts

- [KubeSchedulerDown](/runbooks/kubeschedulerdown/): a failed control plane upgrade can leave components down.
- [KubeControllerManagerDown](/runbooks/kubecontrollermanagerdown/): same risk during upgrades.
- [KubeNodeCordoned](/runbooks/kubenodecordoned/): nodes left cordoned mid-upgrade.
