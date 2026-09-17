---
title: "Redact PII in the OpenTelemetry Collector with OTTL (emails, cards, auth headers)"
description: "A tested transform processor config that masks emails and card numbers and deletes Authorization and cookie attributes from traces and logs."
permalink: /guides/otel-collector-redact-pii-ottl/
breadcrumb: {title: Guides, url: /guides/}
tested_with: "otelcol-contrib 0.161.0"
cta:
  title: "Hardened PII redaction and 15 more tested collector recipes"
  text: "The pack's redaction recipe adds a second layer with the redaction processor, span event coverage, integer card numbers, Basic auth and query-string secrets, verified by an automated end-to-end test."
  button: See the recipes
  url: https://fractaltechware.gumroad.com/l/otel-collector-recipes?utm_source=site&utm_medium=guide&utm_campaign=otel-collector-redact-pii-ottl
  free: https://github.com/Fractal-Techware/opentelemetry-collector-recipes
---
# Redact PII in the OpenTelemetry Collector with OTTL

*Tested with `otel/opentelemetry-collector-contrib:0.161.0`: `otelcol validate` plus a smoke test that sent real spans and logs and checked the debug output.*

Auto-instrumentation records more than you expect: `user.email` on spans, raw request headers, and log lines like `payment by jane@example.com card=4111...`. Once that reaches your tracing or logging backend it is copied, indexed and kept for months. The collector is the last place you control before that happens, so it is a good place for a safety net.

This guide uses the `transform` processor and OTTL to:

- **delete** credential attributes: `Authorization`, `Cookie`, `Set-Cookie`, `X-Api-Key`, and anything named `password`, `secret` or `access_token`
- **mask** email addresses in span names, attribute values, log attributes and log bodies
- **mask** card-like numbers (13–19 digits, optionally separated by spaces or dashes)
- **mask** `Bearer` tokens in free-text log bodies

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

  transform/redact_pii:
    error_mode: ignore
    trace_statements:
      - context: span
        statements:
          # 1. Credentials: remove the attribute entirely.
          - delete_matching_keys(span.attributes, "(?i)(^|\\.)(authorization|cookie|set-cookie|x-api-key|api[_-]?key|password|passwd|secret|access[_-]?token)$$")
          # 2. Emails anywhere in string attribute values and in the span name.
          - replace_all_patterns(span.attributes, "value", "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", "<email>")
          - replace_pattern(span.name, "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", "<email>")
          # 3. Card-like numbers: 13-19 digits, optionally separated by spaces or dashes.
          - replace_all_patterns(span.attributes, "value", "\\b\\d(?:[ -]?\\d){12,18}\\b", "<card>")
    log_statements:
      - context: log
        statements:
          - delete_matching_keys(log.attributes, "(?i)(^|\\.)(authorization|cookie|set-cookie|x-api-key|api[_-]?key|password|passwd|secret|access[_-]?token)$$")
          - replace_all_patterns(log.attributes, "value", "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", "<email>")
          - replace_all_patterns(log.attributes, "value", "\\b\\d(?:[ -]?\\d){12,18}\\b", "<card>")
          # String bodies: emails, cards and bearer tokens inside free text.
          - replace_pattern(log.body, "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", "<email>") where IsString(log.body)
          - replace_pattern(log.body, "\\b\\d(?:[ -]?\\d){12,18}\\b", "<card>") where IsString(log.body)
          - replace_pattern(log.body, "(?i)bearer\\s+[A-Za-z0-9._~+/=-]+", "Bearer <token>") where IsString(log.body)

  batch:
    timeout: 5s

exporters:
  otlp_grpc:
    endpoint: backend.example.internal:4317

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, transform/redact_pii, batch]
      exporters: [otlp_grpc]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, transform/redact_pii, batch]
      exporters: [otlp_grpc]
```

## The important parts

**Delete credentials, don't mask them.** `delete_matching_keys` removes the attribute entirely. A masked `Authorization` header is still noise in storage. The key regex is anchored to the whole name or its last dot-separated segment (`(^|\.)...$`). Without that anchor, a loose pattern such as `token` also deletes useful attributes like `gen_ai.usage.input_tokens`. Our smoke test includes that attribute to make sure it survives.

**`$$` instead of `$`.** The collector expands `${...}` environment variables in the config file, and `$$` is the escape for a literal `$`. Writing `$$` in YAML gives OTTL the regex end anchor `$`.

**Double backslashes.** The statements are YAML strings that contain OTTL strings. `\\.` in the file becomes `\.` in the regex.

**`replace_all_patterns(..., "value", ...)`** rewrites every *string* attribute value that matches. Integer and double attributes are not touched (see pitfalls).

**`where IsString(log.body)`** skips structured (map) bodies. `replace_pattern` on a map body would do nothing, and the condition makes the intent explicit.

**`context:` groups.** The statements are grouped by OTTL context (`span`, `log`). This is the current, unambiguous form. If you later add span *event* statements, give them their own `context: spanevent` group. Mixing both in one flat list makes the whole list run in the span-event context, and then it only touches spans that have events.

**Order.** The processor runs before `batch` and before any exporter. No unredacted copy leaves the process, including through a second exporter on the same pipeline.

## Verify it

Use the debug exporter so you can see the output. Save as `debug.yaml`:

```yaml
exporters:
  debug:
    verbosity: detailed
service:
  pipelines:
    traces:
      exporters: [debug]
    logs:
      exporters: [debug]
```

```bash
docker run --rm -p 4318:4318 -v "$PWD:/cfg" otel/opentelemetry-collector-contrib:0.161.0 \
  --config=/cfg/config.yaml --config=/cfg/debug.yaml
```

Send a log record:

```bash
curl -s -H 'Content-Type: application/json' http://localhost:4318/v1/logs -d '{
 "resourceLogs":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"checkout"}}]},
 "scopeLogs":[{"logRecords":[{"severityNumber":9,
  "body":{"stringValue":"payment by jane.doe@example.com card=4111111111111111 header Authorization: Bearer eyJhbGciOi.abc-123"},
  "attributes":[{"key":"db.password","value":{"stringValue":"hunter2"}},
                {"key":"customer","value":{"stringValue":"bob@shop.io"}}]}]}]}]}'
```

The collector prints:

```text
Body: Str(payment by <email> card=<card> header Authorization: Bearer <token>)
Attributes:
     -> customer: Str(<email>)
```

`db.password` is gone. For spans, we sent `http.request.header.authorization`, `http.request.header.cookie`, `user.email`, `payment.card: "4111 1111 1111 1111"`, a free-text note with a dashed card number and an email, and a span named `lookup jane.doe@example.com`. The output kept `http.route`, `order.id: "12345678"` and `gen_ai.usage.input_tokens: 42` unchanged. The credential attributes were removed and everything else became `<email>` or `<card>`.

Make this a regression test: keep a few sample payloads in your repo, run the collector in CI, and `grep` the debug output for anything that looks like an email.

## Pitfalls

- **Integer card numbers.** A card stored as an `intValue` attribute is not a string, so the regex never sees it. If your apps do that, convert it first, for example `set(span.attributes["payment.card"], "<card>") where span.attributes["payment.card"] != nil`.
- **False positives.** Any 13–19 digit run is masked, including some order IDs and timestamps in nanoseconds. Narrow the pattern (for example, only numbers starting with 3–6) or add a Luhn check upstream if that hurts.
- **Not covered here:** span events (exception messages often contain PII), resource attributes, URL query strings (`?token=...`), IP addresses and structured map bodies. Each needs its own statements.
- **Collector logs.** A `debug` exporter left on in production writes the *redacted* data, but anything logged before the transform (for example receiver errors) can still contain raw payloads. Keep `debug` off outside testing.
- **It is a safety net, not a compliance control.** Fix the instrumentation that records PII, and treat the collector rules as defence in depth.

## Next steps

- Ship the redacted logs somewhere: [send logs to Grafana Loki over OTLP](/guides/otel-collector-logs-to-loki-otlp/).
- Cut volume at the same time: [drop noisy spans, metrics and debug logs](/guides/otel-collector-reduce-telemetry-cost/).
