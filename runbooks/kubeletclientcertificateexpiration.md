---
title: "KubeletClientCertificateExpiration: runbook and fix"
description: "KubeletClientCertificateExpiration means a kubelet's client certificate is close to expiry. Renew it before the node loses access to the API server."
permalink: /runbooks/kubeletclientcertificateexpiration/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes certificates (kubelet & cert-manager)
severity: "warning, critical"
cta:
  title: Get this alert, tested
  text: "KubeletClientCertificateExpiration is one of 6 Kubernetes certificate alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeletclientcertificateexpiration
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeletClientCertificateExpiration

The certificate a kubelet uses to authenticate to the API server will expire soon.

| | |
|---|---|
| Severity | warning, critical |
| Source | kubelet `/metrics` |
| Key metric | `kubelet_certificate_manager_client_ttl_seconds` |

## What it means

Kubelets authenticate with a client certificate, normally rotated automatically well before it expires. This alert means rotation has not happened. The warning fires when only days of validity remain; critical when it is down to its final hours.

When it expires, the kubelet gets 401 responses: the node goes `NotReady`, pod status stops updating and, after the eviction timeout, its pods are rescheduled elsewhere. If many nodes were bootstrapped at the same time, they all expire together.

## Common causes

- Client certificate rotation disabled (`rotateCertificates: false` in the kubelet config).
- CSRs not being approved: kube-controller-manager down, or its signing flags (`--cluster-signing-cert-file`) missing.
- The kubelet cannot reach the API server to submit a CSR.
- Nodes that were offline for most of the certificate's lifetime.

## First checks

1. List nodes by remaining lifetime, in days:
   ```promql
   sort(kubelet_certificate_manager_client_ttl_seconds / 86400)
   ```
2. Check the certificate on the node:
   ```bash
   sudo openssl x509 -in /var/lib/kubelet/pki/kubelet-client-current.pem -noout -subject -enddate
   ```
3. Look for pending CSRs from that node:
   ```bash
   kubectl get csr --sort-by=.metadata.creationTimestamp | grep -i <node>
   ```
4. Check rotation errors in the kubelet log:
   ```bash
   journalctl -u kubelet --since "24 hours ago" | grep -iE "certificate|csr|rotat"
   ```
5. Confirm rotation is enabled: `sudo grep -i rotate /var/lib/kubelet/config.yaml`.

## Fixing it

Approve pending client CSRs (`kubectl certificate approve <csr>`) and fix whatever stopped auto-approval. Enable `rotateCertificates` and restart the kubelet so it requests a new certificate. If the certificate has already expired, re-join the node: on kubeadm clusters generate a fresh bootstrap token with `kubeadm token create --print-join-command`, or replace the node from its node group.

## Related alerts

- [KubeletClientCertificateRenewalErrors](/runbooks/kubeletclientcertificaterenewalerrors/): explains why rotation is failing.
- [KubeletServerCertificateExpiration](/runbooks/kubeletservercertificateexpiration/): the serving certificate on the same node.
- [KubeControllerManagerDown](/runbooks/kubecontrollermanagerdown/): no controller manager means no CSR signing.
