---
title: "AlertmanagerMembersInconsistent: runbook and fix"
description: "AlertmanagerMembersInconsistent means an Alertmanager replica cannot see all its peers, risking duplicate notifications. How to fix gossip."
permalink: /runbooks/alertmanagermembersinconsistent/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Alertmanager self-monitoring
severity: critical
cta:
  title: Get this alert, tested
  text: "AlertmanagerMembersInconsistent is one of 6 Alertmanager alerts in the pack of 179, all shipped with promtool unit tests and a detailed runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=alertmanagermembersinconsistent
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# AlertmanagerMembersInconsistent

At least one Alertmanager replica sees fewer cluster peers than there are replicas in its cluster.

| | |
|---|---|
| Severity | critical |
| Source | Alertmanager's own `/metrics` (0.25+) |
| Key metric | `alertmanager_cluster_members` (peers this instance currently knows about, itself included) |

## What it means

Highly available Alertmanagers form a gossip mesh (memberlist, port 9094 TCP and UDP by default) to share silences and the notification log. Each replica reports how many members it can see. The alert fires when a replica's view stays smaller than the number of replicas Prometheus is scraping for that cluster, for more than a short blip.

The practical impact is a split brain: isolated replicas do not know what the others already sent, so you get duplicate pages, and a silence created on one replica may not suppress notifications from another.

## Common causes

- Port 9094 blocked by a NetworkPolicy, security group or firewall, often only UDP.
- Wrong or stale `--cluster.peer` addresses, for example pointing at a Service that no longer resolves to all pods.
- A new replica that started before DNS for the headless Service was populated and never retried successfully.
- Pods advertising an unreachable address (`--cluster.advertise-address` missing on hosts with several interfaces).
- Replicas in different networks or clusters with no route between them.

## First checks

1. See what each instance reports:
   ```promql
   max by (job, instance) (alertmanager_cluster_members)
   ```
2. Inspect cluster status from one replica:
   ```bash
   amtool cluster show --alertmanager.url=http://<alertmanager>:9093
   ```
   It lists the peers and their addresses. Compare across replicas.
3. Look for memberlist errors:
   ```bash
   kubectl -n monitoring logs <alertmanager-pod> -c alertmanager | grep -iE "memberlist|gossip|peer"
   ```
4. Check the flags passed to the container:
   ```bash
   kubectl -n monitoring get pod <alertmanager-pod> -o jsonpath='{.spec.containers[0].args}'
   ```
5. Test reachability of port 9094 between pods and review NetworkPolicies in the namespace.

## Fixing it

Open TCP and UDP 9094 between replicas, point `--cluster.peer` at every replica (a headless Service DNS name per pod works well) and set the advertise address if needed. Restarting the isolated replica makes it rejoin once the network path is fixed.

## Related alerts

- [AlertmanagerConfigInconsistent](/runbooks/alertmanagerconfiginconsistent/): replicas that disagree on config also behave like separate clusters.
- [AlertmanagerClusterDown](/runbooks/alertmanagerclusterdown/): missing members may simply be down.
- [AlertmanagerClusterCrashlooping](/runbooks/alertmanagerclustercrashlooping/): restarting replicas drop in and out of the mesh.
