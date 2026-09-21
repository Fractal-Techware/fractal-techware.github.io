---
title: "PrometheusNotificationQueueRunningFull: runbook and fix"
description: "PrometheusNotificationQueueRunningFull warns that the alert queue to Alertmanager will soon overflow and drop alerts. How to diagnose and fix it."
permalink: /runbooks/prometheusnotificationqueuerunningfull/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "PrometheusNotificationQueueRunningFull is one of the 20 Prometheus self-monitoring alerts in a 179-alert pack with promtool tests and runbooks."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheusnotificationqueuerunningfull
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusNotificationQueueRunningFull

The in-memory queue of alerts waiting to be sent to Alertmanager is growing fast enough that it is expected to hit capacity soon.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metrics | `prometheus_notifications_queue_length`, `prometheus_notifications_queue_capacity` |

## What it means

Alerts produced by rule evaluation go into a bounded queue before being pushed to Alertmanager. The alert is predictive: it fires when the recent growth trend of the queue, extrapolated forward, would exceed its capacity in the near future, and that trend has held for a while.

Once the queue is full, Prometheus drops the oldest alerts. That means lost or delayed notifications during exactly the kind of incident that makes lots of alerts fire.

## Common causes

- Alertmanager is slow or failing, so batches are not drained.
- An alert storm: a rule that produces thousands of series (one alert per pod, per path, per label value) during a widespread outage.
- High-cardinality alerts from a recently added rule without enough aggregation.
- Capacity left at its default on a Prometheus that evaluates a very large rule set.

## First checks

1. Look at queue length against capacity over the last hours:
   ```promql
   prometheus_notifications_queue_length / prometheus_notifications_queue_capacity
   ```
2. Check whether sends are failing or alerts are already being dropped:
   ```promql
   sum by (alertmanager) (rate(prometheus_notifications_errors_total[5m]))
   rate(prometheus_notifications_dropped_total[5m])
   ```
3. Find which alerts are producing the volume:
   ```promql
   topk(10, count by (alertname) (ALERTS{alertstate="firing"}))
   ```
4. Check how long each send takes:
   ```promql
   rate(prometheus_notifications_latency_seconds_sum[5m]) / rate(prometheus_notifications_latency_seconds_count[5m])
   ```

## Fixing it

If Alertmanager is the bottleneck, fix its health first (see the related alerts). If one rule is flooding the queue, aggregate it with `sum by (...)` or `count by (...)` so it fires once per service instead of once per series. As a last resort, raise `--alertmanager.notification-queue-capacity` and give Prometheus the memory to match; that buys headroom but does not remove the storm.

## Related alerts

- [PrometheusErrorSendingAlertsToAlertmanager](/runbooks/prometheuserrorsendingalertstoalertmanager/): the usual reason the queue is not draining.
- [PrometheusNotConnectedToAlertmanagers](/runbooks/prometheusnotconnectedtoalertmanagers/): nothing to drain the queue into.
- [PrometheusHighQueryLoad](/runbooks/prometheushighqueryload/): an overloaded server evaluates and sends more slowly.
