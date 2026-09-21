---
title: "AlertmanagerFailedToSendAlerts: runbook and fix"
description: "AlertmanagerFailedToSendAlerts means notifications to Slack, PagerDuty, email or webhooks are failing. How to find the failing integration."
permalink: /runbooks/alertmanagerfailedtosendalerts/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Alertmanager self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "AlertmanagerFailedToSendAlerts ships in the pack of 179 alerts alongside 5 other Alertmanager checks, each with promtool unit tests and a runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=alertmanagerfailedtosendalerts
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# AlertmanagerFailedToSendAlerts

Alertmanager is receiving alerts but a noticeable share of its notification attempts to one integration are failing.

| | |
|---|---|
| Severity | warning |
| Source | Alertmanager's own `/metrics` (0.25+) |
| Key metrics | `alertmanager_notifications_failed_total`, `alertmanager_notifications_total` (label `integration`) |

## What it means

For every notification Alertmanager counts attempts and failures per integration (`slack`, `pagerduty`, `email`, `webhook`, `opsgenie` and so on). The alert fires when the failure ratio for an integration stays above a small fraction for several minutes.

Alertmanager retries, so some messages still get through late. But if failures are total for an integration, people routed only to that receiver are not being paged at all. Treat it as urgent if the failing integration is your paging path.

## Common causes

- Expired or revoked credentials: rotated Slack webhook URL, deleted PagerDuty integration key, changed SMTP password.
- Egress blocked: missing proxy settings, a new NetworkPolicy, firewall rules, or DNS failures resolving the API host.
- Rate limiting by the receiving service during an alert storm.
- TLS problems: corporate MITM proxy or a missing CA bundle in the container image.
- A webhook receiver that is down or returning 5xx.

## First checks

1. Identify the failing integration and instance:
   ```promql
   sum by (instance, integration) (rate(alertmanager_notifications_failed_total[5m]))
   ```
2. Read the exact error, which includes the receiver name and HTTP status:
   ```bash
   kubectl -n monitoring logs <alertmanager-pod> -c alertmanager | grep -i "notify" | tail -n 20
   ```
3. Test egress from inside the pod (if the image has a shell and wget):
   ```bash
   kubectl -n monitoring exec <alertmanager-pod> -c alertmanager -- wget -qO- -T 5 https://hooks.slack.com >/dev/null; echo $?
   ```
4. Send a test alert end to end:
   ```bash
   amtool alert add TestNotification severity=warning \
     --alertmanager.url=http://<alertmanager>:9093
   ```
5. Check the receiver config with `amtool check-config` if you recently changed credentials.

## Fixing it

Rotate or restore the credential, fix egress (proxy settings in `http_config`, NetworkPolicy, CA bundle), or raise `group_interval` and grouping to reduce volume if you are rate limited. Keep a second, independent notification path for critical alerts.

## Related alerts

- [AlertmanagerFailedReload](/runbooks/alertmanagerfailedreload/): a credential fix that did not load leaves failures in place.
- [AlertmanagerClusterDown](/runbooks/alertmanagerclusterdown/): no instances left to send anything.
- [PrometheusNotConnectedToAlertmanagers](/runbooks/prometheusnotconnectedtoalertmanagers/): the step before delivery, Prometheus to Alertmanager.
