---
title: "NodeConntrackLimit: runbook and fix"
description: "NodeConntrackLimit means the netfilter conntrack table is nearly full, so new connections will be dropped. How to diagnose and raise the limit."
permalink: /runbooks/nodeconntracklimit/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeConntrackLimit is part of a pack of 179 alerts, 25 of them for hosts, each backed by promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodeconntracklimit
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeConntrackLimit

The kernel's connection tracking table is close to full, and once it is, new connections through this host are silently dropped.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `conntrack` collector |
| Key metrics | `node_nf_conntrack_entries`, `node_nf_conntrack_entries_limit` |

## What it means

Netfilter tracks every flow that passes through iptables or nftables rules that use state, NAT, or Kubernetes Services via kube-proxy. The table has a fixed size, `net.netfilter.nf_conntrack_max`. The alert fires when entries have stayed close to that limit for several minutes.

When the table fills, the kernel logs `nf_conntrack: table full, dropping packet` and new connections time out. The symptoms look like random network failures: intermittent timeouts, failed DNS lookups, health checks flapping, while existing connections keep working.

## Common causes

- A traffic spike or many short-lived connections (no keep-alive, aggressive health checks, DNS over UDP at high rate).
- Long conntrack timeouts keeping idle or closed flows in the table for days.
- Kubernetes nodes running NodePort or many Services where kube-proxy NATs every flow.
- A scan, DDoS, or misbehaving client opening connections in a loop.
- The limit sized for a small instance that has since grown in workload.

## First checks

1. See how full the table is per host:
   ```promql
   node_nf_conntrack_entries / node_nf_conntrack_entries_limit
   ```
2. Confirm drops in the kernel log:
   ```bash
   dmesg -T | grep -i "conntrack"
   ```
3. Check the limit and current count on the host:
   ```bash
   sysctl net.netfilter.nf_conntrack_max net.netfilter.nf_conntrack_count
   sudo conntrack -S
   ```
   A rising `drop` or `insert_failed` in `conntrack -S` confirms real impact.
4. Find which protocol, state and destinations dominate (needs `conntrack-tools`):
   ```bash
   sudo conntrack -L 2>/dev/null | awk '{print $1, $4}' | sort | uniq -c | sort -rn | head
   sudo conntrack -L -p tcp 2>/dev/null | grep -o 'dport=[0-9]*' | sort | uniq -c | sort -rn | head
   ```
5. Review timeouts, especially `net.netfilter.nf_conntrack_tcp_timeout_established`.

## Fixing it

Raise `net.netfilter.nf_conntrack_max` (it costs a small amount of kernel memory per entry) and persist it in `/etc/sysctl.d/`. On Kubernetes, kube-proxy manages this value; adjust its `conntrack.maxPerCore` setting instead, or your change will be overwritten. Shorten excessive TCP timeouts, enable keep-alive on clients, and block abusive sources. Exempting high-volume traffic from tracking with `notrack` rules is an option for experienced operators.

## Related alerts

- [NodeFileDescriptorLimit](/runbooks/nodefiledescriptorlimit/): the same connection storm can exhaust file handles.
- [NodeNetworkReceiveErrs](/runbooks/nodenetworkreceiveerrs/): distinguishes NIC-level drops from conntrack drops.
- [NodeHighCPUUsage](/runbooks/nodehighcpuusage/): heavy softirq load often accompanies a full table.
