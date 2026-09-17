---
title: "AlertmanagerClusterCrashlooping: runbook and fix"
description: "AlertmanagerClusterCrashlooping means half or more Alertmanager replicas keep restarting. How to find the crash cause and stabilise the cluster."
permalink: /runbooks/alertmanagerclustercrashlooping/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Alertmanager self-monitoring
severity: critical
cta:
  title: Get this alert, tested
  text: "AlertmanagerClusterCrashlooping is included with 5 other Alertmanager alerts in the pack of 179, all with promtool unit tests and runbooks."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=alertmanagerclustercrashlooping
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# AlertmanagerClusterCrashlooping

A majority of Alertmanager replicas in a cluster are restarting over and over.

| | |
|---|---|
| Severity | critical |
| Source | Alertmanager's own `/metrics` and Prometheus `up` |
| Key metrics | `process_start_time_seconds`, `up` |

## What it means

Each time the Alertmanager process starts, `process_start_time_seconds` changes. The alert fires when that value changes repeatedly within a short window on at least half of a cluster's replicas.

Restarting replicas lose in-flight notification state between the moments they are up, may re-send notifications, and keep leaving and rejoining the gossip mesh. Even if `up` looks mostly fine because each pod comes back quickly, delivery is unreliable.

## Common causes

- Memory limits too low: OOM kills during alert storms or with many silences.
- Liveness probe too aggressive (short timeout on `/-/healthy`) under load.
- Corrupt or unreadable data directory (`nflog` or `silences` snapshot), or a read-only volume.
- Invalid config or templates that make startup fail after an image upgrade.
- Wrong flags after a version bump, for example removed or renamed command-line options.

## First checks

1. See restart frequency per instance:
   ```promql
   changes(process_start_time_seconds{job=~".*alertmanager.*"}[30m])
   ```
2. Find why the container exited:
   ```bash
   kubectl -n monitoring get pods -l app.kubernetes.io/name=alertmanager
   kubectl -n monitoring get pod <alertmanager-pod> \
     -o jsonpath='{.status.containerStatuses[*].lastState.terminated}'
   ```
   `OOMKilled` or an exit code points you in the right direction.
3. Read logs from the crashed container:
   ```bash
   kubectl -n monitoring logs <alertmanager-pod> -c alertmanager --previous | tail -n 40
   ```
4. Check memory against limits:
   ```promql
   max by (pod) (container_memory_working_set_bytes{container="alertmanager"})
   ```
5. Validate the config: `amtool check-config <file>`.

## Fixing it

For OOM, raise the memory limit and reduce alert volume (grouping, inhibition). For probe kills, relax the liveness timeout. For startup errors, roll back the config or image. If a snapshot file is corrupt, remove it from the data volume of that replica; silences are re-synced from healthy peers.

## Related alerts

- [AlertmanagerClusterDown](/runbooks/alertmanagerclusterdown/): when restarts turn into sustained downtime.
- [AlertmanagerFailedReload](/runbooks/alertmanagerfailedreload/): a bad config that was rejected live can crash pods on restart.
- [AlertmanagerMembersInconsistent](/runbooks/alertmanagermembersinconsistent/): gossip membership churns during crash loops.
