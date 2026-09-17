---
title: "KafkaConsumerGroupInactive: runbook and fix"
description: "KafkaConsumerGroupInactive means a Kafka consumer group has unread messages but no active members. How to find the dead consumer or retire the group."
permalink: /runbooks/kafkaconsumergroupinactive/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Apache Kafka (kafka_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "KafkaConsumerGroupInactive is one of 6 Kafka alerts in the pack of 179, each with a promtool unit test and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kafkaconsumergroupinactive
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KafkaConsumerGroupInactive

A consumer group still has committed offsets and a backlog, but nobody is consuming for it.

| | |
|---|---|
| Severity | warning |
| Source | danielqsj/kafka_exporter 1.7+ |
| Key metrics | `kafka_consumergroup_members`, `kafka_consumergroup_lag` |

## What it means

Kafka keeps a group's committed offsets after all its members leave (until `offsets.retention.minutes` passes). kafka_exporter reports the member count and the lag for that group. The alert fires when a group has had zero members and non-zero lag for a while: messages are arriving for a consumer that no longer exists or is not running.

Either an application is down and its work is piling up, or a group was retired and its offsets are just leftovers.

## Common causes

- **Consumer deployment scaled to zero** or stuck: `CrashLoopBackOff`, `ImagePullBackOff`, or failed scheduling.
- **Authentication or ACL failure**: the app runs but cannot join the group after a credential rotation.
- **Group id changed** in a new release, leaving the old group orphaned with lag.
- **Batch or cron consumers** that run only periodically.
- **Decommissioned service** whose group was never deleted.

## First checks

1. Confirm the group is empty:
   ```bash
   kafka-consumer-groups.sh --bootstrap-server <broker>:9092 --describe --group <group> --state
   kafka-consumer-groups.sh --bootstrap-server <broker>:9092 --describe --group <group>
   ```
   State `Empty` and no `CONSUMER-ID` confirm it.
2. Find the owning application and check it is running:
   ```bash
   kubectl get deploy,statefulset -A | grep -i <app>
   kubectl -n <namespace> get pods -l <consumer-selector>
   ```
3. Check its logs for join or auth errors:
   ```bash
   kubectl -n <namespace> logs deploy/<consumer> --since=1h | grep -iE 'authoriz|authenticat|group|coordinator'
   ```
4. Check whether a new group id replaced it:
   ```promql
   sum by (consumergroup) (kafka_consumergroup_members{consumergroup=~"<app-prefix>.*"})
   ```

## Fixing it

Restore the consumer if it should be running; it resumes from the committed offsets. If the group id changed intentionally, decide whether the new group needs the old offsets and reset it with `--reset-offsets` before starting. For retired groups, delete them so the alert clears:
```bash
kafka-consumer-groups.sh --bootstrap-server <broker>:9092 --delete --group <group>
```
For periodic batch consumers, exclude the group from this alert.

## Related alerts

- [KafkaConsumerGroupLagHigh](/runbooks/kafkaconsumergrouplaghigh/): backlog size for the same group.
- [KafkaConsumerGroupLagGrowing](/runbooks/kafkaconsumergrouplaggrowing/): lag rising while consumers exist but are too slow.
