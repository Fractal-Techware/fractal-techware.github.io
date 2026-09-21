---
title: "NodeClockNotSynchronising: runbook and fix"
description: "NodeClockNotSynchronising means a host has stopped syncing its clock with NTP. How to check chrony or timesyncd and restore time sync."
permalink: /runbooks/nodeclocknotsynchronising/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeClockNotSynchronising is one of 25 host alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodeclocknotsynchronising
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeClockNotSynchronising

The kernel on this host reports that its clock is no longer being disciplined by a time source, so it will slowly drift.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `timex` collector (Linux, enabled by default) |
| Key metrics | `node_timex_sync_status`, `node_timex_maxerror_seconds` |

## What it means

node_exporter reads the kernel's `adjtimex` state. `node_timex_sync_status` is 1 while an NTP daemon (chrony, ntpd, systemd-timesyncd) is actively steering the clock and 0 when it is not. The alert fires when the host has reported "unsynchronised" continuously for several minutes and the kernel's own maximum error estimate has grown large, which rules out a brief blip during a daemon restart.

Nothing breaks immediately, but the clock is now free-running. Over hours or days that drift turns into TLS validation failures, rejected tokens (Kerberos, JWT, AWS request signing), confusing log timelines and, for distributed databases, consistency problems. Treat it as a chance to fix time before [NodeClockSkewDetected](/runbooks/nodeclockskewdetected/) fires.

## Common causes

- The NTP daemon is stopped, crashed, or was never enabled on a newly built image.
- Outbound UDP 123 is blocked by a firewall or security group, so no server is reachable.
- The configured NTP servers are wrong, retired, or not resolvable from this network.
- Two time daemons fighting each other (for example chrony and systemd-timesyncd both enabled).
- Containers or VMs where time is meant to come from the hypervisor but the guest tools are missing.

## First checks

1. See which hosts are affected:
   ```promql
   node_timex_sync_status == 0
   ```
2. Ask the OS what it thinks:
   ```bash
   timedatectl status
   ```
   Look at "System clock synchronized" and "NTP service".
3. If chrony is in use, check that it has a selected source (marked `*`):
   ```bash
   chronyc tracking
   chronyc sources -v
   ```
   For systemd-timesyncd use `timedatectl timesync-status`; for ntpd use `ntpq -p`.
4. Confirm the daemon is running and see why it is not syncing:
   ```bash
   systemctl status chronyd systemd-timesyncd ntpd 2>/dev/null
   journalctl -u chronyd -b --no-pager | tail -50
   ```
5. Test reachability of a server: `chronyc -n sources` showing `?` for every source usually points to a network or DNS problem.

## Fixing it

Run exactly one time daemon, point it at reachable servers (your cloud provider's endpoint is usually best), open UDP 123 outbound, then restart it. If the clock is already far off, `chronyc makestep` corrects it immediately instead of slewing slowly. Bake the working configuration into your base image so new hosts do not repeat the problem.

## Related alerts

- [NodeClockSkewDetected](/runbooks/nodeclockskewdetected/): the drift has become measurable and is not converging.
- [NodeRebootDetected](/runbooks/noderebootdetected/): a reboot can leave the daemon disabled or not yet synced.
- [NodeExporterDown](/runbooks/nodeexporterdown/): if the host stops reporting entirely, the timex data goes with it.
