---
title: "PrometheusTSDBCompactionsFailing: runbook and fix"
description: "PrometheusTSDBCompactionsFailing means TSDB compactions keep failing, so memory and WAL grow. How to find the cause (disk, OOM, corruption) and fix it."
permalink: /runbooks/prometheustsdbcompactionsfailing/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "PrometheusTSDBCompactionsFailing is part of the Prometheus self-monitoring set (20 alerts) in the 179-alert pack, all with tests and runbooks."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheustsdbcompactionsfailing
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusTSDBCompactionsFailing

Prometheus keeps failing to compact its TSDB, so data is piling up in memory and in the write-ahead log instead of being written out as blocks.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metrics | `prometheus_tsdb_compactions_failed_total`, `prometheus_tsdb_compactions_total` |

## What it means

Prometheus writes new samples into an in-memory head block backed by the WAL. Roughly every two hours the head is compacted into an immutable block on disk, and small blocks are later merged into larger ones. The alert fires when compaction failures have kept occurring over a long window.

This degrades slowly and then badly: the head grows, memory rises, the WAL gets longer, restarts take much longer to replay, and eventually the process can be OOM-killed in a loop.

## Common causes

- Not enough free disk space. Compaction writes the new block before deleting the inputs, so it needs temporary headroom.
- Prometheus is OOM-killed during compaction, which is memory hungry on high-cardinality data.
- A corrupted chunk or block that the compactor cannot read.
- Permission problems or a read-only filesystem on the data volume.
- Slow network storage causing compaction to fail or time out.

## First checks

1. Confirm the failure rate against successful runs:
   ```promql
   increase(prometheus_tsdb_compactions_failed_total[6h])
   increase(prometheus_tsdb_compactions_total[6h])
   ```
2. Read the compaction error:
   ```bash
   kubectl -n monitoring logs <prometheus-pod> -c prometheus | grep -iE "compact"
   ```
3. Check free space and recent OOM kills:
   ```bash
   kubectl -n monitoring exec <prometheus-pod> -c prometheus -- df -h /prometheus
   kubectl -n monitoring describe pod <prometheus-pod> | grep -A3 "Last State"
   ```
4. See whether the head is growing out of control:
   ```promql
   prometheus_tsdb_head_series
   ```
5. Look for cardinality offenders that make compaction expensive:
   ```bash
   promtool tsdb analyze /prometheus
   ```

## Fixing it

Give the volume enough headroom (a comfortable share of free space, not a few percent), or shorten retention with `--storage.tsdb.retention.time` or `--storage.tsdb.retention.size`. If OOM is the cause, raise the memory limit and cut cardinality with `metric_relabel_configs`. For a corrupted block named in the logs, stop Prometheus and move that block out of the data directory before starting again.

## Related alerts

- [PrometheusTSDBReloadsFailing](/runbooks/prometheustsdbreloadsfailing/): shares most root causes with this alert.
- [PrometheusNotIngestingSamples](/runbooks/prometheusnotingestingsamples/): what happens if the TSDB stops accepting writes.
- [PrometheusScrapeSampleLimitHit](/runbooks/prometheusscrapesamplelimithit/): a tool for capping the cardinality that makes compaction heavy.
