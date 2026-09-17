---
title: "KubeStatefulSetGenerationMismatch: runbook and fix"
description: "KubeStatefulSetGenerationMismatch means the StatefulSet controller has not observed the latest spec. How to confirm it and get updates applied."
permalink: /runbooks/kubestatefulsetgenerationmismatch/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes workloads
severity: warning
cta:
  title: Get this alert, tested
  text: "The pack of 179 alerts includes KubeStatefulSetGenerationMismatch and 12 other workload alerts, all unit tested with promtool and documented."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubestatefulsetgenerationmismatch
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeStatefulSetGenerationMismatch

A StatefulSet was updated, but the StatefulSet controller has not processed that update, so the change is not being applied.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metrics | `kube_statefulset_metadata_generation`, `kube_statefulset_status_observed_generation` |

## What it means

Kubernetes increments `metadata.generation` on each spec change. The StatefulSet controller records the generation it has acted on in `status.observedGeneration`. When those numbers stay different for several minutes, the controller is behind or not running.

This is distinct from a rollout that is slow or blocked by a bad pod: here the controller has not started on the new spec at all. Image bumps, scaling and config changes to your stateful services are on hold.

## Common causes

- **kube-controller-manager is down**, restarting, or has lost leader election.
- **API server or etcd trouble**: status updates are rejected, throttled or time out.
- **Controller backlog** after a large batch of updates across many workloads.
- **Stale kube-state-metrics**: rare, but a wedged exporter can report old values. Check the object directly before chasing the control plane.

## First checks

1. Compare the two numbers on the live object (this rules out a stale exporter):
   ```bash
   kubectl -n <namespace> get sts <statefulset> \
     -o jsonpath='gen={.metadata.generation} observed={.status.observedGeneration}{"\n"}'
   ```
2. Check whether Deployments are affected too. If they are, the problem is the controller manager, not this StatefulSet.
3. Check controller manager health and leadership:
   ```bash
   kubectl -n kube-system get pods -l component=kube-controller-manager -o wide
   kubectl -n kube-system get lease kube-controller-manager -o yaml | grep -E "holderIdentity|renewTime"
   ```
4. Watch the StatefulSet work queue drain (self-managed control planes):
   ```promql
   workqueue_depth{name="statefulset"}
   ```
5. Scan the controller manager logs for errors against this object:
   ```bash
   kubectl -n kube-system logs <controller-manager-pod> | grep -i "<statefulset>" | tail -30
   ```

## Fixing it

Get kube-controller-manager healthy: fix crash causes (certificates, flags, kubeconfig), and make sure exactly one instance holds the lease. If the API server or etcd is slow, resolve that and the controller catches up without intervention. If only kube-state-metrics was wrong, restart it. On managed Kubernetes, raise it with your provider.

## Related alerts

- [KubeDeploymentGenerationMismatch](/runbooks/kubedeploymentgenerationmismatch/): the Deployment equivalent, often firing at the same time.
- [KubeStatefulSetReplicasMismatch](/runbooks/kubestatefulsetreplicasmismatch/): the spec was observed but pods are not converging.
- [KubeControllerManagerDown](/runbooks/kubecontrollermanagerdown/): the controller responsible has disappeared.
