---
title: "EtcdInsufficientMembers: runbook and fix"
description: "EtcdInsufficientMembers means too few etcd members are up to keep quorum, so the cluster cannot accept writes. How to restore quorum fast."
permalink: /runbooks/etcdinsufficientmembers/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: etcd
severity: critical
cta:
  title: Get this alert, tested
  text: "EtcdInsufficientMembers is one of 8 etcd alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=etcdinsufficientmembers
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# EtcdInsufficientMembers

Fewer than a majority of etcd members are reachable, so the cluster has lost or is about to lose quorum.

| | |
|---|---|
| Severity | critical |
| Source | etcd 3.5+ `/metrics` scraped by Prometheus (kube-prometheus-stack job `kube-etcd`) |
| Key metric | `up` for the etcd job |

## What it means

etcd needs a majority of members (2 of 3, 3 of 5) to elect a leader and commit writes. The alert counts how many etcd scrape targets are up and fires when that count drops below a majority of the configured targets for a few minutes.

On Kubernetes this is a control plane outage: the API server cannot write, so no pods are scheduled, no deployments roll out, and leases and endpoints stop updating. Running workloads keep going, but anything that needs the API fails.

Note that `up` measures whether Prometheus can scrape etcd. A broken scrape config or network policy can trigger this alert while etcd itself is healthy, so confirm with etcdctl.

## Common causes

- **Control plane nodes down**: several nodes rebooted, drained or lost at once.
- **Disk full or failing** on etcd hosts, so members crash.
- **Network partition** between control plane nodes or availability zones.
- **Expired peer or server certificates**, so members reject each other.
- **Scrape problem only**: changed metrics port, certificates or firewall.

## First checks

1. See which targets are down:
   ```promql
   up{job=~".*etcd.*"} == 0
   ```
2. Ask etcd directly from a healthy member:
   ```bash
   # kubeadm layout; adjust pod name, endpoint and cert paths for your setup
   e() { kubectl -n kube-system exec etcd-<node> -- etcdctl --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key "$@"; }
   e endpoint health --cluster -w table
   e endpoint status --cluster -w table
   e member list -w table
   ```
3. On a down member's node, check the process and its logs:
   ```bash
   kubectl -n kube-system get pods -l component=etcd -o wide
   sudo crictl ps -a | grep etcd
   sudo crictl logs <etcd-container-id> 2>&1 | tail -50
   ```
4. Check disk and certificates on that node:
   ```bash
   df -h /var/lib/etcd
   sudo openssl x509 -noout -enddate -in /etc/kubernetes/pki/etcd/peer.crt
   ```

## Fixing it

Bring the failed members back on their existing data directories; they rejoin automatically. Fix disk space or renew certificates (`kubeadm certs renew etcd-peer etcd-server` on kubeadm) as needed. If quorum is permanently lost because a majority of data directories are gone, restore from a snapshot with `etcdutl snapshot restore` following the etcd disaster recovery guide. Do not remove and re-add members while quorum is lost.

## Related alerts

- [EtcdMembersDown](/runbooks/etcdmembersdown/): the earlier stage, with quorum still intact.
- [EtcdNoLeader](/runbooks/etcdnoleader/): members up but unable to elect a leader.
- [KubeAPIDown](/runbooks/kubeapidown/): the API server impact of losing etcd.
