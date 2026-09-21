---
title: "AlertmanagerFailedReload: runbook and fix"
description: "AlertmanagerFailedReload means Alertmanager rejected its new config and is still routing with the old one. How to find the error and fix it."
permalink: /runbooks/alertmanagerfailedreload/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Alertmanager self-monitoring
severity: critical
cta:
  title: Get this alert, tested
  text: "AlertmanagerFailedReload is one of 6 Alertmanager self-monitoring alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://store.fractaltechware.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=alertmanagerfailedreload
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# AlertmanagerFailedReload

Alertmanager tried to load a new configuration file, rejected it, and is still running the previous one.

| | |
|---|---|
| Severity | critical |
| Source | Alertmanager's own `/metrics` (0.25+) |
| Key metric | `alertmanager_config_last_reload_successful` (1 = last reload worked, 0 = failed) |

## What it means

Whenever the config file changes and a reload is triggered (SIGHUP, `POST /-/reload`, or a config-reloader sidecar), Alertmanager parses and validates it. If validation fails, the gauge drops to 0 and the old config stays active. The alert fires when that state persists rather than clearing on the next successful reload.

Nothing is broken yet, which is exactly the danger: the routes, receivers or inhibition rules you just shipped are not live, and the next restart of the pod may fail to start at all because the bad file is still on disk.

## Common causes

- YAML indentation or type errors (a string where a list is expected, tabs instead of spaces).
- A receiver referenced in `route` that does not exist, or a duplicate receiver name.
- Template files listed under `templates:` that are missing or fail to parse.
- Secret files (`*_file` fields such as `api_key_file`) that are not mounted in the container.
- Deprecated or unknown fields after an upgrade, for example old `match`/`match_re` mixed with invalid `matchers` syntax.
- With prometheus-operator, a broken `AlertmanagerConfig` resource merged into the generated config.

## First checks

1. Confirm which instances are affected:
   ```promql
   alertmanager_config_last_reload_successful == 0
   ```
2. Read the actual error from the logs:
   ```bash
   kubectl -n monitoring logs <alertmanager-pod> -c alertmanager | grep -i "loading configuration"
   ```
3. Validate the file that is on disk, not the one in your repo:
   ```bash
   kubectl -n monitoring exec <alertmanager-pod> -c alertmanager -- \
     amtool check-config /etc/alertmanager/config_out/alertmanager.env.yaml
   ```
   Adjust the path to wherever your deployment mounts the config. Locally, `amtool check-config alertmanager.yml` does the same.
4. If you use the operator, check the reloader sidecar logs and the status of your `AlertmanagerConfig` objects.

## Fixing it

Correct the error reported by `amtool check-config`, redeploy, and trigger a reload (`curl -X POST http://<alertmanager>:9093/-/reload`). Confirm the gauge returns to 1 on every replica. Add `amtool check-config` to CI so a bad file never reaches the cluster.

## Related alerts

- [AlertmanagerConfigInconsistent](/runbooks/alertmanagerconfiginconsistent/): replicas that reloaded and replicas that did not end up with different configs.
- [AlertmanagerClusterCrashlooping](/runbooks/alertmanagerclustercrashlooping/): the same bad file can stop pods from starting after a restart.
- [AlertmanagerFailedToSendAlerts](/runbooks/alertmanagerfailedtosendalerts/): receiver fixes you expected to be live may not be.
