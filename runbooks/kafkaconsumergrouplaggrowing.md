---
title: "KafkaConsumerGroupLagGrowing: runbook and fix"
description: "KafkaConsumerGroupLagGrowing means a consumer group falls further behind every minute. How to tell stuck consumers from underprovisioned ones and fix it."
permalink: /runbooks/kafkaconsumergrouplaggrowing/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Apache Kafka (kafka_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "KafkaConsumerGroupLagGrowing is part of the Kafka set in a pack of 179 Prometheus alerts, each with promtool unit tests and a runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kafkaconsumergrouplaggrowing
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KafkaConsumerGroupLagGrowing

A consumer group's backlog on a topic has been increasing steadily, so it is not keeping up with producers.

| | |
|---|---|
| Severity | warning |
| Source | danielqsj/kafka_exporter 1.7+ |
| Key metric | `kafka_consumergroup_lag` (labels `consumergroup`, `topic`, `partition`) |

## What it means

Where a high-lag alert looks at the size of the backlog, this one looks at its direction. It fires when lag for a group and topic has kept rising over a long window and is already non-trivial. A group that is behind but catching up does not trigger it; a group that is losing ground does.

This is the alert to act on early. Growing lag never fixes itself without a change in load or capacity, and eventually it runs into retention and messages expire unread.

## Common causes

- **Consumption stopped** on some partitions: a stuck thread, a poison message, or a consumer blocked on a dead dependency.
- **Produce rate increased** beyond what the current consumer count can process.
- **Consumers restarting** in a crash loop, so they barely process anything between restarts.
- **Continuous rebalancing**, where no member owns partitions long enough to work.
- **Offline partitions**, so the consumer cannot fetch at all.

## First checks

1. See which partitions are growing:
   ```promql
   topk(10, sum by (consumergroup, topic, partition) (delta(kafka_consumergroup_lag{consumergroup="<group>"}[15m])))
   ```
2. Check whether commits are moving at all. A flat line means consumption has stopped:
   ```promql
   sum by (partition) (rate(kafka_consumergroup_current_offset{consumergroup="<group>", topic="<topic>"}[5m]))
   ```
3. Inspect members and assignments:
   ```bash
   kafka-consumer-groups.sh --bootstrap-server <broker>:9092 --describe --group <group>
   kafka-consumer-groups.sh --bootstrap-server <broker>:9092 --describe --group <group> --members
   ```
4. Check the consumer pods for restarts and errors:
   ```bash
   kubectl -n <namespace> get pods -l <consumer-selector>
   kubectl -n <namespace> logs <consumer-pod> --since=30m | grep -iE 'error|exception|rebalanc'
   ```

## Fixing it

If offsets are frozen on a few partitions, find the blocking message or dependency and restart only after the cause is fixed, otherwise it will block again. If all partitions grow evenly, add consumers (up to the partition count) or add partitions and consumers together. Throttle or reschedule the upstream burst if it was a one-off backfill.

## Related alerts

- [KafkaConsumerGroupLagHigh](/runbooks/kafkaconsumergrouplaghigh/): the absolute size of the backlog.
- [KafkaConsumerGroupInactive](/runbooks/kafkaconsumergroupinactive/): the extreme case, with no members consuming.
- [KafkaTopicPartitionNoLeader](/runbooks/kafkatopicpartitionnoleader/): offline partitions stop consumption.
