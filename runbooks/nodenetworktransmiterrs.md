---
title: "NodeNetworkTransmitErrs: runbook and fix"
description: "NodeNetworkTransmitErrs means a host network interface keeps failing to send packets. How to diagnose carrier, duplex, driver and queue problems."
permalink: /runbooks/nodenetworktransmiterrs/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeNetworkTransmitErrs is included in the pack of 179 Prometheus alerts, next to 24 other host alerts, each with unit tests and a runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodenetworktransmiterrs
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeNetworkTransmitErrs

A network interface on this host has been failing to send a meaningful share of its packets for a sustained period.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `netdev` collector |
| Key metrics | `node_network_transmit_errs_total`, `node_network_transmit_packets_total` |

## What it means

Transmit errors are counted when the NIC or driver cannot put a frame on the wire: carrier lost mid-send, collisions on a half-duplex link, aborted or timed-out transmissions. The alert fires when errors remain a clear fraction of sent packets for a long time, and it ignores container virtual interfaces.

Outgoing traffic is being lost and retried, so services on this host respond slowly and replication or backups can fall behind. Transmit errors are less common than receive errors, so a persistent rate is worth taking seriously.

## Common causes

- Half-duplex or speed mismatch, causing collisions.
- Link losing carrier: bad cable, optic or switch port.
- NIC driver or firmware bugs, including transmit queue timeouts.
- A failing NIC or overheating hardware.
- Bonding or VLAN misconfiguration sending on an inactive slave.

## First checks

1. Find the affected interfaces:
   ```promql
   topk(10, rate(node_network_transmit_errs_total{device!~"lo|veth.*|cali.*"}[5m]))
   ```
2. Check drops and carrier changes on the same device:
   ```promql
   rate(node_network_transmit_drop_total{instance="<instance>", device="<device>"}[5m])
   increase(node_network_carrier_changes_total{instance="<instance>", device="<device>"}[1h])
   ```
3. Look at the detailed counters (`carrier`, `collsns`, `aborted`):
   ```bash
   ip -s -s link show <device>
   sudo ethtool -S <device> | grep -iE "tx_.*(err|abort|timeout|carrier)" | grep -v ": 0"
   ```
4. Verify negotiated speed and duplex:
   ```bash
   sudo ethtool <device> | grep -E "Speed|Duplex|Auto-negotiation"
   ```
5. Look for driver resets and transmit timeouts:
   ```bash
   sudo dmesg -T | grep -iE "<device>|tx timeout|transmit queue" | tail
   ```
6. For bonds, check which slave is active and healthy:
   ```bash
   cat /proc/net/bonding/<bond>
   ```

## Fixing it

Force matching speed and full duplex on both the host and the switch, or re-enable autonegotiation on both. Replace cables, optics or switch ports that show carrier losses. Upgrade the NIC driver and firmware if you see transmit timeouts. Fix bonding mode or remove the failing slave. On a cloud VM, stop/start to land on different hardware.

## Related alerts

- [NodeNetworkReceiveErrs](/runbooks/nodenetworkreceiveerrs/): check whether the receive side is also affected.
- [NodeNetworkInterfaceFlapping](/runbooks/nodenetworkinterfaceflapping/): carrier loss often shows up as flapping.
- [NodeConntrackLimit](/runbooks/nodeconntracklimit/): a different cause of lost connections on busy hosts.
