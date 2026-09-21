---
title: "NodeClockSkewDetected: runbook and fix"
description: "NodeClockSkewDetected means a host clock is offset from its time source and not converging. How to measure the skew and correct it safely."
permalink: /runbooks/nodeclockskewdetected/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeClockSkewDetected ships in the pack of 179 alerts alongside 24 other host alerts, all with promtool unit tests and runbooks."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodeclockskewdetected
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeClockSkewDetected

This host's clock is noticeably off from its reference time and the gap is holding steady or getting worse.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `timex` collector |
| Key metric | `node_timex_offset_seconds` |

## What it means

`node_timex_offset_seconds` is the kernel's current estimate of how far the local clock is from the time source the NTP daemon is tracking. A healthy host sits within a few milliseconds. The alert fires when the offset stays beyond tens of milliseconds for several minutes and is moving away from zero rather than back towards it. A skew that is shrinking means correction is working, so it is deliberately ignored.

Skew matters for anything that compares timestamps across machines: distributed locks and leases, database replication, certificate and token validity windows, and log correlation during incidents. Prometheus itself will also store samples from this host with slightly wrong timing.

## Common causes

- The time daemon lost all its sources and is free-running (often alongside [NodeClockNotSynchronising](/runbooks/nodeclocknotsynchronising/)).
- The daemon is configured to only slew, and the initial offset after boot or VM resume was large.
- A VM was paused, live-migrated, or restored from a snapshot.
- Heavy CPU steal or a bad clocksource on the hypervisor makes the clock tick unevenly.
- A single upstream NTP server is itself wrong and there is no quorum to outvote it.

## First checks

1. Compare hosts to spot outliers:
   ```promql
   sort_desc(abs(node_timex_offset_seconds))
   ```
2. Cross-check against the Prometheus server's own clock (rough, includes scrape delay):
   ```promql
   abs(time() - node_time_seconds) > 1
   ```
3. On the host, see the offset, frequency error and the chosen source:
   ```bash
   chronyc tracking
   chronyc sourcestats
   ```
4. Check which clocksource the kernel uses (look for unexpected `jiffies` or warnings about unstable TSC):
   ```bash
   cat /sys/devices/system/clocksource/clocksource0/current_clocksource
   dmesg | grep -i clocksource
   ```
5. Confirm there are at least three usable upstream servers in `/etc/chrony.conf` or `/etc/chrony/chrony.conf`.

## Fixing it

Restore healthy sources first, then correct the offset. With chrony, `chronyc makestep` steps the clock immediately; set `makestep` in the config so large offsets are stepped at startup. Be careful stepping time on database or consensus nodes: drain or fence them first if the jump is large. For VMs, install the guest agent or use the hypervisor's PTP/NTP source.

## Related alerts

- [NodeClockNotSynchronising](/runbooks/nodeclocknotsynchronising/): the root cause when no source is steering the clock.
- [NodeRebootDetected](/runbooks/noderebootdetected/): skew right after boot is common before the first sync.
- [NodeHighCPUUsage](/runbooks/nodehighcpuusage/): a starved host can delay the time daemon.
