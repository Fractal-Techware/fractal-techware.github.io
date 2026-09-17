---
title: "EtcdNoLeader: runbook and fix"
description: "EtcdNoLeader means an etcd member reports no leader and cannot serve writes. How to check quorum, network and disk latency and restore leadership."
permalink: /runbooks/etcdnoleader/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: etcd
severity: critical
cta:
  title: Get this alert, tested
  text: "EtcdNoLeader is one of 8 etcd alerts in the pack of 179, each tested with promtool and paired with a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=etcdnoleader
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# EtcdNoLeader

An etcd member currently has no leader, so it cannot process writes or linearizable reads.

| | |
|---|---|
| Severity | critical |
| Source | etcd 3.5+ `/metrics` (kube-prometheus-stack job `kube-etcd`) |
| Key metric | `etcd_server_has_leader` (1 when the member knows a leader, 0 otherwise) |

## What it means

Each member reports whether it knows who the current Raft leader is. The alert fires quickly once a member reports no leader. If one member is affected, it is isolated from the others. If all members are affected, the cluster has no leader and the Kubernetes API server cannot write anything.

Short gaps happen during a normal election. A leaderless state that persists means elections keep failing, usually because members cannot talk to each other in time or there is no quorum.

## Common causes

- **Lost quorum**: too many members down to elect a leader.
- **Network partition** isolating the member from its peers (firewall on port 2380, security group change).
- **Very slow disk** so heartbeats and votes miss their deadlines.
- **CPU starvation** of the etcd process on an overloaded control plane node.
- **Peer TLS failure** after a certificate rotation.

## First checks

1. See which members report no leader, and whether any member claims to be leader:
   ```promql
   etcd_server_has_leader{job=~".*etcd.*"}
   etcd_server_is_leader{job=~".*etcd.*"}
   ```
2. Check the cluster view:
   ```bash
   # kubeadm layout; adjust pod name, endpoint and cert paths for your setup
   e() { kubectl -n kube-system exec etcd-<node> -- etcdctl --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key "$@"; }
   e endpoint status --cluster -w table
   ```
   The `IS LEADER` and `RAFT TERM` columns show whether a leader exists and whether terms keep increasing.
3. Check peer latency:
   ```promql
   histogram_quantile(0.99, sum by (instance, To, le) (rate(etcd_network_peer_round_trip_time_seconds_bucket[5m])))
   ```
4. Look at member logs for election and connection errors:
   ```bash
   kubectl -n kube-system logs etcd-<node> --since=15m | grep -iE 'lost leader|elect|prober|rafthttp|timed out'
   ```
5. Verify peer connectivity from each control plane node: `nc -zv <peer-ip> 2380`.

## Fixing it

Restore the network path or firewall rules between members, or bring back missing members to regain quorum. If the node is CPU starved, move other workloads off control plane nodes. For slow disks, move etcd to dedicated SSD storage. If the member is isolated but others are healthy, restarting just that member is safe.

## Related alerts

- [EtcdInsufficientMembers](/runbooks/etcdinsufficientmembers/): no quorum means no leader.
- [EtcdHighNumberOfLeaderChanges](/runbooks/etcdhighnumberofleaderchanges/): the unstable, flapping version of this problem.
- [EtcdHighFsyncDurations](/runbooks/etcdhighfsyncdurations/): disk latency that delays heartbeats.
