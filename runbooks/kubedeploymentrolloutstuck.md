---
title: 'KubeDeploymentRolloutStuck: runbook and fix'
description: 'KubeDeploymentRolloutStuck runbook: a rollout exceeded progressDeadlineSeconds. Find the failing new pods, then roll back or fix forward.'
permalink: /runbooks/kubedeploymentrolloutstuck/
breadcrumb:
  title: Alert runbooks
  url: /runbooks/
domain: Kubernetes workloads
severity: warning
free_rule: true
cta:
  title: Get the other 167 alerts, tested
  text: KubeDeploymentRolloutStuck is one of 12 free alerts. The full pack has 179 alerts across 20 domains, each with promtool unit tests and a runbook.
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubedeploymentrolloutstuck
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeDeploymentRolloutStuck

Deployment rollout is not progressing. Free rule (MIT): the complete runbook and rule definition are below.

| | |
|---|---|
| Severity | warning |
| Pending (`for:`) | 15m (warning) |
| Domain | Kubernetes workloads |
| Requires | kube-state-metrics v2.x |
| Rule file | [`rules/kubernetes-workloads.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/kubernetes-workloads.rules.yml) (group `ftw.kubernetes-workloads.alerts`) |

## Meaning

The Deployment controller set `Progressing=False` (reason `ProgressDeadlineExceeded`) because the rollout made no progress within `progressDeadlineSeconds`.

## Impact

The new version is not fully rolled out. Old and new ReplicaSets may be serving side by side.

## Diagnosis

- ```bash
  kubectl -n <namespace> rollout status deployment/<deployment> --timeout=5s
  kubectl -n <namespace> describe deployment <deployment> | sed -n '/Conditions/,/Events/p'
  kubectl -n <namespace> get rs -l <selector>
  ```
- Inspect the newest ReplicaSet's pods for readiness or scheduling failures.

## Mitigation

- Roll back: `kubectl -n <namespace> rollout undo deployment/<deployment>`.
- Or fix the underlying pod problem and re-trigger: `kubectl -n <namespace> rollout restart deployment/<deployment>`.

## Escalation

- **warning**: Notify the owning team's alert channel. Acknowledge within business hours; create a ticket if it cannot be resolved the same day. Escalate to critical handling if it trends toward the critical condition.

Route to the team that owns the namespace. Platform on-call only takes over when several namespaces are affected at once (likely a node, network or control-plane problem).

## Related alerts

- [KubePodCrashLooping](/runbooks/kubepodcrashlooping/): Pod container is crash looping.
- [KubePodNotReady](/runbooks/kubepodnotready/): Pod has been in a non-ready state.
- [KubeContainerOOMKilled](/runbooks/kubecontaineroomkilled/): Container was OOM killed.
- [KubeImagePullBackOff](/runbooks/kubeimagepullbackoff/): Container image cannot be pulled.
- [KubeDeploymentReplicasMismatch](/runbooks/kubedeploymentreplicasmismatch/): Deployment has fewer available replicas than desired.

## Rule definition

From [`rules/kubernetes-workloads.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/kubernetes-workloads.rules.yml) in the free repository (MIT). Unit tests for it are in [`tests/`](https://github.com/Fractal-Techware/prometheus-alert-rules/tree/main/tests).

{% raw %}```yaml
- alert: KubeDeploymentRolloutStuck
  expr: kube_deployment_status_condition{job="kube-state-metrics", namespace=~".+", condition="Progressing", status="false"} != 0
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: Deployment rollout is not progressing.
    description: Rollout of deployment {{ $labels.namespace }}/{{ $labels.deployment }} has exceeded its progress deadline and has not progressed for 15m.
    runbook_url: runbooks/kubernetes-workloads/KubeDeploymentRolloutStuck.md
```
{% endraw %}
