---
title: "LokiCompactorHasNotSuccessfullyRunCompaction: runbook and fix"
description: "LokiCompactorHasNotSuccessfullyRunCompaction means the Loki compactor has not finished a run in hours. Find out why before retention and index size suffer."
permalink: /runbooks/lokicompactorhasnotsuccessfullyruncompaction/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Grafana Loki
severity: warning
cta:
  title: Get this alert, tested
  text: "LokiCompactorHasNotSuccessfullyRunCompaction is one of 5 Grafana Loki alerts in the pack of 179, each with a promtool unit test and a runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=lokicompactorhasnotsuccessfullyruncompaction
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# LokiCompactorHasNotSuccessfullyRunCompaction

The Loki compactor has gone several hours without completing a successful compaction run.

| | |
|---|---|
| Severity | warning |
| Source | Loki compactor `/metrics` (2.9+ and 3.x) |
| Key metrics | `loki_boltdb_shipper_compact_tables_operation_last_successful_run_timestamp_seconds`, `loki_boltdb_shipper_compact_tables_operation_total` (label `status`) |

## What it means

The compactor merges the many small index files written by ingesters into one file per table per day, and it is also what applies retention and log deletion requests. It records the timestamp of its last successful run. Despite the `boltdb_shipper` prefix, the same metrics are used for TSDB indexes. The alert fires when that timestamp has been stale for hours, well beyond the normal compaction interval.

Nothing breaks immediately, but queries slow down as index files pile up, retention stops deleting old data (storage costs grow), and delete requests are not processed.

## Common causes

- **Compactor not running**: no compactor target deployed, pod crash looping, or OOM killed on large tables.
- **Object storage permission errors**: the compactor needs list, read, write and delete on the bucket.
- **Multiple compactors** running at once in older setups, or none holding the ring lock.
- **Working directory full**: the compactor downloads tables to `working_directory` on local disk.
- **Very large tables** that take longer than expected to process.

## First checks

1. Check how long it has been, in hours:
   ```promql
   (time() - loki_boltdb_shipper_compact_tables_operation_last_successful_run_timestamp_seconds) / 3600
   ```
2. See whether runs are attempted and failing:
   ```promql
   sum by (status) (increase(loki_boltdb_shipper_compact_tables_operation_total[6h]))
   ```
3. Check the compactor pod:
   ```bash
   kubectl -n <loki-namespace> get pods -l app.kubernetes.io/component=compactor
   kubectl -n <loki-namespace> describe pod <compactor-pod> | grep -A5 'Last State'
   ```
   In single-binary or simple scalable mode, the compactor runs inside the backend or loki pods.
4. Read its logs for the failure:
   ```bash
   kubectl -n <loki-namespace> logs <compactor-pod> --since=6h | grep -iE 'compact|error' | tail -50
   ```
5. Check local disk: `kubectl -n <loki-namespace> exec <compactor-pod> -- df -h`.

## Fixing it

Fix bucket permissions, give the compactor more memory or a larger volume for its working directory, and make sure exactly one compactor instance runs. Once it succeeds, it catches up on pending tables and retention on its own.

## Related alerts

- [LokiRequestLatency](/runbooks/lokirequestlatency/): uncompacted indexes make queries slower.
- [LokiRequestErrors](/runbooks/lokirequesterrors/): storage issues that break the compactor often break other routes too.
