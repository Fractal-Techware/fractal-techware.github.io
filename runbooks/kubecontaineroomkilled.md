---
title: 'KubeContainerOOMKilled: runbook and fix'
description: 'KubeContainerOOMKilled runbook: confirm the OOM kill, compare memory usage to the limit, and decide between raising limits or fixing a leak.'
permalink: /runbooks/kubecontaineroomkilled/
breadcrumb:
  title: Alert runbooks
  url: /runbooks/
domain: Kubernetes workloads
severity: warning
free_rule: true
cta:
  title: Get the other 167 alerts, tested
  text: KubeContainerOOMKilled is one of 12 free alerts. The full pack has 179 alerts across 20 domains, each with promtool unit tests and a runbook.
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubecontaineroomkilled
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeContainerOOMKilled

Container was OOM killed. Free rule (MIT): the complete runbook and rule definition are below.

| | |
|---|---|
| Severity | warning |
| Pending (`for:`) | 0m (warning) |
| `keep_firing_for:` | 10m |
| Domain | Kubernetes workloads |
| Requires | kube-state-metrics v2.x |
| Rule file | [`rules/kubernetes-workloads.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/kubernetes-workloads.rules.yml) (group `ftw.kubernetes-workloads.alerts`) |

## Meaning

The container restarted within the last 10 minutes and its last termination reason is `OOMKilled` - the kernel killed it for exceeding its cgroup memory limit. `keep_firing_for` keeps the alert up for 10 minutes so a single kill is not lost between notifications.

## Impact

In-flight requests on that replica failed and in-memory state was lost. Repeated kills lead to CrashLoopBackOff.

## Diagnosis

- Confirm the limit and the last state:
  ```bash
  kubectl -n <namespace> get pod <pod> -o jsonpath='{.spec.containers[*].resources}'
  kubectl -n <namespace> describe pod <pod> | grep -A5 "Last State"
  ```
- Memory working set versus limit over time:
  ```promql
  max by (pod, container) (container_memory_working_set_bytes{namespace="<namespace>", pod="<pod>", container!=""})
    / on (pod, container) group_left max by (pod, container) (kube_pod_container_resource_limits{namespace="<namespace>", pod="<pod>", resource="memory"})
  ```
- A steady climb suggests a leak; a sudden spike suggests a large request or batch.

## Mitigation

- Raise the memory limit (and request) to cover the observed peak plus headroom.
- For JVM/Node.js/Go, align heap/GC settings with the container limit (e.g. `-XX:MaxRAMPercentage`, `GOMEMLIMIT`).
- Fix the leak or bound the workload (batch size, cache size) if usage grows without bound.

## Escalation

- **warning**: Notify the owning team's alert channel. Acknowledge within business hours; create a ticket if it cannot be resolved the same day. Escalate to critical handling if it trends toward the critical condition.

Route to the team that owns the namespace. Platform on-call only takes over when several namespaces are affected at once (likely a node, network or control-plane problem).

## Related alerts

- [KubePodCrashLooping](/runbooks/kubepodcrashlooping/): Pod container is crash looping.
- [KubePodNotReady](/runbooks/kubepodnotready/): Pod has been in a non-ready state.
- [KubeImagePullBackOff](/runbooks/kubeimagepullbackoff/): Container image cannot be pulled.
- [KubeDeploymentReplicasMismatch](/runbooks/kubedeploymentreplicasmismatch/): Deployment has fewer available replicas than desired.
- [KubeDeploymentRolloutStuck](/runbooks/kubedeploymentrolloutstuck/): Deployment rollout is not progressing.

## Rule definition

From [`rules/kubernetes-workloads.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/kubernetes-workloads.rules.yml) in the free repository (MIT). Unit tests for it are in [`tests/`](https://github.com/Fractal-Techware/prometheus-alert-rules/tree/main/tests).

{% raw %}```yaml
- alert: KubeContainerOOMKilled
  expr: |-
    (increase(kube_pod_container_status_restarts_total{job="kube-state-metrics", namespace=~".+"}[10m]) >= 1)
    and on (cluster, namespace, pod, container)
    (kube_pod_container_status_last_terminated_reason{job="kube-state-metrics", reason="OOMKilled"} == 1)
  keep_firing_for: 10m
  labels:
    severity: warning
  annotations:
    summary: Container was OOM killed.
    description: Container {{ $labels.container }} in pod {{ $labels.namespace }}/{{ $labels.pod }} restarted after being killed for exceeding its memory limit.
    runbook_url: runbooks/kubernetes-workloads/KubeContainerOOMKilled.md
```
{% endraw %}
