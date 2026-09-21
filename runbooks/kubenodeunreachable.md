---
title: "KubeNodeUnreachable: runbook and fix"
description: "KubeNodeUnreachable means the node controller tainted a node as unreachable because its kubelet stopped reporting. How to diagnose and recover it."
permalink: /runbooks/kubenodeunreachable/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes nodes & capacity
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeNodeUnreachable is one of 8 node and capacity alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubenodeunreachable
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeNodeUnreachable

The control plane has lost contact with a node and marked it unreachable, so its pods are being evicted or are in limbo.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metric | `kube_node_spec_taint` (key `node.kubernetes.io/unreachable`) |

## What it means

When a kubelet stops posting node status, the node lifecycle controller sets the node's Ready condition to `Unknown` and adds the `node.kubernetes.io/unreachable` taint. The alert fires when that taint has stayed on the node for several minutes, so a brief network blip does not page.

After the default toleration (five minutes), pods from Deployments are recreated elsewhere. StatefulSet pods are not: they stay `Terminating` on the lost node until someone confirms it is gone. Local volumes on the node are unavailable.

## Common causes

- **Host down**: kernel panic, hardware failure, hypervisor issue, or the cloud instance was terminated or stopped.
- **Network partition** between the node and the API server (security group, route, firewall, or load balancer change).
- **kubelet stopped**: crashed, killed by the OOM killer, or failing on an expired client certificate.
- **Node frozen** by extreme memory pressure or a hung disk, so the kubelet cannot run.

## First checks

1. Confirm the node state and how long it has been silent:
   ```bash
   kubectl get node <node> -o wide
   kubectl describe node <node> | sed -n '/Conditions:/,/Addresses:/p'
   ```
2. Check whether the host is still alive from Prometheus' point of view. If node_exporter answers but the kubelet does not, the host is up and the kubelet or its API path is the problem:
   ```promql
   up{instance=~"<node-ip>:.*"}
   ```
3. Check the instance in your cloud console or hypervisor (state, system log, status checks).
4. If you can reach the host, inspect the kubelet:
   ```bash
   systemctl status kubelet
   journalctl -u kubelet --since "30 min ago" | tail -50
   ```
5. List what was running there, especially stateful pods:
   ```bash
   kubectl get pods -A --field-selector spec.nodeName=<node> -o wide
   ```

## Fixing it

If the host is alive, restart the kubelet or fix its network path or certificate; the taint is removed automatically once status updates resume. If the host is dead, reboot or replace it. If it is permanently gone, `kubectl delete node <node>` so StatefulSet pods and attached volumes can move. Make sure the machine is really off before doing that.

## Related alerts

- [KubeNodeNotReady](/runbooks/kubenodenotready/): broader not-ready condition, including a kubelet that reports but is unhealthy.
- [KubeNodeReadinessFlapping](/runbooks/kubenodereadinessflapping/): the node keeps dropping out and coming back.
- [KubeStatefulSetReplicasMismatch](/runbooks/kubestatefulsetreplicasmismatch/): stateful pods stuck on the lost node.
