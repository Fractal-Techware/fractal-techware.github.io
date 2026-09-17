---
title: 'NodeMemoryHighUtilization: runbook and fix'
description: 'NodeMemoryHighUtilization runbook: find what is using host memory above 90%, check for leaks and avoid the OOM killer.'
permalink: /runbooks/nodememoryhighutilization/
breadcrumb:
  title: Alert runbooks
  url: /runbooks/
domain: Hosts (node_exporter)
severity: warning
free_rule: true
cta:
  title: Get the other 167 alerts, tested
  text: NodeMemoryHighUtilization is one of 12 free alerts. The full pack has 179 alerts across 20 domains, each with promtool unit tests and a runbook.
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodememoryhighutilization
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeMemoryHighUtilization

Host memory utilisation is above 90%. Free rule (MIT): the complete runbook and rule definition are below.

| | |
|---|---|
| Severity | warning |
| Pending (`for:`) | 15m (warning) |
| Domain | Hosts (node_exporter) |
| Requires | node_exporter 1.x (default collectors; systemd and hwmon noted per alert) |
| Rule file | [`rules/node-exporter.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/node-exporter.rules.yml) (group `ftw.node-exporter.alerts`) |

## Meaning

Less than 10% of memory is available (MemAvailable accounts for reclaimable page cache).

## Impact

Risk of the kernel OOM killer terminating processes, heavy page-cache eviction and swapping.

## Diagnosis

- On the host: `free -m`, `ps aux --sort=-rss | head`, `smem -tk` if installed.
- ```promql
  node_memory_MemAvailable_bytes{instance="<instance>"}
  ```
- Kubernetes: `kubectl top pods -A --sort-by=memory | head`.

## Mitigation

- Restart or limit the leaking process; set memory limits on containers.
- Add memory (bigger instance) or move workloads away.

## Escalation

- **warning**: Notify the owning team's alert channel. Acknowledge within business hours; create a ticket if it cannot be resolved the same day. Escalate to critical handling if it trends toward the critical condition.

Owned by whoever operates the host (platform team for Kubernetes nodes, service owner for standalone VMs).

## Related alerts

- [NodeExporterDown](/runbooks/nodeexporterdown/): Host or node_exporter is down.
- [NodeFilesystemSpaceFillingUp](/runbooks/nodefilesystemspacefillingup/): Filesystem is predicted to run out of space within 24 hours.
- [NodeFilesystemAlmostOutOfSpace](/runbooks/nodefilesystemalmostoutofspace/): Filesystem has less than 10% space left.
- [NodeHighCPUUsage](/runbooks/nodehighcpuusage/): Host CPU usage is above 90%.
- [NodeFilesystemAlmostOutOfFiles](/runbooks/nodefilesystemalmostoutoffiles/): Filesystem has less than 10% inodes left.

## Rule definition

From [`rules/node-exporter.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/node-exporter.rules.yml) in the free repository (MIT). Unit tests for it are in [`tests/`](https://github.com/Fractal-Techware/prometheus-alert-rules/tree/main/tests).

{% raw %}```yaml
- alert: NodeMemoryHighUtilization
  expr: 100 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100) > 90
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: Host memory utilisation is above 90%.
    description: Memory utilisation on {{ $labels.instance }} is {{ $value | printf "%.1f" }}%.
    runbook_url: runbooks/node-exporter/NodeMemoryHighUtilization.md
```
{% endraw %}
