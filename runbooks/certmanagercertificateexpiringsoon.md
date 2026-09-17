---
title: "CertManagerCertificateExpiringSoon: runbook and fix"
description: "CertManagerCertificateExpiringSoon means a cert-manager Certificate is near expiry and was not renewed. Trace the CertificateRequest, Order and Challenge."
permalink: /runbooks/certmanagercertificateexpiringsoon/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes certificates (kubelet & cert-manager)
severity: "warning, critical"
cta:
  title: Get this alert, tested
  text: "CertManagerCertificateExpiringSoon is one of 6 Kubernetes certificate alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=certmanagercertificateexpiringsoon
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# CertManagerCertificateExpiringSoon

A certificate managed by cert-manager is getting close to its expiry date and has not been renewed.

| | |
|---|---|
| Severity | warning, critical |
| Source | cert-manager controller `/metrics` (v1.x) |
| Key metrics | `certmanager_certificate_expiration_timestamp_seconds`, `certmanager_certificate_renewal_timestamp_seconds` |

## What it means

cert-manager renews certificates well before they expire (by default when a third of the lifetime remains, which for a 90-day Let's Encrypt certificate is about 30 days). If a certificate is inside the last few weeks, renewal has been failing silently for a while. The warning tier fires with a few weeks left; critical fires when only days remain.

When it expires, clients see TLS errors on the ingress, webhook or internal service using that Secret.

## Common causes

- ACME HTTP-01 challenges failing: the ingress class changed, a redirect or auth layer intercepts `/.well-known/acme-challenge/`, or DNS points elsewhere.
- DNS-01 solver credentials expired or lack permissions on the zone.
- Let's Encrypt rate limits after repeated failed attempts.
- The Issuer or ClusterIssuer is not ready (bad secret, revoked account key, private CA unreachable).
- cert-manager itself is not running, or the Certificate was edited so its `renewBefore` is wrong.

## First checks

1. List certificates by days remaining:
   ```promql
   sort((certmanager_certificate_expiration_timestamp_seconds - time()) / 86400)
   ```
2. Get a summary of the whole chain for the certificate:
   ```bash
   cmctl status certificate <name> -n <namespace>
   ```
3. Walk the resources manually if you do not have cmctl:
   ```bash
   kubectl -n <namespace> describe certificate <name>
   kubectl -n <namespace> get certificaterequest,order,challenge
   kubectl -n <namespace> describe challenge <challenge>
   ```
4. Check the issuer:
   ```bash
   kubectl get clusterissuer,issuer -A
   ```
5. Read controller logs for this certificate:
   ```bash
   kubectl -n cert-manager logs deploy/cert-manager --tail=300 | grep "<name>"
   ```

## Fixing it

Fix the failure the Challenge or CertificateRequest reports (open the HTTP-01 path, update DNS credentials, repair the issuer), then trigger an immediate attempt with `cmctl renew <name> -n <namespace>`. If you are close to expiry and hitting rate limits, switch temporarily to another issuer or ACME provider.

## Related alerts

- [CertManagerCertificateNotReady](/runbooks/certmanagercertificatenotready/): usually fires first, when issuance fails.
- [BlackboxSslCertificateWillExpireSoon](/runbooks/blackboxsslcertificatewillexpiresoon/): the same expiry as seen from outside.
- [KubeletServerCertificateExpiration](/runbooks/kubeletservercertificateexpiration/): kubelet certificates are not managed by cert-manager.
