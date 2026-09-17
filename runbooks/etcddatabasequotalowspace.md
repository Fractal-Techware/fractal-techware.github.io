---
title: "EtcdDatabaseQuotaLowSpace: runbook and fix"
description: "EtcdDatabaseQuotaLowSpace means the etcd database is near its size quota and will soon reject writes. How to compact, defragment and clear NOSPACE."
permalink: /runbooks/etcddatabasequotalowspace/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: etcd
severity: "warning, critical"
cta:
  title: Get this alert, tested
  text: "EtcdDatabaseQuotaLowSpace is one of 8 etcd alerts in the pack of 179, with warning and critical tiers covered by promtool unit tests."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=etcddatabasequotalowspace
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# EtcdDatabaseQuotaLowSpace

The etcd database file is approaching its configured size quota.

| | |
|---|---|
| Severity | warning, critical |
| Source | etcd 3.5+ `/metrics` (kube-prometheus-stack job `kube-etcd`) |
| Key metrics | `etcd_mvcc_db_total_size_in_bytes`, `etcd_server_quota_backend_bytes`, `etcd_mvcc_db_total_size_in_use_in_bytes` |

## What it means

etcd enforces a backend quota (`--quota-backend-bytes`, 2 GiB by default). When the database file reaches it, etcd raises a `NOSPACE` alarm and rejects every write until the space is reclaimed and the alarm is cleared. For Kubernetes, that means the API server can no longer create or update anything.

The warning fires when the database is well into its quota; critical means it is very close and writes could stop at any moment.

The file size only shrinks after defragmentation. Compaction frees space inside the file, but the file stays the same size.

## Common causes

- **Fragmentation**: lots of deleted or updated data that was compacted but never defragmented.
- **Compaction not running**: the API server normally compacts every few minutes; a broken or disabled compaction lets history pile up.
- **Object explosion**: huge numbers of Events, Secrets, ConfigMaps or custom resources.
- **Large objects**, such as big ConfigMaps or Helm release Secrets with long history.

## First checks

1. Check usage per member, and how much is reclaimable:
   ```promql
   etcd_mvcc_db_total_size_in_bytes / etcd_server_quota_backend_bytes
   etcd_mvcc_db_total_size_in_bytes - etcd_mvcc_db_total_size_in_use_in_bytes
   ```
2. Check status and alarms:
   ```bash
   # kubeadm layout; adjust pod name, endpoint and cert paths for your setup
   e() { kubectl -n kube-system exec etcd-<node> -- etcdctl --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key "$@"; }
   e endpoint status --cluster -w table
   e alarm list
   ```
3. Find what fills the database:
   ```promql
   topk(15, apiserver_storage_objects)
   ```
   ```bash
   kubectl get secrets -A --field-selector type=helm.sh/release.v1 --no-headers | wc -l
   ```

## Fixing it

1. If the in-use size is much smaller than the total, defragment one member at a time, followers first, by pointing the helper at each member's pod (`etcd-<node>`) in turn:
   ```bash
   e defrag
   ```
2. If in-use is also high, compact old revisions first, then defragment:
   ```bash
   rev=$(e endpoint status -w json | grep -o '"revision":[0-9]*' | head -1 | cut -d: -f2)
   e compact "$rev"
   ```
3. Delete what is actually taking space: old Events, stale custom resources, Helm history (`--history-max`).
4. Once below quota, clear the alarm so writes resume: `e alarm disarm`.

Raising `--quota-backend-bytes` buys time (etcd recommends staying at or below 8 GiB) but does not fix growth.

## Related alerts

- [EtcdHighCommitDurations](/runbooks/etcdhighcommitdurations/): large databases commit more slowly.
- [EtcdHighNumberOfFailedGRPCRequests](/runbooks/etcdhighnumberoffailedgrpcrequests/): writes rejected under `NOSPACE` show up as failed requests.
