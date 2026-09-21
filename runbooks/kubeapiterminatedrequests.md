---
title: "KubeAPITerminatedRequests: runbook and fix"
description: "KubeAPITerminatedRequests means the Kubernetes API server is dropping a large share of requests. Find the flow schema and client causing it."
permalink: /runbooks/kubeapiterminatedrequests/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes control plane & kubelet
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeAPITerminatedRequests is part of a pack of 179 Prometheus alerts, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeapiterminatedrequests
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeAPITerminatedRequests

The API server is actively rejecting or cutting off a large fraction of incoming requests instead of serving them.

| | |
|---|---|
| Severity | warning |
| Source | kube-apiserver `/metrics` |
| Key metrics | `apiserver_request_terminations_total`, `apiserver_request_total` |

## What it means

When the API server is overloaded, API Priority and Fairness (APF) and the in-flight limits start terminating requests, typically with HTTP 429. The alert fires when terminations make up a substantial share of all incoming traffic for several minutes.

Clients retry with backoff, so the visible symptom is everything getting slow: kubectl hangs, controllers lag, and low-priority workloads such as operators or CI jobs starve first.

## Common causes

- A misbehaving controller or operator in a tight loop of LIST or UPDATE calls.
- A burst of pods or nodes starting at once (mass rollout, cluster autoscaler scale-up).
- Priority levels sized too small for legitimate traffic.
- Too few API server replicas, or `--max-requests-inflight` set low.
- Slow etcd causing requests to hold concurrency slots longer.

## First checks

1. See what is being terminated:
   ```promql
   topk(10, sum by (verb, resource, code, component) (rate(apiserver_request_terminations_total{job="apiserver"}[5m])))
   ```
2. See which APF priority level and flow schema is rejecting:
   ```promql
   sum by (priority_level, flow_schema, reason) (rate(apiserver_flowcontrol_rejected_requests_total[5m]))
   ```
3. Check queue pressure per priority level:
   ```promql
   sum by (priority_level) (apiserver_flowcontrol_current_inqueue_requests)
   ```
4. Inspect the APF configuration:
   ```bash
   kubectl get prioritylevelconfigurations,flowschemas
   ```
5. Find the noisy client. The debug endpoint lists flows per user:
   ```bash
   kubectl get --raw /debug/api_priority_and_fairness/dump_requests
   ```

## Fixing it

Stop or scale down the client in a loop, then fix its code (use informers, add backoff). If the traffic is legitimate, give it its own FlowSchema and PriorityLevelConfiguration with more shares, or add API server capacity. Do not raise global in-flight limits blindly: it can move the overload onto etcd.

## Related alerts

- [KubeAPILatencyHigh](/runbooks/kubeapilatencyhigh/): the overload usually shows as latency first.
- [KubeAPIErrorsHigh](/runbooks/kubeapierrorshigh/): timeouts may also surface as 5xx.
- [KubeClientErrors](/runbooks/kubeclienterrors/): the client side of the same problem.
