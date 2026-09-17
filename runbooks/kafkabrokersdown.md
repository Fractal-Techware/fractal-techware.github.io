---
title: "KafkaBrokersDown: runbook and fix"
description: "KafkaBrokersDown means the Kafka cluster reports fewer brokers than expected. How to find the missing broker, check partition impact and bring it back."
permalink: /runbooks/kafkabrokersdown/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Apache Kafka (kafka_exporter)
severity: critical
cta:
  title: Get this alert, tested
  text: "KafkaBrokersDown is one of 6 Kafka alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=kafkabrokersdown
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# KafkaBrokersDown

The Kafka cluster metadata lists fewer live brokers than the cluster is supposed to have.

| | |
|---|---|
| Severity | critical |
| Source | danielqsj/kafka_exporter 1.7+ |
| Key metric | `kafka_brokers` (brokers currently registered in cluster metadata) |

## What it means

kafka_exporter asks the cluster for its metadata and reports how many brokers are registered. When that number drops below the expected cluster size for a few minutes, at least one broker has left the cluster: crashed, lost its ZooKeeper/KRaft session, or is stuck starting up.

With one broker missing, partitions whose leader lived there move to other replicas, and topics with a replication factor of 3 and `min.insync.replicas=2` keep working with no spare margin. Lose another broker and producers using `acks=all` start failing. Set the expected broker count in the rule to match your cluster.

## Common causes

- **Broker process crashed**: OOM kill, JVM heap exhaustion, or a fatal log directory error.
- **Disk full** on a log directory, which makes the broker shut down.
- **Node or pod lost**: node drain, eviction, or a StatefulSet pod stuck `Pending` on a volume.
- **Session timeout**: long GC pauses or network problems between the broker and the controller quorum.
- **Rolling restart or upgrade** taking longer than expected.

## First checks

1. Confirm the count and which exporter reports it:
   ```promql
   kafka_brokers
   ```
2. Find the missing broker. On Kubernetes:
   ```bash
   kubectl -n <kafka-namespace> get pods -o wide
   kubectl -n <kafka-namespace> describe pod <broker-pod>
   kubectl -n <kafka-namespace> logs <broker-pod> --previous | tail -100
   ```
3. List brokers the cluster can see:
   ```bash
   kafka-broker-api-versions.sh --bootstrap-server <broker>:9092 | grep -E '^[^ ].*id:'
   ```
4. Check how many partitions are now at risk:
   ```bash
   kafka-topics.sh --bootstrap-server <broker>:9092 --describe --under-replicated-partitions
   kafka-topics.sh --bootstrap-server <broker>:9092 --describe --unavailable-partitions
   ```
5. Check disk on the broker: `kubectl -n <kafka-namespace> exec <broker-pod> -- df -h`.

## Fixing it

Bring the broker back rather than replacing it: free or expand the disk, raise memory if it was OOM-killed, and fix the volume or scheduling problem. The broker rejoins with its existing data and catches up. Only reassign its partitions to other brokers if the machine and its data are truly gone. Pause planned maintenance until the count is back to normal.

## Related alerts

- [KafkaUnderReplicatedPartitions](/runbooks/kafkaunderreplicatedpartitions/): follows almost every broker loss.
- [KafkaTopicPartitionNoLeader](/runbooks/kafkatopicpartitionnoleader/): the outage case when no replica can take over.
