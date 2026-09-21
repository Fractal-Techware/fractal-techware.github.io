---
title: "KafkaConsumerGroupLagHigh: runbook and fix"
description: "KafkaConsumerGroupLagHigh means a consumer group is far behind the latest offsets of a topic. How to find the slow consumer and catch up safely."
permalink: /runbooks/kafkaconsumergrouplaghigh/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Apache Kafka (kafka_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "KafkaConsumerGroupLagHigh is one of 6 Kafka consumer and broker alerts in the pack of 179, each with unit tests and a runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kafkaconsumergrouplaghigh
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KafkaConsumerGroupLagHigh

A consumer group has had a large backlog of unread messages on a topic for a sustained period.

| | |
|---|---|
| Severity | warning |
| Source | danielqsj/kafka_exporter 1.7+ |
| Key metrics | `kafka_consumergroup_lag`, `kafka_consumergroup_current_offset`, `kafka_topic_partition_current_offset` |

## What it means

Lag is the difference between the newest offset in a partition and the offset the group has committed. The alert sums lag per group and topic and fires when it stays large for a while. Lag is measured in messages, so what counts as "large" depends heavily on the topic's throughput; the default threshold is a starting point, not a universal answer.

High lag means downstream data is stale: notifications arrive late, search indexes are behind, or order processing is delayed. If lag outlives topic retention, unread messages are deleted and lost to that consumer.

## Common causes

- **Consumers too slow** for current traffic: a slow database or API call per message.
- **Too few consumer instances**, or more partitions than consumers can handle.
- **Rebalance storms**: consumers exceeding `max.poll.interval.ms` get kicked out and the group keeps rebalancing.
- **Poison message**: one record that keeps failing blocks a partition.
- **Traffic burst** upstream, such as a backfill or batch job.

## First checks

1. See where the lag is, per partition:
   ```promql
   topk(10, sum by (consumergroup, topic, partition) (kafka_consumergroup_lag))
   ```
2. Check the group from Kafka's point of view. Look at `LAG` per partition and whether each has a `CONSUMER-ID`:
   ```bash
   kafka-consumer-groups.sh --bootstrap-server <broker>:9092 --describe --group <group>
   ```
3. Compare produce rate with consume rate:
   ```promql
   sum by (topic) (rate(kafka_topic_partition_current_offset{topic="<topic>"}[5m]))
   sum by (consumergroup, topic) (rate(kafka_consumergroup_current_offset{consumergroup="<group>"}[5m]))
   ```
4. Look at consumer logs for errors, retries and rebalances:
   ```bash
   kubectl -n <namespace> logs deploy/<consumer> --since=30m | grep -iE 'rebalanc|error|exception'
   ```

## Fixing it

If lag is concentrated on one partition, look for a stuck message or a hot key. If spread evenly, scale consumers up to the partition count, or speed up per-message processing. Fix rebalance loops by tuning `max.poll.records` or `max.poll.interval.ms`. Skipping messages with `--reset-offsets` is a business decision, not a default fix.

## Related alerts

- [KafkaConsumerGroupLagGrowing](/runbooks/kafkaconsumergrouplaggrowing/): shows whether the backlog is still getting worse.
- [KafkaConsumerGroupInactive](/runbooks/kafkaconsumergroupinactive/): lag with no consumers at all.
