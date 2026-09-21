---
title: "PrometheusRemoteStorageFailures: runbook and fix"
description: "PrometheusRemoteStorageFailures means remote write is permanently failing samples, so data is lost. How to read the error and fix auth, limits or payloads."
permalink: /runbooks/prometheusremotestoragefailures/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: critical
cta:
  title: Get this alert, tested
  text: "PrometheusRemoteStorageFailures is one of 20 Prometheus self-monitoring alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheusremotestoragefailures
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusRemoteStorageFailures

A noticeable share of the samples Prometheus sends to a remote write endpoint are failing and will not be retried.

| | |
|---|---|
| Severity | critical |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metrics | `prometheus_remote_storage_samples_failed_total`, `prometheus_remote_storage_samples_total` (labels `remote_name`, `url`) |

## What it means

Remote write distinguishes recoverable errors (network errors, HTTP 5xx, 429 when retry-on-rate-limit is enabled), which are retried, from non-recoverable ones (most HTTP 4xx), which are dropped and counted as failed. The alert fires when the failed fraction for one remote endpoint stays above a small percentage for a sustained period.

It is critical because failed samples are gone from the remote store for good. Long-term dashboards, global queries and any alerting that runs on the remote side (Mimir, Thanos, Cortex, a SaaS backend) are missing that data.

## Common causes

- Authentication: expired token, rotated password, wrong tenant header (401, 403).
- Backend limits: per-tenant series or ingestion rate limits, label count or label length limits (400 or 429).
- Samples too old or out of order for the backend, often after Prometheus was down and replays its WAL.
- Payload too large (413) from a proxy or ingress in front of the backend.
- A URL or path that changed (404).

## First checks

1. Identify the endpoint and the failure rate:
   ```promql
   sum by (instance, remote_name, url) (rate(prometheus_remote_storage_samples_failed_total[5m]))
   ```
2. Compare with retries, which indicate a different class of problem:
   ```promql
   sum by (remote_name) (rate(prometheus_remote_storage_samples_retried_total[5m]))
   ```
3. Read the HTTP status and body the backend returned:
   ```bash
   kubectl -n monitoring logs <prometheus-pod> -c prometheus | grep -i "remote" | grep -iE "non-recoverable|status"
   ```
4. Test credentials directly against the endpoint:
   ```bash
   curl -s -o /dev/null -w '%{http_code}\n' -X POST -H "Authorization: Bearer <token>" https://<remote-write-url>
   ```
5. Check the backend's own distributor or gateway logs and per-tenant limit metrics.

## Fixing it

Rotate or correct credentials and reload. For limit errors, either raise the tenant limits on the backend or reduce what you send with `write_relabel_configs` (drop high-cardinality or unused metrics). For 413, raise the proxy body limit or lower `max_samples_per_send` in `queue_config`. Old or out-of-order rejections after an outage usually stop once the backlog clears.

## Related alerts

- [PrometheusRemoteWriteBehind](/runbooks/prometheusremotewritebehind/): the retryable counterpart, where data is delayed rather than rejected.
- [PrometheusOutOfOrderTimestamps](/runbooks/prometheusoutofordertimestamps/): bad timestamps locally often reappear as remote rejections.
