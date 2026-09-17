---
title: "NodeTemperatureCritical: runbook and fix"
description: "NodeTemperatureCritical means a hardware sensor on a host has raised its critical temperature alarm. How to find the sensor and cool the machine."
permalink: /runbooks/nodetemperaturecritical/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeTemperatureCritical is one of 25 node_exporter alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodetemperaturecritical
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeTemperatureCritical

A CPU, disk, or board sensor reports that it has crossed its own critical temperature threshold.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `hwmon` collector (bare metal; most cloud VMs expose no sensors) |
| Key metrics | `node_hwmon_temp_crit_alarm_celsius`, `node_hwmon_temp_celsius`, `node_hwmon_temp_crit_celsius` (labels `chip`, `sensor`) |

## What it means

The hwmon collector reads sensors from `/sys/class/hwmon`. Many drivers expose a critical alarm flag that the chip itself sets when the reading passes the manufacturer's critical limit. The alert fires when that flag has stayed raised for a few minutes. Because the threshold comes from the hardware, you do not need to guess what "too hot" means for each part.

Expect the CPU to throttle, which shows up as unexplained slowness. If the temperature keeps rising, the firmware will power the machine off to protect it, and sustained heat shortens the life of disks and capacitors.

## Common causes

- A failed or slowed fan, or a fan profile set to "quiet" in the BIOS/BMC.
- Blocked airflow: dust, missing blanking panels, cables in front of intakes, a door closed on a small rack.
- Datacenter or room cooling failure (several hosts alert together).
- Dried thermal paste or a loose heatsink after hardware work.
- Sustained full load on a machine that was never sized for it.
- A buggy sensor driver reporting a bogus alarm (only one sensor, value looks normal).

## First checks

1. See every sensor in alarm, then compare readings with their limits:
   ```promql
   node_hwmon_temp_crit_alarm_celsius == 1
   ```
   ```promql
   node_hwmon_temp_celsius * on(instance, chip, sensor) group_left() (node_hwmon_temp_crit_alarm_celsius == 1)
   ```
2. Map cryptic chip labels to driver names:
   ```promql
   node_hwmon_chip_names
   ```
3. Read the sensors directly on the host (lm-sensors):
   ```bash
   sensors
   ```
   On servers with a BMC, `sudo ipmitool sdr type Temperature` and `sudo ipmitool sdr type Fan` show chassis sensors and fan speeds.
4. Check whether the CPU is already throttling:
   ```promql
   rate(node_cpu_core_throttles_total[5m]) > 0
   ```
   ```bash
   dmesg -T | grep -iE "temperature above threshold|throttl"
   ```
5. Check neighbouring hosts in the same rack; if they are all warm, the problem is the room, not the server.

## Fixing it

Reduce heat first: drain or migrate workloads off the host. Then fix the cause on site: replace failed fans, clear airflow, raise the fan profile in the BMC, or escalate a cooling failure to facilities. If a single sensor alarms with a plausible reading, check for a firmware or kernel driver update before ignoring it.

## Related alerts

- [NodeHighCPUUsage](/runbooks/nodehighcpuusage/): sustained load drives CPU temperature up.
- [NodeRebootDetected](/runbooks/noderebootdetected/): a thermal shutdown shows up as an unexpected reboot.
- [NodeExporterDown](/runbooks/nodeexporterdown/): a host that powered itself off stops reporting.
