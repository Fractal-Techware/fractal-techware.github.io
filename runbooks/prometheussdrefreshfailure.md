---
title: "PrometheusSDRefreshFailure: runbook and fix"
description: "PrometheusSDRefreshFailure means a service discovery mechanism keeps failing to refresh its targets. How to find the mechanism, read the error and fix it."
permalink: /runbooks/prometheussdrefreshfailure/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "PrometheusSDRefreshFailure is one of 20 Prometheus self-monitoring alerts in the 179-alert pack, all with promtool unit tests and a runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheussdrefreshfailure
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusSDRefreshFailure

A polling-based service discovery mechanism in Prometheus is repeatedly failing to fetch its list of targets.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metric | `prometheus_sd_refresh_failures_total` (labels `mechanism`, `config`) |

## What it means

Mechanisms such as `ec2`, `azure`, `gce`, `dns`, `http`, `openstack` and several others poll an API on an interval. When a refresh errors, Prometheus keeps the last successful target list and increments the failure counter. The alert fires when failures keep recurring over a longer window.

Nothing breaks immediately. But new instances are not scraped, terminated ones linger as down targets, and if Prometheus restarts while discovery is broken it starts with no targets at all for that job.

## Common causes

- Cloud credentials or IAM: expired keys, a removed role, missing permissions such as describing instances.
- API rate limiting from the cloud provider, especially with short `refresh_interval` values and many Prometheus replicas.
- DNS resolution failures for `dns_sd_configs` records, or the record was deleted.
- An `http_sd_configs` endpoint that is down, slow, or returns invalid JSON.
- Network egress blocked to the provider's API endpoint (proxy, firewall, VPC endpoint changes).

## First checks

1. Identify the failing mechanism and job:
   ```promql
   sum by (instance, mechanism, config) (increase(prometheus_sd_refresh_failures_total[30m])) > 0
   ```
2. Read the error:
   ```bash
   kubectl -n monitoring logs <prometheus-pod> -c prometheus | grep -iE "discovery|refresh"
   ```
3. Compare what is currently discovered in **Status → Service discovery**, or:
   ```promql
   prometheus_sd_discovered_targets{config="<job>"}
   ```
4. Reproduce the call from the Prometheus pod, for example:
   ```bash
   kubectl -n monitoring exec <prometheus-pod> -c prometheus -- nslookup <dns-sd-name>
   kubectl -n monitoring exec <prometheus-pod> -c prometheus -- wget -qO- http://<http-sd-endpoint>
   ```
5. For cloud mechanisms, verify the identity in use has the needed read permissions (check the cloud audit log for denied calls).

## Fixing it

Restore credentials or permissions, fix the DNS record or HTTP SD endpoint, or open the network path. If you are being rate limited, raise `refresh_interval` or narrow the query with filters so fewer API calls are needed. Once refreshes succeed, confirm the discovered target count matches reality.

## Related alerts

- [TargetDown](/runbooks/targetdown/): stale discovery shows up as down targets.
- [PrometheusNotIngestingSamples](/runbooks/prometheusnotingestingsamples/): what a restart with broken discovery can lead to.
- [PrometheusTargetLimitHit](/runbooks/prometheustargetlimithit/): the opposite problem, discovery returning too much.
