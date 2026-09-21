---
title: "AlertmanagerConfigInconsistent: runbook and fix"
description: "AlertmanagerConfigInconsistent means replicas in one Alertmanager cluster run different configs, so routing depends on which one answers."
permalink: /runbooks/alertmanagerconfiginconsistent/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Alertmanager self-monitoring
severity: critical
cta:
  title: Get this alert, tested
  text: "AlertmanagerConfigInconsistent is part of a pack of 179 Prometheus alerts, 6 of them for Alertmanager, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=alertmanagerconfiginconsistent
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# AlertmanagerConfigInconsistent

Alertmanager replicas that belong to the same cluster are not running the same configuration.

| | |
|---|---|
| Severity | critical |
| Source | Alertmanager's own `/metrics` (0.25+) |
| Key metric | `alertmanager_config_hash` (hash of the loaded config, one series per instance) |

## What it means

Every instance exposes a hash of the configuration it has loaded. In a healthy HA setup all replicas report the same value. The alert fires when more than one distinct hash exists within a cluster for longer than a normal rolling update would take.

Because Prometheus sends every alert to every replica, and the replicas deduplicate via gossip, differing configs lead to unpredictable behaviour: an alert may be routed to the old receiver by one replica and the new one by another, or be delivered twice.

## Common causes

- One replica failed to reload the new config and kept the old one.
- A config-reloader sidecar that is stuck or crashed on one pod.
- A rollout that has stalled halfway (PodDisruptionBudget, pending pod, image pull error).
- Replicas managed by different deployment tools or Helm releases that share a cluster label.
- ConfigMap or Secret propagation delay to one node, which normally resolves within a minute or two.

## First checks

1. See which instance holds which hash (table view makes the odd one out obvious):
   ```promql
   max by (job, instance) (alertmanager_config_hash)
   ```
2. Check reload status on the odd instance:
   ```promql
   alertmanager_config_last_reload_successful
   ```
3. Compare the running config of two replicas:
   ```bash
   amtool config show --alertmanager.url=http://<replica-a>:9093 > a.yml
   amtool config show --alertmanager.url=http://<replica-b>:9093 > b.yml
   diff a.yml b.yml
   ```
4. Check rollout and sidecar health:
   ```bash
   kubectl -n monitoring get pods -l app.kubernetes.io/name=alertmanager
   kubectl -n monitoring logs <alertmanager-pod> -c config-reloader --tail=50
   ```

## Fixing it

Fix whatever blocked the reload (usually an invalid file, see AlertmanagerFailedReload), then trigger `POST /-/reload` on the stale replica or restart it. If the rollout is stuck, resolve the pending pod. Make sure all replicas are fed from a single source of config.

## Related alerts

- [AlertmanagerFailedReload](/runbooks/alertmanagerfailedreload/): the most common root cause.
- [AlertmanagerMembersInconsistent](/runbooks/alertmanagermembersinconsistent/): cluster membership problems that compound config drift.
- [AlertmanagerClusterCrashlooping](/runbooks/alertmanagerclustercrashlooping/): restarting replicas may come back with a different file.
