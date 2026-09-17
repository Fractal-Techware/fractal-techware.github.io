---
title: "KubeletServerCertificateExpiration: runbook and fix"
description: "KubeletServerCertificateExpiration means a kubelet serving certificate expires soon, breaking logs, exec and metrics scrapes. Approve CSRs and rotate."
permalink: /runbooks/kubeletservercertificateexpiration/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes certificates (kubelet & cert-manager)
severity: "warning, critical"
cta:
  title: Get this alert, tested
  text: "KubeletServerCertificateExpiration comes with warning and critical tiers in a pack of 179 tested alerts, each with a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubeletservercertificateexpiration
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeletServerCertificateExpiration

The TLS certificate a kubelet presents on its HTTPS port (10250) is about to expire.

| | |
|---|---|
| Severity | warning, critical |
| Source | kubelet `/metrics` |
| Key metric | `kubelet_certificate_manager_server_ttl_seconds` |

## What it means

This metric only exists when the kubelet requests its serving certificate from the cluster (`serverTLSBootstrap: true`); self-signed serving certificates are not tracked. The warning fires when only days remain, critical when expiry is hours away.

Once it expires, anything that connects to the kubelet with TLS verification fails: `kubectl logs`, `kubectl exec`, `port-forward`, metrics-server and Prometheus kubelet scrapes. Running pods are not affected.

## Common causes

- Serving CSRs are never approved. The built-in controller manager does not auto-approve `kubernetes.io/kubelet-serving` CSRs, so something else (a person, kubelet-csr-approver, a cloud controller) must.
- The approver component is down or its allowed hostnames/IPs no longer match the node.
- The kubelet is failing to submit the CSR at all.

## First checks

1. Nodes with the least time left, in days:
   ```promql
   sort(kubelet_certificate_manager_server_ttl_seconds / 86400)
   ```
2. Find pending serving CSRs:
   ```bash
   kubectl get csr --field-selector spec.signerName=kubernetes.io/kubelet-serving
   ```
3. Inspect the current certificate on the node, including its SANs:
   ```bash
   sudo openssl x509 -in /var/lib/kubelet/pki/kubelet-server-current.pem -noout -enddate -ext subjectAltName
   ```
4. Check the kubelet log for rotation messages:
   ```bash
   journalctl -u kubelet --since "24 hours ago" | grep -iE "serving|csr|certificate"
   ```
5. If you run an approver, check its pods and logs for rejected requests.

## Fixing it

Verify the requesting node and SANs in each pending CSR, then approve it with `kubectl certificate approve <csr>`. The kubelet picks up the new certificate without a restart. For a lasting fix, deploy or repair an automatic approver that validates node names and IPs. Do not blindly approve all CSRs; serving CSRs are not authenticated by SAN.

## Related alerts

- [KubeletServerCertificateRenewalErrors](/runbooks/kubeletservercertificaterenewalerrors/): renewal attempts are failing.
- [KubeletClientCertificateExpiration](/runbooks/kubeletclientcertificateexpiration/): the other kubelet certificate.
- [KubeletDown](/runbooks/kubeletdown/): expired serving certificates break kubelet scrapes.
