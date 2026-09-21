---
title: "KubeClientErrors: runbook and fix"
description: "KubeClientErrors means a Kubernetes component or operator is getting 5xx errors from the API server. How to identify the client and the failing call."
permalink: /runbooks/kubeclienterrors/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes control plane & kubelet
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeClientErrors is part of a pack of 179 Prometheus alerts, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeclienterrors
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeClientErrors

A specific client of the Kubernetes API, such as a kubelet, the scheduler or an operator, is seeing server errors on its requests.

| | |
|---|---|
| Severity | warning |
| Source | client-go metrics exposed by the scraped component |
| Key metric | `rest_client_requests_total` (labels `code`, `method`, `host`) |

## What it means

Anything built on client-go counts its own API requests by response code. This alert is per scraped target: it fires when one component's share of 5xx responses stays above a small fraction for a while. It is the client-side view, so it catches problems that the API server's own metrics can hide, like a component talking through a broken proxy or load balancer.

Affected components retry, but reconciliation slows or stalls, and a kubelet with errors may stop reporting pod status.

## Common causes

- The API server itself is erroring (check the server-side alert first).
- The client reaches the API through a load balancer with an unhealthy backend.
- The component calls an aggregated API or CRD whose backend is down.
- A webhook the component's writes trigger is failing.
- Only one node or zone is affected due to network issues.

## First checks

1. Identify the client and how widespread it is:
   ```promql
   topk(10, sum by (job, instance, code) (rate(rest_client_requests_total{code=~"5.."}[5m])))
   ```
2. See which host and method fail (the `host` label reveals a load balancer or direct endpoint):
   ```promql
   sum by (job, host, method, code) (rate(rest_client_requests_total{code=~"5..", instance="<instance>"}[5m]))
   ```
3. Compare with server-side errors:
   ```promql
   sum by (code) (rate(apiserver_request_total{job="apiserver", code=~"5.."}[5m]))
   ```
4. Read the component's logs:
   ```bash
   kubectl -n <namespace> logs <pod> --tail=200 | grep -Ei "50[0-9]|error"
   ```
   For a kubelet: `journalctl -u kubelet --since "30 min ago" | grep -i error`.

## Fixing it

If the server is also erroring, fix the API server or etcd. If only this client is affected, repair the path it uses (remove the bad load balancer backend, fix DNS, check the node's network). If the errors come from one API group, fix that group's backend or webhook.

## Related alerts

- [KubeAPIErrorsHigh](/runbooks/kubeapierrorshigh/): server-side view of the same errors.
- [KubeAggregatedAPIDown](/runbooks/kubeaggregatedapidown/): a frequent source of 503s.
- [KubeAPITerminatedRequests](/runbooks/kubeapiterminatedrequests/): overload shedding.
