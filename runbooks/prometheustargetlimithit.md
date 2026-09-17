---
title: "PrometheusTargetLimitHit: runbook and fix"
description: "PrometheusTargetLimitHit means a scrape config discovered more targets than its target_limit, so its targets are not scraped. How to diagnose and fix."
permalink: /runbooks/prometheustargetlimithit/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "PrometheusTargetLimitHit is one of 20 Prometheus self-monitoring alerts in the 179-alert pack, all with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheustargetlimithit
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusTargetLimitHit

A scrape pool discovered more targets than its configured `target_limit`, and Prometheus stopped scraping that pool's targets.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metric | `prometheus_target_scrape_pool_exceeded_target_limit_total` |

## What it means

`target_limit` is an optional per-job guardrail against runaway discovery. When the number of targets left after relabeling exceeds it, the whole scrape pool is marked as failing rather than scraping an arbitrary subset. The alert fires when this keeps happening for a sustained period.

The impact is larger than the name suggests: every target in that job, not just the surplus, stops producing data, and alerts for that job go quiet.

## Common causes

- Legitimate growth: the cluster or fleet scaled out past a limit that was set long ago.
- A relabeling change that no longer filters discovery, for example a `keep` rule removed or its regex broadened.
- A ServiceMonitor or PodMonitor selector that now matches far more services or pods than intended.
- Many short-lived pods (batch jobs, autoscaled workers) inflating the target count.
- A limit set by a platform team per tenant that was not raised when the tenant grew.

## First checks

1. Find the affected Prometheus:
   ```promql
   increase(prometheus_target_scrape_pool_exceeded_target_limit_total[15m]) > 0
   ```
2. Compare current targets per pool with discovered ones:
   ```promql
   sort_desc(prometheus_target_scrape_pool_targets)
   sort_desc(prometheus_sd_discovered_targets)
   ```
3. Open **Status → Target health**; the affected pool shows a target limit error on its targets.
4. See the configured limit and relabeling for that job:
   ```bash
   curl -s http://<prometheus>:9090/api/v1/status/config | jq -r '.data.yaml' | grep -B2 -A30 'job_name: <job>'
   ```
5. Check recent changes to ServiceMonitor or PodMonitor selectors:
   ```bash
   kubectl get servicemonitors,podmonitors -A
   ```

## Fixing it

If the growth is real, raise `target_limit` for that job (and confirm Prometheus has memory for the extra series). If discovery broadened by mistake, restore the `keep`/`drop` relabeling or tighten the selector. Validate with `promtool check config`, reload, and confirm the pool's targets are scraped again.

## Related alerts

- [PrometheusLabelLimitHit](/runbooks/prometheuslabellimithit/): the same guardrail family, for labels.
- [PrometheusScrapeSampleLimitHit](/runbooks/prometheusscrapesamplelimithit/): the per-scrape sample guardrail.
- [TargetDown](/runbooks/targetdown/): targets in a limited pool will also report as down.
