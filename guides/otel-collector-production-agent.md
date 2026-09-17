---
title: "Production-ready OpenTelemetry Collector: memory_limiter, batch, retries, queue, health_check"
description: "A tested OpenTelemetry Collector config that survives outages and memory spikes: memory_limiter, batch, retries, persistent queue, health_check."
permalink: /guides/otel-collector-production-agent/
breadcrumb: {title: Guides, url: /guides/}
tested_with: "otelcol-contrib 0.161.0"
cta:
  title: "16 production collector recipes, tested end to end"
  text: "Start from this hardened base and add what the pack covers: Kubernetes attributes, agent to gateway mTLS, trace-ID load balancing, a batching-safe persistent queue and ready-made self-monitoring alerts."
  button: See the recipes
  url: https://fractaltechware.gumroad.com/l/otel-collector-recipes?utm_source=site&utm_medium=guide&utm_campaign=otel-collector-production-agent
  free: https://github.com/Fractal-Techware/opentelemetry-collector-recipes
---
# Production-ready OpenTelemetry Collector config

*Tested with `otel/opentelemetry-collector-contrib:0.161.0`: `otelcol validate`, plus a run against an unreachable backend to confirm the health check, retries and the on-disk queue.*

The example config in most READMEs is fine for a demo. In production it fails in two ways. When the backend is down for a few minutes, data is silently dropped. When traffic spikes, the process is OOM-killed and takes everything in memory with it. The fix is only a handful of settings, but they have to be combined correctly.

## The config

```yaml
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
  file_storage/queue:
    directory: /var/lib/otelcol/queue
    create_directory: true

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
  batch:
    send_batch_size: 2048
    send_batch_max_size: 4096
    timeout: 5s

exporters:
  otlp_grpc:
    endpoint: ${env:OTLP_ENDPOINT}
    compression: gzip
    timeout: 10s
    retry_on_failure:
      enabled: true
      initial_interval: 1s
      max_interval: 30s
      max_elapsed_time: 10m
    sending_queue:
      enabled: true
      num_consumers: 8
      queue_size: 5000
      storage: file_storage/queue

service:
  extensions: [health_check, file_storage/queue]
  telemetry:
    logs:
      level: info
    metrics:
      level: normal
      readers:
        - pull:
            exporter:
              prometheus:
                host: 0.0.0.0
                port: 8888
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp_grpc]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp_grpc]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp_grpc]
```

Set `OTLP_ENDPOINT` to your gateway or vendor endpoint, for example `gateway.observability:4317`. For a plaintext endpoint inside the cluster, add `tls: {insecure: true}` to the exporter.

## What each piece does

### memory_limiter: first in every pipeline

Every `check_interval`, the processor compares heap usage with its limits. Above the *soft* limit (`limit_percentage - spike_limit_percentage`, here 60% of available memory), receivers start **refusing** data with a retryable error. OTLP clients back off and retry, so data waits in the SDKs instead of crashing the collector. Above the hard limit (80%) it also forces garbage collection.

Percentages are calculated from the **cgroup memory limit**. Without a container memory limit, "80%" means 80% of the node, and the limiter never triggers before the kernel OOM killer does. Always set:

```yaml
resources:
  limits:
    memory: 512Mi
env:
  - name: GOMEMLIMIT
    value: "410MiB"   # about 80% of the limit
```

It must be the first processor. Anything placed before it (a transform, a tail sampler) uses memory the limiter cannot account for.

### batch: last before the exporters

The batch processor groups items into bigger requests. That means fewer network round trips and much better gzip compression. `send_batch_size` triggers a send once enough items are buffered. `timeout` caps how long data waits when traffic is low. `send_batch_max_size` splits very large incoming requests so you do not hit a backend's maximum request size (often 4 MiB for gRPC).

### retry_on_failure: surviving short outages

On a retryable error (connection refused, 429, 503, gRPC `UNAVAILABLE`), the exporter retries with exponential backoff from `initial_interval` up to `max_interval`. It gives up on a batch after `max_elapsed_time`. With 10 minutes, a restart of the backend or a short network partition loses nothing. Permanent errors (400, invalid data) are not retried. They are logged and dropped.

### sending_queue: buffering, optionally on disk

Exports run from a queue served by `num_consumers` workers, so a slow backend does not block the pipeline. `queue_size` counts batches (requests), not spans. With `storage: file_storage/queue` the queue is written to disk, so **a collector restart during an outage does not lose the buffered data**. Mount a persistent volume at that path, writable by uid 10001. Without `storage`, the queue lives in memory. It is faster, but it is lost on restart and counts against your memory limit.

When the queue is full, new data is rejected. The collector logs a "sending queue is full" error, and `otelcol_exporter_enqueue_failed_*` goes up. Size it for the outage you want to survive: `batches per second × seconds of outage`.

### health_check: probes that mean something

The extension serves HTTP 200 on port 13133 once the collector has started, and 503 while it is starting or shutting down. Point Kubernetes probes at it:

```yaml
livenessProbe:
  httpGet: {path: /, port: 13133}
readinessProbe:
  httpGet: {path: /, port: 13133}
```

Do not expose 13133 or 8888 outside the pod or host. In containers, `0.0.0.0` is needed for probes and scraping to work. On a plain VM, bind to `localhost`.

## Verify it

Validate the config, then deliberately point the exporter at a backend that does not exist:

```bash
docker run --rm -e OTLP_ENDPOINT=x:4317 -v "$PWD:/cfg" \
  otel/opentelemetry-collector-contrib:0.161.0 validate --config=/cfg/config.yaml

mkdir -p queue && sudo chown 10001:10001 queue
docker run -d --name otelcol -e OTLP_ENDPOINT=unreachable.invalid:4317 \
  -p 4318:4318 -p 13133:13133 -p 8888:8888 \
  -v "$PWD/config.yaml:/etc/otelcol-contrib/config.yaml:ro" \
  -v "$PWD/queue:/var/lib/otelcol/queue" \
  otel/opentelemetry-collector-contrib:0.161.0

curl -s localhost:13133/
# {"status":"Server available","upSince":"...","uptime":"4.9s"}
```

Send a span to `localhost:4318/v1/traces` (any OTLP JSON payload), then check:

```bash
docker logs otelcol 2>&1 | grep 'Will retry'
# ... Exporting failed. Will retry the request after interval. ...

curl -s localhost:8888/metrics | grep -E '^otelcol_exporter_queue_(size|capacity)\{data_type="traces"'
# otelcol_exporter_queue_capacity{data_type="traces",exporter="otlp_grpc"} 5000
# otelcol_exporter_queue_size{data_type="traces",exporter="otlp_grpc"} 1

ls queue/
# exporter_otlp_grpc__logs  exporter_otlp_grpc__metrics  exporter_otlp_grpc__traces
```

That is what we saw in our test: the span was accepted, it sits in the on-disk queue, and the exporter keeps retrying.

## Alert on these metrics

- `otelcol_exporter_queue_size / otelcol_exporter_queue_capacity > 0.8`: backend is slow or down, and data loss is close.
- `rate(otelcol_exporter_send_failed_spans[5m]) > 0` or `rate(otelcol_exporter_enqueue_failed_spans[5m]) > 0` (plus the `_metric_points` / `_log_records` variants): data is being dropped, either because retries ran out or because the queue is full.
- `rate(otelcol_receiver_refused_spans[5m]) > 0`: the memory_limiter is refusing data. Scale out or raise the memory limit.

## Pitfalls

- **Deprecated component names.** Configs written for older versions use `otlp` and `otlphttp` as exporter names. In 0.161.0 they still load, but they log `"otlp" alias is deprecated; use "otlp_grpc" instead`. Rename them now, before the aliases are removed.
- **`batch` before `memory_limiter`.** Data is already accepted and buffered before the limiter gets a chance to refuse it, so back-pressure reaches clients too late.
- **Queue on an `emptyDir`.** It survives a container restart but not a pod reschedule. For DaemonSets use a `hostPath` per node, and for gateways a StatefulSet with a PVC.
- **Expecting the disk queue to cover a crash completely.** The `batch` processor holds up to one batch in memory *before* the persistent queue. A hard crash loses that batch. If that matters, drop the `batch` processor and batch inside the exporter queue instead (`sending_queue.batch` with `sizer: items`). The pack's persistent-queue recipe is built that way.
- **Two collectors sharing one queue directory.** The file storage is locked by one process. Give each replica its own path.
- **Receivers bound to `localhost` in a container.** Apps in other containers cannot reach them. Use `0.0.0.0` or the pod IP.

## Next steps

- Keep only the traces that matter: [tail sampling config](/guides/otel-collector-tail-sampling/).
- Cut volume before it hits the queue: [drop noisy spans, metrics and debug logs](/guides/otel-collector-reduce-telemetry-cost/).
