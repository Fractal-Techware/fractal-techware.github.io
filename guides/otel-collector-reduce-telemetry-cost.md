---
title: "Reduce OpenTelemetry costs: drop noisy spans, metrics and debug logs in the Collector"
description: "Tested filter and transform processor config that drops health-check spans, DEBUG logs and unused runtime metrics, and trims high-cardinality attributes."
permalink: /guides/otel-collector-reduce-telemetry-cost/
breadcrumb: {title: Guides, url: /guides/}
tested_with: "otelcol-contrib 0.161.0"
cta:
  title: "A complete cost-reduction recipe and 15 more, tested end to end"
  text: "The pack's cost recipe goes further: probe access-log lines, resource and span event cleanup, broader high-cardinality attribute lists and payload caps, verified by an automated end-to-end test."
  button: See the recipes
  url: https://fractaltechware.gumroad.com/l/otel-collector-recipes?utm_source=site&utm_medium=guide&utm_campaign=otel-collector-reduce-telemetry-cost
  free: https://github.com/Fractal-Techware/opentelemetry-collector-recipes
---
# Reduce OpenTelemetry costs in the Collector

*Tested with `otel/opentelemetry-collector-contrib:0.161.0`: `otelcol validate` plus a smoke test with spans, logs and metrics that confirmed what is dropped and what is kept.*

Observability bills grow from a few predictable sources:

- **Health checks and scrapes.** Kubernetes probes hit `/healthz` every few seconds on every pod, and each hit becomes a span.
- **DEBUG logs** someone forgot to turn off.
- **Runtime metrics** (`go_gc_*`, `go_memstats_*`) that nobody charts.
- **High-cardinality attributes** such as user IDs or full URLs on metrics, which multiply your series count. Huge string attributes such as full SQL text multiply storage.

Fixing each app takes months. Dropping this data in the collector takes one config change.

## The config

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  memory_limiter:
    check_interval: 1s
    limit_percentage: 80
    spike_limit_percentage: 20

  # Drop whole spans, log records and metrics that match ANY condition.
  filter/drop_noise:
    error_mode: ignore
    trace_conditions:
      - 'span.attributes["http.route"] == "/healthz" or span.attributes["http.route"] == "/readyz"'
      - 'span.attributes["url.path"] == "/metrics"'
      - 'span.attributes["rpc.service"] == "grpc.health.v1.Health"'
    log_conditions:
      # TRACE (1-4) and DEBUG (5-8). Records with no severity (0) are kept.
      - 'log.severity_number > SEVERITY_NUMBER_UNSPECIFIED and log.severity_number < SEVERITY_NUMBER_INFO'
    metric_conditions:
      - 'IsMatch(metric.name, "^(go_gc_.*|go_memstats_.*|process_.*_fds)")'

  # Cut cardinality and oversized attributes.
  transform/trim:
    error_mode: ignore
    trace_statements:
      - context: span
        statements:
          - delete_key(span.attributes, "http.request.header.user-agent")
          # Cap every string attribute (SQL text, payload dumps) at 1 KB.
          - truncate_all(span.attributes, 1024)
    metric_statements:
      # Keep only low-cardinality attributes and merge the data points that collide.
      - context: metric
        statements:
          - aggregate_on_attributes("sum", ["http.route", "http.request.method", "http.response.status_code"]) where metric.name == "http.server.request.count"

  batch:
    timeout: 5s

exporters:
  otlp_grpc:
    endpoint: backend.example.internal:4317

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, filter/drop_noise, transform/trim, batch]
      exporters: [otlp_grpc]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, filter/drop_noise, transform/trim, batch]
      exporters: [otlp_grpc]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, filter/drop_noise, batch]
      exporters: [otlp_grpc]
```

## How it works

**One filter processor for three signals.** `trace_conditions`, `log_conditions` and `metric_conditions` are OTTL boolean expressions. If **any** condition in a list is true, the item is dropped. One `filter/drop_noise` definition can sit in all three pipelines, and each pipeline uses only the conditions for its own signal.

**Dropping a span does not drop its trace.** The `/healthz` span is removed, but if it had children (for example a DB ping inside the health check), they stay and become orphans. Usually health checks are single spans. If yours are not, add a condition that matches the children too, or do this in [tail sampling](/guides/otel-collector-tail-sampling/) with a drop policy that removes whole traces.

**The DEBUG condition keeps unset severity.** `SEVERITY_NUMBER_UNSPECIFIED` is 0. Plain-text logs from files often have no severity at all, and a naive `severity_number < 9` would silently drop every one of them. We included such a record in the test to confirm it survives.

**Match metrics by name, not with a catch-all.** `IsMatch` takes a regular expression. Anchor it with `^` so you only drop the prefixes you mean. Use `metric.name == "..."` for exact names. It is faster and easier to review.

**`aggregate_on_attributes` instead of `delete_key` for metrics.** Deleting `user.id` from a counter leaves several data points with identical labels, one per former user. They overwrite each other or get rejected as duplicates. `aggregate_on_attributes("sum", [...])` keeps only the attributes you list and **adds up** the points that now collide, so the totals stay correct. Scope it with `where metric.name == ...`, and use `"sum"` only for counters and histograms-as-sums, never for gauges.

**`truncate_all`** caps every string attribute on a span. It keeps the useful start of a SQL query or error message and removes the multi-kilobyte tail, which is often where most of the trace storage goes.

**`error_mode: ignore`.** If a condition fails at runtime (for example a type mismatch), the item is kept and a warning is logged. With `propagate`, the whole batch is dropped, which is not what you want in a cost filter.

## Verify it

Merge a debug overlay (`debug.yaml`) that points all three pipelines at the `debug` exporter:

```yaml
exporters:
  debug:
    verbosity: detailed
service:
  pipelines:
    traces:
      exporters: [debug]
    metrics:
      exporters: [debug]
    logs:
      exporters: [debug]
```

```bash
docker run --rm -v "$PWD:/cfg" otel/opentelemetry-collector-contrib:0.161.0 validate --config=/cfg/config.yaml
docker run --rm -p 4318:4318 -v "$PWD:/cfg" otel/opentelemetry-collector-contrib:0.161.0 \
  --config=/cfg/config.yaml --config=/cfg/debug.yaml
```

Then POST OTLP JSON to `localhost:4318/v1/traces`, `/v1/metrics` and `/v1/logs`. In our test we sent:

| Sent | Result |
|---|---|
| span `GET /healthz` with `http.route=/healthz` | dropped |
| span `GET /orders/{id}` with `user-agent` and a 3,000-character `db.query.text` | kept. `user-agent` removed, `db.query.text` cut to 1,024 characters |
| log record with severity DEBUG (5) | dropped |
| log records with severity WARN (13) and with no severity | both kept |
| gauge `go_gc_duration_seconds` | dropped |
| sum `http.server.request.count`: two points for the same route, `user.id` u-981 (7) and u-982 (5), each with a different `url.full` | one point `http.route=/orders/{id}`, value 12 |

In production, measure the effect with the collector's own metrics: compare `otelcol_receiver_accepted_spans` with `otelcol_exporter_sent_spans` (same for `_log_records` and `_metric_points`). The gap is what you no longer pay for.

## Pitfalls

- **Dropping errors by accident.** A condition like `IsMatch(span.name, "health")` also matches `HealthRecordService.Save`. Prefer exact comparisons on `http.route` or `url.path`.
- **`delete_key` on metric attributes that make series unique.** Points that differ only by the deleted attribute become duplicates. Prometheus-compatible backends reject them or keep one at random, so your counts drop silently. Use `aggregate_on_attributes`, as shown above.
- **Filtering before tail sampling on a gateway.** That is fine for health checks. Never filter out error spans before a sampler that is supposed to keep errors.
- **Mixing the old and new filter layouts.** Older posts use `traces: span: [...]` with unprefixed paths. That still works in 0.161.0, but combining it with `trace_conditions` in the same processor fails validation with `cannot use context inferred trace conditions ... at the same time`. Pick the flat form shown here, with explicit `span.` / `log.` / `metric.` prefixes.
- **Deleting `service.name` or other resource attributes to save space.** Everything downstream groups by them.

## Next steps

- Remove sensitive data in the same pipeline: [redact PII with OTTL](/guides/otel-collector-redact-pii-ottl/).
- Get RED metrics from traces instead of storing every span: [span metrics and service graph connectors](/guides/otel-collector-span-metrics-service-graph/).
