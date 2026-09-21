---
title: "PrometheusScrapeSampleLimitHit: runbook and fix"
description: "PrometheusScrapeSampleLimitHit means scrapes exceed sample_limit and are rejected whole. How to find the target with too many series and cut cardinality."
permalink: /runbooks/prometheusscrapesamplelimithit/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "PrometheusScrapeSampleLimitHit is one of 20 Prometheus self-monitoring alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheusscrapesamplelimithit
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusScrapeSampleLimitHit

Some targets return more samples than their job's `sample_limit`, and Prometheus is discarding those scrapes entirely.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metric | `prometheus_target_scrapes_exceeded_sample_limit_total` |

## What it means

`sample_limit` caps how many samples a single scrape may contain after metric relabeling. If a scrape goes over, the whole scrape fails: nothing from it is stored and `up` for that target becomes 0. The alert fires when rejected scrapes keep occurring for a sustained period.

This is a cardinality guardrail doing its job, but the affected target is now fully blind, not partially.

## Common causes

- A cardinality explosion in the application: a label carrying user IDs, request paths, query strings or error messages.
- A new histogram with many buckets multiplied by many label combinations.
- An exporter upgrade that added metrics or labels (for example per-queue, per-topic or per-table series).
- Growth in the thing being monitored: more topics, databases, tables or endpoints.
- A limit set too tightly when the job was first added.

## First checks

1. Find targets close to or over the limit:
   ```promql
   topk(10, scrape_samples_post_metric_relabeling)
   ```
   Targets with `up == 0` and a "sample limit exceeded" error in **Status → Target health** are the ones being rejected.
2. See how the count has changed over time for a suspect target:
   ```promql
   scrape_samples_scraped{job="<job>", instance="<instance>"}
   ```
3. Find which metric names dominate the output:
   ```bash
   curl -s http://<target>:<port>/metrics | grep -v '^#' | sed -E 's/[{ ].*//' | sort | uniq -c | sort -rn | head -20
   ```
4. Check which label is exploding for the top metric:
   ```bash
   curl -s http://<target>:<port>/metrics | grep '^<metric_name>' | head -50
   ```

## Fixing it

Fix the source first: remove unbounded labels in the application or exporter, or disable unneeded collectors. In the meantime, drop the offending series at scrape time with `metric_relabel_configs` (`action: drop` on the metric name, or `labeldrop` on the exploding label if that does not create duplicates). Raise `sample_limit` only when the growth is legitimate and Prometheus has memory for it.

## Related alerts

- [TargetDown](/runbooks/targetdown/): rejected scrapes show up as down targets.
- [PrometheusLabelLimitHit](/runbooks/prometheuslabellimithit/): the label-count guardrail.
- [PrometheusTSDBCompactionsFailing](/runbooks/prometheustsdbcompactionsfailing/): unchecked cardinality eventually hurts the TSDB.
