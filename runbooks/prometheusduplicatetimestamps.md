---
title: "PrometheusDuplicateTimestamps: runbook and fix"
description: "PrometheusDuplicateTimestamps means scraped samples share a timestamp but differ in value and get dropped. How to find the target and fix it."
permalink: /runbooks/prometheusduplicatetimestamps/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "PrometheusDuplicateTimestamps is one of 20 Prometheus self-monitoring alerts in the 179-alert pack, each with promtool unit tests and a runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheusduplicatetimestamps
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusDuplicateTimestamps

Prometheus is continuously dropping scraped samples because two samples for the same series arrived with the same timestamp but different values.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metric | `prometheus_target_scrapes_sample_duplicate_timestamp_total` |

## What it means

A series is identified by its metric name and label set. If one scrape (or two targets feeding the same series) produces that identical series twice with different values, Prometheus keeps the first and rejects the rest. The alert fires when this has been happening steadily for several minutes, not just during a single deploy.

The data you do keep is effectively random: whichever duplicate won that scrape. Graphs look jumpy and alerts built on those series can misfire.

## Common causes

- The exporter emits the same series twice, for example two collectors registering the same metric, or a bug in a custom exporter.
- `metric_relabel_configs` with `labeldrop` or `labelmap` removes the label that made series distinct.
- `honor_labels: true` on a federation or Pushgateway job, where pushed labels collide with target labels.
- Two jobs scrape the same endpoint and relabeling gives them identical `job` and `instance` labels.
- Exporters that expose explicit timestamps with coarse resolution.

## First checks

1. Find which Prometheus is affected and how many samples are dropped:
   ```promql
   rate(prometheus_target_scrapes_sample_duplicate_timestamp_total[5m])
   ```
2. The counter has no target label, so get the target from the logs:
   ```bash
   kubectl -n monitoring logs <prometheus-pod> -c prometheus | grep -i "same timestamp"
   ```
   If nothing shows, temporarily run with `--log.level=debug`.
3. Pull the raw metrics and look for repeated series lines:
   ```bash
   curl -s http://<target>:<port>/metrics | grep -v '^#' | sed 's/ [^ ]*$//' | sort | uniq -d | head
   ```
4. Review the job's relabeling in **Status → Configuration**, looking for `labeldrop`, `labelmap` and `honor_labels`.

## Fixing it

If the exporter output itself has duplicates, fix or upgrade the exporter, or disable the overlapping collector. If relabeling caused it, keep the distinguishing label or aggregate upstream instead of dropping it. For federation and Pushgateway, make sure each source contributes a unique label such as `instance`. After the change, confirm the counter stops increasing.

## Related alerts

- [PrometheusOutOfOrderTimestamps](/runbooks/prometheusoutofordertimestamps/): the sibling problem with timestamps going backwards.
- [PrometheusLabelLimitHit](/runbooks/prometheuslabellimithit/): another way relabeling and label hygiene cause dropped data.
