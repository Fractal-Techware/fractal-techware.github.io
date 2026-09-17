---
title: "CoreDNSForwardLatencyHigh: runbook and fix"
description: "CoreDNSForwardLatencyHigh means upstream resolvers behind the CoreDNS forward plugin are slow. How to find the slow upstream and fix it."
permalink: /runbooks/corednsforwardlatencyhigh/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: CoreDNS
severity: warning
cta:
  title: Get this alert, tested
  text: "CoreDNSForwardLatencyHigh is part of the CoreDNS set in the pack of 179 alerts, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=corednsforwardlatencyhigh
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# CoreDNSForwardLatencyHigh

Queries that CoreDNS forwards to an upstream resolver are taking too long to come back.

| | |
|---|---|
| Severity | warning |
| Source | CoreDNS `prometheus` plugin, `forward` plugin metrics |
| Key metric | `coredns_proxy_request_duration_seconds_bucket` (labels `to`, `proxy_name`, `rcode`) |

## What it means

Names outside the cluster domain are sent by the `forward` plugin to upstream resolvers, usually whatever is in the node's `/etc/resolv.conf`. CoreDNS measures each upstream round trip per destination (`to`). The alert fires when the tail latency to an upstream stays around a second or more.

External lookups from every pod inherit this delay, and it is often the root cause behind general CoreDNS latency or SERVFAIL alerts.

## Common causes

- Cloud VPC resolver throttling (per-interface packet limits) under high query volume.
- On-prem upstream DNS servers overloaded or far away.
- Packet loss on the path to the upstream, causing retries.
- One slow upstream in a list, with the default random policy spreading queries onto it.
- Upstream doing recursive lookups for domains with slow authoritative servers.

## First checks

1. Latency per upstream:
   ```promql
   histogram_quantile(0.99, sum by (to, le) (rate(coredns_proxy_request_duration_seconds_bucket{proxy_name="forward"}[5m])))
   ```
2. Query volume per upstream, to spot throttling during spikes:
   ```promql
   sum by (to) (rate(coredns_proxy_request_duration_seconds_count{proxy_name="forward"}[5m]))
   ```
3. See which upstreams are configured:
   ```bash
   kubectl -n kube-system get configmap coredns -o jsonpath='{.data.Corefile}'
   ```
4. Time the upstream directly from a node or pod:
   ```bash
   dig @<upstream-ip> example.com | grep "Query time"
   ```
5. Check whether heavy callers are generating needless external queries (search-domain expansion shows up as many NXDOMAIN answers):
   ```promql
   sum by (rcode) (rate(coredns_dns_responses_total[5m]))
   ```

## Fixing it

Remove or replace the slow upstream in the Corefile, or set `policy sequential` with the fastest first. Raise the `cache` TTL to cut upstream volume, and deploy NodeLocal DNSCache to spread load across node network interfaces, which helps with cloud resolver limits. Lowering `ndots` for chatty workloads cuts wasted queries.

## Related alerts

- [CoreDNSForwardHealthcheckFailures](/runbooks/corednsforwardhealthcheckfailures/): the upstream is not just slow but failing.
- [CoreDNSLatencyHigh](/runbooks/corednslatencyhigh/): the overall latency clients see.
- [CoreDNSErrorsHigh](/runbooks/corednserrorshigh/): upstream timeouts turned into SERVFAIL.
