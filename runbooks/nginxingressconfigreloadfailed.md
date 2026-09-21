---
title: "NginxIngressConfigReloadFailed: runbook and fix"
description: "NginxIngressConfigReloadFailed means ingress-nginx rejected a new nginx.conf and keeps serving the old one. How to find the bad Ingress and fix it."
permalink: /runbooks/nginxingressconfigreloadfailed/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: NGINX Ingress Controller
severity: warning
cta:
  title: Get this alert, tested
  text: "NginxIngressConfigReloadFailed ships with the other NGINX Ingress Controller alerts in a pack of 179, each with a promtool unit test and a runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nginxingressconfigreloadfailed
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NginxIngressConfigReloadFailed

The ingress-nginx controller generated a new NGINX configuration, NGINX refused it, and the controller is still running the previous one.

| | |
|---|---|
| Severity | warning |
| Source | ingress-nginx controller `/metrics` (1.9+) |
| Key metrics | `nginx_ingress_controller_config_last_reload_successful`, `nginx_ingress_controller_config_last_reload_successful_timestamp_seconds` |

## What it means

Whenever Ingresses, Services, Secrets or the ConfigMap change, the controller renders `nginx.conf` and asks NGINX to reload. If the rendered config is invalid, the reload fails and NGINX keeps the last good config. The alert fires when a controller pod has reported a failed last reload for several minutes.

Existing traffic usually keeps working, which is why this is easy to miss. But no change since the failure has taken effect: new Ingresses, certificate renewals and fixed routes are all silently ignored, on that pod only.

## Common causes

- **Bad snippet annotations**: `configuration-snippet` or `server-snippet` with a syntax error or an unknown directive.
- **Invalid values in the controller ConfigMap**, e.g. a malformed `log-format-upstream` or `http-snippet`.
- **Duplicate definitions** created by two Ingresses in ways the admission webhook did not catch.
- **Missing files** such as a referenced auth file or custom template.

## First checks

1. See which controller pods are affected:
   ```promql
   nginx_ingress_controller_config_last_reload_successful == 0
   ```
2. Read the reload error. NGINX reports the file, line and directive:
   ```bash
   kubectl -n ingress-nginx logs <controller-pod> --since=1h | grep -iE 'error reloading|emerg|nginx: \[error\]'
   ```
3. Test the running config inside the pod:
   ```bash
   kubectl -n ingress-nginx exec <controller-pod> -- nginx -t
   ```
4. Map the failing line back to an Ingress. The generated config marks each server block with its host:
   ```bash
   kubectl -n ingress-nginx exec <controller-pod> -- cat /etc/nginx/nginx.conf | sed -n '<line-10>,<line+10>p'
   ```
   With the optional plugin: `kubectl ingress-nginx conf -n ingress-nginx --host <host>`.
5. List recent Ingress changes: `kubectl get ingress -A --sort-by=.metadata.creationTimestamp`.

## Fixing it

Fix or remove the offending annotation or ConfigMap key; the controller retries automatically and the metric returns to 1. Keep the validating admission webhook enabled so bad snippets are rejected at `kubectl apply` time. Do not restart the controller as a fix: a new pod cannot fall back to an old config.

## Related alerts

- [NginxIngressCertificateExpiring](/runbooks/nginxingresscertificateexpiring/): renewed certificates are not picked up while reloads fail.
- [NginxIngressHighHttp4xxErrorRate](/runbooks/nginxingresshighhttp4xxerrorrate/): new routes that never loaded return 404.
- [NginxIngressHighHttp5xxErrorRate](/runbooks/nginxingresshighhttp5xxerrorrate/): user-facing errors on the same controller.
