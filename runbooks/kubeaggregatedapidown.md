---
title: "KubeAggregatedAPIDown: runbook and fix"
description: "KubeAggregatedAPIDown means an APIService such as metrics.k8s.io is unavailable. How to find the broken backend and why it breaks kubectl and HPA."
permalink: /runbooks/kubeaggregatedapidown/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes control plane & kubelet
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeAggregatedAPIDown is one of 12 control plane and kubelet alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeaggregatedapidown
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeAggregatedAPIDown

An API group served by an extension API server (for example `metrics.k8s.io`) is failing its availability checks.

| | |
|---|---|
| Severity | warning |
| Source | kube-apiserver `/metrics` (aggregation layer) |
| Key metric | `aggregator_unavailable_apiservice` (labels `name`, `namespace`) |

## What it means

The API server proxies some API groups to other services, registered as `APIService` objects. It continuously checks whether each backend is reachable. The alert fires when a given APIService has been unavailable for a meaningful part of the recent window, not just a single blip.

Impact depends on the API: a down `metrics.k8s.io` stops `kubectl top` and every CPU/memory based HPA. It can also make discovery fail, so `kubectl` prints "unable to retrieve the complete list of server APIs", and namespace deletion hangs in `Terminating`.

## Common causes

- The backing pods (metrics-server, prometheus-adapter, KEDA, a custom operator) are crashing or scaled to zero.
- The Service referenced by the APIService has no endpoints or a wrong port.
- The API server cannot reach pod IPs, common on clusters where the control plane is outside the pod network or a firewall blocks the port.
- Expired or rotated CA bundle in the APIService.
- An uninstalled operator left its APIService behind.

## First checks

1. Find unavailable APIServices and the reason:
   ```bash
   kubectl get apiservices | grep -v True
   kubectl describe apiservice <name>
   ```
2. See which ones are flapping over time:
   ```promql
   max by (name, namespace) (aggregator_unavailable_apiservice) == 1
   ```
3. Check the backing Service and pods:
   ```bash
   kubectl -n <namespace> get svc,endpoints <service>
   kubectl -n <namespace> get pods -o wide
   kubectl -n <namespace> logs deploy/<backend> --tail=100
   ```
4. Look at the API server's view of the proxy errors:
   ```bash
   kubectl -n kube-system logs -l component=kube-apiserver --tail=300 | grep -i "<name>"
   ```

## Fixing it

Restart or fix the backend deployment and make sure its Service has endpoints. If the control plane cannot reach the pod network (private GKE, EKS with restrictive security groups), open the webhook/aggregation port from the control plane. Delete APIServices left behind by removed software. Fix the `caBundle` if TLS verification fails.

## Related alerts

- [KubeAPIErrorsHigh](/runbooks/kubeapierrorshigh/): requests to the dead group return 503.
- [KubeClientErrors](/runbooks/kubeclienterrors/): controllers that query the group start failing.
