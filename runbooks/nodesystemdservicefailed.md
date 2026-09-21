---
title: "NodeSystemdServiceFailed: runbook and fix"
description: "NodeSystemdServiceFailed means a systemd unit on a host is stuck in the failed state. How to find the unit, read its logs and recover it."
permalink: /runbooks/nodesystemdservicefailed/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeSystemdServiceFailed is one of 25 node_exporter alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodesystemdservicefailed
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeSystemdServiceFailed

A systemd unit on this host has failed and systemd has given up restarting it.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `systemd` collector (disabled by default, enable with `--collector.systemd`) |
| Key metric | `node_systemd_unit_state{state="failed"}` (labels `name`, `instance`) |

## What it means

The systemd collector exports one series per unit and state, set to 1 for the unit's current state. The alert fires when a unit has been sitting in `failed` for a while, which filters out services that fail once and are restarted successfully. The `name` label tells you which unit.

A failed unit can be anything from a critical daemon (your app, kubelet, containerd, a backup agent) to a harmless one-shot job. Either way, whatever that unit was supposed to do is not happening.

## Common causes

- The process exited non-zero repeatedly and hit `StartLimitBurst`, so systemd stopped retrying.
- A bad configuration file after a deploy or package upgrade.
- A dependency is missing: a mount, a network target, a secret file, or another unit.
- The service was OOM-killed or hit a resource limit set in the unit file.
- A `Type=oneshot` timer job (certificate renewal, log rotation, backups) exited with an error.

## First checks

1. List failed units across the fleet:
   ```promql
   node_systemd_unit_state{state="failed"} == 1
   ```
2. On the host, confirm and see the exit status:
   ```bash
   systemctl --failed
   systemctl status <unit>
   ```
3. Read the logs from the current boot, around the failure:
   ```bash
   journalctl -u <unit> -b --no-pager | tail -100
   ```
4. Check whether the kernel killed it:
   ```bash
   journalctl -k -b | grep -iE "oom|killed process"
   ```
5. Validate the unit file and any config it loads, for example `systemd-analyze verify /etc/systemd/system/<unit>` or the daemon's own config test (`nginx -t`, `sshd -t`).

## Fixing it

Fix the underlying error first, then run `systemctl restart <unit>`. If the unit was rate-limited, `systemctl reset-failed <unit>` clears the counter. For one-shot jobs that are expected to fail occasionally, fix the job or add `Restart=on-failure` with a sensible delay. If a unit is obsolete, disable it and run `systemctl reset-failed` so it stops reporting. To reduce cardinality, restrict the collector with `--collector.systemd.unit-include`.

## Related alerts

- [NodeOOMKillDetected](/runbooks/nodeoomkilldetected/): the service may have been killed for memory.
- [NodeTextFileCollectorError](/runbooks/nodetextfilecollectorerror/): a failed timer job often leaves a broken metrics file behind.
- [NodeRebootDetected](/runbooks/noderebootdetected/): units that fail right after boot usually have dependency ordering problems.
