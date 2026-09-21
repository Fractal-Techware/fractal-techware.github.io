---
title: "PrometheusHighQueryLoad: runbook and fix"
description: "PrometheusHighQueryLoad means Prometheus is close to its concurrent query limit, so queries and rules queue. How to find heavy queries and reduce the load."
permalink: /runbooks/prometheushighqueryload/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "PrometheusHighQueryLoad is one of 20 Prometheus self-monitoring alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheushighqueryload
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusHighQueryLoad

Prometheus has been running close to its maximum number of concurrent queries for a sustained period.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metrics | `prometheus_engine_queries`, `prometheus_engine_queries_concurrent_max` |

## What it means

The query engine runs a limited number of queries at once, set by `--query.max-concurrency` (default 20). Extra queries wait in line. The alert fires when, on average, most of those slots have been busy for several minutes.

Once slots are saturated, dashboards load slowly or time out, API clients see latency, and rule evaluation competes for the same capacity, which can turn into missed evaluations and late alerts.

## Common causes

- Grafana dashboards with many panels on short auto-refresh, left open on wall screens or by many users.
- Expensive ad-hoc queries: long ranges, unanchored regex matchers, high-cardinality `histogram_quantile` or `count by` over everything.
- An automated client (a reporting script, autoscaler adapter, Thanos or federation) polling aggressively.
- A dashboard or rule change that replaced a recording rule with the raw expression.
- Prometheus itself is short on CPU or memory, so each query takes longer and holds its slot.

## First checks

1. Watch saturation and queueing over time:
   ```promql
   prometheus_engine_queries / prometheus_engine_queries_concurrent_max
   ```
2. See how long queries spend waiting versus executing:
   ```promql
   prometheus_engine_query_duration_seconds{slice=~"queue_time|inner_eval", quantile="0.9"}
   ```
3. Find which endpoints are busy:
   ```promql
   topk(5, sum by (handler) (rate(prometheus_http_request_duration_seconds_count[5m])))
   ```
4. Identify the actual heavy queries. Enable the query log by setting `query_log_file` in the `global` section and reloading, then:
   ```bash
   kubectl -n monitoring exec <prometheus-pod> -c prometheus -- tail -n 50 <query-log-path>
   ```
   Queries that were running during a crash are also listed in `queries.active` in the data directory.
5. Check pod CPU throttling and memory headroom.

## Fixing it

Turn expensive, frequently used expressions into recording rules and point dashboards at them. Raise dashboard refresh intervals and limit default time ranges. Throttle or fix aggressive API clients. If load is legitimate, add CPU and raise `--query.max-concurrency` moderately, or put a caching query frontend in front of Prometheus. Keep `--query.timeout` in place so runaway queries cannot hold slots indefinitely.

## Related alerts

- [PrometheusMissingRuleEvaluations](/runbooks/prometheusmissingruleevaluations/): the usual knock-on effect on rules.
- [PrometheusRuleFailures](/runbooks/prometheusrulefailures/): rules that hit the query timeout under load.
- [PrometheusRemoteWriteBehind](/runbooks/prometheusremotewritebehind/): CPU contention can slow remote write too.
