---
title: "BlackboxDnsLookupSlow: runbook and fix"
description: "BlackboxDnsLookupSlow means DNS resolution during blackbox probes is consistently slow. How to find the slow resolver and fix it."
permalink: /runbooks/blackboxdnslookupslow/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Endpoint probes (blackbox_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "BlackboxDnsLookupSlow is part of the endpoint probe set in the pack of 179 alerts, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=blackboxdnslookupslow
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# BlackboxDnsLookupSlow

Resolving the hostname of a probed endpoint is taking far longer than DNS normally should.

| | |
|---|---|
| Severity | warning |
| Source | blackbox_exporter `/probe` |
| Key metric | `probe_dns_lookup_time_seconds` |

## What it means

Before connecting, the exporter resolves the target hostname and records how long that took. The alert fires when lookups average several hundred milliseconds over a sustained window. Healthy lookups are typically a few milliseconds when cached.

Every client of that hostname pays the same delay, and slow DNS frequently turns into timeouts. Because the exporter uses its host's resolver, this alert often points at your own DNS infrastructure rather than the target.

## Common causes

- Overloaded or failing cluster DNS (CoreDNS) or node-local DNS cache.
- Upstream resolvers slow or unreachable, with clients waiting for a timeout before trying the next one.
- `ndots:5` in Kubernetes pods causing several search-domain lookups before the real name is tried.
- IPv6 AAAA queries timing out when `preferred_ip_protocol` is ip6 but the network is IPv4-only.
- Authoritative DNS provider having latency issues for your zone.

## First checks

1. See whether one hostname or all probes are affected:
   ```promql
   topk(10, avg_over_time(probe_dns_lookup_time_seconds[10m]))
   ```
2. Time a lookup from the exporter's environment:
   ```bash
   kubectl -n monitoring exec <blackbox-exporter-pod> -- cat /etc/resolv.conf
   dig <hostname> | grep "Query time"
   ```
   Run `dig` from a debug pod in the same namespace if the exporter image has no shell tools.
3. Compare against the authoritative server directly:
   ```bash
   dig +short NS <zone>
   dig @<authoritative-ns> <hostname> | grep "Query time"
   ```
4. If you are in Kubernetes, check cluster DNS latency:
   ```promql
   histogram_quantile(0.99, sum by (le) (rate(coredns_dns_request_duration_seconds_bucket[5m])))
   ```

## Fixing it

Fix the resolver that is slow: scale CoreDNS or add NodeLocal DNSCache, replace a failing upstream, or use fully qualified names (trailing dot) in probe targets to skip search domains. Set `preferred_ip_protocol: ip4` in the module if IPv6 is not routable.

## Related alerts

- [BlackboxSlowProbe](/runbooks/blackboxslowprobe/): total probe time, of which DNS is one phase.
- [BlackboxProbeFlapping](/runbooks/blackboxprobeflapping/): DNS timeouts often cause intermittent failures.
- [CoreDNSLatencyHigh](/runbooks/corednslatencyhigh/): the cluster DNS side of the same problem.
