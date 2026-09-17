---
title: "BlackboxSlowProbe: runbook and fix"
description: "BlackboxSlowProbe means blackbox_exporter probes of an endpoint are consistently slow. How to find which phase (DNS, TLS, server) is slow."
permalink: /runbooks/blackboxslowprobe/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Endpoint probes (blackbox_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "BlackboxSlowProbe is one of the endpoint probe alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=blackboxslowprobe
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# BlackboxSlowProbe

Probes of an endpoint still succeed, but on average they take much longer than a healthy endpoint should.

| | |
|---|---|
| Severity | warning |
| Source | blackbox_exporter `/probe` |
| Key metrics | `probe_duration_seconds`, `probe_http_duration_seconds` (label `phase`) |

## What it means

`probe_duration_seconds` is the total time the exporter spent on a probe, including DNS, connecting, TLS and reading the response. The alert fires when the average stays above roughly a second for a sustained period.

Users are probably seeing the same delay. Slow probes also sit close to the module timeout, so this is often the prelude to flapping or outright failures.

## Common causes

- Slow application responses: database contention, cold caches, saturated worker pools.
- Slow DNS resolution on the exporter host.
- TLS handshake delays (OCSP fetching on the server, long certificate chains, CPU-starved TLS terminator).
- Network latency: the exporter probes from a distant region or through a congested proxy.
- The exporter pod itself CPU-throttled while running many concurrent probes.

## First checks

1. Break the time down by phase for HTTP probes:
   ```promql
   avg by (phase) (avg_over_time(probe_http_duration_seconds{instance="<target>"}[10m]))
   ```
   A large `resolve` points to DNS, `connect` to network, `tls` to the handshake, `processing` to the server.
2. See whether it is one target or many:
   ```promql
   topk(10, avg_over_time(probe_duration_seconds[10m]))
   ```
   Many slow targets at once usually means the exporter or its network is the problem.
3. Time the request from another location:
   ```bash
   curl -s -o /dev/null -w "dns %{time_namelookup} connect %{time_connect} tls %{time_appconnect} ttfb %{time_starttransfer} total %{time_total}\n" https://<target>/
   ```
4. Check exporter throttling:
   ```promql
   rate(container_cpu_cfs_throttled_periods_total{container="blackbox-exporter"}[5m])
   ```

## Fixing it

Fix the slow phase: application performance for `processing`, resolver health for `resolve`, TLS terminator capacity for `tls`. If the exporter is the bottleneck, give it more CPU or split probes across instances. If the endpoint is legitimately slow (a heavy report page), probe a lightweight health path instead.

## Related alerts

- [BlackboxDnsLookupSlow](/runbooks/blackboxdnslookupslow/): isolates the DNS part of the delay.
- [BlackboxProbeFlapping](/runbooks/blackboxprobeflapping/): slow probes that start hitting the timeout.
- [BlackboxProbeFailed](/runbooks/blackboxprobefailed/): when slowness becomes an outage.
