---
title: Tested observability & Kubernetes configs
description: Free runbooks for Prometheus alerts, OpenTelemetry Collector guides and Kubernetes hardening, from the makers of tested alert, dashboard and policy packs.
---
# Tested observability & Kubernetes configs

Everything we publish ships with automated tests: promtool for alerts, `otelcol validate` and end-to-end runs for collector configs, `kyverno test` for policies.

- **[Alert runbooks](/runbooks/)**: what each common Prometheus alert means and what to check first.
- **[Guides](/guides/)**: working OpenTelemetry Collector and Kyverno configurations, explained.

## Free on GitHub (MIT)

| Repo | What you get |
|---|---|
| [prometheus-alert-rules](https://github.com/Fractal-Techware/prometheus-alert-rules) | 12 Kubernetes & node_exporter alerts with promtool tests and runbooks |
| [opentelemetry-collector-recipes](https://github.com/Fractal-Techware/opentelemetry-collector-recipes) | Hardened collector agent, logs to Loki, basic PII redaction |
| [kubernetes-hardening-baseline](https://github.com/Fractal-Techware/kubernetes-hardening-baseline) | Kyverno policies with tests, Pod Security, default-deny NetworkPolicy |
| [grafana-dashboards](https://github.com/Fractal-Techware/grafana-dashboards) | node_exporter & Kubernetes dashboards for Grafana 10/11 |
| [slo-as-code](https://github.com/Fractal-Techware/slo-as-code) | YAML SLOs to burn-rate alerts, with promtool timing tests and documented math |
| [vps-observability-stack](https://github.com/Fractal-Techware/vps-observability-stack) | Prometheus, Grafana and Caddy on one VPS, with generated passwords |
| [helm-production-chart](https://github.com/Fractal-Techware/helm-production-chart) | Secure chart defaults, probes and a strict values schema, kubeconform in CI |
| [n8n-production-compose](https://github.com/Fractal-Techware/n8n-production-compose) | Hardened n8n Compose stack: task runner, PostgreSQL 17, automatic HTTPS |
| [n8n-incident-triage-workflow](https://github.com/Fractal-Techware/n8n-incident-triage-workflow) | Alertmanager group to one triaged chat message, secrets redacted |
| [n8n-github-pr-summary](https://github.com/Fractal-Techware/n8n-github-pr-summary) | PR summarised by an LLM into one comment, HMAC-verified deliveries |

## Full packs

**[The SRE Toolkit](https://fractaltechware.gumroad.com/sre?utm_source=site&utm_medium=home&utm_campaign=sre-toolkit)** puts the six observability and Kubernetes packs on one page, with the bundle maths and the free editions.

### Observability & SRE

- [Prometheus Alert Rules & Runbook Pack](https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=home): 179 alerts, 364 promtool tests, a runbook each
- [OpenTelemetry Collector Production Recipes](https://fractaltechware.gumroad.com/l/otel-collector-recipes?utm_source=site&utm_medium=home): 16 recipes, pinned to otelcol-contrib 0.161.0
- [Grafana Observability Dashboard Pack](https://fractaltechware.gumroad.com/l/grafana-dashboard-pack?utm_source=site&utm_medium=home): up to 13 dashboards, Mimir/Thanos/VictoriaMetrics compatible
- [SLO-as-Code Kit](https://fractaltechware.gumroad.com/l/slo-as-code-kit?utm_source=site&utm_medium=home): 21 SLI templates, 123 burn-rate timing scenarios, error budget reports
- [Single-VPS Observability Stack](https://fractaltechware.gumroad.com/l/vps-observability-stack?utm_source=site&utm_medium=home): Prometheus, Grafana, Loki & Tempo behind HTTPS, backups that restore

### Kubernetes & delivery

- [Kubernetes Hardening Baseline Kit](https://fractaltechware.gumroad.com/l/k8s-hardening-kit?utm_source=site&utm_medium=home): 21 Kyverno policies, 108 assertions, audit CLI
- [Production Helm Chart Kit](https://fractaltechware.gumroad.com/l/helm-production-chart?utm_source=site&utm_medium=home): 266 helm-unittest runs, checked on live 1.35 and 1.37 clusters

### Automation & AI

- [n8n Production Self-Hosting Kit](https://fractaltechware.gumroad.com/l/n8n-production-kit?utm_source=site&utm_medium=home): hardened Compose and queue mode, backups proven to restore
- [n8n AI Incident Triage Workflows](https://fractaltechware.gumroad.com/l/n8n-incident-triage-workflows?utm_source=site&utm_medium=home): 6 / 12 / 16 workflows for Alertmanager, Grafana and Kubernetes
- [n8n AI Workflows for GitHub](https://fractaltechware.gumroad.com/l/n8n-github-ai-workflows?utm_source=site&utm_medium=home): 9 / 15 / 18 workflows, HMAC-verified, diffs redacted and size-capped

### Bundles

- [SRE Observability Bundle](https://fractaltechware.gumroad.com/l/sre-observability-bundle?utm_source=site&utm_medium=home): alerts, Collector recipes, dashboards and hardening — $129, save 31%
- [Kubernetes Delivery Bundle](https://fractaltechware.gumroad.com/l/kubernetes-delivery-bundle?utm_source=site&utm_medium=home): Helm chart, hardening policies and alerts — $99, save 33%
- [n8n Automation Bundle](https://fractaltechware.gumroad.com/l/n8n-automation-bundle?utm_source=site&utm_medium=home): self-hosting kit, incident triage and GitHub workflows — $99, save 33%
