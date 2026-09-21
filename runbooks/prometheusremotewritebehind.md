---
title: "PrometheusRemoteWriteBehind: runbook and fix"
description: "PrometheusRemoteWriteBehind means remote write lags behind ingestion. How to find the bottleneck and tune queue_config before data is lost."
permalink: /runbooks/prometheusremotewritebehind/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: critical
cta:
  title: Get this alert, tested
  text: "PrometheusRemoteWriteBehind is one of the Prometheus self-monitoring alerts (20 in total) in the pack of 179 with promtool tests and runbooks."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheusremotewritebehind
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusRemoteWriteBehind

Remote write is not keeping up: the newest sample sent to the remote endpoint is noticeably older than the newest sample Prometheus has ingested.

| | |
|---|---|
| Severity | critical |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metrics | `prometheus_remote_storage_queue_highest_timestamp_seconds`, `prometheus_remote_storage_queue_highest_sent_timestamp_seconds` |

## What it means

Remote write tails the WAL and ships samples through a set of parallel shards. The gap between "highest timestamp seen" and "highest timestamp successfully sent" is the lag. The alert fires when that lag has stayed above a couple of minutes for a sustained period.

Anything reading from the remote store sees stale data. If the lag keeps growing past what the local WAL retains (a few hours at most), those samples are never delivered.

## Common causes

- The remote backend is slow or returning retryable errors (5xx, 429), so batches are resent.
- Not enough shards: `max_shards` is too low for the ingest rate, or resharding cannot keep up with a traffic jump.
- Network latency or limited egress bandwidth between Prometheus and the backend.
- Prometheus is CPU-starved, so it cannot read the WAL and encode batches fast enough.
- A long backlog after an outage of the backend.

## First checks

1. Measure the lag per endpoint:
   ```promql
   max by (instance, remote_name) (prometheus_remote_storage_queue_highest_timestamp_seconds - prometheus_remote_storage_queue_highest_sent_timestamp_seconds)
   ```
2. See whether it wants more shards than it is allowed:
   ```promql
   max by (remote_name) (prometheus_remote_storage_shards_desired)
   max by (remote_name) (prometheus_remote_storage_shards_max)
   ```
3. Check retries and send latency:
   ```promql
   sum by (remote_name) (rate(prometheus_remote_storage_samples_retried_total[5m]))
   ```
4. Look for errors and throttling in the logs:
   ```bash
   kubectl -n monitoring logs <prometheus-pod> -c prometheus | grep -iE "remote|resharding"
   ```
5. Check Prometheus CPU usage and throttling for the pod.

## Fixing it

If the backend is healthy but shards are pinned at the maximum, raise `max_shards` and consider a larger `max_samples_per_send` in `queue_config`. If the backend is slow or throttling, fix it or raise its limits first; more shards only add pressure. Reduce volume with `write_relabel_configs` if you ship metrics nobody queries remotely. Give Prometheus more CPU if it is throttled.

## Related alerts

- [PrometheusRemoteStorageFailures](/runbooks/prometheusremotestoragefailures/): non-retryable errors that drop data outright.
- [PrometheusHighQueryLoad](/runbooks/prometheushighqueryload/): a busy server has less CPU to spare for remote write.
