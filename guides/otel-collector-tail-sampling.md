---
title: "OpenTelemetry Collector tail sampling: a working config"
description: "Keep every error and slow trace plus a small baseline with tail_sampling. Tested config, how to verify it, and why scaling out needs load balancing."
permalink: /guides/otel-collector-tail-sampling/
breadcrumb: {title: Guides, url: /guides/}
tested_with: "otelcol-contrib 0.161.0"
cta:
  title: "16 production collector recipes, tested end to end"
  text: "The full pack includes a two-tier agent and gateway setup with trace-ID load balancing and tail sampling, plus Docker Compose files and troubleshooting notes."
  button: See the recipes
  url: https://store.fractaltechware.com/l/otel-collector-recipes?utm_source=site&utm_medium=guide&utm_campaign=otel-collector-tail-sampling
  free: https://github.com/Fractal-Techware/opentelemetry-collector-recipes
---
# OpenTelemetry Collector tail sampling: a working config

*Tested with `otel/opentelemetry-collector-contrib:0.161.0`: `otelcol validate` plus a smoke test that sent error, slow and normal traces.*

Head sampling (a percentage chosen in the SDK) is cheap, but it decides before anything has happened. You end up dropping the one trace with the 500 error and keeping thousands of fast health checks. Tail sampling waits until a trace is finished and then decides. The usual goal is:

- keep **every trace that has an error**
- keep **every slow trace**
- keep a **small random baseline** of everything else, so normal traffic still shows up in dashboards

Below is a single-collector config that does exactly that. At the end we cover the part most examples skip: what breaks once you run more than one replica.

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
    limit_percentage: 75
    spike_limit_percentage: 20

  tail_sampling:
    decision_wait: 10s
    num_traces: 50000
    expected_new_traces_per_sec: 500
    decision_cache:
      sampled_cache_size: 100000
      non_sampled_cache_size: 100000
    policies:
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: slow
        type: latency
        latency:
          threshold_ms: 800
      - name: baseline
        type: probabilistic
        probabilistic:
          sampling_percentage: 5

  batch:
    send_batch_size: 1024
    timeout: 5s

exporters:
  otlp_grpc:
    endpoint: tempo.observability.svc:4317
    tls:
      insecure: true

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, tail_sampling, batch]
      exporters: [otlp_grpc]
```

Point `otlp_grpc.endpoint` at your backend (Tempo, Jaeger, a vendor gateway). Set `insecure: true` only inside a trusted network. Remove it and configure `tls` otherwise.

## How it works

**Policies are ORed.** A trace is kept if *any* policy says "sample". An error trace is kept by `errors` even when `baseline` would drop it. You do not need a composite policy for this common case.

**`decision_wait`** is how long the processor buffers spans after it sees the first span of a trace. Spans that arrive later do not change the decision. Set it a bit longer than your slowest normal request. If a trace takes 30 s end to end and `decision_wait` is 10 s, the latency policy only sees the spans that arrived in the first 10 s.

**`num_traces`** is how many traces are held in memory at once. Roughly, you need `traces per second × decision_wait`. At 500 new traces/s and 10 s that is 5,000, so 50,000 leaves plenty of room. If the value is too small, traces are evicted before a decision is made. Give the collector a real memory limit, because this buffer is where the memory goes.

**`decision_cache`** remembers recent decisions by trace ID. When a late span arrives for a trace that was already sampled, it follows the same decision instead of turning into a new, incomplete trace.

**`latency.threshold_ms`** is measured from the earliest span start to the latest span end in the trace, not from a single span.

**`probabilistic`** hashes the trace ID. The same trace ID always gets the same answer, which matters in the scaled-out setup below.

**Processor order.** `memory_limiter` comes first so the collector refuses data before it runs out of memory. `batch` goes *after* `tail_sampling`, because tail sampling releases one trace at a time and re-batching makes exports efficient.

## Verify it

Temporarily send the output to the `debug` exporter instead of your backend. Save this as `debug.yaml`. Lists are replaced when configs are merged, so it swaps the exporter list:

```yaml
exporters:
  debug:
    verbosity: normal
service:
  pipelines:
    traces:
      exporters: [debug]
```

```bash
docker run --rm -v "$PWD:/cfg" otel/opentelemetry-collector-contrib:0.161.0 \
  validate --config=/cfg/config.yaml

docker run --rm -p 4318:4318 -v "$PWD:/cfg" otel/opentelemetry-collector-contrib:0.161.0 \
  --config=/cfg/config.yaml --config=/cfg/debug.yaml
```

Now send one span with `"status":{"code":2}` (ERROR), one span that lasts 1.5 s, and a few dozen fast OK spans to `http://localhost:4318/v1/traces`, each with its own `traceId`. After `decision_wait`, the debug output should contain the error trace, the slow trace and about 5% of the fast ones. In our run, 40 fast traces produced 5 kept traces. With so few traces, that is normal variation around 5%.

In production, watch these metrics on the collector's own telemetry endpoint (port 8888):

- `otelcol_processor_tail_sampling_global_count_traces_sampled{sampled="true|false"}`: your real keep ratio.
- `otelcol_processor_tail_sampling_sampling_trace_dropped_too_early`: if this is above zero, `num_traces` is too small.
- `otelcol_processor_tail_sampling_sampling_traces_on_memory`: how full the buffer is.

## Scaling out: why you need a load-balancing tier

Tail sampling only works if **every span of a trace reaches the same collector instance**. Put three replicas behind a normal Kubernetes Service and the spans of one trace get spread across all three. Each replica sees part of the trace. One might see the error span and keep its part, while another sees only the fast spans and drops them. You end up with broken, partial traces, and the error and latency policies make decisions on incomplete data.

The standard fix is two tiers:

1. **Front tier** (agents or a small stateless deployment) receives OTLP and uses the `load_balancing` exporter with `routing_key: traceID`. It hashes the trace ID and always sends a given trace to the same backend replica.
2. **Sampling tier** runs the config above, usually as a StatefulSet or Deployment behind a **headless** Service, so DNS returns every pod IP.

A minimal front-tier exporter looks like this:

```yaml
exporters:
  load_balancing:
    routing_key: traceID
    protocol:
      otlp:
        tls:
          insecure: true
    resolver:
      dns:
        hostname: otelcol-sampler-headless.observability.svc.cluster.local
        port: "4317"
```

(The `port` has to be a quoted string. A bare number fails validation.) When sampler pods are added or removed, the hash ring changes and some in-flight traces get split for a moment. That is expected and brief. Use the `k8s` resolver instead of `dns` if you want faster updates. Keep `memory_limiter` in the front tier, and give the exporter its own retry and queue settings.

## Pitfalls

- **Filtering too aggressively in the front tier.** Any span dropped before the sampler (for example by a `filter` processor) is invisible to the error and latency policies. Only drop spans there that you never want, such as health checks.
- **Sampling metrics derived from spans.** If you generate RED metrics with the `span_metrics` connector *after* tail sampling, your request rates are wrong by the sampling ratio. Compute them before sampling. See [span metrics and service graphs](/guides/otel-collector-span-metrics-service-graph/).
- **Head sampling in the SDK as well.** If the SDK already samples at 10%, tail sampling only ever sees 10% of the errors. Use `parentbased_always_on` in the SDK when the collector does tail sampling.
- **Health checks eating the baseline.** Drop probe spans first so the 5% baseline is spent on real traffic. [Filtering noisy spans](/guides/otel-collector-reduce-telemetry-cost/) shows how.

## Next steps

- Harden the collector itself: [production-ready collector agent](/guides/otel-collector-production-agent/).
- Remove sensitive data before it reaches storage: [redact PII with OTTL](/guides/otel-collector-redact-pii-ottl/).
