---
title: "BlackboxProbeFlapping: runbook and fix"
description: "BlackboxProbeFlapping means an endpoint probe keeps switching between success and failure. How to find intermittent errors and fix them."
permalink: /runbooks/blackboxprobeflapping/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Endpoint probes (blackbox_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "BlackboxProbeFlapping ships with 5 other blackbox_exporter alerts in the pack of 179, all with promtool unit tests and runbooks."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=blackboxprobeflapping
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# BlackboxProbeFlapping

A blackbox probe keeps alternating between passing and failing instead of settling in one state.

| | |
|---|---|
| Severity | warning |
| Source | blackbox_exporter `/probe` |
| Key metric | `probe_success` |

## What it means

The alert counts how often `probe_success` changes value over a recent window. It fires when the probe toggles several times, which usually means some requests fail and others succeed.

Flapping rarely reaches the threshold of a hard outage alert, yet users experience it as random errors or slow page loads. It is often the earliest visible symptom of an overloaded backend or a bad node behind a load balancer.

## Common causes

- One unhealthy backend behind a load balancer, so probes fail whenever they land on it.
- Probe timeout set close to the normal response time, so small latency spikes become failures.
- Intermittent DNS failures or multiple A records where one address is dead.
- Resource saturation on the service (connection pool exhausted, CPU throttling, GC pauses).
- Rate limiting or WAF rules that block the exporter's traffic part of the time.

## First checks

1. Visualise the pattern over the last few hours:
   ```promql
   probe_success{instance="<target>"}
   ```
   Regular intervals hint at cron jobs or health-check cycles; random ones hint at load.
2. Compare probe duration with the module timeout:
   ```promql
   max_over_time(probe_duration_seconds{instance="<target>"}[15m])
   ```
3. Check whether DNS returns several addresses and whether one is failing:
   ```bash
   dig +short <hostname>
   for ip in $(dig +short <hostname>); do curl -s -o /dev/null -w "$ip %{http_code} %{time_total}\n" --resolve <hostname>:443:$ip https://<hostname>/; done
   ```
4. Run the debug probe several times and compare failures:
   ```bash
   curl -s "http://<blackbox-exporter>:9115/probe?target=<target>&module=<module>&debug=true" | grep -iE "error|fail|status"
   ```
5. Check backend error rates and pod restarts for the service behind the target.

## Fixing it

Remove or repair the unhealthy backend, fix readiness probes so the load balancer stops sending traffic to it, and address saturation. If probes fail only because they time out just above normal latency, give the module a realistic timeout and keep a separate latency alert.

## Related alerts

- [BlackboxProbeFailed](/runbooks/blackboxprobefailed/): the same probe, failing continuously.
- [BlackboxSlowProbe](/runbooks/blackboxslowprobe/): slowness that often precedes timeouts and flapping.
- [BlackboxDnsLookupSlow](/runbooks/blackboxdnslookupslow/): unreliable DNS is a common flapping source.
