---
title: "KubeAPIDown: runbook and fix"
description: "KubeAPIDown means Prometheus cannot scrape any kube-apiserver. How to tell a real control plane outage from a broken scrape, and what to check first."
permalink: /runbooks/kubeapidown/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes control plane & kubelet
severity: critical
cta:
  title: Get this alert, tested
  text: "KubeAPIDown is one of 12 Kubernetes control plane and kubelet alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeapidown
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeAPIDown

Prometheus has lost sight of every Kubernetes API server target, so either the control plane is down or monitoring can no longer reach it.

| | |
|---|---|
| Severity | critical |
| Source | kube-apiserver `/metrics` (kube-prometheus-stack job `apiserver`) |
| Key metric | `up` |

## What it means

The alert fires when no API server target has been successfully scraped for a sustained period. With a single scrape job covering all API server replicas, this is not "one replica is unhealthy": it is "none of them answer Prometheus".

If the API server really is down, nothing that talks to it works: no deployments, no scaling, no new pods, controllers stop reconciling. Running workloads usually keep serving traffic, but the cluster is frozen. If the API server is fine, you have a blind spot instead, and every other control plane alert is unreliable.

## Common causes

- All control plane nodes (or the managed control plane) are down, overloaded or out of memory.
- etcd is unavailable, so the API server fails its readiness checks or crash-loops.
- The API server's serving certificate expired, so both clients and scrapes fail TLS.
- The `kubernetes` Service endpoints or the ServiceMonitor changed, e.g. after a Helm upgrade renamed the job.
- NetworkPolicy, firewall or security group changes blocking Prometheus from port 443/6443.

## First checks

1. Is the API actually reachable from your workstation?
   ```bash
   kubectl get --raw='/readyz?verbose'
   kubectl get --raw='/livez?verbose'
   ```
2. If kubectl works, it is a scrape problem. Look at the target's last error in Prometheus (**Status → Targets**, job `apiserver`) and check the endpoints:
   ```bash
   kubectl get endpoints kubernetes -n default -o wide
   ```
3. Confirm what Prometheus sees:
   ```promql
   up{job=~".*apiserver.*"}
   ```
   No series at all usually means the job label or ServiceMonitor changed, not an outage.
4. If kubectl fails, go to a control plane node:
   ```bash
   sudo crictl ps -a --name kube-apiserver
   sudo crictl logs <container-id> 2>&1 | tail -50
   sudo kubeadm certs check-expiration
   ```
5. Check etcd health from the same node, since the API server depends on it.

## Fixing it

For a real outage, restore etcd first, then the API server (renew expired certificates with `kubeadm certs renew`, free memory or disk on control plane nodes). On managed clusters, check the provider status page and open a ticket. For a scrape-only failure, fix the ServiceMonitor, RBAC or network path so Prometheus can reach `https://kubernetes.default.svc`.

## Related alerts

- [KubeAPIErrorsHigh](/runbooks/kubeapierrorshigh/): the API server is up but failing many requests.
- [KubeControllerManagerDown](/runbooks/kubecontrollermanagerdown/): often fires alongside when a control plane node dies.
- [EtcdInsufficientMembers](/runbooks/etcdinsufficientmembers/): a lost etcd quorum takes the API server with it.
