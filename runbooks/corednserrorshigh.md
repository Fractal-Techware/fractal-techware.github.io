---
title: "CoreDNSErrorsHigh: runbook and fix"
description: "CoreDNSErrorsHigh means CoreDNS returns SERVFAIL for a notable share of queries. How to find the failing zone or upstream and fix it."
permalink: /runbooks/corednserrorshigh/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: CoreDNS
severity: "warning, critical"
cta:
  title: Get this alert, tested
  text: "CoreDNSErrorsHigh is one of 6 CoreDNS alerts in the pack of 179, with warning and critical tiers, promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=corednserrorshigh
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# CoreDNSErrorsHigh

A growing share of DNS responses from CoreDNS are SERVFAIL, meaning the server could not produce an answer.

| | |
|---|---|
| Severity | warning, critical |
| Source | CoreDNS `prometheus` plugin (port 9153) |
| Key metric | `coredns_dns_responses_total` (label `rcode`) |

## What it means

Every response is counted with its return code. NXDOMAIN (name does not exist) is normal; SERVFAIL means CoreDNS tried and failed, usually because an upstream did not answer or a plugin errored. The alert looks at the SERVFAIL ratio across the cluster. The **warning** fires when a small but steady fraction fails; the **critical** fires when the fraction is several times higher and lookups are visibly breaking for workloads.

Applications receiving SERVFAIL generally treat it as a hard failure, so outbound calls, database connections by hostname and webhook deliveries fail.

## Common causes

- Upstream resolvers down or unreachable (check forward health checks).
- DNSSEC validation failures for a specific external domain.
- A stub zone or `forward` block for a private domain pointing at a dead server.
- The `kubernetes` plugin unable to reach the API server, so cluster names fail.
- Upstream rate limiting from cloud VPC resolvers under high query volume.

## First checks

1. See the response code mix:
   ```promql
   sum by (rcode) (rate(coredns_dns_responses_total[5m]))
   ```
2. Narrow to the zone and server returning failures:
   ```promql
   sum by (server, zone) (rate(coredns_dns_responses_total{rcode="SERVFAIL"}[5m]))
   ```
3. Check upstream responses and health:
   ```promql
   sum by (to, rcode) (rate(coredns_proxy_request_duration_seconds_count[5m]))
   sum by (to) (rate(coredns_proxy_healthcheck_failures_total[5m]))
   ```
4. Read the errors plugin output:
   ```bash
   kubectl -n kube-system logs -l k8s-app=kube-dns --tail=100 | grep -iE "error|SERVFAIL|timeout"
   ```
5. Reproduce and compare with the upstream directly:
   ```bash
   kubectl run dnstest --rm -it --restart=Never --image=busybox:1.36 -- nslookup <failing-name>
   dig @<upstream-ip> <failing-name>
   ```

## Fixing it

Replace or fix the failing upstream in the `coredns` ConfigMap, remove dead stub zones, and restore API server connectivity if cluster names fail. If a single external domain is broken, the problem is on their side; consider caching negative answers briefly to reduce load. Enable the `log` plugin temporarily if you need per-query detail.

## Related alerts

- [CoreDNSForwardHealthcheckFailures](/runbooks/corednsforwardhealthcheckfailures/): an unhealthy upstream behind the errors.
- [CoreDNSForwardLatencyHigh](/runbooks/corednsforwardlatencyhigh/): upstream timeouts become SERVFAIL.
- [CoreDNSPanics](/runbooks/corednspanics/): panics recovered mid-query also return SERVFAIL.
