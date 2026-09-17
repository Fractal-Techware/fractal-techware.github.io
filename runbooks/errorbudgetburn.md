---
title: "ErrorBudgetBurn: runbook and fix"
description: "ErrorBudgetBurn is a multi-window, multi-burn-rate SLO alert: a service is spending its error budget too fast. What burn rate means and how to respond."
permalink: /runbooks/errorbudgetburn/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: HTTP availability SLO (multi-window, multi-burn-rate)
severity: "warning, critical"
cta:
  title: Get this alert, tested
  text: "ErrorBudgetBurn is the SLO alert in the pack of 179, shipped with its recording rules, promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=errorbudgetburn
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# ErrorBudgetBurn

A service is failing enough requests that, if nothing changes, it will use up its allowed errors for the SLO period well before the period ends.

| | |
|---|---|
| Severity | warning (slow burn), critical (fast burn) |
| Source | Your application's HTTP request counter with a status code label |
| Key metric | `http_requests_total` (label `code`, grouped by `job`) |

## What it means

An availability SLO such as 99.9% over 30 days gives you an error budget: the 0.1% of requests that are allowed to fail. The **burn rate** is how fast you are spending it. A burn rate of 1 uses exactly the whole budget over the period; a burn rate of 10 would exhaust it in a tenth of the time.

This alert follows the multi-window, multi-burn-rate approach from the Google SRE Workbook. Each condition checks the error ratio over a **long window**, to prove the problem is significant, and a much **shorter window**, to prove it is still happening so the alert resolves quickly after recovery.

- **critical**: a high burn rate over hours. At this pace the monthly budget is gone within days. Page someone.
- **warning**: a lower but sustained burn over a day or more. The budget will run out before the period ends. Ticket it and fix in working hours.

Unlike a plain "error rate above X%" alert, this ignores short harmless blips and still catches slow, steady degradation.

## Common causes

- A bad deploy returning 5xx on some or all endpoints.
- A failing dependency: database, cache, or upstream API timing out.
- Capacity exhaustion: pods OOM-killed or throttled, connection pools full.
- An ingress or load balancer misrouting traffic to unhealthy backends.
- A new client or bot hammering an endpoint that errors.

## First checks

1. Current error ratio per service, short and longer view:
   ```promql
   sum by (job) (rate(http_requests_total{code=~"5.."}[5m]))
     / sum by (job) (rate(http_requests_total[5m]))
   ```
   Change `[5m]` to `[1h]` to see if it is sustained.
2. Which status codes and, if labelled, which handlers:
   ```promql
   sum by (code, handler) (rate(http_requests_total{job="<job>", code=~"5.."}[5m]))
   ```
3. Did it start with a rollout?
   ```bash
   kubectl -n <namespace> rollout history deployment/<name>
   kubectl -n <namespace> get events --sort-by=.lastTimestamp | tail -20
   ```
4. Read application logs for the error:
   ```bash
   kubectl -n <namespace> logs deploy/<name> --since=30m | grep -iE "error|timeout|refused" | tail -50
   ```
5. Check the ingress and dependencies for the same time range (see related alerts).

## Fixing it

Stop the bleeding first: roll back the last deploy (`kubectl rollout undo`), scale up, fail over, or disable the broken feature. Once errors drop, the short window clears and the alert resolves. Afterwards, decide as a team whether the budget spent means pausing risky releases until it recovers.

## Related alerts

- [NginxIngressHighHttp5xxErrorRate](/runbooks/nginxingresshighhttp5xxerrorrate/): 5xx errors seen at the ingress layer.
- [KubeAPIErrorsHigh](/runbooks/kubeapierrorshigh/): control-plane errors can break deploys and controllers.
