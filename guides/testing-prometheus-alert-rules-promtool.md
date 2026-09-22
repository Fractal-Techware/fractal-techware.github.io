---
title: Test your alert rules with promtool
description: We shipped a dashboard querying a metric name that does not exist. Alert rules fail the same way and fail silently — here is the promtool suite that catches it, including the test almost nobody writes.
---
# Test your alert rules with promtool

We shipped a Grafana dashboard whose disk panels queried `node_disk_read_bytes_completed`.

That metric does not exist. node_exporter calls it `node_disk_read_bytes_total`. The panels rendered fine, the dashboard imported cleanly, Grafana reported no error — the graphs were just empty. On a host with no disk activity, an empty graph is also what *correct* looks like. It took a real node_exporter on a real host to notice, and by then it was in a released zip.

That is a dashboard, so the damage is a blank panel. The same class of mistake in an alert rule is worse, because a rule that can never fire is indistinguishable from a system that is healthy. You do not get an error. You get silence, which is exactly what you were hoping for.

Alert rules are code that runs in production and decides whether anyone wakes up. Almost nobody tests them.

## promtool tests rules, not just syntax

Most people know `promtool check rules` — it validates YAML and PromQL syntax. It would not have caught the bug above, because `node_disk_read_bytes_completed` is syntactically perfect PromQL. It just never matches anything.

`promtool test rules` is the other command. You give it synthetic time series, and it runs your real rule files against them and asserts what fired:

```yaml
rule_files:
  - ../rules/kubernetes-workloads.rules.yml
evaluation_interval: 1m
tests:
  - name: 'KubePodCrashLooping fires'
    interval: 1m
    input_series:
      - series: kube_pod_container_status_waiting_reason{job="kube-state-metrics",namespace="shop",pod="api-7d9f",container="api",reason="CrashLoopBackOff"}
        values: 1x40
    alert_rule_test:
      - eval_time: 30m
        alertname: KubePodCrashLooping
        exp_alerts:
          - exp_labels:
              job: kube-state-metrics
              namespace: shop
              pod: api-7d9f
              container: api
              reason: CrashLoopBackOff
              severity: warning
            exp_annotations:
              summary: Pod container is crash looping.
              description: Container api in pod shop/api-7d9f has been in CrashLoopBackOff for at least 15m.
              runbook_url: runbooks/kubernetes-workloads/KubePodCrashLooping.md
```

Run it with `promtool test rules tests/*.test.yml`. It exits non-zero on failure, so it drops straight into CI.

`values: 1x40` means "start at 1, then 40 more samples each adding 0" — a flat line at 1 for 40 minutes. The syntax is `start+increment xN`, and getting comfortable with it is most of the learning curve.

One gotcha that will catch you on the first run: `exp_annotations` and `exp_labels` are **exhaustive**, not a subset match. Leave out the `runbook_url` annotation your rule sets and the test fails with a diff showing the same alert twice, identical apart from the missing line. That strictness is the point — it means an annotation you did not intend to add cannot appear on a pager unnoticed — but it does mean the fastest way to write the first test is to run it once, let it fail, and copy the `got:` block into `exp_alerts`.

The important part is that this test names the metric. If you typo the metric in the rule, the input series no longer matches, the alert does not fire, and the test fails. That is the check the dashboard never had.

## The test almost nobody writes

Here is the one that matters, and it is the one missing from most rule suites:

```yaml
  - name: 'KubePodCrashLooping stays quiet: container still creating'
    interval: 1m
    input_series:
      - series: kube_pod_container_status_waiting_reason{job="kube-state-metrics",namespace="shop",pod="api-7d9f",container="api",reason="ContainerCreating"}
        values: 1x40
    alert_rule_test:
      - eval_time: 30m
        alertname: KubePodCrashLooping
        exp_alerts: []
```

`exp_alerts: []` asserts the alert **does not** fire. A pod that is merely slow to start is not crash looping, and paging someone for it is how a rule gets muted, and how a muted rule stops catching the real thing three months later.

A rule that fires on the bad case is half a rule. The other half is staying quiet on the cases that look similar but are fine. If you write one test per alert, write this one — the positive case usually gets exercised in production eventually, whether you tested it or not. The negative case is what nobody finds out about until the alert has been ignored for a quarter.

## Four things worth asserting

**The `for:` duration actually holds.** An alert with `for: 15m` should not fire at 10m. Set `eval_time: 10m` with `exp_alerts: []`, and a second case at `30m` that fires. This catches the copy-paste where a rule keeps the previous rule's duration.

```yaml
    alert_rule_test:
      - eval_time: 10m
        alertname: KubePodCrashLooping
        exp_alerts: []
      - eval_time: 30m
        alertname: KubePodCrashLooping
        exp_alerts: [...]
```

**Labels survive aggregation.** This is where `by`/`without` clauses quietly drop the label your Alertmanager routes on. If your routing tree keys on `namespace` and an aggregation eats it, every alert lands in the fallback receiver. `exp_labels` is an exact match — a dropped label fails the test.

**Annotation templating renders.** `exp_annotations` compares the rendered string, so `{{ $labels.pod }}` resolving to nothing shows up as a diff. A description reading "Container in pod / has been..." is a real thing that reaches real pagers.

**Recording rules produce what you think.** Use `promql_expr_test` to assert the value:

```yaml
    promql_expr_test:
      - expr: namespace:container_memory_usage:sum
        eval_time: 5m
        exp_samples:
          - labels: 'namespace:container_memory_usage:sum{namespace="shop"}'
            value: 5.24288e+08
```

Alerts built on recording rules inherit their bugs, and a wrong recording rule is even quieter than a wrong alert.

## Wiring it into CI

```yaml
- name: Test alert rules
  run: |
    promtool check rules rules/*.rules.yml
    promtool test rules tests/*.test.yml
```

Both commands exit non-zero on failure. `check rules` catches malformed YAML and invalid PromQL; `test rules` catches rules that are valid and wrong. You want both, in that order, because a syntax error produces a confusing test failure.

One caveat worth knowing: promtool evaluates your rules against the series *you* provide, so it cannot tell you that `kube_pod_container_status_waiting_reason` is the right metric for your kube-state-metrics version — only that your rule and your test agree about it. Synthetic series prove the logic, not the metric's existence in your cluster. For that, check the names against a running exporter. We now do that as a separate step, for exactly the reason this post opens with.

## What this costs

Our alert pack is 179 rules with 364 promtool tests behind them — roughly two tests per rule, which is the positive case plus the quiet case, with extra cases where a rule has a threshold worth pinning down. Writing them took longer than writing the rules did.

That ratio sounds bad until you consider what the alternative is. An untested alert rule is a claim about production that nobody has checked, and the feedback loop on a wrong one is measured in incidents, not in CI runs. The four assertions above are cheap to write once you have the pattern, and each of them fails loudly at the point where it is still free to fix.

## Try it

The free MIT edition has 12 of these alerts — CrashLooping, OOMKilled, stuck rollouts, disk filling up, node down — with their promtool tests and a runbook each, so you can see the pattern in full and lift it into your own repo:

**[github.com/Fractal-Techware/prometheus-alert-rules](https://github.com/Fractal-Techware/prometheus-alert-rules)**

If you want the whole thing rather than the pattern, the [full pack](https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=guide&utm_campaign=promtool-post) is 179 alerts across 20 domains with 364 tests, 165 runbooks, PrometheusRule CRDs and tested Alertmanager routing.
