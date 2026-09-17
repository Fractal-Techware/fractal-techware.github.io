---
title: "BlackboxProbeFailed: runbook and fix"
description: "BlackboxProbeFailed means blackbox_exporter cannot reach an endpoint or the check failed. How to debug the probe and tell outage from probe issue."
permalink: /runbooks/blackboxprobefailed/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Endpoint probes (blackbox_exporter)
severity: critical
cta:
  title: Get this alert, tested
  text: "BlackboxProbeFailed is one of 6 endpoint probe alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=blackboxprobefailed
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# BlackboxProbeFailed

A synthetic check run by blackbox_exporter against an endpoint has been failing continuously.

| | |
|---|---|
| Severity | critical |
| Source | blackbox_exporter `/probe` (http, tcp, dns, icmp modules) |
| Key metric | `probe_success` (1 = check passed, 0 = failed) |

## What it means

Prometheus asks blackbox_exporter to probe a target with a module, and the exporter reports `probe_success`. The alert fires when a probe has stayed at 0 for several minutes, so a single timeout does not page you.

A failed probe is what your users see from the exporter's vantage point: the site is down, the port is closed, the certificate is invalid or the response did not match what the module expects. It can also be a problem with the probe itself, so verify before escalating.

## Common causes

- The service is actually down or returning an unexpected status code (5xx, or a 3xx the module does not follow).
- DNS for the target no longer resolves, or resolves to the wrong address.
- TLS failure: expired certificate, hostname mismatch, or an untrusted CA.
- Module assertions such as `valid_status_codes`, `fail_if_body_not_matches_regexp` or `fail_if_not_ssl` no longer match after a deploy.
- Network path from the exporter blocked (firewall, egress policy, IPv6 preferred but not routable).

## First checks

1. List failing targets:
   ```promql
   probe_success == 0
   ```
2. Look at what part failed:
   ```promql
   probe_http_status_code{instance="<target>"}
   ```
   and `probe_http_duration_seconds` by `phase` (resolve, connect, tls, processing, transfer).
3. Run the probe with full debug output; it shows DNS, connection, TLS and response details plus the reason it failed:
   ```bash
   curl -s "http://<blackbox-exporter>:9115/probe?target=<target>&module=<module>&debug=true"
   ```
4. Reproduce from outside the exporter:
   ```bash
   curl -sv -o /dev/null https://<target>/
   ```
5. If only the exporter fails, check `preferred_ip_protocol` in the module and network policies around the exporter pod.

## Fixing it

If the service is down, this is an incident for the owning team; the probe is doing its job. If the service changed (new redirect, new status code, new body), update the module to match. If only the exporter's network path is broken, fix egress or run the exporter closer to the target.

## Related alerts

- [BlackboxProbeFlapping](/runbooks/blackboxprobeflapping/): intermittent failures that never stay down long enough for this alert.
- [BlackboxSslCertificateWillExpireSoon](/runbooks/blackboxsslcertificatewillexpiresoon/): the warning before an expired certificate breaks the probe.
- [BlackboxExporterProbeScrapeFailed](/runbooks/blackboxexporterprobescrapefailed/): the exporter itself is unreachable, so no probe result exists.
