---
title: "NodeNetworkInterfaceFlapping: runbook and fix"
description: "NodeNetworkInterfaceFlapping means a host network interface keeps going up and down. How to find the bad link, driver or config and stop the flapping."
permalink: /runbooks/nodenetworkinterfaceflapping/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeNetworkInterfaceFlapping is one of 25 node_exporter host alerts in the pack of 179, every one unit tested with promtool and documented."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodenetworkinterfaceflapping
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeNetworkInterfaceFlapping

A network interface on this host is repeatedly changing between up and down within a short time.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `netclass` collector |
| Key metric | `node_network_up` (label `device`) |

## What it means

`node_network_up` is 1 when the interface's operational state is up. The alert fires when that value changes several times within a couple of minutes and keeps doing so, which rules out a single planned restart. Container virtual interfaces, which come and go with pods, are excluded.

Each transition drops traffic on that link. Connections reset, bonds fail over back and forth, and Kubernetes nodes may bounce between Ready and NotReady. Because scrapes happen at intervals, the real number of flaps is often higher than Prometheus shows.

## Common causes

- A loose or damaged cable, bad optic, or failing switch port.
- Autonegotiation fighting between NIC and switch.
- NIC driver or firmware resetting the device (watchdog or transmit timeouts).
- Power management (EEE, ASPM) putting the link to sleep.
- Something repeatedly reconfiguring the interface: NetworkManager, netplan, a DHCP client or a CNI plugin.

## First checks

1. See how often each interface changed state recently:
   ```promql
   sort_desc(changes(node_network_up{device!~"lo|veth.*|cali.*"}[1h]) > 0)
   ```
2. The kernel carrier counters catch flaps between scrapes:
   ```promql
   increase(node_network_carrier_changes_total{instance="<instance>", device="<device>"}[1h])
   ```
3. Watch link events live on the host:
   ```bash
   ip monitor link
   ```
4. Check kernel and network manager logs for link down/up and resets:
   ```bash
   sudo journalctl -k --since "1 hour ago" | grep -iE "<device>|link (is )?(up|down)|reset"
   sudo journalctl -u NetworkManager -u systemd-networkd --since "1 hour ago" | tail -30
   ```
5. Check link settings and error counters:
   ```bash
   sudo ethtool <device>
   sudo ethtool --show-eee <device>
   ```

## Fixing it

If the kernel shows carrier loss, treat it as physical: swap cable or optic, try another switch port, check the switch logs for the port. If the driver is resetting, update driver and firmware or disable EEE (`ethtool --set-eee <device> eee off`). If userspace is reconfiguring the link, fix the conflicting network manager or DHCP setup so only one tool owns the interface.

## Related alerts

- [NodeNetworkReceiveErrs](/runbooks/nodenetworkreceiveerrs/): a degrading link usually corrupts frames too.
- [NodeNetworkTransmitErrs](/runbooks/nodenetworktransmiterrs/): carrier loss during sends.
- [NodeExporterDown](/runbooks/nodeexporterdown/): the host becomes unreachable while the link is down.
- [KubeNodeReadinessFlapping](/runbooks/kubenodereadinessflapping/): the Kubernetes symptom of a flapping node link.
