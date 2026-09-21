---
title: "Watchdog: runbook and fix"
description: "Watchdog is an always-firing heartbeat alert. How to wire it to a dead man's switch, and what to do when the Watchdog alert stops arriving."
permalink: /runbooks/watchdog/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: info
cta:
  title: Get this alert, tested
  text: "Watchdog is the heartbeat behind the 20 Prometheus self-monitoring alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=watchdog
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# Watchdog

Watchdog is supposed to be firing all the time. It is a heartbeat: the problem is when it stops.

| | |
|---|---|
| Severity | info |
| Source | Prometheus rule engine (no exporter needed) |
| Key metric | none, the rule is unconditionally true |

## What it means

The rule always evaluates to true, so as long as Prometheus is evaluating rules, Alertmanager is receiving alerts and notifications are leaving your network, a Watchdog notification keeps flowing. You do not page on it arriving. You page on its absence, using an external dead man's switch that expects a ping every few minutes.

Without this, a dead Prometheus, a broken Alertmanager or an expired receiver credential means silence, and silence looks exactly like "everything is fine".

## Setting up the dead man's switch

1. Create a check on an external heartbeat service: a healthchecks.io check, a Dead Man's Snitch (which can raise PagerDuty incidents), or an Opsgenie heartbeat. Give it a period a bit longer than your repeat interval plus a grace period.
2. Route Watchdog to it in Alertmanager, above your normal routes, with a short repeat interval so it is re-sent continuously:
   ```yaml
   route:
     routes:
       - matchers: ['alertname = "Watchdog"']
         receiver: heartbeat
         group_wait: 0s
         group_interval: 1m
         repeat_interval: 1m
   receivers:
     - name: heartbeat
       webhook_configs:
         - url: https://hc-ping.com/<check-uuid>
           send_resolved: false
   ```
3. Make sure the heartbeat service pages through a path that does not depend on this Alertmanager.

## When the heartbeat stops arriving

Walk the pipeline from the source outwards:

1. Is Prometheus up and evaluating rules? Open **Status → Rule health** and check the last evaluation time of the Watchdog group.
   ```bash
   curl -s http://<prometheus>:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.alertname=="Watchdog")'
   ```
2. Is Prometheus connected to Alertmanager?
   ```promql
   prometheus_notifications_alertmanagers_discovered
   ```
3. Did Alertmanager receive it? Check its UI or `amtool alert query alertname=Watchdog --alertmanager.url=http://<alertmanager>:9093`.
4. Is the webhook failing? Look at `alertmanager_notifications_failed_total{integration="webhook"}` and the Alertmanager logs. Egress proxies and firewall changes are common culprits.
5. Check for a silence or inhibit rule that matches Watchdog: `amtool silence query alertname=Watchdog`.

## Fixing it

Restore whichever hop is broken, then confirm the heartbeat check turns green. Never silence Watchdog to "reduce noise"; route it away from humans instead.

## Related alerts

- [PrometheusNotConnectedToAlertmanagers](/runbooks/prometheusnotconnectedtoalertmanagers/): the most common reason the heartbeat disappears.
- [PrometheusErrorSendingAlertsToAlertmanager](/runbooks/prometheuserrorsendingalertstoalertmanager/): alerts leave Prometheus but do not arrive.
- [AlertmanagerFailedToSendAlerts](/runbooks/alertmanagerfailedtosendalerts/): Alertmanager cannot deliver to receivers.
