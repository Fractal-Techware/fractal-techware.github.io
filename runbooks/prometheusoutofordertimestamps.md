---
title: "PrometheusOutOfOrderTimestamps: runbook and fix"
description: "PrometheusOutOfOrderTimestamps means Prometheus drops scraped samples older than the latest one for their series. How to find the source and fix it."
permalink: /runbooks/prometheusoutofordertimestamps/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "PrometheusOutOfOrderTimestamps is included with 19 other Prometheus self-monitoring rules in the pack of 179 tested alerts with runbooks."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheusoutofordertimestamps
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusOutOfOrderTimestamps

Prometheus is rejecting scraped samples because their timestamps are older than the newest sample it already has for that series.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metric | `prometheus_target_scrapes_sample_out_of_order_total` |

## What it means

By default the TSDB only accepts samples that move forward in time per series. When a scrape brings a sample with an earlier timestamp than the last stored one, it is dropped and this counter increases. The alert fires when drops continue for several minutes.

Normal scrapes stamp samples with the scrape time, so they cannot go backwards. When you see this, something is supplying its own timestamps, or two sources are writing into the same series.

## Common causes

- An exporter exposes explicit timestamps (for example cached values with the time they were collected) and Prometheus honors them.
- Federation: `/federate` returns samples with their original timestamps, and two federated sources map to the same series.
- Two targets end up with identical label sets after relabeling, and their scrapes interleave.
- Clock skew on a host whose exporter writes its own timestamps.
- A Pushgateway job where clients push samples with timestamps.

## First checks

1. See where the drops are happening:
   ```promql
   rate(prometheus_target_scrapes_sample_out_of_order_total[5m])
   ```
2. Find the target in the logs:
   ```bash
   kubectl -n monitoring logs <prometheus-pod> -c prometheus | grep -i "out-of-order"
   ```
   Use `--log.level=debug` temporarily if the warning lacks detail.
3. Check whether the target exposes timestamps (a third field after the value):
   ```bash
   curl -s http://<target>:<port>/metrics | grep -v '^#' | awk 'NF>2' | head
   ```
4. Look for duplicate target identities, i.e. more than one active target with the same labels:
   ```promql
   count by (job, instance) (up) > 1
   ```
5. Check host clocks: `chronyc tracking` or `timedatectl` on the exporter host.

## Fixing it

For exporters that stamp their own time, set `honor_timestamps: false` on the scrape job so Prometheus uses scrape time. For federation, make sure every source adds a distinct external label. For colliding targets, fix relabeling so each target keeps a unique `instance`. Fix NTP on hosts with skewed clocks.

## Related alerts

- [PrometheusDuplicateTimestamps](/runbooks/prometheusduplicatetimestamps/): same family of problem, same timestamp with a different value.
- [PrometheusRemoteStorageFailures](/runbooks/prometheusremotestoragefailures/): out-of-order data is also a common reason remote backends reject writes.
