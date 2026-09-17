---
title: "CoreDNSForwardHealthcheckFailures: runbook and fix"
description: "CoreDNSForwardHealthcheckFailures means CoreDNS health checks to an upstream resolver keep failing. How to verify the upstream and fix it."
permalink: /runbooks/corednsforwardhealthcheckfailures/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: CoreDNS
severity: warning
cta:
  title: Get this alert, tested
  text: "CoreDNSForwardHealthcheckFailures is one of 6 CoreDNS alerts in the pack of 179, all shipped with promtool unit tests and a runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=corednsforwardhealthcheckfailures
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# CoreDNSForwardHealthcheckFailures

The CoreDNS `forward` plugin keeps failing its health checks against at least one upstream resolver.

| | |
|---|---|
| Severity | warning |
| Source | CoreDNS `prometheus` plugin, `forward` plugin metrics |
| Key metric | `coredns_proxy_healthcheck_failures_total` (labels `to`, `proxy_name`) |

## What it means

When a forwarded query fails, the `forward` plugin starts health-checking that upstream in the background (a query for `.` by default) until it responds again, and marks it down while checks fail. The alert fires when failures for an upstream continue over a sustained window.

With several upstreams, CoreDNS routes around the broken one, so impact may be limited to extra latency. With a single upstream, or when all are failing, external name resolution breaks and CoreDNS falls back to trying upstreams at random.

## Common causes

- Upstream resolver down, decommissioned or its IP changed.
- Firewall or security group change blocking UDP/TCP 53 from nodes to the upstream.
- Upstream refusing queries from the node's source range (ACL on the resolver).
- Upstream configured for DNS-over-TLS (`tls://`) with a wrong `tls_servername` or certificate issue.
- Node `/etc/resolv.conf` pointing at a local stub (such as 127.0.0.53) that is not reachable from the pod network.

## First checks

1. Which upstream is failing and how often:
   ```promql
   sum by (to) (rate(coredns_proxy_healthcheck_failures_total[5m]))
   ```
2. Check the configured upstreams:
   ```bash
   kubectl -n kube-system get configmap coredns -o jsonpath='{.data.Corefile}' | grep -A3 forward
   ```
   If it forwards to `/etc/resolv.conf`, look at that file on the nodes.
3. Query the upstream from a pod on the same network as CoreDNS:
   ```bash
   kubectl run dnstest --rm -it --restart=Never --image=busybox:1.36 -- nslookup example.com <upstream-ip>
   ```
4. Check CoreDNS logs for forward errors:
   ```bash
   kubectl -n kube-system logs -l k8s-app=kube-dns --tail=100 | grep -iE "forward|unhealthy|i/o timeout"
   ```

## Fixing it

Restore reachability (firewall, ACL) or replace the upstream IP in the `coredns` ConfigMap; the `reload` plugin picks up changes without a restart. Keep at least two independent upstreams. If nodes use a local stub resolver, forward to real resolver addresses instead.

## Related alerts

- [CoreDNSErrorsHigh](/runbooks/corednserrorshigh/): SERVFAIL rising when no healthy upstream remains.
- [CoreDNSForwardLatencyHigh](/runbooks/corednsforwardlatencyhigh/): a degrading upstream is often slow before it fails.
- [CoreDNSLatencyHigh](/runbooks/corednslatencyhigh/): failover between upstreams adds client latency.
