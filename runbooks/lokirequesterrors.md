---
title: "LokiRequestErrors: runbook and fix"
description: "LokiRequestErrors means a Loki route is returning a high share of 5xx errors. How to find the failing component and restore log queries or ingestion."
permalink: /runbooks/lokirequesterrors/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Grafana Loki
severity: critical
cta:
  title: Get this alert, tested
  text: "LokiRequestErrors is one of 5 Grafana Loki alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=lokirequesterrors
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# LokiRequestErrors

A Loki component is failing a large share of requests on one route with server errors.

| | |
|---|---|
| Severity | critical |
| Source | Loki's own `/metrics` (2.9+ and 3.x) |
| Key metric | `loki_request_duration_seconds_count` (labels `job`, `route`, `status_code`) |

## What it means

Every Loki component records each HTTP and gRPC request with its route and status code. The alert fires when the 5xx share on a route stays well above normal for a sustained period.

The `route` label tells you what is broken. Push routes (`loki_api_v1_push`, `/logproto.Pusher/Push`) mean logs are being rejected and may be lost if clients give up retrying. Query routes (`loki_api_v1_query_range` and similar) mean Grafana dashboards and log searches fail.

## Common causes

- **Object storage problems**: S3/GCS/Azure errors, expired credentials, or throttling.
- **Ingesters unhealthy**: OOM kills, not ready in the ring, or a ring with too many unhealthy members for the replication factor.
- **Queriers out of memory** on large queries, causing failures upstream at the query frontend.
- **Query timeouts** hitting `query_timeout` or the server's write timeout.
- **Network or DNS issues** between components (memberlist, gRPC).

## First checks

1. Find the job and route with errors:
   ```promql
   sum by (job, route, status_code) (rate(loki_request_duration_seconds_count{status_code=~"5.."}[5m]))
   ```
2. Check pod health across Loki components:
   ```bash
   kubectl -n <loki-namespace> get pods -o wide
   kubectl -n <loki-namespace> get events --sort-by=.lastTimestamp | tail -20
   ```
3. Read the logs of the failing component:
   ```bash
   kubectl -n <loki-namespace> logs <pod> --since=15m | grep -E 'level=error' | tail -50
   ```
   Storage errors usually mention the bucket, `AccessDenied`, `SlowDown` or timeouts.
4. For push errors, check the ingester ring. Port-forward a distributor and open `/ring`, or:
   ```bash
   kubectl -n <loki-namespace> port-forward svc/<distributor-or-loki> 3100
   curl -s localhost:3100/ring | grep -ciE 'unhealthy'
   ```
5. Check for OOM kills: `kubectl -n <loki-namespace> get pods -o jsonpath='{range .items[*]}{.metadata.name} {.status.containerStatuses[0].lastState.terminated.reason}{"\n"}{end}'`.

## Fixing it

Fix storage credentials or permissions first, since every component depends on them. Give OOM-killed ingesters or queriers more memory, and limit expensive queries with `max_query_parallelism`, `max_query_series` or split intervals. Remove stale ingesters from the ring with the "Forget" button on `/ring` if they will not come back.

## Related alerts

- [LokiRequestPanics](/runbooks/lokirequestpanics/): crashes often surface as 5xx.
- [LokiRequestLatency](/runbooks/lokirequestlatency/): slow requests turn into timeouts.
- [LokiDiscardedSamples](/runbooks/lokidiscardedsamples/): rejected logs that return 4xx rather than 5xx.
