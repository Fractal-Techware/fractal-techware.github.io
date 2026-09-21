---
title: "CertManagerCertificateNotReady: runbook and fix"
description: "CertManagerCertificateNotReady means a cert-manager Certificate has been not Ready for a while. How to find the failing issuer, order or challenge."
permalink: /runbooks/certmanagercertificatenotready/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes certificates (kubelet & cert-manager)
severity: warning
cta:
  title: Get this alert, tested
  text: "CertManagerCertificateNotReady is part of a pack of 179 tested Prometheus alerts, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=certmanagercertificatenotready
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# CertManagerCertificateNotReady

A cert-manager Certificate resource has had its `Ready` condition set to `False` or `Unknown` for a while.

| | |
|---|---|
| Severity | warning |
| Source | cert-manager controller `/metrics` (v1.x) |
| Key metric | `certmanager_certificate_ready_status` (labels `name`, `condition`) |

## What it means

cert-manager reports each Certificate's Ready condition as a metric. The alert fires when a certificate stays not ready beyond a short grace period, which covers normal issuance time.

What breaks depends on the situation. For a new certificate, the Secret may not exist yet, so the ingress or webhook that references it has no valid TLS. For an existing one, the old certificate usually still works, and this is the earliest sign that renewal is failing.

## Common causes

- The referenced Issuer or ClusterIssuer does not exist, is in another namespace, or is not ready.
- ACME challenges failing (HTTP-01 not reachable, DNS-01 credentials wrong, CAA records blocking the CA).
- The CertificateRequest was denied by an approver policy (approver-policy or a custom approver).
- Invalid spec: a DNS name the issuer refuses, a key algorithm the CA does not support, or a Secret name already owned by another Certificate.
- Rate limits from the ACME server.

## First checks

1. List not-ready certificates across the cluster:
   ```bash
   kubectl get certificate -A | grep -v True
   ```
2. See how long each has been failing:
   ```promql
   max by (exported_namespace, name, condition) (certmanager_certificate_ready_status{condition!="True"}) == 1
   ```
3. Read the condition message and the chain:
   ```bash
   cmctl status certificate <name> -n <namespace>
   kubectl -n <namespace> describe certificaterequest
   ```
4. For ACME issuers, find the stuck step:
   ```bash
   kubectl -n <namespace> get order,challenge
   kubectl -n <namespace> describe challenge <challenge>
   ```
5. Confirm the issuer is ready:
   ```bash
   kubectl -n <namespace> describe issuer <issuer>
   ```

## Fixing it

Fix what the failing resource reports: correct the `issuerRef`, repair the issuer's credentials, make the challenge reachable, or fix the spec. Then run `cmctl renew <name> -n <namespace>` to retry right away rather than waiting for backoff. If a CertificateRequest was denied, update the approval policy or the request.

## Related alerts

- [CertManagerCertificateExpiringSoon](/runbooks/certmanagercertificateexpiringsoon/): what happens if this is not fixed in time.
- [BlackboxSslCertificateWillExpireSoon](/runbooks/blackboxsslcertificatewillexpiresoon/): external check of the served certificate.
