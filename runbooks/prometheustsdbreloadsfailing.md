---
title: "PrometheusTSDBReloadsFailing: runbook and fix"
description: "PrometheusTSDBReloadsFailing means Prometheus keeps failing to load TSDB blocks from disk. How to find the bad block, check the disk and recover."
permalink: /runbooks/prometheustsdbreloadsfailing/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Prometheus self-monitoring
severity: warning
cta:
  title: Get this alert, tested
  text: "PrometheusTSDBReloadsFailing is one of 20 Prometheus self-monitoring alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=prometheustsdbreloadsfailing
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PrometheusTSDBReloadsFailing

Prometheus has repeatedly failed to reload its on-disk TSDB blocks over the last few hours.

| | |
|---|---|
| Severity | warning |
| Source | Prometheus' own `/metrics` (2.x and 3.x) |
| Key metric | `prometheus_tsdb_reloads_failures_total` |

## What it means

After every compaction and retention pass, the TSDB re-reads the block directories in its data path so queries see the current set of blocks. When that reload errors, the counter increments. The alert looks at a long window, so it fires on a persistent problem, not a single hiccup.

Symptoms can include queries missing older data, retention not deleting old blocks, and disk usage creeping up. A failing reload often comes before a failed restart, so fix it while the process is still running.

## Common causes

- A corrupted block: missing `meta.json`, a truncated index or chunk file, often after a node crash or an unclean volume detach.
- The data volume is full or has become read-only.
- Permission or ownership changes on the data directory (for example after changing `securityContext.fsGroup`).
- Leftover `.tmp` directories or partially copied blocks from a manual restore or a backup tool.
- Underlying storage errors on the node (network block storage latency, filesystem errors).

## First checks

1. Confirm the failures are ongoing and on which instance:
   ```promql
   increase(prometheus_tsdb_reloads_failures_total[1h])
   ```
2. Read the error, which usually names the block ULID:
   ```bash
   kubectl -n monitoring logs <prometheus-pod> -c prometheus | grep -iE "reload|block|corrupt"
   ```
3. Check disk space and whether the mount is writable:
   ```bash
   kubectl -n monitoring exec <prometheus-pod> -c prometheus -- df -h /prometheus
   kubectl -n monitoring exec <prometheus-pod> -c prometheus -- ls -la /prometheus
   ```
4. List blocks and their time ranges to spot the odd one out:
   ```bash
   promtool tsdb list /prometheus
   ```
5. Check node kernel logs for I/O errors on the underlying disk.

## Fixing it

Free or expand disk space if it is full, and fix ownership if permissions changed. For a corrupted block, stop Prometheus, move that block directory out of the data path (keep it for a while rather than deleting it), and start Prometheus again. You lose that block's time range, but everything else loads. If the storage itself is throwing errors, move the volume to healthy storage before doing anything else.

## Related alerts

- [PrometheusTSDBCompactionsFailing](/runbooks/prometheustsdbcompactionsfailing/): usually fails alongside for the same disk or corruption reason.
- [PrometheusNotIngestingSamples](/runbooks/prometheusnotingestingsamples/): the worst-case outcome of a broken TSDB.
