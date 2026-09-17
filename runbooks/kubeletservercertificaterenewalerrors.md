---
title: "KubeletServerCertificateRenewalErrors: runbook and fix"
description: "KubeletServerCertificateRenewalErrors means a kubelet cannot renew its serving certificate. Check unapproved kubelet-serving CSRs and the approver."
permalink: /runbooks/kubeletservercertificaterenewalerrors/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes certificates (kubelet & cert-manager)
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeletServerCertificateRenewalErrors is included in a pack of 179 Prometheus alerts, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeletservercertificaterenewalerrors
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeletServerCertificateRenewalErrors

A kubelet keeps failing to renew the certificate it serves on port 10250.

| | |
|---|---|
| Severity | warning |
| Source | kubelet `/metrics` |
| Key metric | `kubelet_server_expiration_renew_errors` |

## What it means

With `serverTLSBootstrap` enabled, the kubelet requests its serving certificate through a CSR. Each failed renewal increments an error counter, and the alert fires when failures continue for a sustained period.

Nothing is broken yet. But when the current certificate runs out, `kubectl logs` and `exec`, metrics-server and Prometheus scrapes against that node start failing TLS verification.

## Common causes

- Nobody approves `kubernetes.io/kubelet-serving` CSRs. Kubernetes does not approve them automatically, so a manual process was forgotten or an approver (such as kubelet-csr-approver) is down.
- The approver rejects the request because the node's hostname or IP addresses changed and no longer match its policy.
- The CSR requests fail to be created: API connectivity or RBAC problems.
- A timeout while waiting for approval, repeated on every retry.

## First checks

1. Find affected nodes:
   ```promql
   sum by (node, instance) (increase(kubelet_server_expiration_renew_errors[1h])) > 0
   ```
2. List serving CSRs and their state:
   ```bash
   kubectl get csr --field-selector spec.signerName=kubernetes.io/kubelet-serving --sort-by=.metadata.creationTimestamp
   ```
3. Inspect one to confirm the requestor and SANs:
   ```bash
   kubectl get csr <csr> -o jsonpath='{.spec.request}' | base64 -d | openssl req -noout -text | grep -A1 "Alternative Name"
   ```
4. Read the kubelet error:
   ```bash
   journalctl -u kubelet --since "2 hours ago" | grep -iE "serving|csr"
   ```
5. Check the approver's logs, if you run one.

## Fixing it

After verifying the node name and addresses, approve the CSR with `kubectl certificate approve <csr>`. Then restore automatic approval: restart or reconfigure the approver so its allowed DNS names and IP ranges match your nodes. Clean up piles of old pending CSRs; the controller manager garbage-collects them eventually, but they clutter diagnosis.

## Related alerts

- [KubeletServerCertificateExpiration](/runbooks/kubeletservercertificateexpiration/): how close the current certificate is to expiry.
- [KubeletClientCertificateRenewalErrors](/runbooks/kubeletclientcertificaterenewalerrors/): client-side rotation failures.
