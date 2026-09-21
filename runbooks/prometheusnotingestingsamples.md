---
title: "PrometheusNotIngestingSamples: runbook and fix"
description: "PrometheusNotIngestingSamples means Prometheus has targets or rules but appends no samples. How to tell if scraping, relabeling or the TSDB is at fault."
permalink: /runbooks/prometheusnotingestingsamples/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "PrometheusNotIngestingSamples is one of 20 Prometheus self-monitoring alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheusnotingestingsamples
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusNotIngestingSamples

Prometheus is configured to scrape targets or evaluate rules, yet nothing is being written to its TSDB.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metrics | `prometheus_tsdb_head_samples_appended_total`, `prometheus_target_metadata_cache_entries`, `prometheus_rule_group_rules` |

## What it means

Every successful scrape and recording rule appends samples to the head block. The alert fires when the append rate has been flat at zero for several minutes on an instance that clearly should be busy, because it has scrape metadata or loaded rules. An empty, unconfigured Prometheus does not trigger it.

Impact is broad: dashboards go flat and every alert that depends on fresh data stops working. Since this alert is itself evaluated by the instance in trouble, it is often raised by a second Prometheus watching the first.

## Common causes

- The TSDB cannot write: disk full, read-only filesystem, or a stuck head after repeated compaction failures.
- Every target is failing its scrape, for example after a NetworkPolicy change or a certificate rotation.
- A relabeling change drops all targets or all samples (`action: drop` / `keep` with the wrong regex).
- Service discovery returns nothing: RBAC removed, or the ServiceMonitor selector no longer matches.
- The process is wedged or so overloaded that scrapes never complete.

## First checks

1. Confirm ingestion really is at zero:
   ```promql
   rate(prometheus_tsdb_head_samples_appended_total[5m])
   ```
2. Check scrape health across the board:
   ```promql
   count by (job) (up == 1)
   sum by (job) (scrape_samples_post_metric_relabeling)
   ```
3. Check discovered versus kept targets in **Status → Service discovery** and **Status → Target health**.
4. Look for storage errors and free space:
   ```bash
   kubectl -n monitoring logs <prometheus-pod> -c prometheus | grep -iE "append|wal|no space|read-only"
   kubectl -n monitoring exec <prometheus-pod> -c prometheus -- df -h /prometheus
   ```
5. Review the most recent config or Helm change for relabeling or selector edits.

## Fixing it

Free disk space or fix the volume if writes fail; if the head is stuck, a restart after the disk issue is solved usually recovers it (expect a WAL replay). For relabeling or discovery mistakes, revert the change, check it with `promtool check config`, and reload. Verify that the append rate climbs back to its normal level.

## Related alerts

- [TargetDown](/runbooks/targetdown/): a partial version of the same symptom.
- [PrometheusTSDBCompactionsFailing](/runbooks/prometheustsdbcompactionsfailing/): a common precursor on the storage side.
- [PrometheusSDRefreshFailure](/runbooks/prometheussdrefreshfailure/): no discovered targets means nothing to ingest.
