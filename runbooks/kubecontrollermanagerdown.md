---
title: "KubeControllerManagerDown: runbook and fix"
description: "KubeControllerManagerDown means kube-controller-manager vanished from monitoring. Why replicas, nodes and jobs stop reconciling, and how to recover."
permalink: /runbooks/kubecontrollermanagerdown/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes control plane & kubelet
severity: critical
cta:
  title: Get this alert, tested
  text: "KubeControllerManagerDown is included in a pack of 179 Prometheus alerts, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubecontrollermanagerdown
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeControllerManagerDown

kube-controller-manager was being scraped before and now no instance of it is up.

| | |
|---|---|
| Severity | critical |
| Source | kube-controller-manager `/metrics` (HTTPS, port 10257) |
| Key metric | `up` |

## What it means

The alert is scoped to clusters where the controller manager has been seen recently, so managed control planes that hide it stay quiet. It fires once all instances have been unreachable for a sustained window.

The controller manager runs the reconciliation loops: ReplicaSets, Deployments, Jobs, node lifecycle, endpoints, service accounts, garbage collection and certificate signing. When it is gone, deleted pods are not replaced, dead nodes are not marked or evicted, and kubelet CSRs stop being approved.

## Common causes

- The static pod crashes because of an invalid flag in `/etc/kubernetes/manifests/kube-controller-manager.yaml`.
- Expired `controller-manager.conf` client certificate.
- Metrics bound to `127.0.0.1` after a kubeadm upgrade, so only the scrape fails.
- Control plane node down or under heavy memory pressure.
- Leader election loss loops caused by a very slow API server.

## First checks

1. Check whether reconciliation still works: scale a test deployment and see if pods appear.
   ```bash
   kubectl -n default create deployment kcm-check --image=registry.k8s.io/pause:3.9
   kubectl -n default get rs,pods -l app=kcm-check
   kubectl -n default delete deployment kcm-check
   ```
2. Inspect the pods and logs:
   ```bash
   kubectl -n kube-system get pods -l component=kube-controller-manager -o wide
   kubectl -n kube-system logs -l component=kube-controller-manager --tail=100
   ```
3. Check the leader lease renew time:
   ```bash
   kubectl -n kube-system get lease kube-controller-manager -o jsonpath='{.spec.holderIdentity} {.spec.renewTime}'
   ```
4. On the control plane node:
   ```bash
   sudo crictl ps -a --name kube-controller-manager
   sudo kubeadm certs check-expiration
   ```
5. Check scrape errors in Prometheus **Status → Targets**.

## Fixing it

Revert the broken manifest change or renew certificates with `kubeadm certs renew controller-manager.conf`. For scrape-only failures, change `--bind-address` and confirm the ServiceMonitor targets port 10257 over HTTPS. If the API server is slow, fix that first or the leader election will keep failing.

## Related alerts

- [KubeSchedulerDown](/runbooks/kubeschedulerdown/): usually shares the root cause.
- [KubeAPILatencyHigh](/runbooks/kubeapilatencyhigh/): can cause lost leases and restarts.
- [KubeletClientCertificateRenewalErrors](/runbooks/kubeletclientcertificaterenewalerrors/): kubelet CSRs pile up while it is down.
