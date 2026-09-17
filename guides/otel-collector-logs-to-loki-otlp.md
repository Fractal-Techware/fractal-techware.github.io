---
title: "Send logs to Grafana Loki with the OpenTelemetry Collector (native OTLP)"
description: "Tail log files with the file_log receiver and ship them to Loki 3's native OTLP endpoint. Tested config, labels vs structured metadata, and LogQL checks."
permalink: /guides/otel-collector-logs-to-loki-otlp/
breadcrumb: {title: Guides, url: /guides/}
tested_with: "otelcol-contrib 0.161.0, Loki 3.7.7"
cta:
  title: "16 production collector recipes, tested end to end"
  text: "The full pack adds Kubernetes metadata enrichment, per-tenant routing to Loki and Tempo, an on-disk queue for backend outages and Docker Compose files for every recipe."
  button: See the recipes
  url: https://fractaltechware.gumroad.com/l/otel-collector-recipes?utm_source=site&utm_medium=guide&utm_campaign=otel-collector-logs-to-loki-otlp
  free: https://github.com/Fractal-Techware/opentelemetry-collector-recipes
---
# Send logs to Grafana Loki with the OpenTelemetry Collector (native OTLP)

*Tested with `otel/opentelemetry-collector-contrib:0.161.0` and `grafana/loki:3.7.7`: we wrote lines to a file and queried them back from Loki.*

Many "OpenTelemetry to Loki" examples use the `loki` exporter. That exporter is gone from collector-contrib. Since Loki 3.0, Loki accepts OTLP directly at `/otlp`, so all you need is the standard `otlp_http` exporter. This guide tails application log files, parses JSON lines, and sends everything to Loki with offsets saved to disk, so a restart does not duplicate or lose lines.

## The config

```yaml
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
  file_storage:
    directory: /var/lib/otelcol/file_storage
    create_directory: true

receivers:
  file_log:
    include: [/var/log/app/*.log]
    start_at: end
    include_file_path: true
    storage: file_storage
    operators:
      # Parse JSON lines; leave anything else as a plain string body.
      - type: json_parser
        if: 'body matches "^\\s*\\{"'
        parse_to: attributes
        timestamp:
          parse_from: attributes.time
          layout_type: strptime
          layout: '%Y-%m-%dT%H:%M:%S.%LZ'
        severity:
          parse_from: attributes.level

processors:
  memory_limiter:
    check_interval: 1s
    limit_percentage: 80
    spike_limit_percentage: 20
  resource/service:
    attributes:
      - key: service.name
        value: payments-api
        action: upsert
      - key: deployment.environment.name
        value: production
        action: upsert
  batch:
    timeout: 5s

exporters:
  otlp_http/loki:
    endpoint: http://loki:3100/otlp
    headers:
      X-Scope-OrgID: tenant-a
    retry_on_failure:
      enabled: true
    sending_queue:
      enabled: true

service:
  extensions: [health_check, file_storage]
  pipelines:
    logs:
      receivers: [file_log]
      processors: [memory_limiter, resource/service, batch]
      exporters: [otlp_http/loki]
```

## The important parts

**`file_log` receiver.** In 0.161.0 the receiver is `file_log`. Older posts call it `filelog`, which now triggers a deprecation warning. `start_at: end` means only new lines are read on first start. Use `beginning` once if you want to backfill.

**`storage: file_storage`.** The receiver saves how far it has read in each file. Without it, a restart with `start_at: end` skips everything written while the collector was down. The directory must be writable by the collector user (uid 10001 in the official image) and must survive restarts: a volume, or a `hostPath` on a DaemonSet.

**The JSON parser only runs on JSON.** The `if:` expression means plain-text lines pass through untouched instead of producing parser errors. Parsed fields go to attributes. `timestamp` and `severity` are set from the `time` and `level` fields. Change the field names and `layout` to match your logger. If your lines have no timestamp, remove the `timestamp` block and the read time is used.

**The endpoint is `/otlp`, not `/otlp/v1/logs`.** The `otlp_http` exporter adds `/v1/logs` itself. If you set the full path, the requests go to `/otlp/v1/logs/v1/logs` and fail with 404.

**`X-Scope-OrgID`** selects the tenant in multi-tenant Loki (Grafana Enterprise Logs, Mimir-style setups, most Helm installs with `auth_enabled: true`). Single-tenant Loki ignores it.

**`service.name` matters.** Loki turns a few well-known resource attributes into **stream labels**, including `service.name` → `service_name` and `deployment.environment.name` → `deployment_environment_name`. Everything else, including your parsed JSON fields, becomes **structured metadata**, not labels. That is deliberate: it keeps label cardinality low. If `service.name` is missing, logs land under `service_name="unknown_service"`.

## Verify it

Run Loki and the collector on one Docker network:

```bash
docker network create logs
docker run -d --name loki --network logs -p 3100:3100 grafana/loki:3.7.7 \
  -config.file=/etc/loki/local-config.yaml
mkdir -p logs data && sudo chown 10001:10001 data
docker run -d --name otelcol --network logs \
  -v "$PWD/config.yaml:/etc/otelcol-contrib/config.yaml:ro" \
  -v "$PWD/logs:/var/log/app:ro" -v "$PWD/data:/var/lib/otelcol" \
  otel/opentelemetry-collector-contrib:0.161.0
```

Write a JSON line and a plain line:

```bash
echo "{\"time\":\"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)\",\"level\":\"error\",\"msg\":\"payment declined\",\"order_id\":\"A-1001\"}" >> logs/app.log
echo "plain text line WARN disk almost full" >> logs/app.log
```

After about 10 seconds, check which labels exist and query the stream:

```bash
curl -s http://localhost:3100/loki/api/v1/labels
# {"status":"success","data":["deployment_environment_name","service_name"]}

curl -sG http://localhost:3100/loki/api/v1/query_range \
  --data-urlencode 'query={service_name="payments-api"} | order_id="A-1001"' \
  --data-urlencode 'since=10m'
```

In our test the query returned the JSON line with `order_id`, `level`, `msg` and `severity_text: error` as structured metadata. The plain line came back without a `level` attribute, and Loki still showed `detected_level: warn`. In Grafana Explore, the same LogQL works: filter on structured metadata with `| order_id="A-1001"` after the stream selector.

## Pitfalls

- **Expecting JSON fields as labels.** `{order_id="A-1001"}` returns nothing, because `order_id` is not a label. Use `{service_name="payments-api"} | order_id="A-1001"`. If you really need an extra label, add it to `distributor.otlp_config` / `limits_config.otlp_config` in Loki, not in the collector. Keep it low-cardinality.
- **Structured metadata disabled.** Loki needs `allow_structured_metadata: true` and a TSDB schema v13. Both are the default in Loki 3, but upgraded installs sometimes still run schema v12, and then OTLP ingestion is rejected.
- **Out-of-order or too-old timestamps.** If you parse `time` from old files, Loki can reject lines older than `reject_old_samples_max_age`. The exporter logs a 400. Backfills need that limit raised, or drop the `timestamp` block.
- **Permission denied on the storage directory.** The image runs as uid 10001. `chown` the volume or set `fsGroup: 10001` in Kubernetes.
- **Rotated files.** Exclude compressed rotations (`exclude: ["*.gz"]`) if they match your glob, otherwise you read binary data.
- **Log lines containing PII.** Add a redaction step before `batch`. See [redact PII with OTTL](/guides/otel-collector-redact-pii-ottl/).

## Next steps

- Keep noisy DEBUG lines out of Loki: [reduce telemetry cost](/guides/otel-collector-reduce-telemetry-cost/).
- Make the collector itself production-ready: [memory_limiter, retries, queues and health checks](/guides/otel-collector-production-agent/).
- A fuller free version of this recipe (with JSON/plain-text routing and Docker Compose) is in the [free GitHub repo](https://github.com/Fractal-Techware/opentelemetry-collector-recipes).
