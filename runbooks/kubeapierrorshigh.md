---
title: "KubeAPIErrorsHigh: runbook and fix"
description: "KubeAPIErrorsHigh means the Kubernetes API server returns too many 5xx responses. How to find the failing verbs and resources and fix the backend."
permalink: /runbooks/kubeapierrorshigh/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes control plane & kubelet
severity: "warning, critical"
cta:
  title: Get this alert, tested
  text: "KubeAPIErrorsHigh ships with warning and critical tiers in a pack of 179 tested alerts, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeapierrorshigh
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeAPIErrorsHigh

A noticeable share of requests to the Kubernetes API server are failing with server-side (5xx) errors.

| | |
|---|---|
| Severity | warning, critical |
| Source | kube-apiserver `/metrics` |
| Key metric | `apiserver_request_total` (labels `verb`, `resource`, `code`) |

## What it means

The alert compares 5xx responses to total API traffic across the cluster. The warning tier fires when a small but persistent fraction of requests fail; critical fires when the error ratio is several times higher. Client errors (4xx) are not counted.

Controllers, operators, CI pipelines and kubectl users all see these failures. Deployments stall, leader elections can flap, and retries add load that makes things worse.

## Common causes

- etcd is slow, out of quota or has lost a member, so writes return 500 or 504.
- An aggregated API (commonly metrics-server) is down, producing 503 for its group.
- A failing admission webhook with `failurePolicy: Fail` returning errors or timing out.
- API server overload: priority and fairness rejecting requests with 429 plus timeouts surfacing as 504.
- A single API server replica unhealthy behind the load balancer.

## First checks

1. Break the errors down by what is failing:
   ```promql
   topk(10, sum by (code, verb, resource, group) (rate(apiserver_request_total{job="apiserver", code=~"5.."}[5m])))
   ```
2. Check whether one replica is responsible:
   ```promql
   sum by (instance, code) (rate(apiserver_request_total{job="apiserver", code=~"5.."}[5m]))
   ```
3. Look for unavailable aggregated APIs and failing webhooks:
   ```bash
   kubectl get apiservices | grep -v True
   kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
   ```
4. Read the API server logs for the dominant error:
   ```bash
   kubectl -n kube-system logs -l component=kube-apiserver --tail=200 | grep -Ei "error|timeout|etcd"
   ```
5. Check etcd latency seen by the API server:
   ```promql
   histogram_quantile(0.99, sum by (operation, le) (rate(etcd_request_duration_seconds_bucket[5m])))
   ```

## Fixing it

Fix the backend that the breakdown points to: restore the broken APIService or its pods, repair or temporarily relax a failing webhook, defragment or compact etcd if it is near quota, or take an unhealthy API server replica out of rotation. If a runaway client is flooding the API, throttle or scale it down.

## Related alerts

- [KubeAPILatencyHigh](/runbooks/kubeapilatencyhigh/): latency and errors usually rise together.
- [KubeAggregatedAPIDown](/runbooks/kubeaggregatedapidown/): a common source of 503s for one API group.
- [KubeAPITerminatedRequests](/runbooks/kubeapiterminatedrequests/): overload shedding requests.
- [EtcdHighCommitDurations](/runbooks/etcdhighcommitdurations/): slow etcd behind the errors.
