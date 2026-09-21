---
title: 'KubeDeploymentReplicasMismatch: runbook and fix'
description: 'KubeDeploymentReplicasMismatch runbook: why a Deployment has fewer available replicas than desired and how to get them back.'
permalink: /runbooks/kubedeploymentreplicasmismatch/
breadcrumb:
  title: Alert runbooks
  url: /runbooks/
domain: Kubernetes workloads
severity: warning
free_rule: true
cta:
  title: Get the other 167 alerts, tested
  text: KubeDeploymentReplicasMismatch is one of 12 free alerts. The full pack has 179 alerts across 20 domains, each with promtool unit tests and a runbook.
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubedeploymentreplicasmismatch
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeDeploymentReplicasMismatch

Deployment has fewer available replicas than desired. Free rule (MIT): the complete runbook and rule definition are below.

| | |
|---|---|
| Severity | warning |
| Pending (`for:`) | 15m (warning) |
| Domain | Kubernetes workloads |
| Requires | kube-state-metrics v2.x |
| Rule file | [`rules/kubernetes-workloads.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/kubernetes-workloads.rules.yml) (group `ftw.kubernetes-workloads.alerts`) |

## Meaning

Desired replicas are higher than available replicas and the rollout is not making progress (updated replicas unchanged for 10 minutes).

## Impact

Reduced capacity and redundancy; an outage if available replicas reach zero.

## Diagnosis

- ```bash
  kubectl -n <namespace> get deployment <deployment> -o wide
  kubectl -n <namespace> get pods -l <selector> -o wide
  ```
- Unavailable pods usually show why: Pending (scheduling), CrashLoopBackOff, or failing readiness probes.
- ```promql
  kube_deployment_spec_replicas{deployment="<deployment>"} - kube_deployment_status_replicas_available{deployment="<deployment>"}
  ```

## Mitigation

- Resolve the pod-level cause (see [KubePodNotReady](/runbooks/kubepodnotready/) / [KubePodCrashLooping](/runbooks/kubepodcrashlooping/)).
- If an HPA raised replicas beyond cluster capacity, add nodes or cap `maxReplicas`.
- Roll back a release that broke readiness: `kubectl -n <namespace> rollout undo deployment/<deployment>`.

## Escalation

- **warning**: Notify the owning team's alert channel. Acknowledge within business hours; create a ticket if it cannot be resolved the same day. Escalate to critical handling if it trends toward the critical condition.

Route to the team that owns the namespace. Platform on-call only takes over when several namespaces are affected at once (likely a node, network or control-plane problem).

## Related alerts

- [KubePodCrashLooping](/runbooks/kubepodcrashlooping/): Pod container is crash looping.
- [KubePodNotReady](/runbooks/kubepodnotready/): Pod has been in a non-ready state.
- [KubeContainerOOMKilled](/runbooks/kubecontaineroomkilled/): Container was OOM killed.
- [KubeImagePullBackOff](/runbooks/kubeimagepullbackoff/): Container image cannot be pulled.
- [KubeDeploymentRolloutStuck](/runbooks/kubedeploymentrolloutstuck/): Deployment rollout is not progressing.

## Rule definition

From [`rules/kubernetes-workloads.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/kubernetes-workloads.rules.yml) in the free repository (MIT). Unit tests for it are in [`tests/`](https://github.com/Fractal-Techware/prometheus-alert-rules/tree/main/tests).

{% raw %}```yaml
- alert: KubeDeploymentReplicasMismatch
  expr: |-
    (kube_deployment_spec_replicas{job="kube-state-metrics", namespace=~".+"} > kube_deployment_status_replicas_available{job="kube-state-metrics", namespace=~".+"})
    and
    (changes(kube_deployment_status_replicas_updated{job="kube-state-metrics", namespace=~".+"}[10m]) == 0)
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: Deployment has fewer available replicas than desired.
    description: Deployment {{ $labels.namespace }}/{{ $labels.deployment }} has had fewer available replicas than the desired {{ $value | humanize }} for longer than 15m, and no rollout is progressing.
    runbook_url: runbooks/kubernetes-workloads/KubeDeploymentReplicasMismatch.md
```
{% endraw %}
