---
title: "PrometheusErrorSendingAlertsToAlertmanager: runbook and fix"
description: "PrometheusErrorSendingAlertsToAlertmanager means some alert pushes to Alertmanager fail. How to find the failing instance and the error behind it."
permalink: /runbooks/prometheuserrorsendingalertstoalertmanager/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "PrometheusErrorSendingAlertsToAlertmanager ships in the pack of 179 alerts alongside 19 other Prometheus self-monitoring rules, all unit tested."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheuserrorsendingalertstoalertmanager
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusErrorSendingAlertsToAlertmanager

Prometheus is failing to deliver a noticeable share of its alert batches to one or more Alertmanagers.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metrics | `prometheus_notifications_errors_total`, `prometheus_notifications_sent_total` (label `alertmanager`) |

## What it means

Prometheus pushes firing alerts to every discovered Alertmanager on each evaluation. The alert fires when the error rate for a specific Alertmanager stays above a small percentage of sends for a sustained period.

If you run an Alertmanager cluster and only one member is failing, notifications still go out through the others, so impact is limited. If every Alertmanager label shows errors, alerts are effectively not being delivered.

## Common causes

- One Alertmanager pod is restarting, overloaded or stuck, while Prometheus still has it in discovery.
- Network problems between Prometheus and Alertmanager: NetworkPolicy, service mesh mTLS, proxies.
- TLS or auth mismatch after rotating certificates or enabling basic auth on Alertmanager.
- API version mismatch: Prometheus 3.x and Alertmanager 0.27+ only speak the v2 API, so an old `api_version: v1` setting breaks.
- Alertmanager rejecting payloads, for example alerts with invalid labels.

## First checks

1. Find which Alertmanager is failing:
   ```promql
   sum by (instance, alertmanager) (rate(prometheus_notifications_errors_total[5m]))
   ```
2. Check whether alerts are also being dropped outright:
   ```promql
   rate(prometheus_notifications_dropped_total[5m])
   ```
3. Read the error Prometheus gets back:
   ```bash
   kubectl -n monitoring logs <prometheus-pod> -c prometheus | grep -i "error sending alert"
   ```
4. Test the endpoint from the Prometheus pod:
   ```bash
   kubectl -n monitoring exec <prometheus-pod> -c prometheus -- wget -qO- http://<alertmanager>:9093/api/v2/status
   ```
5. On the Alertmanager side, look at its logs and `alertmanager_alerts_invalid_total`.

## Fixing it

Restart or reschedule the unhealthy Alertmanager member, fix the network path or TLS settings, and set `api_version: v2` if an old config still says v1. If the failing address is a stale pod IP, check that discovery uses the headless service or endpoints rather than a hardcoded address.

## Related alerts

- [PrometheusNotConnectedToAlertmanagers](/runbooks/prometheusnotconnectedtoalertmanagers/): no Alertmanager discovered at all.
- [PrometheusNotificationQueueRunningFull](/runbooks/prometheusnotificationqueuerunningfull/): failing sends make the queue back up.
- [Watchdog](/runbooks/watchdog/): end-to-end proof that alerts actually arrive.
