---
title: "KubeHpaMaxedOut: runbook and fix"
description: "KubeHpaMaxedOut means an HPA has been running at maxReplicas for a while and cannot add more pods. How to tell real load from a bad metric."
permalink: /runbooks/kubehpamaxedout/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes autoscaling (HPA)
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeHpaMaxedOut is one of the autoscaling alerts in the pack of 179, each shipped with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubehpamaxedout
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeHpaMaxedOut

A HorizontalPodAutoscaler has been pinned at its maximum replica count, so it has no room left to absorb more load.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x (autoscaling/v2) |
| Key metrics | `kube_horizontalpodautoscaler_status_current_replicas`, `kube_horizontalpodautoscaler_spec_max_replicas` |

## What it means

The workload is running exactly `maxReplicas` pods and has stayed there for a sustained period. HPAs with min equal to max are ignored, since those are fixed on purpose. The HPA's `ScalingLimited` condition will usually show `TooManyReplicas`.

It matters because the autoscaler is no longer protecting you: if load keeps rising, latency and error rates will climb and nothing will react.

## Common causes

- Genuine traffic growth; `maxReplicas` was set for last year's peak.
- A performance regression in a recent release makes each pod handle less.
- A slow dependency (database, external API) keeps pods busy, pushing CPU or queue metrics up.
- Requests set too low, so normal usage looks like high utilization as a percentage.
- A custom or external metric that is wrong or stuck at a high value.

## First checks

1. Rank HPAs by how close they are to their ceiling:
   ```promql
   sort_desc(kube_horizontalpodautoscaler_status_current_replicas / on (namespace, horizontalpodautoscaler) kube_horizontalpodautoscaler_spec_max_replicas)
   ```
2. See the metric values against targets and the scaling conditions:
   ```bash
   kubectl -n <ns> get hpa <hpa>
   kubectl -n <ns> describe hpa <hpa>
   ```
3. Check actual usage against requests:
   ```bash
   kubectl -n <ns> top pods -l <selector>
   kubectl -n <ns> get deploy <name> -o jsonpath='{.spec.template.spec.containers[*].resources}'
   ```
4. Check whether a recent deploy lines up with the change:
   ```bash
   kubectl -n <ns> rollout history deploy/<name>
   ```
5. Look at request rate and latency for the service to confirm the load is real (from your ingress or application metrics).

## Fixing it

If the load is real and the cluster has capacity, raise `maxReplicas`. Confirm nodes, quota and downstream dependencies can take the extra pods first. If a release regressed performance, roll back. If requests are unrealistically small, correct them, since utilization targets are percentages of requests. For a wrong custom metric, fix the metrics pipeline before adding replicas.

## Related alerts

- [KubeHpaReplicasMismatch](/runbooks/kubehpareplicasmismatch/): the HPA wants replicas it cannot get.
- [KubeHpaMetricsUnavailable](/runbooks/kubehpametricsunavailable/): rules out a broken metric source.
- [CPUThrottlingHigh](/runbooks/cputhrottlinghigh/): throttled pods can drive CPU-based scaling to the max.
- [KubeClusterCPURequestsHigh](/runbooks/kubeclustercpurequestshigh/): whether the cluster can fit a higher max.
