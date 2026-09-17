---
title: "NodeOOMKillDetected: runbook and fix"
description: "NodeOOMKillDetected means the Linux kernel OOM killer terminated a process on this host. How to find what was killed, why, and how to prevent it."
permalink: /runbooks/nodeoomkilldetected/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeOOMKillDetected is one of 179 alerts in the pack, including 25 for node_exporter hosts, all with promtool unit tests and runbooks."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodeoomkilldetected
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeOOMKillDetected

The kernel ran out of memory, either for the whole host or inside a cgroup, and killed a process to recover.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `vmstat` collector (kernel 4.13+) |
| Key metric | `node_vmstat_oom_kill` |

## What it means

`node_vmstat_oom_kill` counts every OOM kill since boot, including kills caused by a container hitting its cgroup memory limit. The alert fires as soon as the counter increases and stays active for a short while afterwards, so a single kill is visible long enough to be noticed.

A killed process may be restarted by systemd or Kubernetes and look healthy again, but requests in flight were lost, and repeated kills mean the problem will come back. If the kernel picked something important (a database, sshd, kubelet), the impact is bigger than the alert suggests.

## Common causes

- A container exceeding its memory limit (in Kubernetes this also shows as `OOMKilled`).
- A memory leak slowly growing until the host runs out.
- A traffic spike or a large query/batch job allocating more than usual.
- Host overcommitted: too many services or pods without memory requests.
- No swap and very little headroom left for page cache.

## First checks

1. Find what was killed and the memory state at the time:
   ```bash
   sudo journalctl -k --since "1 hour ago" | grep -iE "out of memory|oom-kill|killed process"
   ```
2. See how often it happens across the fleet:
   ```promql
   sort_desc(increase(node_vmstat_oom_kill[24h]) > 0)
   ```
3. On Kubernetes, find containers terminated for OOM:
   ```bash
   kubectl get pods -A -o json | jq -r '.items[] | .metadata.namespace + "/" + .metadata.name + " " + (.status.containerStatuses[]? | select(.lastState.terminated.reason=="OOMKilled") | .name)'
   ```
4. Check memory headroom on the host leading up to the kill:
   ```promql
   node_memory_MemAvailable_bytes{instance="<instance>"}
   ```
5. For a systemd service, check its restarts and limits:
   ```bash
   systemctl status <unit>
   systemctl show <unit> -p MemoryMax -p NRestarts
   ```

## Fixing it

If a cgroup limit was hit, the killed process says `oom_memcg` / "Memory cgroup out of memory" in the log: raise the limit or reduce the app's usage. If the whole host ran out, move workloads, set memory requests so the scheduler stops overpacking, or add memory. For leaks, capture a heap profile before the next kill. Protect critical daemons with `OOMScoreAdjust=` in their systemd unit.

## Related alerts

- [NodeMemoryHighUtilization](/runbooks/nodememoryhighutilization/): the early warning for host-wide exhaustion.
- [NodeMemoryMajorPagesFaults](/runbooks/nodememorymajorpagesfaults/): thrashing that often precedes a kill.
- [NodeSystemdServiceFailed](/runbooks/nodesystemdservicefailed/): a killed service that did not come back.
- [KubeNodePressure](/runbooks/kubenodepressure/): the kubelet reporting memory pressure on the node.
