---
title: "KubeSchedulerDown: runbook and fix"
description: "KubeSchedulerDown means kube-scheduler stopped being scrapable after previously working. Check the static pod, bind address and leader election."
permalink: /runbooks/kubeschedulerdown/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes control plane & kubelet
severity: critical
cta:
  title: Get this alert, tested
  text: "KubeSchedulerDown is one of 12 control plane and kubelet alerts in the pack of 179, each tested with promtool and shipped with a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeschedulerdown
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeSchedulerDown

kube-scheduler used to be monitored in this cluster and now no instance of it is answering.

| | |
|---|---|
| Severity | critical |
| Source | kube-scheduler `/metrics` (HTTPS, port 10259) |
| Key metric | `up` |

## What it means

The alert only considers clusters where the scheduler was successfully scraped at some point recently, so managed clusters that never expose the scheduler do not trigger it. It fires when every scheduler target has then been down for a sustained period.

Without a scheduler, running pods keep running, but new pods stay `Pending` forever: rollouts, scale-ups, evicted pods and jobs all stop making progress.

## Common causes

- The kube-scheduler static pod crashed, often after a manifest edit in `/etc/kubernetes/manifests/` with a typo.
- Its kubeconfig certificate expired, so it cannot talk to the API server.
- A kubeadm upgrade reset `--bind-address` to `127.0.0.1`, making metrics unreachable from Prometheus while the scheduler still works.
- The control plane node hosting it is down.

## First checks

1. Is anything actually unscheduled?
   ```bash
   kubectl get pods -A --field-selector=status.phase=Pending
   ```
   Fresh pods being scheduled means the scheduler works and only the scrape broke.
2. Check the scheduler pods and restarts:
   ```bash
   kubectl -n kube-system get pods -l component=kube-scheduler -o wide
   kubectl -n kube-system logs -l component=kube-scheduler --tail=100
   ```
3. See who holds the leader lease:
   ```bash
   kubectl -n kube-system get lease kube-scheduler -o yaml
   ```
4. On a control plane node, check the container and the bind address:
   ```bash
   sudo crictl ps -a --name kube-scheduler
   sudo grep bind-address /etc/kubernetes/manifests/kube-scheduler.yaml
   ```
5. Check certificate expiry: `sudo kubeadm certs check-expiration`.

## Fixing it

Fix the manifest error or renew certificates (`kubeadm certs renew scheduler.conf`), and the kubelet restarts the static pod automatically. If only metrics are unreachable, set `--bind-address=0.0.0.0` (or the node IP) and make sure the scrape uses HTTPS on 10259 with a token that is allowed to read `/metrics`.

## Related alerts

- [KubeControllerManagerDown](/runbooks/kubecontrollermanagerdown/): the same static-pod failure modes apply.
- [KubeAPIDown](/runbooks/kubeapidown/): the scheduler cannot work without the API server.
- [KubeVersionMismatch](/runbooks/kubeversionmismatch/): half-finished upgrades often break components.
