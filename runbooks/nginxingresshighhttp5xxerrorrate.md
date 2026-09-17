---
title: "NginxIngressHighHttp5xxErrorRate: runbook and fix"
description: "NginxIngressHighHttp5xxErrorRate means an Ingress is serving a high share of 5xx responses. How to tell backend failures from controller issues."
permalink: /runbooks/nginxingresshighhttp5xxerrorrate/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: NGINX Ingress Controller
severity: "warning, critical"
cta:
  title: Get this alert, tested
  text: "NginxIngressHighHttp5xxErrorRate is one of 5 NGINX Ingress alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nginxingresshighhttp5xxerrorrate
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NginxIngressHighHttp5xxErrorRate

A meaningful fraction of requests through one Ingress are ending in 5xx, so real users are seeing errors.

| | |
|---|---|
| Severity | warning, critical |
| Source | ingress-nginx controller `/metrics` (1.9+) |
| Key metric | `nginx_ingress_controller_requests` (labels `namespace`, `ingress`, `service`, `status`) |

## What it means

The controller counts every request per Ingress and status code. The alert compares the 5xx share against total traffic for each Ingress, and ignores Ingresses with almost no traffic so a single failed request does not page anyone. The warning fires when the error share is elevated for a sustained period; critical means a large share of requests is failing right now.

The key question is who produced the 5xx: the backend application, or NGINX itself because it could not reach the backend.

## Common causes

- **Application errors**: the backend returns 500 after a bad deploy, a failing dependency or a database outage.
- **No ready endpoints**: all pods behind the Service are down or failing readiness, so NGINX returns 503.
- **Upstream timeouts**: slow backends exceed `proxy-read-timeout`, giving 504.
- **Connection resets**: pods killed during rollouts without graceful shutdown, giving 502.
- **Oversized headers or bodies** handled badly by the backend.

## First checks

1. Split errors by status code and service:
   ```promql
   sum by (namespace, ingress, service, status) (rate(nginx_ingress_controller_requests{status=~"5.."}[5m]))
   ```
   Mostly 502/503/504 points at connectivity; mostly 500 points at the app.
2. Check the Service has ready endpoints:
   ```bash
   kubectl -n <namespace> get endpointslices -l kubernetes.io/service-name=<service>
   kubectl -n <namespace> get pods -l <app-selector> -o wide
   ```
3. Read the controller access and error logs. The upstream status and address show which pod failed:
   ```bash
   kubectl -n ingress-nginx logs deploy/ingress-nginx-controller --since=15m | grep '<host>' | grep -E '" 5[0-9]{2} '
   kubectl -n ingress-nginx logs deploy/ingress-nginx-controller --since=15m | grep -E 'upstream timed out|connect\(\) failed|no live upstreams'
   ```
4. Check the backend's own logs and recent rollouts:
   ```bash
   kubectl -n <namespace> rollout history deploy/<app>
   kubectl -n <namespace> logs deploy/<app> --since=15m | tail -100
   ```

## Fixing it

Roll back a bad deploy first, then investigate. For 503s, restore ready pods or fix readiness probes. For 504s, fix the slow dependency or raise the timeout with the `nginx.ingress.kubernetes.io/proxy-read-timeout` annotation only if the long request is legitimate. For 502s during rollouts, add a `preStop` sleep and make the app drain connections on SIGTERM.

## Related alerts

- [NginxIngressHighLatency](/runbooks/nginxingresshighlatency/): slow backends often precede 504s.
- [NginxIngressHighHttp4xxErrorRate](/runbooks/nginxingresshighhttp4xxerrorrate/): client-side errors on the same Ingress.
- [NginxIngressConfigReloadFailed](/runbooks/nginxingressconfigreloadfailed/): a stale config can route to pods that no longer exist.
