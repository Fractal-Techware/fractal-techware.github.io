---
title: "EtcdMembersDown: runbook and fix"
description: "EtcdMembersDown means one or more etcd members are unreachable. The cluster still has quorum but no margin. How to find and recover the member."
permalink: /runbooks/etcdmembersdown/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: etcd
severity: warning
cta:
  title: Get this alert, tested
  text: "EtcdMembersDown is part of the etcd set in a pack of 179 Prometheus alerts, each shipped with promtool unit tests and a runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=etcdmembersdown
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# EtcdMembersDown

At least one etcd member has been unreachable for a while; the cluster still works but has lost its failure tolerance.

| | |
|---|---|
| Severity | warning |
| Source | etcd 3.5+ `/metrics` scraped by Prometheus (kube-prometheus-stack job `kube-etcd`) |
| Key metric | `up` for the etcd job |

## What it means

The alert fires when any etcd scrape target has been down for several minutes. In a 3-member cluster, one member down leaves exactly the 2 needed for quorum. One more failure, even a routine node reboot, takes the Kubernetes control plane down.

Treat this as "fix before the next maintenance window", not as noise. Also check that it is not just a scrape problem: `up` reflects Prometheus' ability to reach the metrics endpoint.

## Common causes

- **Node reboot or drain** of a control plane node that did not come back cleanly.
- **etcd crash looping**: corrupted data directory, disk full, or a bad manifest change in `/etc/kubernetes/manifests/etcd.yaml`.
- **Slow disk** causing the member to fall behind and be restarted.
- **Certificate expiry** on the member's server or peer certificate.
- **Metrics endpoint changed** (for example `--listen-metrics-urls`) so only the scrape fails.

## First checks

1. Identify the down target:
   ```promql
   up{job=~".*etcd.*"} == 0
   ```
2. Check cluster membership and health from a healthy member:
   ```bash
   # kubeadm layout; adjust pod name, endpoint and cert paths for your setup
   e() { kubectl -n kube-system exec etcd-<node> -- etcdctl --endpoints=https://127.0.0.1:2379 \
     --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt \
     --key=/etc/kubernetes/pki/etcd/server.key "$@"; }
   e member list -w table
   e endpoint health --cluster -w table
   ```
   If etcdctl reports the member healthy, the problem is the scrape, not etcd.
3. Inspect the member on its node:
   ```bash
   kubectl -n kube-system describe pod etcd-<down-node>
   sudo crictl ps -a | grep etcd
   sudo crictl logs <etcd-container-id> 2>&1 | grep -iE 'error|panic|fatal' | tail -30
   ```
4. Check disk space and certificate dates:
   ```bash
   df -h /var/lib/etcd
   sudo kubeadm certs check-expiration
   ```

## Fixing it

Fix the underlying cause and let the static pod restart. If the data directory is corrupted, remove the member with `e member remove <id>`, wipe its data directory, re-add it with `e member add` and start it with `--initial-cluster-state=existing`. Do this for one member at a time only, and only while the rest of the cluster is healthy.

## Related alerts

- [EtcdInsufficientMembers](/runbooks/etcdinsufficientmembers/): what this becomes if another member fails.
- [EtcdHighNumberOfLeaderChanges](/runbooks/etcdhighnumberofleaderchanges/): a flapping member often causes elections.
- [EtcdHighFsyncDurations](/runbooks/etcdhighfsyncdurations/): slow disks are a common reason members drop out.
