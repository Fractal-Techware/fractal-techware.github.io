---
title: "AlertmanagerClusterDown: runbook and fix"
description: "AlertmanagerClusterDown means half or more Alertmanager replicas are unreachable, so notifications are at risk. How to restore the cluster."
permalink: /runbooks/alertmanagerclusterdown/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Alertmanager self-monitoring
severity: critical
cta:
  title: Get this alert, tested
  text: "AlertmanagerClusterDown is one of 6 Alertmanager alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=alertmanagerclusterdown
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# AlertmanagerClusterDown

Half or more of the Alertmanager replicas in a cluster are failing their Prometheus scrapes.

| | |
|---|---|
| Severity | critical |
| Source | Prometheus scrape of Alertmanager |
| Key metric | `up` for the Alertmanager job |

## What it means

Prometheus scrapes each Alertmanager replica. When at least half of a cluster's instances have been down for most of the recent window, the alert fires. A single replica outage in a three-node cluster does not trigger it; losing a majority does.

With most replicas gone, notification delivery depends on the survivors. If all are down, alerts are queued in Prometheus and nobody is paged. Note that this alert may itself not be delivered, which is why an external dead man's switch matters.

## Common causes

- Pods evicted or stuck `Pending` (node pressure, insufficient resources, PVC for the data volume not bound).
- A bad config or image upgrade that prevents startup on every replica.
- All replicas scheduled on the same node or zone that just failed (no anti-affinity).
- Scrape-side problems only: changed port name, ServiceMonitor selector mismatch, NetworkPolicy blocking Prometheus.
- OOM kills during a large alert storm.

## First checks

1. Confirm which instances are down:
   ```promql
   up{job=~".*alertmanager.*"} == 0
   ```
2. Check pod state and recent events:
   ```bash
   kubectl -n monitoring get pods -l app.kubernetes.io/name=alertmanager -o wide
   kubectl -n monitoring describe pod <alertmanager-pod> | tail -n 30
   ```
3. Look at logs from the previous container if it restarted:
   ```bash
   kubectl -n monitoring logs <alertmanager-pod> -c alertmanager --previous
   ```
4. If pods look healthy, test the scrape path directly:
   ```bash
   kubectl -n monitoring port-forward <alertmanager-pod> 9093 &
   curl -s localhost:9093/-/healthy
   ```
   Then check the target's error in Prometheus under **Status > Targets**.

## Fixing it

Restore capacity first: free node resources, fix the PVC, or roll back the config or image that broke startup. If only scraping is broken, fix the ServiceMonitor or NetworkPolicy. Afterwards, add pod anti-affinity or topology spread constraints and a PodDisruptionBudget.

## Related alerts

- [AlertmanagerClusterCrashlooping](/runbooks/alertmanagerclustercrashlooping/): replicas restarting rather than staying down.
- [AlertmanagerMembersInconsistent](/runbooks/alertmanagermembersinconsistent/): survivors will report missing peers.
- [PrometheusNotConnectedToAlertmanagers](/runbooks/prometheusnotconnectedtoalertmanagers/): Prometheus has no Alertmanager left to send to.
