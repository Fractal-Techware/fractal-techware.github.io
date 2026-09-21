---
title: "LokiRequestLatency: runbook and fix"
description: "LokiRequestLatency means p99 latency on a Loki route is high. How to find whether queries, ingestion or storage is slow and how to speed it up."
permalink: /runbooks/lokirequestlatency/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Grafana Loki
severity: warning
cta:
  title: Get this alert, tested
  text: "LokiRequestLatency is one of 5 Loki alerts in the pack of 179 Prometheus alerts, all unit tested with promtool and documented."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=lokirequestlatency
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# LokiRequestLatency

Requests on at least one Loki route have been slow at the 99th percentile for a sustained period.

| | |
|---|---|
| Severity | warning |
| Source | Loki's own `/metrics` (2.9+ and 3.x) |
| Key metric | `loki_request_duration_seconds_bucket` (labels `job`, `route`) |

## What it means

The alert computes p99 request duration per component and route and fires when it stays high. Routes that are long-lived by design, such as live tailing and the internal querier-to-scheduler streams, are excluded because they would always look slow.

Slow push routes create back-pressure on log agents (Promtail, Alloy, Fluent Bit), which buffer and eventually drop logs. Slow query routes make Grafana panels time out.

## Common causes

- **Heavy queries**: wide time ranges, no label filters, or regex over high-volume streams.
- **Not enough queriers**, so queries wait in the scheduler queue.
- **Slow object storage** reads or writes, or missing caches (results, chunks, index).
- **Ingester pressure**: high memory, slow flushes, or a WAL replay after restart.
- **CPU throttling** on Loki pods.

## First checks

1. Find the slow job and route:
   ```promql
   topk(10, histogram_quantile(0.99, sum by (job, route, le) (rate(loki_request_duration_seconds_bucket[5m]))))
   ```
2. For query routes, check whether queries are queueing:
   ```promql
   sum by (__name__, job) ({__name__=~".+_query_(scheduler|frontend)_queue_length"})
   ```
   The metric prefix (`cortex_` or `loki_`) depends on the Loki version and whether you run a scheduler.
3. Find the slowest recent queries. The query frontend logs `duration=` for each:
   ```bash
   kubectl -n <loki-namespace> logs <query-frontend-pod> --since=30m | grep 'metrics.go' | grep -E 'duration=[0-9]+(\.[0-9]+)?s' | tail -20
   ```
4. Check storage latency:
   ```promql
   histogram_quantile(0.99, sum by (operation, le) (rate(loki_s3_request_duration_seconds_bucket[5m])))
   ```
   For GCS or Azure, use the matching `loki_gcs_*` or `loki_azure_blob_*` duration metric.
5. Check resources: `kubectl -n <loki-namespace> top pods`.

## Fixing it

Scale queriers if work is queueing. Enable or enlarge the results and chunk caches. Tighten per-tenant limits like `max_query_length` and `max_query_series`, and encourage label filters in dashboards. For push latency, scale ingesters or distributors and check storage flush times. Remove CPU limits that throttle latency-sensitive components.

## Related alerts

- [LokiRequestErrors](/runbooks/lokirequesterrors/): timeouts become 5xx.
- [LokiDiscardedSamples](/runbooks/lokidiscardedsamples/): slow ingestion can push clients into rate limits.
