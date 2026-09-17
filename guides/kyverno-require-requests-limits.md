---
title: "Kyverno policy: require CPU and memory requests and limits (tested)"
description: "A tested Kyverno ValidatingPolicy requiring CPU/memory requests and a memory limit on every container, with messages that name the container."
permalink: /guides/kyverno-require-requests-limits/
breadcrumb: {title: Guides, url: /guides/}
tested_with: "Kyverno CLI 1.19.1"
cta:
  title: "21 tested Kyverno policies, ready for Audit to Enforce rollout"
  text: "The hardening kit bundles resource governance with probes, non-root, seccomp, capabilities and image controls, plus a Helm chart, Warn and Enforce overlays and an exceptions workflow."
  button: See the hardening kit
  url: https://fractaltechware.gumroad.com/l/k8s-hardening-kit?utm_source=site&utm_medium=guide&utm_campaign=kyverno-require-requests-limits
  free: https://github.com/Fractal-Techware/kubernetes-hardening-baseline
---
# Kyverno: require CPU and memory requests and limits

*Tested with `ghcr.io/kyverno/kyverno-cli:v1.19.1`: `kyverno test` (6 of 6 cases pass) and `kyverno apply` for the messages shown.*

A pod without resource requests is invisible to the scheduler. It gets placed on a node that is already full, and when memory runs out it is among the first to be OOM-killed. A pod without a memory limit can grow until it takes the whole node down with it. Both problems are cheap to prevent at admission.

## What to require (and what not to)

| Setting | Require? | Why |
|---|---|---|
| `requests.cpu` | Yes | Scheduling and CPU share under contention |
| `requests.memory` | Yes | Scheduling, and eviction order under memory pressure |
| `limits.memory` | Yes | Memory cannot be throttled, so the limit is the only hard boundary |
| `limits.cpu` | **No** by default | CPU limits cause CFS throttling and latency spikes even on idle nodes. Many teams deliberately leave them off |

The policy below follows that table. If your organisation requires `limits.cpu`, you can add it with one more validation.

## The policy

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-requests-limits
  annotations:
    policies.kyverno.io/title: Require CPU/memory requests and a memory limit
    policies.kyverno.io/severity: medium
spec:
  validationActions: [Audit]
  matchConstraints:
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [pods]
  variables:
    - name: containers
      expression: object.spec.containers + object.spec.?initContainers.orValue([])
    - name: missingRequests
      expression: >-
        variables.containers.filter(c,
          !has(c.resources) || !has(c.resources.requests) ||
          !('cpu' in c.resources.requests) || !('memory' in c.resources.requests)
        ).map(c, c.name)
    - name: missingMemoryLimit
      expression: >-
        variables.containers.filter(c,
          !has(c.resources) || !has(c.resources.limits) || !('memory' in c.resources.limits)
        ).map(c, c.name)
  validations:
    - expression: size(variables.missingRequests) == 0
      messageExpression: >-
        'resources.requests.cpu and resources.requests.memory are required. Missing on: ' +
        variables.missingRequests.join(', ')
    - expression: size(variables.missingMemoryLimit) == 0
      messageExpression: >-
        'resources.limits.memory is required. Missing on: ' + variables.missingMemoryLimit.join(', ')
```

## How it works

**Variables compute the offenders once.** `missingRequests` and `missingMemoryLimit` are lists of container *names*. Each validation checks that its list is empty, and the message prints the list. A developer sees `Missing on: migrate` and knows it is the init container, not the app.

**`has()` guards every level.** `resources`, `requests` and `limits` are all optional in the Pod schema. Reading a missing field in CEL is an error, so every step is checked with `has()` before the `in` test. Without that, a pod with no `resources` block at all produces a policy *error* instead of a clean *fail*. When we removed the guards, 3 of the 4 expected failures turned into errors.

**Init containers are included.** They count toward the pod's effective requests and are a common place to forget resources. Ephemeral (debug) containers are left out on purpose. Kubernetes does not allow resources on them.

**Two validations, two messages.** When requests *and* limits are missing, Kyverno reports the first failing validation. After the developer fixes it, the second one appears. If you prefer one combined message, merge them into one expression.

**Autogen covers controllers.** As with every Pod-matching `ValidatingPolicy`, Kyverno generates matching rules for Deployments, StatefulSets, DaemonSets, Jobs and CronJobs. The test proves it with a Deployment.

**Requiring CPU limits too.** Add a third variable and validation using `'cpu' in c.resources.limits`, following the same pattern.

## The test

`resources.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata: {name: complete, namespace: team-a}
spec:
  containers:
    - name: app
      image: ghcr.io/acme/api:1.8.3
      resources:
        requests: {cpu: 100m, memory: 128Mi}
        limits: {memory: 256Mi}
---
apiVersion: v1
kind: Pod
metadata: {name: with-cpu-limit, namespace: team-a}
spec:
  containers:
    - name: app
      image: ghcr.io/acme/api:1.8.3
      resources:
        requests: {cpu: 100m, memory: 128Mi}
        limits: {cpu: 500m, memory: 256Mi}
---
apiVersion: v1
kind: Pod
metadata: {name: no-resources, namespace: team-a}
spec:
  containers:
    - {name: app, image: "ghcr.io/acme/api:1.8.3"}
---
apiVersion: v1
kind: Pod
metadata: {name: no-memory-limit, namespace: team-a}
spec:
  containers:
    - name: app
      image: ghcr.io/acme/api:1.8.3
      resources:
        requests: {cpu: 100m, memory: 128Mi}
---
apiVersion: v1
kind: Pod
metadata: {name: init-container-missing, namespace: team-a}
spec:
  initContainers:
    - {name: migrate, image: "ghcr.io/acme/migrate:1.8.3"}
  containers:
    - name: app
      image: ghcr.io/acme/api:1.8.3
      resources:
        requests: {cpu: 100m, memory: 128Mi}
        limits: {memory: 256Mi}
---
apiVersion: apps/v1
kind: Deployment
metadata: {name: api, namespace: team-a}
spec:
  selector: {matchLabels: {app: api}}
  template:
    metadata: {labels: {app: api}}
    spec:
      containers:
        - name: api
          image: ghcr.io/acme/api:1.8.3
          resources:
            requests: {memory: 128Mi}
```

`kyverno-test.yaml`:

```yaml
apiVersion: cli.kyverno.io/v1alpha1
kind: Test
metadata:
  name: require-requests-limits
policies:
  - require-requests-limits.yaml
resources:
  - resources.yaml
results:
  - isValidatingPolicy: true
    policy: require-requests-limits
    kind: Pod
    resources: [team-a/complete, team-a/with-cpu-limit]
    result: pass
  - isValidatingPolicy: true
    policy: require-requests-limits
    kind: Pod
    resources: [team-a/no-resources, team-a/no-memory-limit, team-a/init-container-missing]
    result: fail
  - isValidatingPolicy: true
    policy: require-requests-limits
    kind: Deployment
    resources: [team-a/api]
    result: fail
```

Run the test and look at the messages:

```bash
docker run --rm -v "$PWD:/work" -w /work ghcr.io/kyverno/kyverno-cli:v1.19.1 test . --remove-color
# Test Summary: 6 tests passed and 0 tests failed

docker run --rm -v "$PWD:/work" -w /work ghcr.io/kyverno/kyverno-cli:v1.19.1 \
  apply require-requests-limits.yaml --resource resources.yaml --remove-color
```

```text
policy require-requests-limits -> resource team-a/Pod/no-resources failed:
1 -  resources.requests.cpu and resources.requests.memory are required. Missing on: app
policy require-requests-limits -> resource team-a/Pod/no-memory-limit failed:
1 -  resources.limits.memory is required. Missing on: app
policy require-requests-limits -> resource team-a/Pod/init-container-missing failed:
1 -  resources.requests.cpu and resources.requests.memory are required. Missing on: migrate
policy require-requests-limits -> resource team-a/Deployment/api failed:
1 -  resources.requests.cpu and resources.requests.memory are required. Missing on: api

pass: 2, fail: 4, warn: 0, error: 0, skip: 0
```

## Policy or LimitRange?

A namespace `LimitRange` can *inject* default requests and limits into pods that have none. That avoids rejections, but it hides the problem: every service gets the same guessed numbers. A common split:

- **LimitRange** in namespaces where teams are onboarding, as a safety net.
- **This policy in Audit** everywhere, so PolicyReports show who relies on defaults.
- **This policy in Deny** once teams set real values, ideally based on actual usage (VPA recommendations or Prometheus `container_memory_working_set_bytes`).

Admission runs *after* the LimitRange defaults are applied, so a namespace with a LimitRange passes this policy automatically. That is usually what you want.

## Pitfalls

- **Helm charts with empty `resources: {}`.** Many upstream charts ship this by default. Expect a wave of Audit findings from third-party charts. Set values per release, or add PolicyExceptions for the ones you cannot change yet.
- **Sidecars injected by a mutating webhook.** Service mesh proxies are added during admission. If the injector does not set resources, the pod fails *after* the developer's manifest looked fine. Configure the injector's default resources.
- **Requests equal to limits everywhere.** That is valid (Guaranteed QoS) but wastes capacity for bursty services. The policy intentionally does not force it.
- **Memory limit below real usage.** The policy only checks that the field exists. Too-low limits show up as `OOMKilled` restarts, so alert on them.

## Next steps

- Roll this out without breaking deploys: [Kyverno Audit to Enforce](/guides/kyverno-audit-to-enforce/).
- Pair with [disallow the :latest tag](/guides/kyverno-disallow-latest-tag/).
