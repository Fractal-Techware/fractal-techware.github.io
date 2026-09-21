---
title: "KubeJobFailed: runbook and fix"
description: "KubeJobFailed means a Kubernetes Job gave up after exhausting retries or hitting its deadline. How to find why the pods failed, rerun, and clear it."
permalink: /runbooks/kubejobfailed/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes Jobs & CronJobs
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeJobFailed is one of 3 Job and CronJob alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubejobfailed
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeJobFailed

A Kubernetes Job has been marked Failed, so the batch work it was supposed to do did not complete.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metric | `kube_job_failed` (labels `namespace`, `job_name`, `condition`) |

## What it means

The Job controller sets a `Failed` condition when a Job exceeds its `backoffLimit` (too many failed pod attempts) or its `activeDeadlineSeconds`. The alert fires once a Job has carried that condition for a few minutes.

The alert keeps firing for as long as the failed Job object exists. For a CronJob, the next run may already have succeeded while the old failure still alerts, so check whether the problem is current before digging in. Missed backups, reports or migrations are the usual impact.

## Common causes

- **Application error**: the container exits non-zero (bad input, dependency down, expired credentials).
- **OOMKilled**: the pod exceeded its memory limit on a larger than usual dataset.
- **Deadline exceeded**: the run took longer than `activeDeadlineSeconds`.
- **Too few retries**: a low `backoffLimit` on work that fails transiently.
- **Node disruption**: pods lost to eviction or node shutdown counted as failures.

## First checks

1. Read the failure reason (`BackoffLimitExceeded`, `DeadlineExceeded`, `PodFailurePolicy`):
   ```bash
   kubectl -n <namespace> get job <job> -o jsonpath='{range .status.conditions[*]}{.type}: {.reason} {.message}{"\n"}{end}'
   ```
2. List the Job's pods and how each one ended:
   ```bash
   kubectl -n <namespace> get pods -l job-name=<job> -o wide
   kubectl -n <namespace> get pods -l job-name=<job> \
     -o jsonpath='{range .items[*]}{.metadata.name}: {.status.containerStatuses[0].state.terminated.reason} exit={.status.containerStatuses[0].state.terminated.exitCode}{"\n"}{end}'
   ```
3. Read the logs of a failed attempt:
   ```bash
   kubectl -n <namespace> logs <pod> --tail=100
   ```
4. Check whether failures are recurring for this workload over time:
   ```promql
   sum by (namespace, job_name) (kube_job_status_failed)
   ```
5. For a CronJob, see if a newer run succeeded: `kubectl -n <namespace> get jobs --sort-by=.metadata.creationTimestamp`.

## Fixing it

Fix the root cause (memory limit, dependency, input data, deadline), then rerun. For a CronJob, trigger a manual run with `kubectl -n <namespace> create job <job>-rerun --from=cronjob/<cronjob>`. Once handled, delete the failed Job to clear the alert, and set `ttlSecondsAfterFinished` or a low `failedJobsHistoryLimit` so old failures clean themselves up.

## Related alerts

- [KubeJobNotCompleted](/runbooks/kubejobnotcompleted/): the Job has not failed but is running far too long.
- [KubeCronJobMissedSchedule](/runbooks/kubecronjobmissedschedule/): the next run did not start at all.
- [KubeContainerOOMKilled](/runbooks/kubecontaineroomkilled/): a common reason Job pods fail.
