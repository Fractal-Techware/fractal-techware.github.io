---
title: "KubeletClientCertificateRenewalErrors: runbook and fix"
description: "KubeletClientCertificateRenewalErrors means a kubelet keeps failing to renew its client certificate. Find why the CSR fails before the node goes NotReady."
permalink: /runbooks/kubeletclientcertificaterenewalerrors/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes certificates (kubelet & cert-manager)
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeletClientCertificateRenewalErrors is one of 6 Kubernetes certificate alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeletclientcertificaterenewalerrors
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeletClientCertificateRenewalErrors

A kubelet is trying to rotate its API client certificate and the attempts keep failing.

| | |
|---|---|
| Severity | warning |
| Source | kubelet `/metrics` |
| Key metric | `kubelet_certificate_manager_client_expiration_renew_errors` |

## What it means

The kubelet counts every failed attempt to renew its client certificate. The alert fires when that counter keeps rising over a sustained period, so it is a persistent failure, not a single retry.

The current certificate is still valid, which is why this is a warning. It is your head start: if renewals keep failing, the certificate eventually expires and the node drops out of the cluster.

## Common causes

- The CSR is created but never signed: kube-controller-manager down, or cluster signing disabled.
- The CSR is denied, or the auto-approval ClusterRoleBindings for node client renewal (`system:certificates.k8s.io:certificatesigningrequests:selfnodeclient`) were removed.
- The kubelet cannot reach the API server, or its current credentials are already rejected.
- Clock skew on the node making certificates appear not yet valid or expired.

## First checks

1. Which nodes are failing:
   ```promql
   sum by (node, instance) (increase(kubelet_certificate_manager_client_expiration_renew_errors[1h])) > 0
   ```
2. Read the actual error:
   ```bash
   journalctl -u kubelet --since "2 hours ago" | grep -iE "certificate_manager|csr|rotat"
   ```
3. Check the CSRs for that node and their condition:
   ```bash
   kubectl get csr | grep -E "<node>|Pending|Denied"
   ```
4. Verify the approval bindings exist:
   ```bash
   kubectl get clusterrolebinding -o wide | grep -i certificatesigningrequests
   ```
5. Check time sync on the node: `timedatectl status`.

## Fixing it

Approve the pending CSR to buy time, then fix the root cause: restore the controller manager or its signing flags, recreate the auto-approval ClusterRoleBinding for `system:nodes`, fix NTP, or restore connectivity to the API server. Watch the error counter stop increasing and the certificate TTL jump back up.

## Related alerts

- [KubeletClientCertificateExpiration](/runbooks/kubeletclientcertificateexpiration/): how much time is left.
- [KubeletServerCertificateRenewalErrors](/runbooks/kubeletservercertificaterenewalerrors/): the serving certificate equivalent.
- [KubeControllerManagerDown](/runbooks/kubecontrollermanagerdown/): the component that signs these CSRs.
