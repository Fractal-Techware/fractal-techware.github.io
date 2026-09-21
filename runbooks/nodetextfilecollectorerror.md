---
title: "NodeTextFileCollectorError: runbook and fix"
description: "NodeTextFileCollectorError means node_exporter cannot parse a .prom file in its textfile directory. How to find the bad file and fix the writer."
permalink: /runbooks/nodetextfilecollectorerror/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeTextFileCollectorError is one of 25 node_exporter alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodetextfilecollectorerror
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeTextFileCollectorError

node_exporter is failing to read one or more metric files that a script or cron job drops into its textfile directory.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `textfile` collector (`--collector.textfile.directory`) |
| Key metrics | `node_textfile_scrape_error`, `node_textfile_mtime_seconds` |

## What it means

The textfile collector reads every `*.prom` file in the configured directory on each scrape. If any file cannot be parsed or read, `node_textfile_scrape_error` is set to 1. The alert fires when that has been true for a sustained period, so a one-off race with a writer does not page anyone.

When parsing fails, the metrics from the broken file are missing. Anything built on them, such as backup freshness, package update counts, or RAID controller status from a vendor script, silently goes stale or disappears.

## Common causes

- The writer is not atomic: node_exporter reads a half-written file.
- Invalid exposition format: missing newline at the end, bad label quoting, non-numeric values.
- The same metric name appears in two files with different `HELP` or `TYPE` lines, or duplicate series with identical labels.
- A metric in the file collides with one node_exporter already exports.
- File permissions or ownership prevent the exporter's user from reading it.

## First checks

1. Find affected hosts:
   ```promql
   node_textfile_scrape_error == 1
   ```
2. The exporter log names the file and the parse error:
   ```bash
   journalctl -u node_exporter --since "1 hour ago" --no-pager | grep -i textfile
   ```
   In Kubernetes, `kubectl -n monitoring logs <node-exporter-pod> | grep -i textfile`.
3. Validate each file with promtool:
   ```bash
   for f in /var/lib/node_exporter/textfile_collector/*.prom; do
     echo "== $f"; promtool check metrics < "$f"
   done
   ```
   `promtool check metrics` also prints lint warnings; focus on the errors.
4. Check which files are old (a stale writer):
   ```promql
   time() - node_textfile_mtime_seconds > 3600
   ```
5. Check ownership and permissions: `ls -l <textfile-dir>`.

## Fixing it

Fix or remove the broken file, and the error clears on the next scrape. To stop it recurring, make every writer atomic: write to a temporary file in the same directory with a different extension, then `mv` it into place. The `sponge` utility from moreutils does this in one step. Give each script its own metric prefix so files never redefine each other's metrics.

## Related alerts

- [NodeSystemdServiceFailed](/runbooks/nodesystemdservicefailed/): the timer or service that writes the file may have failed.
- [NodeExporterDown](/runbooks/nodeexporterdown/): if the exporter is down, no textfile metrics are collected at all.
- [NodeFilesystemAlmostOutOfSpace](/runbooks/nodefilesystemalmostoutofspace/): a full disk truncates metric files mid-write.
