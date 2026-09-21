---
title: "PrometheusLabelLimitHit: runbook and fix"
description: "PrometheusLabelLimitHit means targets are rejected for exceeding label_limit or label length limits. How to find the offending job and fix the labels."
permalink: /runbooks/prometheuslabellimithit/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "PrometheusLabelLimitHit ships with the other Prometheus self-monitoring alerts, 20 of the 179 in the pack, each unit tested with promtool."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheuslabellimithit
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusLabelLimitHit

Prometheus is dropping targets from a scrape pool because their labels break the configured label limits.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metric | `prometheus_target_scrape_pool_exceeded_label_limits_total` |

## What it means

A scrape config can set `label_limit` (maximum number of labels), `label_name_length_limit` and `label_value_length_limit`. They protect the TSDB from label explosions. When targets exceed them during target sync, Prometheus rejects them and increments this counter. The alert fires when that continues for a sustained period.

Those targets are not scraped, so their data and the alerts built on it disappear.

## Common causes

- Kubernetes SD with a `labelmap` over `__meta_kubernetes_pod_label_(.+)` or annotations, and a workload that added many labels.
- Very long label values, such as full image references, commit messages, JSON blobs or URLs copied into labels.
- A Helm chart or operator upgrade that started adding extra pod labels.
- Limits copied from another environment where workloads carry fewer labels.

## First checks

1. Find the affected Prometheus and how often it happens:
   ```promql
   increase(prometheus_target_scrape_pool_exceeded_label_limits_total[15m]) > 0
   ```
2. Look for the rejection details in the logs:
   ```bash
   kubectl -n monitoring logs <prometheus-pod> -c prometheus | grep -i "label"
   ```
3. Find which jobs define limits:
   ```bash
   curl -s http://<prometheus>:9090/api/v1/status/config | jq -r '.data.yaml' | grep -nE 'job_name|label_limit|label_name_length_limit|label_value_length_limit'
   ```
4. Inspect the discovered labels of candidate targets in **Status → Service discovery**, and count labels on a suspect pod:
   ```bash
   kubectl -n <namespace> get pod <pod> -o json | jq '.metadata.labels | length'
   ```

## Fixing it

Prefer trimming labels over raising limits. Replace a broad `labelmap` with explicit `replace` rules for the few labels you actually query, or add `labeldrop` for noisy ones. If the labels are legitimate and bounded, raise the specific limit for that job only. Reload after `promtool check config` and confirm the counter stops increasing.

## Related alerts

- [PrometheusTargetLimitHit](/runbooks/prometheustargetlimithit/): the equivalent guardrail for target counts.
- [PrometheusScrapeSampleLimitHit](/runbooks/prometheusscrapesamplelimithit/): the equivalent guardrail for samples per scrape.
- [PrometheusDuplicateTimestamps](/runbooks/prometheusduplicatetimestamps/): what can happen if you drop labels too aggressively.
