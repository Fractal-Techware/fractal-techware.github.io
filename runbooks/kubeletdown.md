---
title: "KubeletDown: runbook and fix"
description: "KubeletDown means Prometheus cannot scrape any kubelet in the cluster. How to tell a monitoring misconfiguration from a real node-wide failure."
permalink: /runbooks/kubeletdown/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes control plane & kubelet
severity: critical
cta:
  title: Get this alert, tested
  text: "KubeletDown is one of 12 Kubernetes control plane and kubelet alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeletdown
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeletDown

Prometheus has not been able to scrape a single kubelet for a while.

| | |
|---|---|
| Severity | critical |
| Source | kubelet `/metrics` and cAdvisor (kube-prometheus-stack job `kubelet`) |
| Key metric | `up` |

## What it means

This alert does not fire for one bad node. It fires when there is no healthy kubelet target at all over a sustained window. That is rarely every node dying at once; far more often the kubelet scrape itself is broken cluster-wide.

Either way it matters: kubelet and cAdvisor metrics feed container CPU and memory dashboards, volume usage alerts and pod-level alerts, and all of those go quiet.

## Common causes

- The kubelet Service that the Prometheus Operator maintains (`kube-system/<release>-kubelet`) was deleted or has no endpoints.
- The ServiceMonitor for kubelet was disabled or its job label changed in a chart upgrade.
- Prometheus lost RBAC access to `nodes/metrics` or `nodes/proxy`.
- A NetworkPolicy, firewall or security group blocks port 10250 from the Prometheus pods.
- kubelet TLS or authentication changes (webhook authn disabled, new serving certificates not trusted).
- Genuinely all nodes down, for example after a bad node image rollout.

## First checks

1. Are the nodes actually healthy?
   ```bash
   kubectl get nodes
   ```
   If they are all `Ready`, the kubelets are alive and this is a scrape problem.
2. Look at the scrape error in **Status → Targets** for the kubelet job, or query:
   ```promql
   count by (job) (up{job=~".*kubelet.*"})
   ```
3. Check the Service and endpoints:
   ```bash
   kubectl -n kube-system get svc,endpoints -l app.kubernetes.io/name=kubelet
   ```
4. Test access with the Prometheus service account:
   ```bash
   kubectl auth can-i get nodes/metrics --as=system:serviceaccount:monitoring:<prometheus-sa>
   ```
5. Fetch metrics through the API server proxy to rule out the kubelet itself:
   ```bash
   kubectl get --raw /api/v1/nodes/<node>/proxy/metrics | head
   ```

## Fixing it

Restore the kubelet Service (restarting the Prometheus Operator recreates it when kubelet service management is enabled), re-enable the ServiceMonitor, fix the ClusterRole, or open port 10250 from the monitoring namespace. If nodes are really down, treat it as a node outage.

## Related alerts

- [KubeAPIDown](/runbooks/kubeapidown/): check this first; a dead API server breaks service discovery too.
- [KubeletPlegDurationHigh](/runbooks/kubeletplegdurationhigh/): a slow but still running kubelet.
- [KubeNodeNotReady](/runbooks/kubenodenotready/): per-node kubelet failures.
