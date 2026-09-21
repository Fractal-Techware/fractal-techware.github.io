---
title: "KubeDeploymentGenerationMismatch: runbook and fix"
description: "KubeDeploymentGenerationMismatch means the controller has not processed a Deployment spec change. How to check kube-controller-manager and fix it."
permalink: /runbooks/kubedeploymentgenerationmismatch/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes workloads
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeDeploymentGenerationMismatch ships with promtool unit tests and a full runbook, alongside 178 other alerts in the pack."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubedeploymentgenerationmismatch
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeDeploymentGenerationMismatch

You changed a Deployment, but the deployment controller has not acknowledged the change, so nothing is rolling out.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metrics | `kube_deployment_metadata_generation`, `kube_deployment_status_observed_generation` |

## What it means

Every write to a Deployment's spec bumps `metadata.generation`. When the deployment controller in kube-controller-manager processes that version, it copies the number into `status.observedGeneration`. The alert fires when the two have disagreed for several minutes.

That gap is almost never a problem with the Deployment itself. It means the controller is not doing its job: new images, replica changes and rollbacks are all silently ignored. If more than one Deployment is affected, treat it as a control plane issue.

## Common causes

- **kube-controller-manager down** or crash looping, or no instance holds the leader lease.
- **API server overloaded**: the controller's requests are throttled or time out, so its work queue backs up.
- **etcd latency** making status writes slow or failing.
- **A burst of changes** (a mass redeploy by GitOps tooling) that the controller is still working through.

## First checks

1. Confirm the gap on the object itself:
   ```bash
   kubectl -n <namespace> get deploy <deployment> \
     -o jsonpath='{.metadata.generation} {.status.observedGeneration}{"\n"}'
   ```
2. Check how widespread it is. If many Deployments and StatefulSets show it, go straight to the controller.
3. Is the controller manager running, and who is leader?
   ```bash
   kubectl -n kube-system get pods -l component=kube-controller-manager
   kubectl -n kube-system get lease kube-controller-manager -o jsonpath='{.spec.holderIdentity}{"\n"}'
   ```
4. Look at its work queue and logs (self-managed clusters):
   ```promql
   workqueue_depth{name="deployment"}
   ```
   ```bash
   kubectl -n kube-system logs <controller-manager-pod> | grep -iE "deployment|throttl|error" | tail -50
   ```
5. On managed clusters (EKS, GKE, AKS) you cannot see the controller manager. Check the provider's status page and control plane logs.

## Fixing it

Restore kube-controller-manager: fix its static pod manifest or certificates, or restart it. If the API server or etcd is struggling, fix that first, since the controller recovers on its own once requests succeed. A burst of changes clears by itself; confirm `workqueue_depth` is falling.

## Related alerts

- [KubeStatefulSetGenerationMismatch](/runbooks/kubestatefulsetgenerationmismatch/): the same symptom for StatefulSets, usually with the same cause.
- [KubeDeploymentRolloutStuck](/runbooks/kubedeploymentrolloutstuck/): the controller saw the change but the rollout cannot progress.
- [KubeControllerManagerDown](/runbooks/kubecontrollermanagerdown/): the most common root cause.
