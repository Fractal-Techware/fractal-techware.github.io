---
title: 'NodeExporterDown: runbook and fix'
description: 'NodeExporterDown runbook: tell a dead host from a stopped node_exporter or a broken scrape, with the checks for each case.'
permalink: /runbooks/nodeexporterdown/
breadcrumb:
  title: Alert runbooks
  url: /runbooks/
domain: Hosts (node_exporter)
severity: critical
free_rule: true
cta:
  title: Get the other 167 alerts, tested
  text: NodeExporterDown is one of 12 free alerts. The full pack has 179 alerts across 20 domains, each with promtool unit tests and a runbook.
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodeexporterdown
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeExporterDown

Host or node_exporter is down. Free rule (MIT): the complete runbook and rule definition are below.

| | |
|---|---|
| Severity | critical |
| Pending (`for:`) | 5m (critical) |
| Domain | Hosts (node_exporter) |
| Requires | node_exporter 1.x (default collectors; systemd and hwmon noted per alert) |
| Rule file | [`rules/node-exporter.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/node-exporter.rules.yml) (group `ftw.node-exporter.alerts`) |

## Meaning

Prometheus cannot scrape node_exporter on the host. Either the host is down, the exporter stopped, or the network path between Prometheus and the host is broken.

## Impact

All host alerts for this instance are blind. If the host itself is down, everything running on it is unavailable.

## Diagnosis

- Check the scrape error in Prometheus: **Status → Targets**, or
  ```promql
  up{instance="<instance>"}
  ```
- Is the host reachable? `ping <host>` / `curl -s http://<host>:9100/metrics | head`.
- On the host: `systemctl status node_exporter` (Kubernetes: `kubectl -n monitoring get pods -o wide | grep node-exporter`).

## Mitigation

- Restart node_exporter or the host.
- Fix firewall/security-group rules for port 9100.
- If the host was intentionally removed, remove it from service discovery / file_sd targets.

## Escalation

- **critical**: Page the on-call engineer immediately. If not acknowledged within 15 minutes, escalate to the secondary on-call. Open an incident channel when user impact is confirmed.

Owned by whoever operates the host (platform team for Kubernetes nodes, service owner for standalone VMs).

## Related alerts

- [NodeFilesystemSpaceFillingUp](/runbooks/nodefilesystemspacefillingup/): Filesystem is predicted to run out of space within 24 hours.
- [NodeFilesystemAlmostOutOfSpace](/runbooks/nodefilesystemalmostoutofspace/): Filesystem has less than 10% space left.
- [NodeHighCPUUsage](/runbooks/nodehighcpuusage/): Host CPU usage is above 90%.
- [NodeMemoryHighUtilization](/runbooks/nodememoryhighutilization/): Host memory utilisation is above 90%.
- [NodeFilesystemAlmostOutOfFiles](/runbooks/nodefilesystemalmostoutoffiles/): Filesystem has less than 10% inodes left.

## Rule definition

From [`rules/node-exporter.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/node-exporter.rules.yml) in the free repository (MIT). Unit tests for it are in [`tests/`](https://github.com/Fractal-Techware/prometheus-alert-rules/tree/main/tests).

{% raw %}```yaml
- alert: NodeExporterDown
  expr: up{job=~"node|node-exporter|node_exporter|prometheus-node-exporter"} == 0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: Host or node_exporter is down.
    description: node_exporter target {{ $labels.instance }} (job {{ $labels.job }}) has been unreachable for 5m.
    runbook_url: runbooks/node-exporter/NodeExporterDown.md
```
{% endraw %}
