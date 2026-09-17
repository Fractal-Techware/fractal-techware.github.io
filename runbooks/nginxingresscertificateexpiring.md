---
title: "NginxIngressCertificateExpiring: runbook and fix"
description: "NginxIngressCertificateExpiring means a TLS certificate served by ingress-nginx is close to expiry. How to find it and why renewal is not landing."
permalink: /runbooks/nginxingresscertificateexpiring/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: NGINX Ingress Controller
severity: "warning, critical"
cta:
  title: Get this alert, tested
  text: "NginxIngressCertificateExpiring is one of 5 NGINX Ingress alerts in the pack of 179, with warning and critical tiers covered by promtool unit tests."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nginxingresscertificateexpiring
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NginxIngressCertificateExpiring

A certificate that the ingress controller is actually serving will expire soon.

| | |
|---|---|
| Severity | warning, critical |
| Source | ingress-nginx controller `/metrics` (1.9+) |
| Key metric | `nginx_ingress_controller_ssl_expire_time_seconds` (labels `host`, and `secret_name` in recent versions) |

## What it means

The controller exports the expiry timestamp of each certificate it loaded. The warning fires when one expires within the next few weeks; critical means only a few days are left and browsers and API clients will soon reject the connection.

Because the metric reflects what NGINX serves, not what sits in the Secret, this also catches cases where the Secret was renewed but the controller never loaded it.

## Common causes

- **cert-manager renewal failing**: ACME HTTP-01 or DNS-01 challenge errors, rate limits, or a broken Issuer.
- **Manually managed certificate** that nobody rotated.
- **Secret renewed but not served**: the controller's config reload is failing, or the Ingress points to a different Secret name.
- **Invalid new certificate** (key mismatch, wrong SAN), so the controller falls back to the default fake certificate or the old one.

## First checks

1. List certificates by time left, in days:
   ```promql
   sort((nginx_ingress_controller_ssl_expire_time_seconds - time()) / 86400)
   ```
2. Confirm what clients actually receive:
   ```bash
   echo | openssl s_client -servername <host> -connect <host>:443 2>/dev/null | openssl x509 -noout -subject -enddate
   ```
3. Compare with the Secret the Ingress references:
   ```bash
   kubectl -n <namespace> get ingress <ingress> -o jsonpath='{.spec.tls}'
   kubectl -n <namespace> get secret <tls-secret> -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -enddate
   ```
4. If cert-manager owns it, check why it has not renewed:
   ```bash
   kubectl -n <namespace> describe certificate <name>
   cmctl status certificate <name> -n <namespace>
   ```
5. Check the controller logs for certificate errors: `kubectl -n ingress-nginx logs deploy/ingress-nginx-controller | grep -i ssl`.

## Fixing it

Fix the Issuer or challenge problem, then force a renewal with `cmctl renew <name> -n <namespace>`. For manual certificates, update the Secret with the new `tls.crt` and `tls.key`. If the Secret is already fresh but the old certificate is served, fix the failed reload first.

## Related alerts

- [NginxIngressConfigReloadFailed](/runbooks/nginxingressconfigreloadfailed/): a failed reload keeps the old certificate in use.
- [CertManagerCertificateExpiringSoon](/runbooks/certmanagercertificateexpiringsoon/): the same problem seen from cert-manager.
- [BlackboxSslCertificateWillExpireSoon](/runbooks/blackboxsslcertificatewillexpiresoon/): external view of the served certificate.
