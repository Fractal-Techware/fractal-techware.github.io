---
title: "EtcdHighNumberOfLeaderChanges: runbook and fix"
description: "EtcdHighNumberOfLeaderChanges means etcd keeps re-electing its leader, stalling writes each time. How to find the disk, network or CPU cause."
permalink: /runbooks/etcdhighnumberofleaderchanges/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: etcd
severity: warning
cta:
  title: Get this alert, tested
  text: "EtcdHighNumberOfLeaderChanges ships with the other etcd alerts in a pack of 179, each with a promtool unit test and a runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=etcdhighnumberofleaderchanges
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# EtcdHighNumberOfLeaderChanges

The etcd cluster has changed leaders several times in a short period.

| | |
|---|---|
| Severity | warning |
| Source | etcd 3.5+ `/metrics` (kube-prometheus-stack job `kube-etcd`) |
| Key metric | `etcd_server_leader_changes_seen_total` |

## What it means

A leader election happens when followers stop receiving heartbeats from the leader within the election timeout. One election after a restart or upgrade is normal. The alert fires when a member has seen repeated leader changes within a short window, which points to an ongoing stability problem.

During each election, writes stall. On Kubernetes that shows up as slow or failed API requests, leader election churn in controllers, and occasional `etcdserver: leader changed` errors.

## Common causes

- **Slow disk I/O** on the leader, delaying heartbeats (the most common cause).
- **Network latency or packet loss** between members, especially across zones.
- **CPU contention**: etcd sharing a node with busy workloads or the API server under load.
- **Rolling restarts** of control plane nodes, which are expected and usually short-lived.
- **Timeouts too tight** for the environment (`--heartbeat-interval`, `--election-timeout`).

## First checks

1. Confirm the churn and whether it is ongoing:
   ```promql
   sum by (instance) (increase(etcd_server_leader_changes_seen_total{job=~".*etcd.*"}[1h]))
   ```
2. Check disk latency on every member:
   ```promql
   histogram_quantile(0.99, sum by (instance, le) (rate(etcd_disk_wal_fsync_duration_seconds_bucket[5m])))
   ```
3. Check peer round trip times:
   ```promql
   histogram_quantile(0.99, sum by (instance, To, le) (rate(etcd_network_peer_round_trip_time_seconds_bucket[5m])))
   ```
4. Check CPU on control plane nodes and etcd logs around the elections:
   ```bash
   kubectl top nodes -l node-role.kubernetes.io/control-plane
   kubectl -n kube-system logs etcd-<node> --since=1h | grep -iE 'elected leader|became leader|lost leader|heartbeat'
   ```
   Log lines about sending heartbeats taking too long point at disk or CPU on the leader.
5. Rule out planned work: recent node reboots or control plane upgrades.

## Fixing it

Put etcd on fast dedicated SSDs and avoid noisy neighbours on the same disk. Reserve CPU for etcd and keep heavy workloads off control plane nodes. For high-latency networks, raise `--heartbeat-interval` and `--election-timeout` together (keeping the election timeout around ten times the heartbeat) on all members.

## Related alerts

- [EtcdHighFsyncDurations](/runbooks/etcdhighfsyncdurations/): the usual root cause.
- [EtcdNoLeader](/runbooks/etcdnoleader/): the failure case when an election does not complete.
- [EtcdMembersDown](/runbooks/etcdmembersdown/): a restarting member triggers elections.
