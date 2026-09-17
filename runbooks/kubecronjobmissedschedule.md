---
title: "KubeCronJobMissedSchedule: runbook and fix"
description: "KubeCronJobMissedSchedule means a CronJob that is not suspended has not started a run long after it was due. How to find what blocks it and catch up."
permalink: /runbooks/kubecronjobmissedschedule/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Kubernetes Jobs & CronJobs
severity: warning
cta:
  title: Get this alert, tested
  text: "KubeCronJobMissedSchedule is one of 3 Job and CronJob alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kubecronjobmissedschedule
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KubeCronJobMissedSchedule

A CronJob's scheduled run time passed a long time ago without a new Job being started, and the CronJob is not suspended.

| | |
|---|---|
| Severity | warning |
| Source | kube-state-metrics v2.x |
| Key metrics | `kube_cronjob_next_schedule_time`, `kube_cronjob_spec_suspend` |

## What it means

kube-state-metrics computes when each CronJob should next run. If that time is far in the past, the CronJob controller did not create the Job. Suspended CronJobs are excluded, so this is an unintended skip.

Scheduled work (backups, cleanups, billing exports, certificate rotations) is silently not happening. These gaps are easy to miss for days.

## Common causes

- **`concurrencyPolicy: Forbid`** with the previous run still active or hung, so each new run is skipped.
- **Too many missed start times**: after a long outage the controller refuses to schedule and logs a "too many missed start times" error; this happens when there is no `startingDeadlineSeconds`.
- **`startingDeadlineSeconds` too short**: a brief controller delay pushes the run past its deadline, so it is skipped.
- **kube-controller-manager down** or unhealthy, so no CronJob runs anywhere.
- **Job creation rejected** by a ResourceQuota or admission webhook.

## First checks

1. See the last run and active Jobs:
   ```bash
   kubectl -n <namespace> get cronjob <cronjob>
   kubectl -n <namespace> describe cronjob <cronjob> | sed -n '/Events:/,$p'
   ```
2. How long since it last actually ran:
   ```promql
   time() - kube_cronjob_status_last_schedule_time{cronjob="<cronjob>"}
   ```
3. Find Jobs it owns, including any still running:
   ```bash
   kubectl -n <namespace> get jobs -o json \
     | jq -r '.items[] | select(.metadata.ownerReferences[0].name=="<cronjob>") | "\(.metadata.name) active=\(.status.active // 0) start=\(.status.startTime)"'
   ```
4. Check the schedule, time zone and policies:
   ```bash
   kubectl -n <namespace> get cronjob <cronjob> \
     -o jsonpath='{.spec.schedule} tz={.spec.timeZone} policy={.spec.concurrencyPolicy} deadline={.spec.startingDeadlineSeconds}{"\n"}'
   ```
5. If several CronJobs are late at once, check kube-controller-manager health and logs for `cronjob` errors.

## Fixing it

If a previous run is hung, investigate and delete it so scheduling resumes. Run the missed work by hand: `kubectl -n <namespace> create job <cronjob>-manual --from=cronjob/<cronjob>`. Set `startingDeadlineSeconds` to a sensible window (for example a few minutes to an hour) so the controller recovers after outages instead of giving up. If the job is intentionally paused, suspend it properly so the alert stays quiet:

```bash
kubectl -n <namespace> patch cronjob <cronjob> -p '{"spec":{"suspend":true}}'
```

## Related alerts

- [KubeJobNotCompleted](/runbooks/kubejobnotcompleted/): a long-running run that blocks the next one.
- [KubeJobFailed](/runbooks/kubejobfailed/): runs start but fail.
- [KubeControllerManagerDown](/runbooks/kubecontrollermanagerdown/): no controller, no scheduled Jobs.
