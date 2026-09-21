---
title: "OpenTelemetry Collector span metrics and service graph: a working connector config"
description: "Generate RED metrics and a service graph from traces with the span_metrics and service_graph connectors. Tested config, metric names, pitfalls."
permalink: /guides/otel-collector-span-metrics-service-graph/
breadcrumb: {title: Guides, url: /guides/}
tested_with: "otelcol-contrib 0.161.0, Prometheus 3.14.0"
cta:
  title: "16 production collector recipes, tested end to end"
  text: "The pack's span metrics recipe adds exemplars, virtual nodes for databases and queues and cardinality guards, alongside the tail sampling and load-balancing recipes that fit around it."
  button: See the recipes
  url: https://store.fractaltechware.com/l/otel-collector-recipes?utm_source=site&utm_medium=guide&utm_campaign=otel-collector-span-metrics-service-graph
  free: https://github.com/Fractal-Techware/opentelemetry-collector-recipes
---
# Span metrics and service graph with OpenTelemetry Collector connectors

*Tested with `otel/opentelemetry-collector-contrib:0.161.0` and `prom/prometheus:v3.14.0`: `otelcol validate`, a smoke test that sent a client/server span pair, and a query of the generated series in Prometheus.*

Traces tell you what happened to one request. Dashboards and alerts need **rates, errors and durations** (RED) per service and endpoint, and a map of who calls whom. You can compute both in the collector from spans you already have, before sampling throws most of them away.

Two **connectors** do this. A connector is an exporter in one pipeline and a receiver in another.

- `span_metrics` turns spans into a call counter and a duration histogram per service, span name, kind, status and any dimensions you add.
- `service_graph` pairs client and server spans across services and produces request, failure and latency metrics per edge (`client` → `server`).

Older configs call these `spanmetrics` and `servicegraph`. In 0.161.0 those names still load but log a deprecation warning.

## The config

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

connectors:
  span_metrics:
    histogram:
      unit: s
      explicit:
        buckets: [10ms, 50ms, 100ms, 250ms, 500ms, 1s, 2500ms, 5s]
    dimensions:
      - name: http.request.method
      - name: http.response.status_code
      - name: http.route
    metrics_flush_interval: 15s
    metrics_expiration: 5m
    aggregation_cardinality_limit: 2000

  service_graph:
    latency_histogram_buckets: [10ms, 50ms, 100ms, 250ms, 500ms, 1s, 2500ms, 5s]
    store:
      ttl: 5s
      max_items: 10000
    metrics_flush_interval: 15s

processors:
  memory_limiter:
    check_interval: 1s
    limit_percentage: 80
    spike_limit_percentage: 20
  batch:
    timeout: 5s

exporters:
  otlp_grpc/traces:
    endpoint: tempo.observability.svc:4317
    tls:
      insecure: true
  otlp_http/metrics:
    endpoint: http://mimir.observability.svc:8080/otlp

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp_grpc/traces, span_metrics, service_graph]
    metrics/from_spans:
      receivers: [span_metrics, service_graph]
      processors: [batch]
      exporters: [otlp_http/metrics]
```

Replace the two endpoints with your trace backend and an OTLP-capable metrics backend. Mimir, Prometheus 3 (with `--web.enable-otlp-receiver`, endpoint `http://prometheus:9090/api/v1/otlp`), and most vendors accept OTLP metrics.

## The important parts

**Wiring.** The `traces` pipeline sends every span to three places: the trace backend and both connectors. The connectors appear again as *receivers* of `metrics/from_spans`. A connector must be used on both sides, or validation fails.

**`histogram.unit: s`.** The default unit is milliseconds. With seconds, the Prometheus name becomes `traces_span_metrics_duration_seconds_bucket`, which matches the convention most Grafana dashboards expect. The bucket values accept durations (`10ms`, `2500ms`) either way.

**Dimensions are cardinality.** Every distinct combination of `service.name` × span name × kind × status × your dimensions is a separate series. `http.route` (`/orders/{id}`) is safe. `url.full` or `user.id` would create one series per URL or user. `aggregation_cardinality_limit` is a hard cap. Extra combinations are folded into an overflow series instead of growing forever.

**`metrics_expiration`** forgets series that stopped receiving spans, such as old routes after a deploy. Without it, cumulative series stay in memory as long as the collector runs.

**`service_graph.store.ttl`** is how long an unpaired client or server span waits for its partner. Both halves must arrive at **the same collector** within that time. For most in-cluster calls, 5 s is plenty. Raise it for slow async hops, and remember that memory scales with `max_items`.

**Where to put it.** Put the connectors **before** tail or probabilistic sampling. Sampled traces produce sampled request rates, so a 10% sample makes your traffic look 10× smaller.

## Verify it

Use this overlay (`debug.yaml`). It removes the trace backend from the `traces` pipeline and prints the generated metrics:

```yaml
exporters:
  debug:
    verbosity: detailed
service:
  pipelines:
    traces:
      exporters: [span_metrics, service_graph]
    metrics/from_spans:
      exporters: [debug]
```

```bash
docker run --rm -p 4318:4318 -v "$PWD:/cfg" otel/opentelemetry-collector-contrib:0.161.0 \
  --config=/cfg/config.yaml --config=/cfg/debug.yaml
```

Send one trace with two spans: a CLIENT span (`kind: 3`) from `frontend`, and a SERVER span (`kind: 2`) from `checkout` whose `parentSpanId` is the client span's ID. Put each under its own `resource` with its own `service.name`. After the 15 s flush, the debug output in our test contained:

```text
-> Name: traces.span.metrics.calls
-> Name: traces.span.metrics.duration
-> Name: traces_service_graph_request_total
-> Name: traces_service_graph_request_client
-> Name: traces_service_graph_request_server
-> client: Str(frontend)
-> server: Str(checkout)
-> http.route: Str(/checkout)
```

Sent to Prometheus 3.14 over OTLP, they arrived as `traces_span_metrics_calls_total`, `traces_span_metrics_duration_seconds_bucket`, `traces_service_graph_request_total` and `traces_service_graph_request_server_seconds_bucket`. Labels included `service_name`, `span_kind`, `span_name`, `status_code`, `http_route` and `http_response_status_code`. A typical RED query:

```text
sum by (service_name, http_route) (rate(traces_span_metrics_calls_total{span_kind="SPAN_KIND_SERVER"}[5m]))
```

## Pitfalls

- **Empty service graph with several collector replicas.** The client span lands on replica A and the server span on replica B, so neither can pair them. Route by trace ID with the `load_balancing` exporter (see [why tail sampling needs a load-balancing tier](/guides/otel-collector-tail-sampling/)), or generate the graph in a single gateway.
- **No edges to databases or queues.** A database has no server span. `service_graph` can create *virtual nodes* from client span attributes (`virtual_node_peer_attributes`, for example `db.system.name` or `peer.service`) if your instrumentation sets them.
- **Double counting.** Running `span_metrics` in both agents and a gateway doubles every rate. Generate RED metrics in exactly one tier.
- **Status never ERROR.** HTTP server spans for 4xx responses keep status `UNSET` by semantic convention. Use `http.response.status_code` as a dimension if you want client errors on dashboards.
- **Metrics look delayed.** Values are flushed every `metrics_flush_interval`, then batched. A 15 s interval plus a 5 s batch timeout means up to about 20 s of lag.

## Next steps

- Keep full traces only for errors and slow requests after computing metrics: [tail sampling](/guides/otel-collector-tail-sampling/).
- Make the collector survive backend outages: [production-ready collector agent](/guides/otel-collector-production-agent/).
