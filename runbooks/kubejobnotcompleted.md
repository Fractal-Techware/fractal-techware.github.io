---
title: "KubeJobNotCompleted: runbook and fix"
description: "KubeJobNotCompleted means a Kubernetes Job has had active pods for many hours without finishing. How to tell a hung Job from a slow one and fix it."
permalink: /runbooks/kubejobnotcompleted/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes Jobs & CronJobs
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeJobNotCompleted is part of a pack of 179 Prometheus alerts, all with promtool unit tests and full runbooks, including 3 for Jobs and CronJobs."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubejobnotcompleted
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeJobNotCompleted

A Job started a long time ago, still has active pods, and has not finished.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metrics | `kube_job_status_start_time`, `kube_job_status_active` |

## What it means

The alert fires when a Job that is still active has been running for many hours, far beyond what typical batch work takes. It does not know how long *your* Job should take, so first decide whether this one is legitimately long or stuck.

A Job that never ends holds its resources, may keep a lock or a database connection open, and, if it belongs to a CronJob with `concurrencyPolicy: Forbid`, blocks every later scheduled run.

## Common causes

- **Hung process**: waiting forever on a network call without a timeout, a deadlock, or a lock held elsewhere.
- **Pods stuck Pending**: no node fits the requests, or a volume cannot attach, so the Job counts as active but does nothing.
- **Retry loop inside the pod**: with `restartPolicy: OnFailure` the container restarts in place while the Job stays active.
- **No `activeDeadlineSeconds`**, so nothing ever stops a runaway run.
- **Wrong completions**: `completions` set higher than the work queue can ever satisfy.

## First checks

1. Check progress and age:
   ```bash
   kubectl -n <namespace> get job <job> -o wide
   kubectl -n <namespace> get pods -l job-name=<job> -o wide
   ```
2. Compare succeeded pods with the target, to see if it is moving at all:
   ```promql
   kube_job_status_succeeded{job_name="<job>"}
   ```
   ```promql
   kube_job_spec_completions{job_name="<job>"}
   ```
3. Is the pod doing work? Near-zero CPU for hours suggests it is hung:
   ```promql
   sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="<namespace>", pod=~"<job>-.*", container!=""}[5m]))
   ```
4. Read recent logs and restart counts:
   ```bash
   kubectl -n <namespace> logs <pod> --tail=50 --timestamps
   kubectl -n <namespace> get pod <pod> -o jsonpath='{.status.containerStatuses[0].restartCount}{"\n"}'
   ```
5. For Pending pods, `kubectl -n <namespace> describe pod <pod>` shows the scheduling or mount error.

## Fixing it

If it is making progress and the duration is expected, let it finish and consider making it faster or splitting the work. If it is hung, capture a thread dump or logs, then stop it with `kubectl -n <namespace> delete job <job>` and rerun. Prevent repeats: set `activeDeadlineSeconds`, add timeouts to external calls, and make the work resumable.

## Related alerts

- [KubeJobFailed](/runbooks/kubejobfailed/): the Job ended in failure instead of hanging.
- [KubeCronJobMissedSchedule](/runbooks/kubecronjobmissedschedule/): a long-running Job often blocks the next CronJob run.
- [KubeContainerWaiting](/runbooks/kubecontainerwaiting/): Job pods that never actually start.
