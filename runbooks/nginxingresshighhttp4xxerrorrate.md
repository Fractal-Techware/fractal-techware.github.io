---
title: "NginxIngressHighHttp4xxErrorRate: runbook and fix"
description: "NginxIngressHighHttp4xxErrorRate means an Ingress returns a large share of 4xx responses. How to find out whether clients, auth or routing are to blame."
permalink: /runbooks/nginxingresshighhttp4xxerrorrate/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: NGINX Ingress Controller
severity: info
cta:
  title: Get this alert, tested
  text: "NginxIngressHighHttp4xxErrorRate is part of the NGINX Ingress set in a pack of 179 alerts, each shipped with promtool unit tests and a runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nginxingresshighhttp4xxerrorrate
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NginxIngressHighHttp4xxErrorRate

A large share of requests through one Ingress are being rejected with 4xx codes for a long stretch.

| | |
|---|---|
| Severity | info |
| Source | ingress-nginx controller `/metrics` (1.9+) |
| Key metric | `nginx_ingress_controller_requests` (labels `namespace`, `ingress`, `status`) |

## What it means

4xx responses are normally the client's fault, so some are expected. This alert fires only when a big portion of an Ingress's traffic has been 4xx for a sustained period, and only for Ingresses with real traffic. It is informational: nothing is necessarily broken, but a pattern like this often hides a real problem, such as a broken frontend calling the wrong path, expired tokens, or someone scanning your site.

## Common causes

- **404 after a deploy**: a path was renamed, or the Ingress `path`/`pathType` no longer matches what clients call.
- **401/403 spikes**: expired credentials, a broken auth provider, or `auth-url` annotations failing.
- **429**: rate limiting annotations (`limit-rps`, `limit-connections`) tripping for legitimate clients.
- **413**: uploads larger than `proxy-body-size`.
- **Bots and vulnerability scanners** probing random URLs.

## First checks

1. Break the errors down by code:
   ```promql
   sum by (namespace, ingress, status) (rate(nginx_ingress_controller_requests{status=~"4.."}[5m]))
   ```
2. Find the top paths and client IPs producing them from the access log:
   ```bash
   kubectl -n ingress-nginx logs deploy/ingress-nginx-controller --since=30m \
     | grep '<host>' | grep -E '" 4[0-9]{2} ' | awk '{print $1, $7, $9}' | sort | uniq -c | sort -rn | head -20
   ```
   Field positions depend on your `log-format-upstream`; adjust as needed.
3. Compare the Ingress rules with what clients request:
   ```bash
   kubectl -n <namespace> get ingress <ingress> -o yaml
   ```
4. If 401/403 dominate, check the auth service or identity provider logs, and any `nginx.ingress.kubernetes.io/auth-*` annotations.

## Fixing it

Fix routing mistakes in the Ingress or restore the old path with a redirect. Raise `nginx.ingress.kubernetes.io/proxy-body-size` for legitimate large uploads. Loosen rate limits if real users hit them. For scanners, consider blocking at a WAF or with `denylist-source-range`, or exclude that Ingress from the alert if the noise is expected.

## Related alerts

- [NginxIngressHighHttp5xxErrorRate](/runbooks/nginxingresshighhttp5xxerrorrate/): server-side failures on the same traffic.
- [NginxIngressConfigReloadFailed](/runbooks/nginxingressconfigreloadfailed/): new routes that never loaded cause 404s.
