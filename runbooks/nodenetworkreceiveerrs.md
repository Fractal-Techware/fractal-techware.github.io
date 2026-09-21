---
title: "NodeNetworkReceiveErrs: runbook and fix"
description: "NodeNetworkReceiveErrs means a host network interface keeps reporting receive errors. How to find bad cables, NIC, MTU or driver problems and fix them."
permalink: /runbooks/nodenetworkreceiveerrs/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeNetworkReceiveErrs is one of 25 host alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodenetworkreceiveerrs
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeNetworkReceiveErrs

A physical or primary network interface on this host has been receiving a noticeable share of bad packets for a long time.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `netdev` collector |
| Key metrics | `node_network_receive_errs_total`, `node_network_receive_packets_total` |

## What it means

The kernel counts a receive error when a frame arrives damaged or cannot be accepted: CRC/frame errors, length errors, FIFO overruns and similar. The alert looks at errors as a fraction of received packets and fires only when that fraction stays elevated for an extended period. Virtual interfaces from container networking (veth, cali, flannel, cilium, docker bridges) are ignored.

Every errored frame is a lost packet. TCP recovers with retransmits, so the symptom is usually higher latency, lower throughput, and occasional timeouts rather than a clean outage.

## Common causes

- A damaged cable, dirty fibre, or failing transceiver/switch port.
- Speed or duplex mismatch between the NIC and the switch.
- MTU mismatch (jumbo frames on one side only).
- Receive ring buffer too small for bursts, causing overruns.
- NIC driver or firmware bugs, or a failing NIC.

## First checks

1. Find the worst interfaces across the fleet:
   ```promql
   topk(10, rate(node_network_receive_errs_total{device!~"lo|veth.*|cali.*"}[5m]))
   ```
2. Compare with drops, which point to buffer or CPU issues rather than wire damage:
   ```promql
   rate(node_network_receive_drop_total{instance="<instance>", device="<device>"}[5m])
   ```
3. Inspect the interface counters on the host:
   ```bash
   ip -s -s link show <device>
   ```
4. Get the detailed NIC statistics, link speed and duplex:
   ```bash
   sudo ethtool -S <device> | grep -iE "err|crc|fifo|over|miss" | grep -v ": 0"
   sudo ethtool <device> | grep -E "Speed|Duplex|Link detected"
   ```
5. Check ring buffer sizes and kernel messages:
   ```bash
   sudo ethtool -g <device>
   sudo dmesg -T | grep -i <device> | tail
   ```

## Fixing it

CRC and frame errors are almost always physical: reseat or replace the cable or optic, or move to another switch port, and check the switch-side counters. Fix speed/duplex or MTU mismatches on both ends. For overruns, enlarge the ring buffer (`ethtool -G <device> rx <size>`) and spread interrupts across CPUs. Update NIC firmware and driver if errors persist on known-good cabling. On cloud VMs, stop and start the instance to move it to other hardware.

## Related alerts

- [NodeNetworkTransmitErrs](/runbooks/nodenetworktransmiterrs/): the same interface failing on the send side.
- [NodeNetworkInterfaceFlapping](/runbooks/nodenetworkinterfaceflapping/): a bad link often flaps as well.
- [NodeExporterDown](/runbooks/nodeexporterdown/): severe packet loss can make scrapes fail.
