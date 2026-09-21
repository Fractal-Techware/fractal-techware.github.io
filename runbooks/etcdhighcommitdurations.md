---
title: "EtcdHighCommitDurations: runbook and fix"
description: "EtcdHighCommitDurations means etcd backend commits to its bbolt database are slow. How to tell disk latency from a bloated database and fix it."
permalink: /runbooks/etcdhighcommitdurations/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: etcd
severity: warning
cta:
  title: Get this alert, tested
  text: "EtcdHighCommitDurations is part of the etcd set in a pack of 179 alerts, each shipped with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=etcdhighcommitdurations
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# EtcdHighCommitDurations

etcd is slow to commit batched changes into its backend database.

| | |
|---|---|
| Severity | warning |
| Source | etcd 3.5+ `/metrics` (kube-prometheus-stack job `kube-etcd`) |
| Key metric | `etcd_disk_backend_commit_duration_seconds_bucket` |

## What it means

After entries are written to the WAL, etcd applies them to its bbolt database and periodically commits that transaction to disk. The alert fires when p99 commit time on a member stays high for several minutes. Normal values are in the tens of milliseconds.

Slow commits back up the apply loop, so the API server sees higher latency and, eventually, `etcdserver: request timed out` errors.

## Common causes

- **Slow or contended disk**, the same root causes as slow WAL fsync.
- **Large, fragmented database**: bigger files mean more pages to write per commit.
- **Heavy write load** from many objects or frequent updates (Events, Leases, custom resources in tight loops).
- **Defragmentation** or compaction running on the member at the same time.

## First checks

1. Compare commit and fsync latency per member:
   ```promql
   histogram_quantile(0.99, sum by (instance, le) (rate(etcd_disk_backend_commit_duration_seconds_bucket{job=~".*etcd.*"}[5m])))
   histogram_quantile(0.99, sum by (instance, le) (rate(etcd_disk_wal_fsync_duration_seconds_bucket{job=~".*etcd.*"}[5m])))
   ```
   Both high means the disk. Commit high alone suggests database size or load.
2. Check database size and how much of it is actually in use:
   ```promql
   etcd_mvcc_db_total_size_in_bytes
   etcd_mvcc_db_total_size_in_use_in_bytes
   ```
   A large gap means fragmentation that defrag can reclaim.
3. Check write rate and the object types driving it:
   ```promql
   sum(rate(etcd_mvcc_put_total[5m]))
   topk(10, apiserver_storage_objects)
   ```
4. Inspect the member's status and logs:
   ```bash
   # kubeadm layout; adjust pod name, endpoint and cert paths for your setup
   e() { kubectl -n kube-system exec etcd-<node> -- etcdctl --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key "$@"; }
   e endpoint status --cluster -w table
   ```
   ```bash
   kubectl -n kube-system logs etcd-<node> --since=30m | grep -iE 'apply request took too long|slow'
   ```

## Fixing it

Fix disk performance first (dedicated SSD, higher IOPS tier). If the database is fragmented, defragment one member at a time during a quiet period, starting with followers, since defrag blocks that member while it runs. Point the helper at each member's pod (`etcd-<node>`) in turn and run:
```bash
e defrag
```
Reduce object churn by cleaning up unused custom resources and fixing controllers that update objects in loops.

## Related alerts

- [EtcdHighFsyncDurations](/runbooks/etcdhighfsyncdurations/): WAL latency on the same disk.
- [EtcdDatabaseQuotaLowSpace](/runbooks/etcddatabasequotalowspace/): a growing database also slows commits.
