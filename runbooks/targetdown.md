---
title: "TargetDown: runbook and fix"
description: "TargetDown means a noticeable share of a job's scrape targets are failing. How to find the failing targets, read the scrape error and fix it."
permalink: /runbooks/targetdown/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "TargetDown is one of 20 Prometheus self-monitoring alerts in the pack of 179 alerts, each shipped with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=targetdown
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# TargetDown

A meaningful fraction of the targets behind one job are failing their scrapes, so Prometheus has gaps in that data.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus scrape loop (synthetic series) |
| Key metric | `up` (labels `job`, `instance`, `namespace`, `service`) |

## What it means

Every scrape produces an `up` sample: 1 if the scrape succeeded, 0 if it did not. The alert fires when, for a given job (grouped by namespace and service), more than a small share of its targets have been reporting 0 for several minutes. A single flapping pod is tolerated; a real slice of the fleet going dark is not.

The target may be perfectly healthy and only unscrapeable, but either way every alert that depends on its metrics is now blind.

## Common causes

- The process crashed, or the pods are in CrashLoopBackOff or Pending.
- A NetworkPolicy, security group or firewall change blocks Prometheus from the metrics port.
- The metrics endpoint moved (port renamed, path changed, TLS enabled) and the ServiceMonitor or scrape config was not updated.
- Scrapes time out because the exporter is slow, e.g. a database exporter running expensive queries.
- Auth changes: expired bearer token or client certificate.

## First checks

1. List the failing targets and their errors. In the UI: **Status → Target health** (2.x: **Status → Targets**), filter to unhealthy. Or:
   ```bash
   curl -s 'http://<prometheus>:9090/api/v1/targets?state=active' \
     | jq -r '.data.activeTargets[] | select(.health=="down") | "\(.labels.job) \(.scrapeUrl) \(.lastError)"'
   ```
2. See which jobs are affected and how badly:
   ```promql
   sum by (job, namespace) (up == 0)
   ```
3. Check whether the workload itself is running:
   ```bash
   kubectl -n <namespace> get pods -o wide
   kubectl -n <namespace> get endpoints <service>
   ```
4. Scrape it the way Prometheus would, from inside the cluster:
   ```bash
   kubectl -n monitoring exec <prometheus-pod> -c prometheus -- wget -qO- -T 10 http://<pod-ip>:<port>/metrics | head
   ```
5. If the error is "context deadline exceeded", compare `scrape_duration_seconds` for that job against its scrape timeout.

## Fixing it

Match the fix to the `lastError`: "connection refused" means the process or port is wrong, "i/o timeout" points at the network, "deadline exceeded" at a slow exporter (raise `scrape_timeout` or make the exporter cheaper), and 401/403 at credentials. If the targets are intentionally gone, remove them from discovery rather than leaving them down.

## Related alerts

- [PrometheusSDRefreshFailure](/runbooks/prometheussdrefreshfailure/): discovery is failing, so the target list may be stale.
- [PrometheusScrapeSampleLimitHit](/runbooks/prometheusscrapesamplelimithit/): scrapes rejected for too many samples also show as down.
- [PrometheusNotIngestingSamples](/runbooks/prometheusnotingestingsamples/): the extreme case where nothing is ingested at all.
