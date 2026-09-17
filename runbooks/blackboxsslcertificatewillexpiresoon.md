---
title: "BlackboxSslCertificateWillExpireSoon: runbook and fix"
description: "BlackboxSslCertificateWillExpireSoon means a probed endpoint serves a TLS certificate close to expiry. How to find which cert and renew it."
permalink: /runbooks/blackboxsslcertificatewillexpiresoon/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Endpoint probes (blackbox_exporter)
severity: "warning, critical"
cta:
  title: Get this alert, tested
  text: "BlackboxSslCertificateWillExpireSoon is one of 6 blackbox_exporter alerts in the pack of 179, with warning and critical tiers, unit tests and a runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=blackboxsslcertificatewillexpiresoon
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# BlackboxSslCertificateWillExpireSoon

An endpoint probed over TLS is serving a certificate chain that expires soon.

| | |
|---|---|
| Severity | warning, critical |
| Source | blackbox_exporter `/probe` (http or tcp module with TLS) |
| Key metric | `probe_ssl_earliest_cert_expiry` (Unix time of the first certificate in the chain to expire) |

## What it means

On every TLS probe the exporter records when the soonest-expiring certificate in the presented chain runs out. The alert compares that with the current time. The **warning** fires a couple of weeks ahead, when there is time for a normal renewal. The **critical** fires when only a few days remain and an outage is imminent.

Once the certificate expires, browsers and API clients refuse to connect, so this is a guaranteed outage with a known date.

## Common causes

- Automated renewal (cert-manager, certbot, a cloud provider) silently failing, often due to a broken ACME HTTP-01 or DNS-01 challenge.
- A renewed certificate that was issued but never deployed or reloaded by the web server or ingress.
- An expiring intermediate certificate in the chain, not the leaf.
- Manually managed certificates nobody owns anymore.
- Several backends behind one hostname, with only some serving the renewed certificate.

## First checks

1. List certificates by days left:
   ```promql
   sort((probe_ssl_earliest_cert_expiry - time()) / 86400)
   ```
2. Inspect what the endpoint serves right now:
   ```bash
   openssl s_client -connect <host>:443 -servername <host> -showcerts </dev/null 2>/dev/null \
     | openssl x509 -noout -subject -issuer -enddate
   ```
   If the leaf looks fine, check the intermediates printed by `-showcerts`.
3. Use the exporter debug output to see the chain it received:
   ```bash
   curl -s "http://<blackbox-exporter>:9115/probe?target=https://<host>&module=<module>&debug=true"
   ```
4. For cert-manager managed certificates:
   ```bash
   kubectl get certificate -A
   cmctl status certificate <name> -n <namespace>
   ```

## Fixing it

Fix the renewal path (challenge, DNS credentials, rate limits), then force renewal, for example `cmctl renew <name> -n <namespace>`. Make sure the ingress or server picks up the new secret; some need a reload. Replace an expiring intermediate by serving the chain your CA currently provides.

## Related alerts

- [BlackboxProbeFailed](/runbooks/blackboxprobefailed/): what happens once the certificate actually expires.
- [BlackboxExporterProbeScrapeFailed](/runbooks/blackboxexporterprobescrapefailed/): without scrapes, expiry data goes stale.
- [BlackboxSlowProbe](/runbooks/blackboxslowprobe/): TLS handshake issues also show up as slow probes.
