---
title: "PostgresqlDown: runbook and fix"
description: "PostgresqlDown means postgres_exporter cannot connect to PostgreSQL. How to tell a dead database from an exporter or auth problem and recover."
permalink: /runbooks/postgresqldown/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: PostgreSQL (postgres_exporter)
severity: critical
cta:
  title: Get this alert, tested
  text: "PostgresqlDown is one of 10 PostgreSQL alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=postgresqldown
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PostgresqlDown

postgres_exporter has been unable to open a connection to PostgreSQL for a couple of minutes, so the database is either down or unreachable from the exporter.

| | |
|---|---|
| Severity | critical |
| Source | prometheus-community/postgres_exporter 0.15+ |
| Key metric | `pg_up` (1 = last connection succeeded, 0 = failed) |

## What it means

`pg_up` is set by the exporter on every scrape: it tries to connect with its configured DSN and reports 0 if that fails. The alert fires once it has stayed at 0 for a short period, which rules out a single blip during a restart.

Note what this does and does not prove. The exporter itself is up (otherwise you would only see `up == 0` for the job), but the database may be fine and only the exporter's path to it broken. Treat it as an outage until you have confirmed otherwise: applications using the same host and credentials are probably failing too.

## Common causes

- The postmaster crashed or was stopped (OOM kill, failed upgrade, manual stop).
- The data or WAL volume filled up and PostgreSQL shut down with a PANIC.
- A failover moved the primary and the exporter still points at the old address.
- Credentials, `pg_hba.conf` or TLS settings changed and the exporter's login is rejected.
- `max_connections` is exhausted, so new logins (including the exporter's) get "too many clients already".

## First checks

1. Test the connection from the exporter's network location:
   ```bash
   pg_isready -h <host> -p 5432 -d postgres
   psql "host=<host> user=<exporter_user> dbname=postgres" -c 'select 1'
   ```
2. Read the exporter log; it prints the exact connection error:
   ```bash
   kubectl -n <ns> logs deploy/<postgres-exporter> --tail=50
   ```
3. Check the server process and its log:
   ```bash
   systemctl status postgresql
   journalctl -u postgresql --since "30 min ago" | tail -50
   # Kubernetes: kubectl -n <ns> logs <postgres-pod> --previous
   ```
4. Look for disk exhaustion and OOM kills on the host:
   ```bash
   df -h /var/lib/postgresql
   dmesg -T | grep -i -E 'killed process|out of memory'
   ```
5. See how widespread it is:
   ```promql
   count by (job) (pg_up == 0)
   ```

## Fixing it

If PostgreSQL is stopped, free disk space first (never delete files in `pg_wal` by hand; remove old logs or grow the volume), then start the service and watch the log for crash recovery to finish. If the database is healthy, fix the exporter side: update its DSN after a failover, restore the monitoring role's password or `pg_hba.conf` entry, or reserve connections for monitoring.

## Related alerts

- [PostgresqlRestarted](/runbooks/postgresqlrestarted/): confirms the postmaster came back after the outage.
- [PostgresqlTooManyConnections](/runbooks/postgresqltoomanyconnections/): a full connection pool can lock the exporter out.
- [PostgresqlExporterScrapeError](/runbooks/postgresqlexporterscrapeerror/): the exporter connects but some queries fail.
