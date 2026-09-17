---
title: "PrometheusMissingRuleEvaluations: runbook and fix"
description: "PrometheusMissingRuleEvaluations means rule groups take longer than their interval, so evaluations are skipped. How to find the slow group and speed it up."
permalink: /runbooks/prometheusmissingruleevaluations/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "PrometheusMissingRuleEvaluations is one of 20 Prometheus self-monitoring alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheusmissingruleevaluations
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusMissingRuleEvaluations

At least one rule group is taking longer to evaluate than its interval, so Prometheus is skipping evaluations.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metrics | `prometheus_rule_group_iterations_missed_total`, `prometheus_rule_group_last_duration_seconds` (label `rule_group`) |

## What it means

Rules in a group run sequentially, once per interval. If one run is still going when the next is due, Prometheus skips that iteration and counts it as missed. The alert fires when a group keeps missing iterations for a sustained period.

Missed iterations mean recording rules have gaps and alerting rules react late. Alerts that rely on a pending period can also take longer to fire or flap, because their state is updated less often than you configured.

## Common causes

- One expensive expression: a regex matcher over a huge metric, a long range like `[1d]`, or a high-cardinality `histogram_quantile`.
- Too many rules in one group, so the sum of their runtimes exceeds the interval.
- A group interval set too short for what it computes.
- General query pressure: dashboards and API clients competing for the same query slots and CPU.
- Remote or Thanos Ruler setups where the query backend is slow.

## First checks

1. Find the slow groups relative to their interval:
   ```promql
   topk(10, prometheus_rule_group_last_duration_seconds / prometheus_rule_group_interval_seconds)
   ```
2. Confirm which groups are missing runs:
   ```promql
   sum by (instance, rule_group) (increase(prometheus_rule_group_iterations_missed_total[15m])) > 0
   ```
3. Open **Status → Rule health**. Each rule shows its last evaluation duration, which pinpoints the expensive expression inside the group.
4. Run that expression in the query page and check the query stats, or time it with the API:
   ```bash
   time curl -s 'http://<prometheus>:9090/api/v1/query' --data-urlencode 'query=<expression>' > /dev/null
   ```
5. Check overall engine pressure: `prometheus_engine_queries` against `prometheus_engine_queries_concurrent_max`.

## Fixing it

Split large groups into smaller ones so they evaluate in parallel. Precompute the heavy inner part of an expression in a recording rule and reference it. Tighten matchers and avoid unanchored regexes. Lengthen the interval for groups that do not need fast evaluation. Recent Prometheus versions can also evaluate independent rules within a group concurrently with `--enable-feature=concurrent-rule-eval`.

## Related alerts

- [PrometheusRuleFailures](/runbooks/prometheusrulefailures/): slow rules that hit the query timeout become failures.
- [PrometheusHighQueryLoad](/runbooks/prometheushighqueryload/): rule evaluation shares query capacity with dashboards.
