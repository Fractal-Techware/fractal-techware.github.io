---
title: "CoreDNSLatencyHigh: runbook and fix"
description: "CoreDNSLatencyHigh means CoreDNS is answering queries slowly at the tail. How to tell overload, slow upstreams and ndots issues apart."
permalink: /runbooks/corednslatencyhigh/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: CoreDNS
severity: warning
cta:
  title: Get this alert, tested
  text: "CoreDNSLatencyHigh comes with 5 other CoreDNS alerts in the pack of 179, all with promtool unit tests and runbooks."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=corednslatencyhigh
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# CoreDNSLatencyHigh

CoreDNS is taking too long to answer a meaningful share of DNS queries.

| | |
|---|---|
| Severity | warning |
| Source | CoreDNS `prometheus` plugin (port 9153) |
| Key metric | `coredns_dns_request_duration_seconds_bucket` (labels `server`, `zone`, `type`) |

## What it means

CoreDNS records a latency histogram for every query it serves. The alert fires when the high percentile of that histogram stays well above normal for a zone over several minutes. Cached answers take microseconds, so tail latency in the hundreds of milliseconds means queries are waiting on something.

Applications pay this on every uncached lookup, and many clients time out after a few seconds, so slow DNS shows up as random connection errors across unrelated services.

## Common causes

- Slow upstream resolvers for external names (check forward latency).
- CoreDNS pods CPU-throttled or too few replicas for the query volume.
- Query amplification from `ndots:5`: each external name is first tried against several cluster search domains.
- Cache too small or evicting heavily, so more queries go upstream.
- Conntrack or UDP packet drops on nodes causing client retries.

## First checks

1. Find the slow zone and server:
   ```promql
   histogram_quantile(0.99, sum by (server, zone, le) (rate(coredns_dns_request_duration_seconds_bucket[5m])))
   ```
2. Check whether forwarding is the slow part:
   ```promql
   histogram_quantile(0.99, sum by (to, le) (rate(coredns_proxy_request_duration_seconds_bucket[5m])))
   ```
3. Look for throttling and query volume per pod:
   ```promql
   sum by (pod) (rate(container_cpu_cfs_throttled_periods_total{namespace="kube-system", container="coredns"}[5m]))
   sum by (instance) (rate(coredns_dns_requests_total[5m]))
   ```
4. Check cache effectiveness:
   ```promql
   sum(rate(coredns_cache_hits_total[5m])) / (sum(rate(coredns_cache_hits_total[5m])) + sum(rate(coredns_cache_misses_total[5m])))
   ```
5. Measure from a pod:
   ```bash
   kubectl run dnstest --rm -it --restart=Never --image=busybox:1.36 -- sh -c 'time nslookup example.com'
   ```

## Fixing it

Scale CoreDNS (more replicas or the cluster-proportional autoscaler) and raise CPU limits if throttled. Increase the `cache` size in the Corefile. For external-name heavy workloads, lower `ndots` in pod `dnsConfig` or use trailing dots. NodeLocal DNSCache removes much of the load and the conntrack issues.

## Related alerts

- [CoreDNSForwardLatencyHigh](/runbooks/corednsforwardlatencyhigh/): upstream slowness is the most common cause.
- [CoreDNSErrorsHigh](/runbooks/corednserrorshigh/): timeouts upstream turn into SERVFAIL.
- [BlackboxDnsLookupSlow](/runbooks/blackboxdnslookupslow/): the client-side view of slow DNS.
