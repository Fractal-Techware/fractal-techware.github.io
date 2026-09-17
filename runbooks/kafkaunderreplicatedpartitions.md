---
title: "KafkaUnderReplicatedPartitions: runbook and fix"
description: "KafkaUnderReplicatedPartitions means some topic partitions have fewer in-sync replicas than configured. Find the lagging broker and restore replication."
permalink: /runbooks/kafkaunderreplicatedpartitions/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Apache Kafka (kafka_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "KafkaUnderReplicatedPartitions is one of the 6 Kafka alerts in a pack of 179 Prometheus alerts, all unit tested and documented."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kafkaunderreplicatedpartitions
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KafkaUnderReplicatedPartitions

One or more partitions of a topic have replicas that are not keeping up with the leader.

| | |
|---|---|
| Severity | warning |
| Source | danielqsj/kafka_exporter 1.7+ |
| Key metrics | `kafka_topic_partition_under_replicated_partition`, `kafka_topic_partition_in_sync_replica`, `kafka_topic_partition_replicas` |

## What it means

A partition is under-replicated when its in-sync replica set (ISR) is smaller than its replica list. A follower drops out of the ISR when it has not caught up with the leader within `replica.lag.time.max.ms`. The alert fires when a topic has stayed under-replicated for several minutes, which rules out the short blips seen during a normal broker restart.

Data is still being served, but durability is reduced. If the ISR shrinks below `min.insync.replicas`, producers using `acks=all` get `NotEnoughReplicas` errors.

## Common causes

- **A broker is down** or restarting, so all its follower replicas are out of the ISR.
- **Slow or saturated disk** on one broker, so its followers cannot fetch fast enough.
- **Network problems** between brokers or throttled replication traffic.
- **Reassignment in progress**, where new replicas are still copying data.
- **Traffic spike** on a single large topic that followers cannot keep up with.

## First checks

1. See which topics and how many partitions are affected:
   ```promql
   sum by (topic) (kafka_topic_partition_under_replicated_partition) > 0
   ```
2. List the partitions and compare `Replicas` with `Isr`. The broker id missing from `Isr` again and again is the suspect:
   ```bash
   kafka-topics.sh --bootstrap-server <broker>:9092 --describe --under-replicated-partitions
   ```
3. Confirm all brokers are up:
   ```promql
   kafka_brokers
   ```
4. On the suspect broker, look at disk and replication errors:
   ```bash
   kubectl -n <kafka-namespace> exec <broker-pod> -- df -h
   kubectl -n <kafka-namespace> logs <broker-pod> --since=30m | grep -iE 'ReplicaFetcher|Shrinking ISR|error'
   ```
5. Check for a running reassignment:
   ```bash
   kafka-reassign-partitions.sh --bootstrap-server <broker>:9092 --list
   ```

## Fixing it

Restore the missing or slow broker first; followers rejoin the ISR on their own once they catch up. Fix disk saturation or move heavy partitions to less loaded brokers. If a reassignment is throttled too tightly, raise the replication throttle so it finishes. Avoid restarting more brokers until the count returns to zero.

## Related alerts

- [KafkaBrokersDown](/runbooks/kafkabrokersdown/): the most common root cause.
- [KafkaTopicPartitionNoLeader](/runbooks/kafkatopicpartitionnoleader/): what happens if the ISR shrinks to nothing.
