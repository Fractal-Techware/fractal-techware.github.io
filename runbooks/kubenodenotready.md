---
title: 'KubeNodeNotReady: runbook and fix'
description: 'KubeNodeNotReady runbook: check kubelet, container runtime, disk and network on a NotReady Kubernetes node and recover or replace it.'
permalink: /runbooks/kubenodenotready/
breadcrumb:
  title: Alert runbooks
  url: /runbooks/
domain: Kubernetes nodes & capacity
severity: warning
free_rule: true
cta:
  title: Get the other 167 alerts, tested
  text: KubeNodeNotReady is one of 12 free alerts. The full pack has 179 alerts across 20 domains, each with promtool unit tests and a runbook.
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubenodenotready
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeNodeNotReady

Node is not ready. Free rule (MIT): the complete runbook and rule definition are below.

| | |
|---|---|
| Severity | warning |
| Pending (`for:`) | 15m (warning) |
| Domain | Kubernetes nodes & capacity |
| Requires | kube-state-metrics v2.x |
| Rule file | [`rules/kubernetes-nodes.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/kubernetes-nodes.rules.yml) (group `ftw.kubernetes-nodes.alerts`) |

## Meaning

The kubelet on the node has not reported `Ready=True` for the whole pending period.

## Impact

No new pods are scheduled on the node. After the eviction timeout (default 5 minutes) its pods are evicted and rescheduled, which can overload the remaining nodes.

## Diagnosis

- ```bash
  kubectl get nodes -o wide
  kubectl describe node <node> | sed -n '/Conditions/,/Addresses/p'
  ```
- On the node (SSH/SSM): `systemctl status kubelet containerd` and `journalctl -u kubelet --since "30 min ago"`.
- Check host metrics for resource exhaustion:
  ```promql
  node_memory_MemAvailable_bytes{instance=~"<node>.*"} / node_memory_MemTotal_bytes{instance=~"<node>.*"}
  ```

## Mitigation

- Restart the kubelet or container runtime if they crashed.
- If the node cannot recover: `kubectl cordon <node>`, `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data`, then replace it (managed node groups: terminate the instance).

## Escalation

- **warning**: Notify the owning team's alert channel. Acknowledge within business hours; create a ticket if it cannot be resolved the same day. Escalate to critical handling if it trends toward the critical condition.

Owned by the platform / cluster team. Involve the cloud provider when nodes fail at the infrastructure level.

## Related alerts

- [KubeNodeUnreachable](/runbooks/kubenodeunreachable/): Node is unreachable.
- [KubeNodePressure](/runbooks/kubenodepressure/): Node has an active pressure condition.
- [KubeNodeReadinessFlapping](/runbooks/kubenodereadinessflapping/): Node readiness is flapping.
- [KubeletTooManyPods](/runbooks/kubelettoomanypods/): Node is running at its pod capacity.
- [KubeNodeCordoned](/runbooks/kubenodecordoned/): Node has been cordoned for a long time.

## Rule definition

From [`rules/kubernetes-nodes.rules.yml`](https://github.com/Fractal-Techware/prometheus-alert-rules/blob/main/rules/kubernetes-nodes.rules.yml) in the free repository (MIT). Unit tests for it are in [`tests/`](https://github.com/Fractal-Techware/prometheus-alert-rules/tree/main/tests).

{% raw %}```yaml
- alert: KubeNodeNotReady
  expr: kube_node_status_condition{job="kube-state-metrics", condition="Ready", status="true"} == 0
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: Node is not ready.
    description: Node {{ $labels.node }} has not been Ready for more than 15m.
    runbook_url: runbooks/kubernetes-nodes/KubeNodeNotReady.md
```
{% endraw %}
