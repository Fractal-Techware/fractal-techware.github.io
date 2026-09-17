---
title: "BlackboxExporterProbeScrapeFailed: runbook and fix"
description: "BlackboxExporterProbeScrapeFailed means Prometheus cannot scrape blackbox_exporter for a probe, so results are missing. How to fix it."
permalink: /runbooks/blackboxexporterprobescrapefailed/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Endpoint probes (blackbox_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "BlackboxExporterProbeScrapeFailed is one of 6 blackbox_exporter alerts in the pack of 179, each with promtool unit tests and a runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=blackboxexporterprobescrapefailed
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# BlackboxExporterProbeScrapeFailed

Prometheus is not getting a response from blackbox_exporter for a probe job, so there is no probe result to evaluate.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus scrape of blackbox_exporter `/probe` |
| Key metric | `up` for the blackbox job |

## What it means

For probe jobs, each "target" in Prometheus is really a request to the exporter's `/probe` endpoint. `up` reflects whether that HTTP request to the exporter worked, not whether the probed endpoint is healthy (that is `probe_success`). The alert fires when those scrapes keep failing for several minutes.

While it fires, `probe_success` for the affected targets goes stale, so probe alerts cannot fire either. You have a monitoring blind spot rather than a confirmed outage.

## Common causes

- blackbox_exporter pod down, crashlooping or OOM-killed.
- Scrape timeout: the probe takes longer than `scrape_timeout`, so Prometheus gives up before the exporter answers.
- Relabeling mistakes, so `__address__` no longer points at the exporter.
- Unknown module name in the `module` parameter, which makes the exporter return an error.
- Network policy or Service change blocking Prometheus from port 9115.

## First checks

1. Find the failing scrapes and the error text in **Status > Targets**, or query:
   ```promql
   up{job=~".*blackbox.*"} == 0
   ```
2. Check the exporter is running and its config loaded:
   ```bash
   kubectl -n monitoring get pods -l app.kubernetes.io/name=prometheus-blackbox-exporter
   curl -s http://<blackbox-exporter>:9115/metrics | grep blackbox_exporter_config_last_reload_successful
   ```
3. Call the probe exactly as Prometheus does and time it:
   ```bash
   time curl -s "http://<blackbox-exporter>:9115/probe?target=<target>&module=<module>&debug=true" | tail -n 20
   ```
   An error about the module means it is missing from the exporter config.
4. Compare the probe duration with the job's `scrape_timeout`:
   ```promql
   scrape_duration_seconds{job=~".*blackbox.*"}
   ```

## Fixing it

Restore the exporter (resources, config, image). Fix relabeling so `__address__` is the exporter and `__param_target` the endpoint. Keep the module `timeout` below the scrape timeout; the exporter also honours the timeout header Prometheus sends, reduced by `--timeout-offset`.

## Related alerts

- [BlackboxProbeFailed](/runbooks/blackboxprobefailed/): the probe runs but the endpoint fails.
- [BlackboxSlowProbe](/runbooks/blackboxslowprobe/): slow probes that approach the scrape timeout.
- [BlackboxSslCertificateWillExpireSoon](/runbooks/blackboxsslcertificatewillexpiresoon/): expiry data stops updating while scrapes fail.
