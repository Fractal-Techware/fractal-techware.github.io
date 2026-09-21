---
title: "EtcdHighNumberOfFailedGRPCRequests: runbook and fix"
description: "EtcdHighNumberOfFailedGRPCRequests means a notable share of etcd gRPC calls fail. How to read the method and code labels and find the real cause."
permalink: /runbooks/etcdhighnumberoffailedgrpcrequests/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: etcd
severity: warning
cta:
  title: Get this alert, tested
  text: "EtcdHighNumberOfFailedGRPCRequests is one of 8 etcd alerts in the pack of 179, each with a promtool unit test and a runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=etcdhighnumberoffailedgrpcrequests
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# EtcdHighNumberOfFailedGRPCRequests

A significant share of gRPC requests to an etcd member are ending in server-side error codes.

| | |
|---|---|
| Severity | warning |
| Source | etcd 3.5+ `/metrics` (kube-prometheus-stack job `kube-etcd`) |
| Key metric | `grpc_server_handled_total` (labels `grpc_service`, `grpc_method`, `grpc_code`) |

## What it means

etcd serves its API over gRPC and counts each finished call by service, method and status code. The alert looks at codes that indicate a server problem (`Unavailable`, `DeadlineExceeded`, `ResourceExhausted`, `Internal` and similar) rather than client mistakes such as `NotFound` or `InvalidArgument`, and fires when their share on a method stays elevated for several minutes.

The method tells you who is affected. Failures on `Range`, `Txn` or `Put` hit the Kubernetes API server directly. Failures on `Watch` or `LeaseKeepAlive` can come from clients disconnecting and are sometimes noise.

## Common causes

- **No leader or elections in progress**, returning `Unavailable`.
- **Slow disk or overload**, causing `DeadlineExceeded` on requests.
- **Database over quota** (`NOSPACE` alarm), returning `ResourceExhausted` on writes.
- **Too many requests** from a misbehaving client or controller.
- **Watch streams cancelled** by clients, which some versions count as errors.

## First checks

1. Find the failing method and code:
   ```promql
   sum by (instance, grpc_service, grpc_method, grpc_code) (rate(grpc_server_handled_total{job=~".*etcd.*", grpc_code!="OK"}[5m]))
   ```
2. Check leader stability and alarms:
   ```bash
   # kubeadm layout; adjust pod name, endpoint and cert paths for your setup
   e() { kubectl -n kube-system exec etcd-<node> -- etcdctl --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key "$@"; }
   e endpoint status --cluster -w table
   e alarm list
   ```
3. Check disk latency and database size:
   ```promql
   histogram_quantile(0.99, sum by (instance, le) (rate(etcd_disk_wal_fsync_duration_seconds_bucket[5m])))
   etcd_mvcc_db_total_size_in_bytes / etcd_server_quota_backend_bytes
   ```
4. Look at etcd and API server logs for the matching errors:
   ```bash
   kubectl -n kube-system logs etcd-<node> --since=15m | grep -iE 'error|took too long|rejected'
   kubectl -n kube-system logs kube-apiserver-<node> --since=15m | grep -i etcd | tail -30
   ```

## Fixing it

Fix the underlying condition: restore leadership, speed up the disk, or free space and disarm the `NOSPACE` alarm. If the errors are only on `Watch` with codes caused by client cancellation, and the API server is otherwise healthy, exclude that method from the alert.

## Related alerts

- [EtcdNoLeader](/runbooks/etcdnoleader/): leaderless members return `Unavailable`.
- [EtcdDatabaseQuotaLowSpace](/runbooks/etcddatabasequotalowspace/): quota exhaustion rejects writes.
- [KubeAPIErrorsHigh](/runbooks/kubeapierrorshigh/): the API server side of the same failures.
