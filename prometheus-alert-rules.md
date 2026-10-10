---
title: "Tested Prometheus alerts: Free vs Pro ($49)"
description: "Try 12 free Kubernetes and host alerts with promtool tests. Compare the $49 Pro pack: 179 alerting rules, 364 tests, runbooks and Alertmanager routing."
permalink: /prometheus-alert-rules/
---
# Prometheus alerts you can test before deploying

Start with 12 MIT-licensed alert types (14 rules including severity variants) for Kubernetes workloads, nodes and Linux hosts. Each has a runbook and tests for failure and healthy input. Run the tests, inspect the PromQL and check the metrics against your environment before installing.

**[Try the free edition on GitHub](https://github.com/Fractal-Techware/prometheus-alert-rules)** · **[Get Pro — $49 once](https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=comparison&utm_campaign=first_sale_oct2026&utm_content=top)** (select Pro on the product page)

## Watch the test catch a broken alert

This 62-second terminal demonstration uses synthetic input. A job-label typo passes the syntax check but fails the firing test. On-screen captions explain each step; there is no audio.

<video controls playsinline preload="metadata" aria-label="Prometheus alert test demonstration with on-screen captions" style="width:100%;max-width:960px;height:auto">
  <source src="{{ '/assets/demos/promtool-demo.mp4' | relative_url }}" type="video/mp4">
  Your browser does not support embedded video. <a href="{{ '/assets/demos/promtool-demo.mp4' | relative_url }}">Download the demonstration</a>.
</video>

**What happens:** the original NodeExporterDown rule passes its healthy, pending and firing scenarios. Changing the job matcher leaves the YAML valid, but the expected alert disappears from the test result. The matching runbook then explains how to investigate a scrape failure. These tests do not verify your actual scrape labels or notification delivery.

[Read the testing guide](/guides/testing-prometheus-alert-rules-promtool/) or [inspect the free rules, tests and runbooks](https://github.com/Fractal-Techware/prometheus-alert-rules).

## What changes when you choose Pro?

| | Free | Pro — $49 |
|---|---|---|
| Alerting rules | 14 rules covering 12 alert names | 179 rules covering 165 alert names |
| Coverage | Kubernetes workloads, nodes and node_exporter hosts | 20 domains, including control plane, databases, certificates, probes and SLO burn rates |
| promtool unit tests | 28 | 364 |
| Runbooks | 12 | 165 |
| Recording rules | — | 17 |
| Ready-to-apply PrometheusRule CRDs | Manual wrapping instructions | Included |
| Tested Alertmanager routing and inhibition config | — | Included |
| License | MIT | Perpetual use within your own organization |
| Updates | Public repository releases | One year from purchase |

Both editions use the same test standard. Pro saves you assembling the wider coverage, routing configuration and runbooks yourself. Unit tests exercise synthetic input; they do not replace checking that your exporters expose the expected metrics and labels.

## Is it a fit for your stack?

Choose Pro if you already operate Prometheus and want tested starting rules for Kubernetes, hosts, PostgreSQL, Redis, Kafka, NGINX Ingress, Loki, CoreDNS, etcd, blackbox probes or HTTP SLOs. Enable only the domains whose metrics you collect. The defaults follow kube-prometheus-stack job names; adapt job labels, thresholds, notification destinations and runbook URLs to your environment.

Stay with Free if you only need the included workload and host alerts or want to inspect the test quality first. This is a downloadable configuration pack: it does not install exporters, host monitoring or provide a managed on-call service.

Using the paid pack in client environments requires **Agency ($299)**. Starter and Pro cover your own organization. Starter ($19) includes 49 rules and 30 days of updates; Pro and Agency include one year. Support is documentation-based.

## Already running kube-prometheus-stack?

Check the chart's existing rules before adding these. Some alert names and conditions overlap. Avoid loading both versions of the same alert, and review coverage before disabling an entire default rule group: the free sample does not replace every alert in those groups. Pro includes an installation guide with the overlapping groups to review; validate your selected rules and routing before sending notifications to production receivers.

## Try the test suite first

```bash
git clone https://github.com/Fractal-Techware/prometheus-alert-rules.git
cd prometheus-alert-rules
./run-tests.sh
```

Requires local `promtool` or Docker. For an explanation of the assertions, read [how to test alert rules with promtool](/guides/testing-prometheus-alert-rules-promtool/).

**[Get Pro — $49 once →](https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=comparison&utm_campaign=first_sale_oct2026&utm_content=bottom)** Select **Pro** on the product page; the default Starter tier is $19. Pro includes one year of updates and a perpetual own-organization license. If it does not work with a supported setup and the troubleshooting guide does not resolve it, contact us within 14 days for a refund.
