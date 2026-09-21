---
title: "LokiRequestPanics: runbook and fix"
description: "LokiRequestPanics means a Loki component recovered from a Go panic. How to find the stack trace, the triggering request and the fix or upgrade."
permalink: /runbooks/lokirequestpanics/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Grafana Loki
severity: critical
cta:
  title: Get this alert, tested
  text: "LokiRequestPanics ships with the other Grafana Loki alerts in a pack of 179, each tested with promtool and documented in a runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=lokirequestpanics
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# LokiRequestPanics

A Loki process hit a Go panic while handling a request.

| | |
|---|---|
| Severity | critical |
| Source | Loki's own `/metrics` (2.9+ and 3.x) |
| Key metric | `loki_panic_total` (labels `job`, `namespace`) |

## What it means

Loki catches panics in request handlers, increments `loki_panic_total`, logs the stack trace and returns an error for that request. The alert fires as soon as that counter increases, and keeps firing for a short while afterwards so a single panic is not lost between evaluations.

A panic is always a bug, either in Loki or triggered by unexpected input. The process may survive, but the request failed, and repeated panics usually come with data or query loss. Panics outside a request handler crash the pod instead, which shows up as restarts.

## Common causes

- **A specific query** (unusual LogQL, a parser stage, very large label sets) hitting a code path bug.
- **Corrupted or unexpected chunk or index data** read from object storage.
- **Known bugs in a particular Loki version**, often fixed in a patch release.
- **Configuration combinations** not well tested, e.g. after a schema or storage migration.

## First checks

1. See which component and pods are panicking:
   ```promql
   sum by (namespace, job, pod) (increase(loki_panic_total[1h]))
   ```
2. Get the stack trace from the logs:
   ```bash
   kubectl -n <loki-namespace> logs <pod> --since=1h | grep -iE -A 30 'panic'
   ```
   If the pod restarted, use `--previous`.
3. Check restarts across the deployment:
   ```bash
   kubectl -n <loki-namespace> get pods -o custom-columns=NAME:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount
   ```
4. For query-path panics, find the query that triggered it. The query frontend logs each query with `query=` and `org_id=` near the same timestamp:
   ```bash
   kubectl -n <loki-namespace> logs <query-frontend-pod> --since=1h | grep 'metrics.go' | grep -v 'status=200'
   ```
5. Note the running version from the image tag: `kubectl -n <loki-namespace> get pod <pod> -o jsonpath='{.spec.containers[0].image}'`.

## Fixing it

Search the Loki GitHub issues and changelog for the top frames of the stack trace; most panics are known and fixed in a later patch release, so upgrading is the usual fix. Until then, block or limit the offending query pattern, or ask the tenant to change it. If the panic comes from bad stored data, identify the chunk or table in the trace and remove or skip it.

## Related alerts

- [LokiRequestErrors](/runbooks/lokirequesterrors/): panicking requests are returned as errors.
- [LokiRequestLatency](/runbooks/lokirequestlatency/): restarts and retries slow everything down.
