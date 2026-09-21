---
title: "PostgresqlExporterScrapeError: runbook and fix"
description: "PostgresqlExporterScrapeError means postgres_exporter keeps failing part of its scrape, leaving PostgreSQL metrics missing. Find the failing collector."
permalink: /runbooks/postgresqlexporterscrapeerror/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: PostgreSQL (postgres_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "PostgresqlExporterScrapeError is one of 10 PostgreSQL alerts in a 179-alert pack, every rule covered by promtool unit tests and a runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=postgresqlexporterscrapeerror
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# PostgresqlExporterScrapeError

postgres_exporter has been reporting an error on its scrapes for a while, so some PostgreSQL metrics (and the alerts built on them) are missing or stale.

| | |
|---|---|
| Severity | warning |
| Source | prometheus-community/postgres_exporter 0.15+ |
| Key metric | `pg_exporter_last_scrape_error` (1 = last scrape had an error) |

## What it means

The exporter runs a set of queries against PostgreSQL on each scrape. If any of them fails, it still returns what it could but sets the error flag. The alert fires when that flag stays set for a sustained period, which means a persistent problem rather than a one-off timeout.

The danger is silent gaps: other PostgreSQL alerts that depend on the failing collector simply have no data and cannot fire.

## Common causes

- The monitoring role lacks privileges (it should be a member of `pg_monitor`).
- A collector or custom query references a view or column that changed in a newer PostgreSQL major version.
- A collector needs an extension that is not installed, such as `pg_stat_statements`.
- Queries timing out on a busy server or a database with very many tables.
- Auto-discovered databases the role cannot connect to.

## First checks

1. Read the exporter log; it names the collector and the SQL error:
   ```bash
   kubectl -n <ns> logs deploy/<postgres-exporter> --since=30m | grep -i error
   ```
2. Look at the raw metrics output for the flag and missing series:
   ```bash
   curl -s http://<exporter>:9187/metrics | grep -E '^pg_(up|exporter_last_scrape_error)'
   ```
3. Check the role's privileges:
   ```sql
   SELECT r.rolname, m.rolname AS member_of
   FROM pg_auth_members am
   JOIN pg_roles r ON r.oid = am.member
   JOIN pg_roles m ON m.oid = am.roleid
   WHERE r.rolname = '<exporter_user>';
   ```
4. See which instances are affected and for how long:
   ```promql
   max_over_time(pg_exporter_last_scrape_error[1h])
   ```
5. Compare exporter and server versions: `SELECT version();` and the exporter's `--version`.

## Fixing it

Grant the role what it needs: `GRANT pg_monitor TO <exporter_user>;`. Fix or remove custom queries that no longer match the schema, create missing extensions, or disable a collector you do not need with its `--no-collector.<name>` flag. Upgrade the exporter after a PostgreSQL major upgrade.

## Related alerts

- [PostgresqlDown](/runbooks/postgresqldown/): the exporter cannot connect at all.
- [PostgresqlHighDeadTuples](/runbooks/postgresqlhighdeadtuples/): depends on a collector that commonly breaks on permissions.
- [PostgresqlRestarted](/runbooks/postgresqlrestarted/): errors starting right after an upgrade restart point to version drift.
