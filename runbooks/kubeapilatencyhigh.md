---
title: "KubeAPILatencyHigh: runbook and fix"
description: "KubeAPILatencyHigh means Kubernetes API server tail latency is too high. Find the slow verbs, resources and clients, and check etcd and webhooks."
permalink: /runbooks/kubeapilatencyhigh/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes control plane & kubelet
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeAPILatencyHigh is one of 12 control plane and kubelet alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeapilatencyhigh
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeAPILatencyHigh

The slowest requests to the Kubernetes API server are taking far longer than they should.

| | |
|---|---|
| Severity | warning |
| Source | kube-apiserver `/metrics` |
| Key metric | `apiserver_request_duration_seconds_bucket` (labels `verb`, `resource`) |

## What it means

The alert looks at tail (p99) latency of ordinary read and write verbs, excluding long-running calls such as `exec`, `logs`, `port-forward` and watches. It fires when that tail has stayed in the multi-second range, far above normal, for a sustained window.

Slow API calls make kubectl sluggish, delay controllers reconciling, and can push leader-election renewals past their deadline, causing controller-manager or scheduler restarts.

## Common causes

- etcd disk latency (slow fsync on shared or burstable volumes).
- Large unpaginated LIST calls, e.g. a tool listing all pods or secrets cluster-wide every few seconds.
- Slow admission webhooks adding their timeout to every matching request.
- API server CPU or memory pressure, or too few replicas for the cluster size.
- Very large objects (huge ConfigMaps, CRDs with big status fields).

## First checks

1. Find which verbs and resources are slow:
   ```promql
   topk(10, histogram_quantile(0.99, sum by (verb, resource, le) (rate(apiserver_request_duration_seconds_bucket{job="apiserver", verb!~"WATCH|CONNECT"}[5m]))))
   ```
2. Find heavy LIST traffic:
   ```promql
   topk(10, sum by (resource, scope) (rate(apiserver_request_total{job="apiserver", verb="LIST"}[5m])))
   ```
3. Check etcd latency from the API server side:
   ```promql
   histogram_quantile(0.99, sum by (operation, type, le) (rate(etcd_request_duration_seconds_bucket[5m])))
   ```
4. Check webhook latency:
   ```promql
   histogram_quantile(0.99, sum by (name, le) (rate(apiserver_admission_webhook_admission_duration_seconds_bucket[5m])))
   ```
5. Identify noisy clients in the audit log (if enabled) by `userAgent`, or check API server resource usage:
   ```bash
   kubectl -n kube-system top pods -l component=kube-apiserver
   ```

## Fixing it

Move etcd to faster, dedicated disks. Get the noisy client to use informers or paginated lists, or cap it with a FlowSchema. Shorten webhook `timeoutSeconds` and scope their rules tightly. Give the API server more CPU or replicas when it is simply undersized.

## Related alerts

- [KubeAPIErrorsHigh](/runbooks/kubeapierrorshigh/): slow requests often turn into timeouts.
- [KubeAPITerminatedRequests](/runbooks/kubeapiterminatedrequests/): the API server starts shedding load.
- [EtcdHighFsyncDurations](/runbooks/etcdhighfsyncdurations/): the most common root cause.
