---
title: "NginxIngressHighLatency: runbook and fix"
description: "NginxIngressHighLatency means p95 request time through an Ingress is high. How to tell a slow backend from a saturated controller and fix it."
permalink: /runbooks/nginxingresshighlatency/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: NGINX Ingress Controller
severity: warning
cta:
  title: Get this alert, tested
  text: "NginxIngressHighLatency is one of 5 ingress-nginx alerts in the pack of 179 Prometheus alerts, all unit tested with promtool and documented."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nginxingresshighlatency
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NginxIngressHighLatency

Requests through an Ingress have been slow at the 95th percentile for several minutes.

| | |
|---|---|
| Severity | warning |
| Source | ingress-nginx controller `/metrics` (1.9+) |
| Key metrics | `nginx_ingress_controller_request_duration_seconds_bucket`, `nginx_ingress_controller_response_duration_seconds_bucket` |

## What it means

`request_duration` is the total time NGINX spent on a request, from the first client byte to the last byte sent. The alert fires when the p95 of that, per Ingress, stays high. Users feel this directly, and it is often the early sign of 504s.

Latency here includes the backend (upstream) time plus any time spent in NGINX and on the client connection. Comparing the two histograms tells you which one grew.

## Common causes

- **Slow backend**: database contention, a slow external API, CPU throttling on the app pods.
- **Too few backend replicas** for current traffic, so requests queue.
- **Large uploads or downloads** on slow clients, which inflate total request time without the app being slow.
- **Controller saturation**: controller pods CPU-throttled or out of worker connections.
- **Long-polling or streaming endpoints** that are slow by design.

## First checks

1. Compare total time with upstream time for the Ingress:
   ```promql
   histogram_quantile(0.95, sum by (le) (rate(nginx_ingress_controller_request_duration_seconds_bucket{ingress="<ingress>"}[5m])))
   histogram_quantile(0.95, sum by (le) (rate(nginx_ingress_controller_response_duration_seconds_bucket{ingress="<ingress>"}[5m])))
   ```
   If both are high, the backend is slow. If only the first is, look at clients or the controller.
2. Check backend pod resources and throttling:
   ```bash
   kubectl -n <namespace> top pods -l <app-selector>
   ```
   ```promql
   sum by (pod) (rate(container_cpu_cfs_throttled_periods_total{namespace="<namespace>"}[5m]))
   ```
3. Check the controller itself:
   ```bash
   kubectl -n ingress-nginx top pods
   kubectl -n ingress-nginx logs deploy/ingress-nginx-controller --since=15m | grep -i 'worker_connections are not enough'
   ```
4. Find the slowest paths in the access log (`$request_time` and `$upstream_response_time` are in the default format).

## Fixing it

Scale the backend or fix the slow dependency. Remove CPU limits that cause throttling on latency-sensitive services. If the controller is saturated, add replicas or raise its CPU. Exclude known long-running routes (websockets, streaming, large exports) with a label filter rather than raising the threshold for everyone.

## Related alerts

- [NginxIngressHighHttp5xxErrorRate](/runbooks/nginxingresshighhttp5xxerrorrate/): timeouts turn latency into 504s.
- [NginxIngressHighHttp4xxErrorRate](/runbooks/nginxingresshighhttp4xxerrorrate/): 429s from rate limiting can follow a latency spike.
