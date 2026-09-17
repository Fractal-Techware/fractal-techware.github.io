---
title: "PrometheusRuleFailures: runbook and fix"
description: "PrometheusRuleFailures means rule evaluations are erroring, so alerts silently cannot fire. How to find the broken rule and fix it."
permalink: /runbooks/prometheusrulefailures/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: critical
cta:
  title: Get this alert, tested
  text: "PrometheusRuleFailures is one of 20 Prometheus self-monitoring alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheusrulefailures
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusRuleFailures

Prometheus is failing to evaluate one or more alerting or recording rules, which means some of your alerts are blind right now.

| | |
|---|---|
| Severity | critical |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metric | `prometheus_rule_evaluation_failures_total` (labels `rule_group`, `instance`) |

## What it means

Every evaluation interval, Prometheus runs each rule group. When a rule's query returns an error instead of a result, the failure counter for that group goes up. The alert fires when that counter keeps increasing, i.e. the rule is broken on every run, not just once during a restart.

It is critical because a failing alerting rule never fires. The outage you are not being paged for may already be happening.

## Common causes

- **many-to-many matching**: a binary operation (`/`, `and`, `* on(...) group_left`) where one side suddenly has duplicate label sets. Typical after an exporter upgrade adds a label, or when two exporters scrape the same target.
- **Recording rule collisions**: two recording rules (or a rule and a scraped series) write the same series with identical labels, giving "vector contains metrics with the same labelset after applying rule labels".
- **Query limits**: evaluations hitting `--query.timeout` or `--query.max-samples` on high-cardinality data.
- **Remote/Thanos Ruler setups**: the query backend is unreachable, so every evaluation errors.

## First checks

1. Find the failing rules and their error message. In the UI it is **Status → Rule health** (Prometheus 2.x: **Status → Rules**). From the API:
   ```bash
   curl -s http://<prometheus>:9090/api/v1/rules \
     | jq -r '.data.groups[].rules[] | select(.health != "ok") | "\(.name): \(.lastError)"'
   ```
2. See which group and instance are failing, and since when:
   ```promql
   sum by (instance, rule_group) (increase(prometheus_rule_evaluation_failures_total[15m])) > 0
   ```
3. Look at the logs for the exact evaluation error:
   ```bash
   kubectl -n monitoring logs <prometheus-pod> -c prometheus | grep -i "evaluating rule"
   ```
4. Paste the rule's expression into the expression browser and run it. For "many-to-many" or "duplicate series" errors, drop the operator and query each side with `count by (<matching labels>) (...) > 1` to find the duplicated label set.
5. Validate rule files before redeploying: `promtool check rules <file>.yml`. For behaviour, `promtool test rules` catches matching errors that a syntax check misses.

## Fixing it

Aggregate away the extra label (`sum by (...)`, `max by (...)`) or constrain the match with `on(...)`/`ignoring(...)`. For collisions, rename one of the recording rules. If the backend is timing out, simplify the expression or move the heavy part into a recording rule.

## Related alerts

- [PrometheusMissingRuleEvaluations](/runbooks/prometheusmissingruleevaluations/): rule groups are too slow to finish within their interval.
- [PrometheusConfigReloadFailed](/runbooks/prometheusconfigreloadfailed/): a new rule file was rejected, so old rules are still running.
- [Watchdog](/runbooks/watchdog/): confirms the alerting pipeline end to end.
