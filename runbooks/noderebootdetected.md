---
title: "NodeRebootDetected: runbook and fix"
description: "NodeRebootDetected means a host rebooted recently. How to tell a planned reboot from a crash, kernel panic or watchdog reset, and what to verify."
permalink: /runbooks/noderebootdetected/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: info
cta:
  title: Get this alert, tested
  text: "NodeRebootDetected is one of 179 tested alerts in the pack, with 25 covering hosts, each shipped with promtool unit tests and a runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=noderebootdetected
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeRebootDetected

The host's boot time changed, so it restarted within the last several minutes.

| | |
|---|---|
| Severity | info |
| Source | node_exporter 1.x, `stat` collector |
| Key metric | `node_boot_time_seconds` |

## What it means

`node_boot_time_seconds` is the Unix timestamp at which the kernel started. It stays constant while the host is up and jumps when it reboots. The alert fires when that value has changed recently.

It is informational: planned reboots for kernel updates are normal. It is worth a look when nobody expected it, when it repeats, or when it lines up with an outage, because an unexpected reboot usually means a crash, a hardware fault, or automation you did not know about.

## Common causes

- Automatic security updates rebooting the host (unattended-upgrades, dnf-automatic, kured on Kubernetes).
- Kernel panic, hardware watchdog reset, or a machine check exception.
- Power or hypervisor events: host maintenance, spot or preemptible instance reclaim, live migration failure.
- Severe memory exhaustion leading to a hang and a watchdog reboot.
- Someone ran `reboot` by hand.

## First checks

1. See which hosts rebooted and when:
   ```promql
   changes(node_boot_time_seconds[1h]) > 0
   ```
   `time() - node_boot_time_seconds` gives current uptime.
2. Confirm the reboot history on the host:
   ```bash
   last -x reboot shutdown | head
   journalctl --list-boots | tail -5
   ```
3. Read the end of the previous boot's journal. A clean shutdown shows systemd stopping units; a crash simply stops mid-stream:
   ```bash
   journalctl -b -1 -e --no-pager | tail -80
   ```
   This needs persistent journald storage (`/var/log/journal`).
4. Look for hardware or panic evidence:
   ```bash
   journalctl -k -b -1 | grep -iE "panic|mce|hardware error|watchdog|oom"
   ls /var/crash/ 2>/dev/null
   ```
5. Check your cloud or hypervisor console for maintenance or host failure events at that time.

## Fixing it

For planned reboots, nothing to fix; consider silencing during maintenance windows. For a crash, confirm workloads and time sync came back, then chase the cause: collect the kdump, update firmware or the kernel, or open a hardware ticket. Repeated reboots on one machine usually point to failing memory or power, so drain it.

## Related alerts

- [NodeExporterDown](/runbooks/nodeexporterdown/): fires while the host is down, before this one fires after it returns.
- [NodeMemoryHighUtilization](/runbooks/nodememoryhighutilization/): memory pressure before the reboot is a strong hint.
- [NodeTemperatureCritical](/runbooks/nodetemperaturecritical/): thermal shutdowns look like unexplained reboots.
