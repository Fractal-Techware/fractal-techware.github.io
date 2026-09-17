---
title: "EtcdHighFsyncDurations: runbook and fix"
description: "EtcdHighFsyncDurations means etcd WAL fsync latency is high, threatening leader stability and API performance. How to confirm a slow disk and fix it."
permalink: /runbooks/etcdhighfsyncdurations/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: etcd
severity: warning
cta:
  title: Get this alert, tested
  text: "EtcdHighFsyncDurations is one of 8 etcd alerts in the pack of 179 Prometheus alerts, all unit tested with promtool and documented."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=etcdhighfsyncdurations
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# EtcdHighFsyncDurations

etcd is taking too long to fsync its write-ahead log to disk.

| | |
|---|---|
| Severity | warning |
| Source | etcd 3.5+ `/metrics` (kube-prometheus-stack job `kube-etcd`) |
| Key metric | `etcd_disk_wal_fsync_duration_seconds_bucket` |

## What it means

Before etcd acknowledges any write, it appends the entry to its WAL and calls fsync. The alert fires when the p99 fsync time on a member stays high for several minutes. etcd's own guidance is that p99 should normally be around 10ms; sustained values far above that mean the disk cannot keep up.

Slow fsync slows every write in the cluster, and on the leader it delays heartbeats, which leads to leader elections and, in the worst case, members dropping out.

## Common causes

- **Network or shared storage** (network-attached volumes with low IOPS limits, burst credits exhausted).
- **Noisy neighbours** on the same disk: container logs, images, other databases.
- **HDD or throttled cloud volumes** instead of SSDs.
- **Large bursts of writes** from the API server, e.g. mass creation of objects or events.
- **Defragmentation or snapshot** running on the member.

## First checks

1. Compare members; one slow member points to that node's disk:
   ```promql
   histogram_quantile(0.99, sum by (instance, le) (rate(etcd_disk_wal_fsync_duration_seconds_bucket{job=~".*etcd.*"}[5m])))
   ```
2. Check disk utilisation on the node (node_exporter):
   ```promql
   rate(node_disk_io_time_seconds_total{instance=~"<node>.*"}[5m])
   rate(node_disk_write_time_seconds_total[5m]) / rate(node_disk_writes_completed_total[5m])
   ```
3. On the node, see what else writes to the same device:
   ```bash
   df -h /var/lib/etcd
   sudo iostat -x 5 3
   sudo iotop -o -b -n 3
   ```
4. Look for slow operation warnings in the etcd logs:
   ```bash
   kubectl -n kube-system logs etcd-<node> --since=30m | grep -iE 'slow fdatasync|took too long'
   ```
5. Optionally run a short benchmark against a healthy cluster outside peak hours:
   ```bash
   # kubeadm layout; adjust pod name, endpoint and cert paths for your setup
   e() { kubectl -n kube-system exec etcd-<node> -- etcdctl --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key "$@"; }
   e check perf
   ```

## Fixing it

Move `/var/lib/etcd` to a dedicated local SSD or a provisioned-IOPS volume, separate from container runtime and log storage. Raise the volume's IOPS or throughput tier on cloud providers. Reduce write pressure from the API server, e.g. excessive Events or controllers updating objects in loops.

## Related alerts

- [EtcdHighCommitDurations](/runbooks/etcdhighcommitdurations/): the other disk latency signal, usually elevated too.
- [EtcdHighNumberOfLeaderChanges](/runbooks/etcdhighnumberofleaderchanges/): slow fsync on the leader causes elections.
- [EtcdNoLeader](/runbooks/etcdnoleader/): extreme disk latency can block elections entirely.
