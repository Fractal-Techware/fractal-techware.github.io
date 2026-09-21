---
title: 'KubeImagePullBackOff: runbook and fix'
description: 'KubeImagePullBackOff runbook: diagnose wrong image tags, missing imagePullSecrets, registry auth and rate limits, then fix the pull.'
permalink: /runbooks/kubeimagepullbackoff/
breadcrumb:
  title: Alert runbooks
  url: /runbooks/
domain: Kubernetes workloads
severity: warning
free_rule: true
cta:
  title: Get the other 167 alerts, tested
  text: KubeImagePullBackOff is one of 12 free alerts. The full pack has 179 alerts across 20 domains, each with promtool unit tests and a runbook.
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeimagepullbackoff
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeImagePullBackOff

Container image cannot be pulled. Free rule (MIT): the complete runbook and rule definition are below.

| | |
|---|---|
| Severity | warning |
| Pending (`for:`) | 10m (warning) |
| Domain | Kubernetes workloads |
| Requires | kube-state-metrics v2.x |
| Rule file | [`rules/kubernetes-workloads.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/kubernetes-workloads.rules.yml) (group `ftw.kubernetes-workloads.alerts`) |

## Meaning

The kubelet cannot pull the container image (wrong name or tag, missing registry credentials, registry unavailable or rate limited).

## Impact

New pods cannot start. Rollouts stall and scale-out does not add capacity.

## Diagnosis

- The pull error is in the pod events:
  ```bash
  kubectl -n <namespace> describe pod <pod> | grep -iA3 "failed to pull"
  ```
- Verify the image reference and the pull secret:
  ```bash
  kubectl -n <namespace> get pod <pod> -o jsonpath='{.spec.containers[*].image}{"\n"}{.spec.imagePullSecrets}'
  ```
- Several namespaces affected at once points to the registry or node egress, not the manifest.

## Mitigation

- Fix the tag or digest in the manifest and re-apply.
- Create or refresh the pull secret and reference it from the ServiceAccount or pod spec.
- Docker Hub rate limits: authenticate pulls or mirror the image into your own registry.

## Escalation

- **warning**: Notify the owning team's alert channel. Acknowledge within business hours; create a ticket if it cannot be resolved the same day. Escalate to critical handling if it trends toward the critical condition.

Route to the team that owns the namespace. Platform on-call only takes over when several namespaces are affected at once (likely a node, network or control-plane problem).

## Related alerts

- [KubePodCrashLooping](/runbooks/kubepodcrashlooping/): Pod container is crash looping.
- [KubePodNotReady](/runbooks/kubepodnotready/): Pod has been in a non-ready state.
- [KubeContainerOOMKilled](/runbooks/kubecontaineroomkilled/): Container was OOM killed.
- [KubeDeploymentReplicasMismatch](/runbooks/kubedeploymentreplicasmismatch/): Deployment has fewer available replicas than desired.
- [KubeDeploymentRolloutStuck](/runbooks/kubedeploymentrolloutstuck/): Deployment rollout is not progressing.

## Rule definition

From [`rules/kubernetes-workloads.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/kubernetes-workloads.rules.yml) in the free repository (MIT). Unit tests for it are in [`tests/`](https://github.com/Fractal-Techware/prometheus-alert-rules/tree/main/tests).

{% raw %}```yaml
- alert: KubeImagePullBackOff
  expr: max_over_time(kube_pod_container_status_waiting_reason{job="kube-state-metrics", namespace=~".+", reason=~"ImagePullBackOff|ErrImagePull|InvalidImageName"}[5m]) >= 1
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: Container image cannot be pulled.
    description: Container {{ $labels.container }} in pod {{ $labels.namespace }}/{{ $labels.pod }} is waiting with reason {{ $labels.reason }}.
    runbook_url: runbooks/kubernetes-workloads/KubeImagePullBackOff.md
```
{% endraw %}
