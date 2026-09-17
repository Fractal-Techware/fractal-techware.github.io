---
title: "PrometheusNotConnectedToAlertmanagers: runbook and fix"
description: "PrometheusNotConnectedToAlertmanagers means Prometheus has discovered no Alertmanager, so alerts go nowhere. How to find why and restore delivery."
permalink: /runbooks/prometheusnotconnectedtoalertmanagers/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "PrometheusNotConnectedToAlertmanagers is one of 20 Prometheus self-monitoring alerts in the pack of 179, each with promtool unit tests and a runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheusnotconnectedtoalertmanagers
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusNotConnectedToAlertmanagers

Prometheus currently knows about zero Alertmanagers, so every alert it fires is evaluated and then dropped on the floor.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metric | `prometheus_notifications_alertmanagers_discovered` |

## What it means

Prometheus finds Alertmanagers through the `alerting.alertmanagers` section of its config, using static targets or service discovery. The gauge counts how many it has discovered. The alert fires when that count has stayed at zero for several minutes.

Rules still evaluate and alerts still show as firing in the Prometheus UI, but nobody gets notified. Treat this as more urgent than its severity suggests. Note that this alert itself may not reach you through the broken path, which is why an external [Watchdog](/runbooks/watchdog/) heartbeat matters.

## Common causes

- The `alerting` block is missing or was lost in a config refactor or Helm values change.
- Kubernetes SD points at the wrong namespace, service name or port name, or relabeling drops every endpoint.
- Alertmanager pods are all down, so the Endpoints object is empty.
- RBAC: the Prometheus service account cannot list endpoints or endpointslices in the Alertmanager namespace.
- With the Operator, `spec.alerting.alertmanagers` references a service that does not exist.

## First checks

1. Ask Prometheus what it thinks it is connected to:
   ```bash
   curl -s http://<prometheus>:9090/api/v1/alertmanagers | jq '.data'
   ```
   Empty `activeAlertmanagers` with entries in `droppedAlertmanagers` points at relabeling.
2. Inspect the loaded alerting config in **Status → Configuration**, or:
   ```bash
   curl -s http://<prometheus>:9090/api/v1/status/config | jq -r '.data.yaml' | grep -A15 '^alerting:'
   ```
3. Check that Alertmanager has ready endpoints:
   ```bash
   kubectl -n monitoring get pods -l app.kubernetes.io/name=alertmanager
   kubectl -n monitoring get endpointslices -l kubernetes.io/service-name=<alertmanager-service>
   ```
4. Look for discovery or permission errors:
   ```bash
   kubectl -n monitoring logs <prometheus-pod> -c prometheus | grep -iE "alertmanager|forbidden"
   ```

## Fixing it

Restore the `alerting` config or fix the service and port names, grant the missing RBAC, or bring Alertmanager back. After a config change, validate with `promtool check config` and reload. Confirm the gauge is back to the expected number of Alertmanager replicas, then check that the Watchdog heartbeat resumed.

## Related alerts

- [PrometheusErrorSendingAlertsToAlertmanager](/runbooks/prometheuserrorsendingalertstoalertmanager/): Alertmanagers are discovered but sends fail.
- [PrometheusConfigReloadFailed](/runbooks/prometheusconfigreloadfailed/): the fixed alerting config may not be live yet.
- [AlertmanagerClusterDown](/runbooks/alertmanagerclusterdown/): the Alertmanager side of the same outage.
