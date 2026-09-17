---
title: "KafkaTopicPartitionNoLeader: runbook and fix"
description: "KafkaTopicPartitionNoLeader means Kafka partitions have no leader and are offline for producers and consumers. How to find them and bring them back."
permalink: /runbooks/kafkatopicpartitionnoleader/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Apache Kafka (kafka_exporter)
severity: critical
cta:
  title: Get this alert, tested
  text: "KafkaTopicPartitionNoLeader is one of 6 Kafka alerts in the pack of 179, each tested with promtool and paired with a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kafkatopicpartitionnoleader
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KafkaTopicPartitionNoLeader

Some partitions currently have no leader, so they cannot be written to or read from.

| | |
|---|---|
| Severity | critical |
| Source | danielqsj/kafka_exporter 1.7+ |
| Key metric | `kafka_topic_partition_leader` (reports `-1` for a partition with no leader) |

## What it means

Every partition needs one leader broker to serve reads and writes. When the leader goes away, the controller elects a new one from the in-sync replicas. If no in-sync replica is alive, and unclean leader election is disabled (the default), the partition stays offline. The alert fires when a topic has had leaderless partitions for a few minutes.

This is an outage for that data: producers time out or get `NOT_LEADER_OR_FOLLOWER` / `LEADER_NOT_AVAILABLE`, and consumers stall on those partitions.

## Common causes

- **All replicas down**: a topic with replication factor 1, or several brokers lost at once.
- **ISR had shrunk to the broker that died**, so the remaining replicas are not eligible.
- **Controller problems**: the active controller is unhealthy or the KRaft/ZooKeeper quorum is degraded, so elections do not happen.
- **Log directory failure** on the only in-sync replica.

## First checks

1. Find the leaderless partitions:
   ```promql
   count by (topic) (kafka_topic_partition_leader == -1)
   ```
2. See their replica lists and which brokers they depend on:
   ```bash
   kafka-topics.sh --bootstrap-server <broker>:9092 --describe --unavailable-partitions
   ```
3. Check which brokers are alive and bring back the ones listed in `Replicas`:
   ```bash
   kubectl -n <kafka-namespace> get pods -o wide
   kafka-broker-api-versions.sh --bootstrap-server <broker>:9092 | grep -E '^[^ ].*id:'
   ```
4. For KRaft clusters, check the controller quorum:
   ```bash
   kafka-metadata-quorum.sh --bootstrap-server <broker>:9092 describe --status
   ```
5. Read the logs of the returning broker for log directory or recovery errors.

## Fixing it

Start the broker that holds the last in-sync replica; the partition comes back with no data loss. If that broker's data is permanently lost, you can accept data loss and elect a leader from an out-of-sync replica:
```bash
kafka-leader-election.sh --bootstrap-server <broker>:9092 --election-type unclean --topic <topic> --partition <n>
```
Treat that as a last resort and record which partitions lost messages. Afterwards, raise replication factor on any topic that had only one replica.

## Related alerts

- [KafkaBrokersDown](/runbooks/kafkabrokersdown/): usually fires first.
- [KafkaUnderReplicatedPartitions](/runbooks/kafkaunderreplicatedpartitions/): the warning stage before partitions go offline.
- [KafkaConsumerGroupLagGrowing](/runbooks/kafkaconsumergrouplaggrowing/): consumers stuck on offline partitions build lag.
