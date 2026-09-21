---
title: "CoreDNSDown: runbook and fix"
description: "CoreDNSDown means Prometheus has no healthy CoreDNS target, so cluster DNS may be broken. How to check the pods, Service and metrics scrape."
permalink: /runbooks/corednsdown/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: CoreDNS
severity: critical
cta:
  title: Get this alert, tested
  text: "CoreDNSDown is one of 6 CoreDNS alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=corednsdown
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# CoreDNSDown

Prometheus has not seen a single healthy CoreDNS target for a sustained period.

| | |
|---|---|
| Severity | critical |
| Source | Prometheus scrape of CoreDNS (`prometheus` plugin, port 9153) |
| Key metric | `up` for the CoreDNS job |

## What it means

The alert fires when there is no CoreDNS target reporting `up == 1`, either because every target is failing or because the targets have vanished from service discovery entirely. The second case matters: a mislabelled Service makes the targets disappear rather than go down.

If CoreDNS is really down, almost everything in the cluster breaks: service discovery, image pulls from in-cluster registries, and any outbound call by hostname. If only scraping is broken, DNS works but you have lost visibility into it.

## Common causes

- CoreDNS pods crashlooping, usually from a Corefile error or the `loop` plugin detecting a forwarding loop.
- Pods `Pending` because of node pressure, taints or a failed rollout.
- The metrics endpoint removed from the Corefile (`prometheus :9153` missing) or the port not exposed on the Service.
- ServiceMonitor or scrape config selector no longer matching after a Helm or managed add-on upgrade.
- NetworkPolicy blocking Prometheus from port 9153 in `kube-system`.

## First checks

1. Check pod status:
   ```bash
   kubectl -n kube-system get pods -l k8s-app=kube-dns -o wide
   kubectl -n kube-system logs -l k8s-app=kube-dns --tail=30
   ```
2. Test DNS from a throwaway pod to see if resolution actually works:
   ```bash
   kubectl run dnstest --rm -it --restart=Never --image=busybox:1.36 -- nslookup kubernetes.default.svc.cluster.local
   ```
3. Check that the metrics port is configured and exposed:
   ```bash
   kubectl -n kube-system get configmap coredns -o yaml | grep prometheus
   kubectl -n kube-system get endpoints kube-dns -o yaml | grep -A2 9153
   ```
4. Look at what Prometheus discovers:
   ```promql
   up{job=~".*dns.*"}
   ```
   If the job name differs from what the alert expects, the rule needs adjusting rather than CoreDNS.

## Fixing it

If pods are failing, read the logs: fix the Corefile in the `coredns` ConfigMap, or break the loop by pointing `forward` at a real upstream instead of a resolver that points back at CoreDNS. Then `kubectl -n kube-system rollout restart deployment coredns`. If only scraping is broken, restore port 9153 on the Service and fix the ServiceMonitor selector.

## Related alerts

- [CoreDNSPanics](/runbooks/corednspanics/): crashes that may precede pods going down.
- [CoreDNSErrorsHigh](/runbooks/corednserrorshigh/): CoreDNS running but failing queries.
- [TargetDown](/runbooks/targetdown/): generic scrape failures across jobs.
