---
title: Prometheus alert runbooks
description: Runbooks for common Prometheus alerts on Kubernetes, Linux hosts, Prometheus, databases and ingress. What the alert means, likely causes and first checks.
---
# Prometheus alert runbooks

<!-- RUNBOOK_INDEX:START -->
Mid-incident and staring at an unfamiliar alert name? Each page below explains what a common Prometheus alert means in plain words, what usually causes it, and the first commands to run (kubectl, PromQL, shell) to find out what is actually wrong.

The alerts come from the [Prometheus Alert Rules & Runbook Pack](https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=index): 179 alerts across 20 domains, every one covered by promtool unit tests. 12 of them, with their rules, tests and full runbooks, are free under MIT in [prometheus-alert-rules on GitHub](https://github.com/Fractal-Techware/prometheus-alert-rules); those pages are marked *free rule*.

## Kubernetes workloads

- [KubePodCrashLooping](/runbooks/kubepodcrashlooping/): Pod container is crash looping. (warning, *free rule*)
- [KubePodNotReady](/runbooks/kubepodnotready/): Pod has been in a non-ready state. (warning, *free rule*)
- [KubeContainerOOMKilled](/runbooks/kubecontaineroomkilled/): Container was OOM killed. (warning, *free rule*)
- [KubeImagePullBackOff](/runbooks/kubeimagepullbackoff/): Container image cannot be pulled. (warning, *free rule*)
- [KubeContainerWaiting](/runbooks/kubecontainerwaiting/): Container has been waiting to start for a long time. (warning)
- [KubeDeploymentReplicasMismatch](/runbooks/kubedeploymentreplicasmismatch/): Deployment has fewer available replicas than desired. (warning, *free rule*)
- [KubeDeploymentRolloutStuck](/runbooks/kubedeploymentrolloutstuck/): Deployment rollout is not progressing. (warning, *free rule*)
- [KubeDeploymentGenerationMismatch](/runbooks/kubedeploymentgenerationmismatch/): Deployment generation mismatch. (warning)
- [KubeStatefulSetReplicasMismatch](/runbooks/kubestatefulsetreplicasmismatch/): StatefulSet has not matched the expected number of ready replicas. (warning)
- [KubeStatefulSetGenerationMismatch](/runbooks/kubestatefulsetgenerationmismatch/): StatefulSet generation mismatch. (warning)
- [KubeDaemonSetRolloutStuck](/runbooks/kubedaemonsetrolloutstuck/): DaemonSet rollout is stuck. (warning)
- [KubeDaemonSetNotScheduled](/runbooks/kubedaemonsetnotscheduled/): DaemonSet pods are not scheduled. (warning)
- [KubeDaemonSetMisScheduled](/runbooks/kubedaemonsetmisscheduled/): DaemonSet pods are running where they are not supposed to run. (warning)

## Kubernetes nodes & capacity

- [KubeNodeNotReady](/runbooks/kubenodenotready/): Node is not ready. (warning, *free rule*)
- [KubeNodeUnreachable](/runbooks/kubenodeunreachable/): Node is unreachable. (warning)
- [KubeNodePressure](/runbooks/kubenodepressure/): Node has an active pressure condition. (warning)
- [KubeNodeReadinessFlapping](/runbooks/kubenodereadinessflapping/): Node readiness is flapping. (warning)
- [KubeletTooManyPods](/runbooks/kubelettoomanypods/): Node is running at its pod capacity. (warning)
- [KubeNodeCordoned](/runbooks/kubenodecordoned/): Node has been cordoned for a long time. (info)
- [KubeClusterCPURequestsHigh](/runbooks/kubeclustercpurequestshigh/): Cluster CPU requests are close to allocatable capacity. (warning)
- [KubeClusterMemoryRequestsHigh](/runbooks/kubeclustermemoryrequestshigh/): Cluster memory requests are close to allocatable capacity. (warning)

## Hosts (node_exporter)

- [NodeExporterDown](/runbooks/nodeexporterdown/): Host or node_exporter is down. (critical, *free rule*)
- [NodeFilesystemSpaceFillingUp](/runbooks/nodefilesystemspacefillingup/): Filesystem is predicted to run out of space within 24 hours. (warning / critical, *free rule*)
- [NodeFilesystemAlmostOutOfSpace](/runbooks/nodefilesystemalmostoutofspace/): Filesystem has less than 10% space left. (warning / critical, *free rule*)
- [NodeFilesystemAlmostOutOfFiles](/runbooks/nodefilesystemalmostoutoffiles/): Filesystem has less than 10% inodes left. (warning / critical)
- [NodeFilesystemDeviceError](/runbooks/nodefilesystemdeviceerror/): Filesystem cannot be read by node_exporter. (warning)
- [NodeHighCPUUsage](/runbooks/nodehighcpuusage/): Host CPU usage is above 90%. (warning, *free rule*)
- [NodeCPUHighIOWait](/runbooks/nodecpuhighiowait/): Host CPUs are spending a lot of time waiting for I/O. (warning)
- [NodeLoadHigh](/runbooks/nodeloadhigh/): Host load average is high relative to its CPU count. (warning)
- [NodeMemoryHighUtilization](/runbooks/nodememoryhighutilization/): Host memory utilisation is above 90%. (warning, *free rule*)
- [NodeMemoryMajorPagesFaults](/runbooks/nodememorymajorpagesfaults/): Host is under memory pressure (major page faults). (warning)
- [NodeOOMKillDetected](/runbooks/nodeoomkilldetected/): The kernel OOM killer terminated a process. (warning)
- [NodeDiskIOSaturation](/runbooks/nodediskiosaturation/): Disk I/O queue is saturated. (warning)
- [NodeNetworkReceiveErrs](/runbooks/nodenetworkreceiveerrs/): Network interface is reporting receive errors. (warning)
- [NodeNetworkTransmitErrs](/runbooks/nodenetworktransmiterrs/): Network interface is reporting transmit errors. (warning)
- [NodeNetworkInterfaceFlapping](/runbooks/nodenetworkinterfaceflapping/): Network interface is flapping. (warning)
- [NodeClockNotSynchronising](/runbooks/nodeclocknotsynchronising/): Host clock is not synchronising. (warning)
- [NodeClockSkewDetected](/runbooks/nodeclockskewdetected/): Host clock is skewed. (warning)
- [NodeSystemdServiceFailed](/runbooks/nodesystemdservicefailed/): A systemd service has failed. (warning)
- [NodeRAIDDegraded](/runbooks/noderaiddegraded/): Software RAID array is degraded. (critical)
- [NodeRAIDDiskFailure](/runbooks/noderaiddiskfailure/): Disk in a software RAID array has failed. (warning)
- [NodeTextFileCollectorError](/runbooks/nodetextfilecollectorerror/): node_exporter textfile collector failed. (warning)
- [NodeRebootDetected](/runbooks/noderebootdetected/): Host rebooted. (info)
- [NodeFileDescriptorLimit](/runbooks/nodefiledescriptorlimit/): Host is running out of file descriptors. (warning)
- [NodeConntrackLimit](/runbooks/nodeconntracklimit/): Conntrack table is almost full. (warning)
- [NodeTemperatureCritical](/runbooks/nodetemperaturecritical/): Hardware sensor reports a critical temperature. (warning)

## Kubernetes persistent volumes

- [KubePersistentVolumeFillingUp](/runbooks/kubepersistentvolumefillingup/): PersistentVolume is almost full. (warning / critical)
- [KubePersistentVolumeInodesFillingUp](/runbooks/kubepersistentvolumeinodesfillingup/): PersistentVolume is running out of inodes. (critical)
- [KubePersistentVolumeErrors](/runbooks/kubepersistentvolumeerrors/): PersistentVolume is in a failed or pending state. (critical)
- [KubePersistentVolumeClaimPending](/runbooks/kubepersistentvolumeclaimpending/): PersistentVolumeClaim is not bound. (warning)
- [KubePersistentVolumeClaimLost](/runbooks/kubepersistentvolumeclaimlost/): PersistentVolumeClaim lost its volume. (critical)

## Kubernetes Jobs & CronJobs

- [KubeJobFailed](/runbooks/kubejobfailed/): Job failed to complete. (warning)
- [KubeJobNotCompleted](/runbooks/kubejobnotcompleted/): Job is taking too long to complete. (warning)
- [KubeCronJobMissedSchedule](/runbooks/kubecronjobmissedschedule/): CronJob did not run on schedule. (warning)

## Kubernetes autoscaling (HPA)

- [KubeHpaReplicasMismatch](/runbooks/kubehpareplicasmismatch/): HPA has not reached its desired number of replicas. (warning)
- [KubeHpaMaxedOut](/runbooks/kubehpamaxedout/): HPA is running at maximum replicas. (warning)
- [KubeHpaUnableToScale](/runbooks/kubehpaunabletoscale/): HPA is unable to scale its target. (warning)
- [KubeHpaMetricsUnavailable](/runbooks/kubehpametricsunavailable/): HPA cannot read the metrics it scales on. (warning)

## Kubernetes quotas, limits & disruption budgets

- [KubeQuotaAlmostFull](/runbooks/kubequotaalmostfull/): Namespace quota is almost full. (info)
- [KubeQuotaFullyUsed](/runbooks/kubequotafullyused/): Namespace quota is fully used. (info)
- [KubeQuotaExceeded](/runbooks/kubequotaexceeded/): Namespace quota is exceeded. (warning)
- [CPUThrottlingHigh](/runbooks/cputhrottlinghigh/): Container is heavily CPU throttled. (info)
- [KubeContainerMemoryNearLimit](/runbooks/kubecontainermemorynearlimit/): Container memory usage is close to its limit. (warning)
- [KubePodDisruptionBudgetViolated](/runbooks/kubepoddisruptionbudgetviolated/): PodDisruptionBudget is violated. (warning)
- [KubePodDisruptionBudgetBlocksEviction](/runbooks/kubepoddisruptionbudgetblockseviction/): PodDisruptionBudget allows no disruptions. (info)

## Kubernetes control plane & kubelet

- [KubeAPIDown](/runbooks/kubeapidown/): Kubernetes API server is unreachable. (critical)
- [KubeAPIErrorsHigh](/runbooks/kubeapierrorshigh/): Kubernetes API server is returning many 5xx errors. (warning / critical)
- [KubeAPILatencyHigh](/runbooks/kubeapilatencyhigh/): Kubernetes API server is slow. (warning)
- [KubeAPITerminatedRequests](/runbooks/kubeapiterminatedrequests/): Kubernetes API server is terminating requests. (warning)
- [KubeletDown](/runbooks/kubeletdown/): No kubelet can be scraped. (critical)
- [KubeSchedulerDown](/runbooks/kubeschedulerdown/): kube-scheduler has disappeared. (critical)
- [KubeControllerManagerDown](/runbooks/kubecontrollermanagerdown/): kube-controller-manager has disappeared. (critical)
- [KubeVersionMismatch](/runbooks/kubeversionmismatch/): Different Kubernetes versions are running. (warning)
- [KubeAggregatedAPIDown](/runbooks/kubeaggregatedapidown/): An aggregated API is down. (warning)
- [KubeClientErrors](/runbooks/kubeclienterrors/): Kubernetes API client is experiencing errors. (warning)
- [KubeletPlegDurationHigh](/runbooks/kubeletplegdurationhigh/): Kubelet pod lifecycle event generator is slow. (warning)
- [KubeletPodStartUpLatencyHigh](/runbooks/kubeletpodstartuplatencyhigh/): Kubelet pod startup latency is high. (warning)

## Kubernetes certificates (kubelet & cert-manager)

- [KubeletClientCertificateExpiration](/runbooks/kubeletclientcertificateexpiration/): Kubelet client certificate is about to expire. (warning / critical)
- [KubeletServerCertificateExpiration](/runbooks/kubeletservercertificateexpiration/): Kubelet serving certificate is about to expire. (warning / critical)
- [KubeletClientCertificateRenewalErrors](/runbooks/kubeletclientcertificaterenewalerrors/): Kubelet fails to renew its client certificate. (warning)
- [KubeletServerCertificateRenewalErrors](/runbooks/kubeletservercertificaterenewalerrors/): Kubelet fails to renew its serving certificate. (warning)
- [CertManagerCertificateExpiringSoon](/runbooks/certmanagercertificateexpiringsoon/): cert-manager certificate expires soon and has not been renewed. (warning / critical)
- [CertManagerCertificateNotReady](/runbooks/certmanagercertificatenotready/): cert-manager certificate is not ready. (warning)

## Prometheus self-monitoring

- [Watchdog](/runbooks/watchdog/): Alerting pipeline heartbeat (always firing). (info)
- [TargetDown](/runbooks/targetdown/): Some scrape targets are down. (warning)
- [PrometheusConfigReloadFailed](/runbooks/prometheusconfigreloadfailed/): Prometheus configuration reload failed. (warning)
- [PrometheusNotConnectedToAlertmanagers](/runbooks/prometheusnotconnectedtoalertmanagers/): Prometheus is not connected to any Alertmanager. (warning)
- [PrometheusErrorSendingAlertsToAlertmanager](/runbooks/prometheuserrorsendingalertstoalertmanager/): Prometheus has errors sending alerts to an Alertmanager. (warning)
- [PrometheusNotificationQueueRunningFull](/runbooks/prometheusnotificationqueuerunningfull/): Prometheus alert notification queue predicted to run full. (warning)
- [PrometheusTSDBReloadsFailing](/runbooks/prometheustsdbreloadsfailing/): Prometheus has issues reloading blocks from disk. (warning)
- [PrometheusTSDBCompactionsFailing](/runbooks/prometheustsdbcompactionsfailing/): Prometheus has issues compacting blocks. (warning)
- [PrometheusNotIngestingSamples](/runbooks/prometheusnotingestingsamples/): Prometheus is not ingesting samples. (warning)
- [PrometheusDuplicateTimestamps](/runbooks/prometheusduplicatetimestamps/): Prometheus is dropping samples with duplicate timestamps. (warning)
- [PrometheusOutOfOrderTimestamps](/runbooks/prometheusoutofordertimestamps/): Prometheus drops samples with out-of-order timestamps. (warning)
- [PrometheusRemoteStorageFailures](/runbooks/prometheusremotestoragefailures/): Prometheus fails to send samples to remote storage. (critical)
- [PrometheusRemoteWriteBehind](/runbooks/prometheusremotewritebehind/): Prometheus remote write is falling behind. (critical)
- [PrometheusRuleFailures](/runbooks/prometheusrulefailures/): Prometheus is failing rule evaluations. (critical)
- [PrometheusMissingRuleEvaluations](/runbooks/prometheusmissingruleevaluations/): Prometheus is missing rule evaluations due to slow rule group evaluation. (warning)
- [PrometheusTargetLimitHit](/runbooks/prometheustargetlimithit/): Prometheus has dropped targets because some scrape configs exceeded the targets limit. (warning)
- [PrometheusLabelLimitHit](/runbooks/prometheuslabellimithit/): Prometheus has dropped targets because some scrape configs exceeded the label limits. (warning)
- [PrometheusScrapeSampleLimitHit](/runbooks/prometheusscrapesamplelimithit/): Prometheus rejects scrapes that exceed the sample limit. (warning)
- [PrometheusSDRefreshFailure](/runbooks/prometheussdrefreshfailure/): Prometheus service discovery is failing. (warning)
- [PrometheusHighQueryLoad](/runbooks/prometheushighqueryload/): Prometheus is reaching its maximum query capacity. (warning)

## Alertmanager self-monitoring

- [AlertmanagerFailedReload](/runbooks/alertmanagerfailedreload/): Reloading an Alertmanager configuration has failed. (critical)
- [AlertmanagerMembersInconsistent](/runbooks/alertmanagermembersinconsistent/): A member of an Alertmanager cluster has not found all other cluster members. (critical)
- [AlertmanagerFailedToSendAlerts](/runbooks/alertmanagerfailedtosendalerts/): An Alertmanager instance failed to send notifications. (warning)
- [AlertmanagerConfigInconsistent](/runbooks/alertmanagerconfiginconsistent/): Alertmanager instances within the same cluster have different configurations. (critical)
- [AlertmanagerClusterDown](/runbooks/alertmanagerclusterdown/): Half or more of the Alertmanager instances within the same cluster are down. (critical)
- [AlertmanagerClusterCrashlooping](/runbooks/alertmanagerclustercrashlooping/): Half or more of the Alertmanager instances within the same cluster are crashlooping. (critical)

## Endpoint probes (blackbox_exporter)

- [BlackboxProbeFailed](/runbooks/blackboxprobefailed/): Endpoint probe is failing. (critical)
- [BlackboxProbeFlapping](/runbooks/blackboxprobeflapping/): Endpoint probe is flapping. (warning)
- [BlackboxSlowProbe](/runbooks/blackboxslowprobe/): Endpoint probe is slow. (warning)
- [BlackboxSslCertificateWillExpireSoon](/runbooks/blackboxsslcertificatewillexpiresoon/): TLS certificate of a probed endpoint expires soon. (warning / critical)
- [BlackboxDnsLookupSlow](/runbooks/blackboxdnslookupslow/): DNS resolution for a probed endpoint is slow. (warning)
- [BlackboxExporterProbeScrapeFailed](/runbooks/blackboxexporterprobescrapefailed/): Prometheus cannot reach blackbox_exporter for a probe. (warning)

## PostgreSQL (postgres_exporter)

- [PostgresqlDown](/runbooks/postgresqldown/): PostgreSQL is down. (critical)
- [PostgresqlTooManyConnections](/runbooks/postgresqltoomanyconnections/): PostgreSQL is close to its connection limit. (warning)
- [PostgresqlReplicationLagHigh](/runbooks/postgresqlreplicationlaghigh/): PostgreSQL replica is lagging. (warning)
- [PostgresqlDeadlocks](/runbooks/postgresqldeadlocks/): PostgreSQL is detecting deadlocks. (warning)
- [PostgresqlHighRollbackRate](/runbooks/postgresqlhighrollbackrate/): PostgreSQL has a high transaction rollback rate. (warning)
- [PostgresqlLongRunningTransaction](/runbooks/postgresqllongrunningtransaction/): PostgreSQL has a long-running transaction. (warning)
- [PostgresqlHighDeadTuples](/runbooks/postgresqlhighdeadtuples/): PostgreSQL table has many dead tuples. (warning)
- [PostgresqlCacheHitRatioLow](/runbooks/postgresqlcachehitratiolow/): PostgreSQL buffer cache hit ratio is low. (info)
- [PostgresqlExporterScrapeError](/runbooks/postgresqlexporterscrapeerror/): postgres_exporter reports scrape errors. (warning)
- [PostgresqlRestarted](/runbooks/postgresqlrestarted/): PostgreSQL restarted. (info)

## Redis (redis_exporter)

- [RedisDown](/runbooks/redisdown/): Redis is down. (critical)
- [RedisMissingMaster](/runbooks/redismissingmaster/): Redis has no master. (critical)
- [RedisReplicaLinkDown](/runbooks/redisreplicalinkdown/): Redis replica lost its link to the master. (critical)
- [RedisReplicasDisconnected](/runbooks/redisreplicasdisconnected/): Redis master lost replicas. (warning)
- [RedisMemoryHigh](/runbooks/redismemoryhigh/): Redis is close to its maxmemory limit. (warning)
- [RedisTooManyConnections](/runbooks/redistoomanyconnections/): Redis is close to its client connection limit. (warning)
- [RedisRejectedConnections](/runbooks/redisrejectedconnections/): Redis is rejecting connections. (warning)
- [RedisRdbLastSaveFailed](/runbooks/redisrdblastsavefailed/): Redis RDB snapshot failed. (warning)
- [RedisKeyEvictions](/runbooks/rediskeyevictions/): Redis is evicting keys. (info)

## NGINX Ingress Controller

- [NginxIngressHighHttp5xxErrorRate](/runbooks/nginxingresshighhttp5xxerrorrate/): Ingress is returning many 5xx responses. (warning / critical)
- [NginxIngressHighHttp4xxErrorRate](/runbooks/nginxingresshighhttp4xxerrorrate/): Ingress is returning many 4xx responses. (info)
- [NginxIngressHighLatency](/runbooks/nginxingresshighlatency/): Ingress p95 latency is high. (warning)
- [NginxIngressConfigReloadFailed](/runbooks/nginxingressconfigreloadfailed/): NGINX Ingress configuration reload failed. (warning)
- [NginxIngressCertificateExpiring](/runbooks/nginxingresscertificateexpiring/): Certificate served by the ingress controller expires soon. (warning / critical)

## Apache Kafka (kafka_exporter)

- [KafkaBrokersDown](/runbooks/kafkabrokersdown/): Kafka cluster has fewer brokers than expected. (critical)
- [KafkaUnderReplicatedPartitions](/runbooks/kafkaunderreplicatedpartitions/): Kafka topic has under-replicated partitions. (warning)
- [KafkaTopicPartitionNoLeader](/runbooks/kafkatopicpartitionnoleader/): Kafka partitions have no leader. (critical)
- [KafkaConsumerGroupLagHigh](/runbooks/kafkaconsumergrouplaghigh/): Kafka consumer group lag is high. (warning)
- [KafkaConsumerGroupLagGrowing](/runbooks/kafkaconsumergrouplaggrowing/): Kafka consumer group lag keeps growing. (warning)
- [KafkaConsumerGroupInactive](/runbooks/kafkaconsumergroupinactive/): Kafka consumer group has lag but no members. (warning)

## Grafana Loki

- [LokiRequestErrors](/runbooks/lokirequesterrors/): Loki is returning many 5xx errors. (critical)
- [LokiRequestPanics](/runbooks/lokirequestpanics/): Loki is panicking. (critical)
- [LokiRequestLatency](/runbooks/lokirequestlatency/): Loki requests are slow. (warning)
- [LokiDiscardedSamples](/runbooks/lokidiscardedsamples/): Loki is discarding log lines. (warning)
- [LokiCompactorHasNotSuccessfullyRunCompaction](/runbooks/lokicompactorhasnotsuccessfullyruncompaction/): Loki compaction has not run recently. (warning)

## CoreDNS

- [CoreDNSDown](/runbooks/corednsdown/): CoreDNS has disappeared from Prometheus target discovery. (critical)
- [CoreDNSLatencyHigh](/runbooks/corednslatencyhigh/): CoreDNS is responding slowly. (warning)
- [CoreDNSErrorsHigh](/runbooks/corednserrorshigh/): CoreDNS is returning SERVFAIL for many requests. (warning / critical)
- [CoreDNSForwardLatencyHigh](/runbooks/corednsforwardlatencyhigh/): CoreDNS upstream forwarding is slow. (warning)
- [CoreDNSForwardHealthcheckFailures](/runbooks/corednsforwardhealthcheckfailures/): CoreDNS health checks to an upstream resolver are failing. (warning)
- [CoreDNSPanics](/runbooks/corednspanics/): CoreDNS is panicking. (critical)

## etcd

- [EtcdInsufficientMembers](/runbooks/etcdinsufficientmembers/): etcd cluster has insufficient members for quorum. (critical)
- [EtcdMembersDown](/runbooks/etcdmembersdown/): etcd cluster members are down. (warning)
- [EtcdNoLeader](/runbooks/etcdnoleader/): etcd member has no leader. (critical)
- [EtcdHighNumberOfLeaderChanges](/runbooks/etcdhighnumberofleaderchanges/): etcd leader changes too often. (warning)
- [EtcdHighFsyncDurations](/runbooks/etcdhighfsyncdurations/): etcd WAL fsync is slow. (warning)
- [EtcdHighCommitDurations](/runbooks/etcdhighcommitdurations/): etcd backend commits are slow. (warning)
- [EtcdDatabaseQuotaLowSpace](/runbooks/etcddatabasequotalowspace/): etcd database is close to its size quota. (warning / critical)
- [EtcdHighNumberOfFailedGRPCRequests](/runbooks/etcdhighnumberoffailedgrpcrequests/): etcd is failing many gRPC requests. (warning)

## HTTP availability SLO (multi-window, multi-burn-rate)

- [ErrorBudgetBurn](/runbooks/errorbudgetburn/): Service is burning its error budget very fast. (warning / critical)
<!-- RUNBOOK_INDEX:END -->
