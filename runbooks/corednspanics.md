---
title: "CoreDNSPanics: runbook and fix"
description: "CoreDNSPanics means CoreDNS recovered from a Go panic while serving queries. How to find the stack trace, the trigger and fix it."
permalink: /runbooks/corednspanics/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: CoreDNS
severity: critical
cta:
  title: Get this alert, tested
  text: "CoreDNSPanics ships with 5 other CoreDNS alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=corednspanics
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# CoreDNSPanics

CoreDNS hit a Go panic while handling a request and recovered from it.

| | |
|---|---|
| Severity | critical |
| Source | CoreDNS `prometheus` plugin (port 9153) |
| Key metric | `coredns_panics_total` |

## What it means

CoreDNS catches panics in its request handling so a single bad query does not kill the whole process, and counts each one. The alert fires as soon as that counter increases and stays active for a while afterwards so short bursts are not missed.

Any panic is a bug being triggered. The query that caused it gets a failure response, and if the trigger is repeatable (a malformed packet, a specific record type, a plugin combination) it can be hit continuously, degrading DNS for the whole cluster.

## Common causes

- A known bug in the running CoreDNS version, often in a specific plugin.
- Unusual or malformed queries from a misbehaving client or scanner.
- A third-party or less common plugin compiled into a custom CoreDNS build.
- Corefile combinations that exercise untested code paths after an upgrade.
- API server data (unusual Service or EndpointSlice objects) that the `kubernetes` plugin handles badly.

## First checks

1. Which pods are panicking and how often:
   ```promql
   sum by (instance) (increase(coredns_panics_total[1h]))
   ```
2. Get the stack trace from the logs:
   ```bash
   kubectl -n kube-system logs -l k8s-app=kube-dns --tail=500 | grep -A20 -i "panic"
   ```
   The first frames name the plugin and function involved.
3. Record the version and configuration:
   ```bash
   kubectl -n kube-system get deployment coredns -o jsonpath='{.spec.template.spec.containers[0].image}'
   kubectl -n kube-system get configmap coredns -o jsonpath='{.data.Corefile}'
   ```
4. Correlate with query types and sources. Temporarily adding the `log` plugin to the Corefile shows the queries around the panic; remove it afterwards, as it is noisy.
5. Check restarts, since not every panic is recoverable:
   ```bash
   kubectl -n kube-system get pods -l k8s-app=kube-dns
   ```

## Fixing it

Search the CoreDNS GitHub issues and release notes for the function in the stack trace; upgrading to a fixed version is the usual remedy. If a recent upgrade introduced it, roll back. As a stopgap, disable the offending plugin or block the misbehaving client.

## Related alerts

- [CoreDNSErrorsHigh](/runbooks/corednserrorshigh/): repeated panics show up as failed responses.
- [CoreDNSDown](/runbooks/corednsdown/): unrecovered crashes can take every replica down.
- [CoreDNSLatencyHigh](/runbooks/corednslatencyhigh/): panicking pods can slow the remaining replicas.
