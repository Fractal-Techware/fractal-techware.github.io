---
title: "LokiDiscardedSamples: runbook and fix"
description: "LokiDiscardedSamples means Loki is rejecting log lines for a tenant. How to read the discard reason and fix limits, old timestamps or long lines."
permalink: /runbooks/lokidiscardedsamples/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Grafana Loki
severity: warning
cta:
  title: Get this alert, tested
  text: "LokiDiscardedSamples is part of the Grafana Loki set in a pack of 179 alerts, each shipped with promtool unit tests and a runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=lokidiscardedsamples
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# LokiDiscardedSamples

Loki has been dropping incoming log lines for a tenant, and those logs are gone.

| | |
|---|---|
| Severity | warning |
| Source | Loki's own `/metrics` (2.9+ and 3.x) |
| Key metrics | `loki_discarded_samples_total`, `loki_discarded_bytes_total` (labels `tenant`, `reason`) |

## What it means

When a distributor or ingester rejects log entries, it counts them by tenant and reason. The client gets a 4xx (often 429 or 400) and usually does not retry, so the entries are lost. The alert fires when discards continue for a sustained period rather than during a single burst.

The `reason` label is the whole diagnosis. Common values:

- `rate_limited`: tenant exceeded `ingestion_rate_mb` / `ingestion_burst_size_mb`.
- `per_stream_rate_limit`: one stream exceeded `per_stream_rate_limit`.
- `stream_limit`: tenant hit `max_global_streams_per_user`.
- `greater_than_max_sample_age`: timestamps older than `reject_old_samples_max_age`.
- `too_far_in_future`: timestamps ahead of the clock beyond `creation_grace_period`.
- `line_too_long`: line exceeds `max_line_size`.

## Common causes

- A noisy application or a log loop suddenly increasing volume.
- High-cardinality labels (pod IDs, request IDs) creating too many streams.
- An agent replaying a backlog of old files after a restart.
- Wrong clocks on nodes, or timestamps parsed from the log body incorrectly.
- Stack traces or JSON blobs logged as a single huge line.

## First checks

1. Break discards down by tenant and reason:
   ```promql
   sum by (tenant, reason) (rate(loki_discarded_samples_total[5m]))
   ```
2. Check the effective limits for the tenant:
   ```bash
   kubectl -n <loki-namespace> port-forward svc/<loki-or-distributor> 3100
   curl -s localhost:3100/config | grep -E 'ingestion_rate_mb|ingestion_burst_size_mb|per_stream_rate_limit|max_line_size|reject_old_samples|max_global_streams'
   curl -s localhost:3100/runtime_config
   ```
3. For rate or stream limits, find the heaviest streams with LogCLI or Grafana:
   ```bash
   logcli series '{namespace="<namespace>"}' --analyze-labels
   ```
4. Read the distributor logs; rejected pushes name the stream and reason:
   ```bash
   kubectl -n <loki-namespace> logs <distributor-pod> --since=15m | grep -iE 'discard|rate limit|too long|too old'
   ```

## Fixing it

Remove high-cardinality labels in the agent config. Raise limits per tenant in the runtime overrides when growth is legitimate. Fix clocks or timestamp parsing for age-related reasons. For long lines, truncate in the agent or raise `max_line_size` (with `max_line_size_truncate` to keep the start of the line instead of dropping it).

## Related alerts

- [LokiRequestErrors](/runbooks/lokirequesterrors/): server-side push failures.
- [LokiRequestLatency](/runbooks/lokirequestlatency/): slow ingestion that may precede client backlogs.
