---
title: 'NodeFilesystemSpaceFillingUp: runbook and fix'
description: 'NodeFilesystemSpaceFillingUp runbook: find what is filling the disk (du, deleted open files, logs, images) before it hits 100%.'
permalink: /runbooks/nodefilesystemspacefillingup/
breadcrumb:
  title: Alert runbooks
  url: /runbooks/
domain: Hosts (node_exporter)
severity: warning, critical
free_rule: true
cta:
  title: Get the other 167 alerts, tested
  text: NodeFilesystemSpaceFillingUp is one of 12 free alerts. The full pack has 179 alerts across 20 domains, each with promtool unit tests and a runbook.
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodefilesystemspacefillingup
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeFilesystemSpaceFillingUp

Filesystem is predicted to run out of space within 24 hours. Free rule (MIT): the complete runbook and rule definition are below.

| | |
|---|---|
| Severity | critical, warning |
| Pending (`for:`) | 1h (warning), 1h (critical) |
| Domain | Hosts (node_exporter) |
| Requires | node_exporter 1.x (default collectors; systemd and hwmon noted per alert) |
| Rule file | [`rules/node-exporter.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/node-exporter.rules.yml) (group `ftw.node-exporter.alerts`) |

## Meaning

Free space is below the threshold AND a linear prediction over the last 6 hours says the filesystem will be full within the prediction horizon (24h for warning, 4h for critical).

## Impact

When the filesystem is full, writes fail - databases crash or go read-only, logs are lost, container images cannot be pulled.

## Diagnosis

- Trend of free space:
  ```promql
  node_filesystem_avail_bytes{instance="<instance>", mountpoint="<mountpoint>"}
  ```
- Find what is growing on the host:
  ```bash
  sudo du -xh --max-depth=2 <mountpoint> 2>/dev/null | sort -h | tail -20
  sudo find <mountpoint> -xdev -type f -size +500M -mmin -360 2>/dev/null
  ```
- Deleted-but-open files still consume space: `sudo lsof +L1 | sort -k7 -n | tail`.

## Mitigation

- Remove or rotate large logs (`journalctl --vacuum-size=500M`), prune old images (`docker system prune`, `crictl rmi --prune`).
- Restart the process holding deleted files open.
- Grow the volume (cloud volumes can be resized online; then `growpart` + `resize2fs`/`xfs_growfs`).

## Escalation

- **warning**: Notify the owning team's alert channel. Acknowledge within business hours; create a ticket if it cannot be resolved the same day. Escalate to critical handling if it trends toward the critical condition.
- **critical**: Page the on-call engineer immediately. If not acknowledged within 15 minutes, escalate to the secondary on-call. Open an incident channel when user impact is confirmed.

Owned by whoever operates the host (platform team for Kubernetes nodes, service owner for standalone VMs).

## Related alerts

- [NodeExporterDown](/runbooks/nodeexporterdown/): Host or node_exporter is down.
- [NodeFilesystemAlmostOutOfSpace](/runbooks/nodefilesystemalmostoutofspace/): Filesystem has less than 10% space left.
- [NodeHighCPUUsage](/runbooks/nodehighcpuusage/): Host CPU usage is above 90%.
- [NodeMemoryHighUtilization](/runbooks/nodememoryhighutilization/): Host memory utilisation is above 90%.
- [NodeFilesystemAlmostOutOfFiles](/runbooks/nodefilesystemalmostoutoffiles/): Filesystem has less than 10% inodes left.

## Rule definition

From [`rules/node-exporter.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/node-exporter.rules.yml) in the free repository (MIT). Unit tests for it are in [`tests/`](https://github.com/Fractal-Techware/prometheus-alert-rules/tree/main/tests).

{% raw %}```yaml
- alert: NodeFilesystemSpaceFillingUp
  expr: |-
    (
      node_filesystem_avail_bytes{fstype!="", fstype!~"tmpfs|ramfs|squashfs|overlay|nsfs|fuse.lxcfs|fuse.snapfuse", mountpoint!~"/run(/.*)?|/var/lib/kubelet/.+|/var/lib/docker/.+"} / node_filesystem_size_bytes{fstype!="", fstype!~"tmpfs|ramfs|squashfs|overlay|nsfs|fuse.lxcfs|fuse.snapfuse", mountpoint!~"/run(/.*)?|/var/lib/kubelet/.+|/var/lib/docker/.+"} * 100 < 15
    and
      predict_linear(node_filesystem_avail_bytes{fstype!="", fstype!~"tmpfs|ramfs|squashfs|overlay|nsfs|fuse.lxcfs|fuse.snapfuse", mountpoint!~"/run(/.*)?|/var/lib/kubelet/.+|/var/lib/docker/.+"}[6h], 24 * 3600) < 0
    and
      node_filesystem_readonly{fstype!="", fstype!~"tmpfs|ramfs|squashfs|overlay|nsfs|fuse.lxcfs|fuse.snapfuse", mountpoint!~"/run(/.*)?|/var/lib/kubelet/.+|/var/lib/docker/.+"} == 0
    )
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: Filesystem is predicted to run out of space within 24 hours.
    description: Filesystem {{ $labels.mountpoint }} ({{ $labels.device }}) on {{ $labels.instance }} has {{ $value | printf "%.1f" }}% free and, at the current rate, fills up within 24 hours.
    runbook_url: runbooks/node-exporter/NodeFilesystemSpaceFillingUp.md
- alert: NodeFilesystemSpaceFillingUp
  expr: |-
    (
      node_filesystem_avail_bytes{fstype!="", fstype!~"tmpfs|ramfs|squashfs|overlay|nsfs|fuse.lxcfs|fuse.snapfuse", mountpoint!~"/run(/.*)?|/var/lib/kubelet/.+|/var/lib/docker/.+"} / node_filesystem_size_bytes{fstype!="", fstype!~"tmpfs|ramfs|squashfs|overlay|nsfs|fuse.lxcfs|fuse.snapfuse", mountpoint!~"/run(/.*)?|/var/lib/kubelet/.+|/var/lib/docker/.+"} * 100 < 10
    and
      predict_linear(node_filesystem_avail_bytes{fstype!="", fstype!~"tmpfs|ramfs|squashfs|overlay|nsfs|fuse.lxcfs|fuse.snapfuse", mountpoint!~"/run(/.*)?|/var/lib/kubelet/.+|/var/lib/docker/.+"}[6h], 4 * 3600) < 0
    and
      node_filesystem_readonly{fstype!="", fstype!~"tmpfs|ramfs|squashfs|overlay|nsfs|fuse.lxcfs|fuse.snapfuse", mountpoint!~"/run(/.*)?|/var/lib/kubelet/.+|/var/lib/docker/.+"} == 0
    )
  for: 1h
  labels:
    severity: critical
  annotations:
    summary: Filesystem is predicted to run out of space within 4 hours.
    description: Filesystem {{ $labels.mountpoint }} ({{ $labels.device }}) on {{ $labels.instance }} has {{ $value | printf "%.1f" }}% free and, at the current rate, fills up within 4 hours.
    runbook_url: runbooks/node-exporter/NodeFilesystemSpaceFillingUp.md
```
{% endraw %}
