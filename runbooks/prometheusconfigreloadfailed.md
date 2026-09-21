---
title: "PrometheusConfigReloadFailed: runbook and fix"
description: "PrometheusConfigReloadFailed means Prometheus rejected a new config and is still running the old one. How to find the error and reload safely."
permalink: /runbooks/prometheusconfigreloadfailed/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "PrometheusConfigReloadFailed is one of 20 Prometheus self-monitoring alerts in the 179-alert pack, all with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheusconfigreloadfailed
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusConfigReloadFailed

Prometheus tried to load a new configuration, rejected it, and is still running the previous one.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metric | `prometheus_config_last_reload_successful` (1 = ok, 0 = failed) |

## What it means

A reload happens on SIGHUP, on `POST /-/reload`, or automatically when a config-reloader sidecar (Prometheus Operator, Helm charts) sees the files change. If the new config or any rule file fails to parse, Prometheus logs the error, keeps the old config in memory, and sets the gauge to 0. The alert fires once the last reload has stayed failed for several minutes.

Nothing is down yet, but your change (a new scrape job, a new alert, a fixed rule) is not live, and the next restart may fail to start at all with the same broken file.

## Common causes

- YAML syntax or indentation errors in `prometheus.yml` or a rule file.
- A rule with invalid PromQL, or a duplicate rule group name within one file.
- A referenced file that does not exist or is unreadable: `rule_files` glob, `bearer_token_file`, TLS cert or key.
- A field removed or renamed between versions, for example after upgrading from 2.x to 3.x.
- A bad PrometheusRule or ServiceMonitor object that the Operator rendered into the config.

## First checks

1. Confirm which instance is affected and when the last good reload happened:
   ```promql
   time() - prometheus_config_last_reload_success_timestamp_seconds
   ```
2. Read the actual error from the logs:
   ```bash
   kubectl -n monitoring logs <prometheus-pod> -c prometheus | grep -iE "error loading config|reload"
   ```
3. Validate the config and every rule file it pulls in. Run this against the rendered config the pod actually sees:
   ```bash
   kubectl -n monitoring exec <prometheus-pod> -c prometheus -- promtool check config /etc/prometheus/config_out/prometheus.env.yaml
   promtool check rules rules/*.yml
   ```
4. With the Operator, check the reloader sidecar and the Operator logs for rejected objects:
   ```bash
   kubectl -n monitoring logs <prometheus-pod> -c config-reloader
   ```

## Fixing it

Fix or revert the offending change, validate with `promtool`, then trigger a reload. `curl -X POST http://<prometheus>:9090/-/reload` only works when Prometheus runs with `--web.enable-lifecycle`; otherwise send SIGHUP to the process. Watch the gauge return to 1. Adding `promtool check config` and `promtool check rules` to CI prevents most of these.

## Related alerts

- [PrometheusRuleFailures](/runbooks/prometheusrulefailures/): rules that load fine but error at evaluation time.
- [PrometheusSDRefreshFailure](/runbooks/prometheussdrefreshfailure/): config is valid but discovery credentials are not.
- [AlertmanagerFailedReload](/runbooks/alertmanagerfailedreload/): the same failure on the Alertmanager side.
