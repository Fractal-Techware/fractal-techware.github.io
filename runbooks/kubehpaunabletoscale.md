---
title: "KubeHpaUnableToScale: runbook and fix"
description: "KubeHpaUnableToScale means an HPA reports AbleToScale=False and cannot read or update its target's scale. How to find the cause and fix it."
permalink: /runbooks/kubehpaunabletoscale/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes autoscaling (HPA)
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeHpaUnableToScale is one of 4 Kubernetes autoscaling alerts in the pack of 179, all with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubehpaunabletoscale
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeHpaUnableToScale

A HorizontalPodAutoscaler has been reporting that it cannot scale its target, so autoscaling for that workload is effectively off.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x (autoscaling/v2) |
| Key metric | `kube_horizontalpodautoscaler_status_condition` (`condition="AbleToScale"`, `status="false"`) |

## What it means

Every HPA publishes status conditions. `AbleToScale` says whether the controller can fetch and update the target's `/scale` subresource. When it has been `False` for a sustained period, this alert fires. The condition's `reason` tells you where it broke, typically `FailedGetScale` (cannot read the target) or `FailedUpdateScale` (cannot write the new replica count).

The workload stays at whatever replica count it had, whatever the load does.

## Common causes

- `scaleTargetRef` names a Deployment or StatefulSet that was renamed or deleted.
- Wrong `apiVersion` or `kind` in `scaleTargetRef`, or a custom resource without a scale subresource.
- An admission webhook or policy engine rejects the replica update.
- A custom resource's operator or CRD is not installed or its API is unavailable.

## First checks

1. List HPAs in this state:
   ```promql
   kube_horizontalpodautoscaler_status_condition{condition="AbleToScale", status="false"} == 1
   ```
2. Read the condition reason and message:
   ```bash
   kubectl -n <ns> describe hpa <hpa>
   kubectl -n <ns> get hpa <hpa> -o jsonpath='{range .status.conditions[*]}{.type}={.status} {.reason}: {.message}{"\n"}{end}'
   ```
3. Confirm the target exists and matches `scaleTargetRef`:
   ```bash
   kubectl -n <ns> get hpa <hpa> -o jsonpath='{.spec.scaleTargetRef}'
   kubectl -n <ns> get <kind> <name>
   ```
4. Check the scale subresource directly:
   ```bash
   kubectl get --raw /apis/<group>/<version>/namespaces/<ns>/<resource>/<name>/scale
   ```
5. Look for webhook denials in events:
   ```bash
   kubectl -n <ns> get events --field-selector involvedObject.name=<hpa>
   ```

## Fixing it

Point `scaleTargetRef` at the correct kind, API version and name. For custom resources, make sure the CRD defines a scale subresource and its API is served. If a webhook or policy blocks the update, add an exception for the HPA controller. Once fixed, the condition flips back to `True` on the next sync.

## Related alerts

- [KubeHpaMetricsUnavailable](/runbooks/kubehpametricsunavailable/): the other HPA condition that silently disables scaling.
- [KubeHpaReplicasMismatch](/runbooks/kubehpareplicasmismatch/): scale was requested but pods did not follow.
- [KubeHpaMaxedOut](/runbooks/kubehpamaxedout/): scaling works but has hit its ceiling.
