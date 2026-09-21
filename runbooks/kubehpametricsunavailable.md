---
title: "KubeHpaMetricsUnavailable: runbook and fix"
description: "KubeHpaMetricsUnavailable means an HPA reports ScalingActive=False because it cannot read its metrics. How to fix metrics-server or the adapter."
permalink: /runbooks/kubehpametricsunavailable/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes autoscaling (HPA)
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeHpaMetricsUnavailable is one of the HPA alerts in the pack of 179 Prometheus alerts, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubehpametricsunavailable
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeHpaMetricsUnavailable

A HorizontalPodAutoscaler cannot get the metrics it scales on, so it has stopped making scaling decisions.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x (autoscaling/v2) |
| Key metric | `kube_horizontalpodautoscaler_status_condition` (`condition="ScalingActive"`, `status="false"`) |

## What it means

The HPA's `ScalingActive` condition turns `False` when it cannot compute a replica count, most often because a metric query failed. When that lasts for a sustained period, this alert fires. Reasons you will see include `FailedGetResourceMetric`, `FailedGetPodsMetric`, `FailedGetObjectMetric` and `FailedGetExternalMetric`. `ScalingDisabled` means the target was scaled to zero by hand.

The workload is frozen at its current size. It will not grow under load or shrink when idle.

## Common causes

- metrics-server is down, not ready, or cannot scrape kubelets (TLS or network issues).
- Containers have no CPU or memory `requests`, so utilization cannot be computed.
- prometheus-adapter or KEDA is down, or its rule no longer matches the series name after a relabel.
- The custom or external metric has no data (the exporter stopped, the label selector is wrong).
- New pods not yet reporting metrics during a large rollout.

## First checks

1. Read the condition reason and message:
   ```bash
   kubectl -n <ns> describe hpa <hpa>
   ```
2. Check the metrics APIs are registered and available:
   ```bash
   kubectl get apiservices | grep -E 'metrics.k8s.io|custom.metrics|external.metrics'
   ```
3. For resource metrics, test metrics-server directly:
   ```bash
   kubectl -n <ns> top pods
   kubectl -n kube-system logs deploy/metrics-server --tail=50
   ```
4. Confirm every container in the target has requests for the metric's resource:
   ```bash
   kubectl -n <ns> get deploy <name> -o jsonpath='{range .spec.template.spec.containers[*]}{.name}: {.resources.requests}{"\n"}{end}'
   ```
5. For custom metrics, query the adapter and check the backing series exists in Prometheus:
   ```bash
   kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1/namespaces/<ns>/pods/*/<metric>"
   ```

## Fixing it

Restore the metrics source: restart or fix metrics-server (commonly its `--kubelet-preferred-address-types` or kubelet TLS settings), or fix the adapter's rules. Add missing requests to every container, including sidecars. Scaling resumes on the next HPA sync once metrics return.

## Related alerts

- [KubeHpaUnableToScale](/runbooks/kubehpaunabletoscale/): the other condition that stops autoscaling.
- [KubeHpaMaxedOut](/runbooks/kubehpamaxedout/): a bad metric can also pin an HPA at max.
- [KubeAggregatedAPIDown](/runbooks/kubeaggregatedapidown/): the metrics APIs are aggregated APIs.
