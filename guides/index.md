---
title: OpenTelemetry Collector & Kyverno guides
description: Working, tested OpenTelemetry Collector configurations and Kyverno policies, explained step by step.
---
# Guides

Each guide solves one specific problem with a complete configuration you can copy, explains the settings that matter, and shows how to prove it works. Every config was checked before publishing: `otelcol validate` and a smoke test for collector configs, `kyverno test` for policies, and `kubeconform -strict` for Kubernetes manifests. The tool versions are listed at the top of each guide.

## Prometheus alerts

- **[Test your alert rules with promtool](/guides/testing-prometheus-alert-rules-promtool/)**: a rule that can never fire looks exactly like a healthy system — how to assert that an alert fires, and the test almost nobody writes, that it stays quiet.

## OpenTelemetry Collector

- **[Tail sampling: a working config](/guides/otel-collector-tail-sampling/)**: keep every error and slow trace plus a small baseline, and why scaling out needs a trace-ID load-balancing tier.
- **[Redact PII with OTTL](/guides/otel-collector-redact-pii-ottl/)**: mask emails and card numbers and delete Authorization and cookie attributes in traces and logs.
- **[Send logs to Grafana Loki over OTLP](/guides/otel-collector-logs-to-loki-otlp/)**: `file_log` receiver to Loki 3's native OTLP endpoint, plus labels vs structured metadata.
- **[Production-ready collector agent](/guides/otel-collector-production-agent/)**: memory_limiter, batch, retries, a persistent sending queue and health checks that survive outages.
- **[Reduce telemetry cost](/guides/otel-collector-reduce-telemetry-cost/)**: drop health-check spans, DEBUG logs and unused metrics, and cut cardinality safely.
- **[Span metrics and service graph](/guides/otel-collector-span-metrics-service-graph/)**: RED metrics and a dependency map from traces with the `span_metrics` and `service_graph` connectors.

## Kubernetes & Kyverno

- **[Kyverno: disallow the :latest tag](/guides/kyverno-disallow-latest-tag/)**: a ValidatingPolicy that handles registry ports, digests and init containers, with a `kyverno test` suite.
- **[Kyverno: require requests and limits](/guides/kyverno-require-requests-limits/)**: CPU/memory requests and a memory limit on every container, with messages that name the container.
- **[Kyverno: Audit to Enforce, safely](/guides/kyverno-audit-to-enforce/)**: a phased rollout with PolicyReports, Warn mode and a tested, narrowly scoped PolicyException.
- **[Default-deny NetworkPolicy that allows DNS](/guides/kubernetes-default-deny-networkpolicy-dns/)**: block all traffic without breaking name resolution, and how to test that it is enforced.
- **[Pod Security Admission restricted migration](/guides/pod-security-admission-restricted-migration/)**: move a live namespace to `restricted` with dry runs, warn and audit modes, and a pinned enforce version.
