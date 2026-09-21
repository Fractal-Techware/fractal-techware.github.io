---
title: "Kyverno policy to disallow the :latest image tag (with kyverno test)"
description: "A tested Kyverno ValidatingPolicy that blocks :latest and untagged images, including init containers and registry ports, with kyverno test."
permalink: /guides/kyverno-disallow-latest-tag/
breadcrumb: {title: Guides, url: /guides/}
tested_with: "Kyverno CLI 1.19.1"
cta:
  title: "21 tested Kyverno policies, ready for Audit to Enforce rollout"
  text: "The hardening kit ships this policy alongside image digests, registry allowlists, Pod Security controls and more, each with good and bad test fixtures, Helm chart, rollout overlays and PolicyException workflow."
  button: See the hardening kit
  url: https://store.fractaltechware.com/l/k8s-hardening-kit?utm_source=site&utm_medium=guide&utm_campaign=kyverno-disallow-latest-tag
  free: https://github.com/Fractal-Techware/kubernetes-hardening-baseline
---
# Kyverno: disallow the :latest image tag

*Tested with `ghcr.io/kyverno/kyverno-cli:v1.19.1`: `kyverno test` (8 of 8 cases pass) and `kyverno apply` for the messages shown below.*

`image: nginx` and `image: nginx:latest` mean "whatever was pushed most recently". Two nodes can run different code under the same pod spec, a rollback redeploys the same broken image, and nobody can say which version was running during an incident. Blocking mutable tags at admission is one of the cheapest guardrails you can add.

The catch is that most copy-paste policies get the edge cases wrong:

- `registry.local:5000/team/api` contains a `:`, but it is **untagged**. The colon belongs to the registry port.
- `ghcr.io/acme/api@sha256:...` has no tag but is pinned by digest, so it is fine.
- `initContainers` and `ephemeralContainers` are easy to forget.

## The policy

This uses the CEL-based `ValidatingPolicy` API (`policies.kyverno.io/v1`, Kyverno 1.19+). The older `ClusterPolicy` type is deprecated.

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: disallow-latest-tag
  annotations:
    policies.kyverno.io/title: Disallow latest and untagged images
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
    - name: images
      expression: >-
        (object.spec.containers +
         object.spec.?initContainers.orValue([]) +
         object.spec.?ephemeralContainers.orValue([])).map(c, c.image)
  validations:
    - expression: >-
        variables.images.all(img,
          img.contains('@') ||
          (img.split('/')[img.split('/').size() - 1].contains(':') && !img.endsWith(':latest')))
      messageExpression: >-
        'Pin every image to a version tag or digest. Offending: ' +
        variables.images.filter(img, !(img.contains('@') ||
          (img.split('/')[img.split('/').size() - 1].contains(':') && !img.endsWith(':latest')))).join(', ')
```

## How it works

**Collect every image once.** The `images` variable joins `containers`, `initContainers` and `ephemeralContainers`. The `?.` / `orValue([])` syntax handles pods that do not have the optional lists.

**Only look at the last path segment for a tag.** For `registry.local:5000/team/api`, splitting on `/` and taking the last part gives `api`, which has no `:`, so the image is untagged. For `registry.local:5000/team/api:2.0.1` the last part is `api:2.0.1`, so it is tagged.

**Digests always pass.** Anything containing `@` is pinned by content, with or without a tag.

**`messageExpression` names the offending images.** A plain `message` says "not allowed". This one tells the developer exactly which image to fix, which saves a round trip when a pod has five containers.

**Pods only, controllers automatically.** The policy matches `pods`. Kyverno *autogen* generates the equivalent checks for Deployments, StatefulSets, DaemonSets, Jobs and CronJobs, so a bad Deployment is reported (or rejected) at `kubectl apply` time, not later when its ReplicaSet fails to create pods. The test below includes a Deployment to prove that.

**`validationActions: [Audit]`.** Violations are recorded in PolicyReports but nothing is blocked. Start here, then move to `[Deny]`. See [rolling out Kyverno from Audit to Enforce](/guides/kyverno-audit-to-enforce/).

## The test

Save the policy as `disallow-latest-tag.yaml`, then add `resources.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata: {name: pinned-tag, namespace: team-a}
spec:
  containers:
    - {name: app, image: "ghcr.io/acme/api:1.8.3"}
---
apiVersion: v1
kind: Pod
metadata: {name: pinned-digest, namespace: team-a}
spec:
  containers:
    - {name: app, image: "ghcr.io/acme/api@sha256:9db7b59979c38555a39def84a31fb98b5296952f9e3afd4f6f11f05b07adfab0"}
---
apiVersion: v1
kind: Pod
metadata: {name: registry-port-tag, namespace: team-a}
spec:
  containers:
    - {name: app, image: "registry.local:5000/team/api:2.0.1"}
---
apiVersion: v1
kind: Pod
metadata: {name: latest-tag, namespace: team-a}
spec:
  containers:
    - {name: app, image: "nginx:latest"}
---
apiVersion: v1
kind: Pod
metadata: {name: no-tag, namespace: team-a}
spec:
  containers:
    - {name: app, image: "nginx"}
---
apiVersion: v1
kind: Pod
metadata: {name: registry-port-no-tag, namespace: team-a}
spec:
  containers:
    - {name: app, image: "registry.local:5000/team/api"}
---
apiVersion: v1
kind: Pod
metadata: {name: latest-init-container, namespace: team-a}
spec:
  initContainers:
    - {name: migrate, image: "busybox:latest"}
  containers:
    - {name: app, image: "ghcr.io/acme/api:1.8.3"}
---
apiVersion: apps/v1
kind: Deployment
metadata: {name: web, namespace: team-a}
spec:
  selector: {matchLabels: {app: web}}
  template:
    metadata: {labels: {app: web}}
    spec:
      containers:
        - {name: web, image: "nginx:latest"}
```

And `kyverno-test.yaml`:

```yaml
apiVersion: cli.kyverno.io/v1alpha1
kind: Test
metadata:
  name: disallow-latest-tag
policies:
  - disallow-latest-tag.yaml
resources:
  - resources.yaml
results:
  - isValidatingPolicy: true
    policy: disallow-latest-tag
    kind: Pod
    resources: [team-a/pinned-tag, team-a/pinned-digest, team-a/registry-port-tag]
    result: pass
  - isValidatingPolicy: true
    policy: disallow-latest-tag
    kind: Pod
    resources: [team-a/latest-tag, team-a/no-tag, team-a/registry-port-no-tag, team-a/latest-init-container]
    result: fail
  - isValidatingPolicy: true
    policy: disallow-latest-tag
    kind: Deployment
    resources: [team-a/web]
    result: fail
```

Run it with a local `kyverno` binary or the container:

```bash
docker run --rm -v "$PWD:/work" -w /work ghcr.io/kyverno/kyverno-cli:v1.19.1 test . --remove-color
```

```text
│ 1  │ disallow-latest-tag │      │ v1/Pod/team-a/pinned-tag            │ Pass   │ Ok     │
│ 2  │ disallow-latest-tag │      │ v1/Pod/team-a/pinned-digest         │ Pass   │ Ok     │
...
│ 8  │ disallow-latest-tag │      │ apps/v1/Deployment/team-a/web       │ Pass   │ Ok     │

Test Summary: 8 tests passed and 0 tests failed
```

"Pass" here means *the result matched your expectation*, including the expected failures. To be sure the test is not passing by accident, flip one expected `fail` to `pass` and confirm the CLI reports `1 tests failed`. We did.

To see what developers will see, run `apply`:

```bash
docker run --rm -v "$PWD:/work" -w /work ghcr.io/kyverno/kyverno-cli:v1.19.1 \
  apply disallow-latest-tag.yaml --resource resources.yaml --remove-color
```

```text
policy disallow-latest-tag -> resource team-a/Pod/registry-port-no-tag failed:
1 -  Pin every image to a version tag or digest. Offending: registry.local:5000/team/api
policy disallow-latest-tag -> resource team-a/Pod/latest-init-container failed:
1 -  Pin every image to a version tag or digest. Offending: busybox:latest
...
pass: 3, fail: 5, warn: 0, error: 0, skip: 0
```

Run `kyverno test` in CI for every change to your policies, the same way you run unit tests.

## Pitfalls

- **A tag is not immutable either.** `api:1.8.3` can be re-pushed. If you need true immutability, require digests (usually filled in by CI or a mutating policy) and enable tag immutability in your registry.
- **System namespaces.** Some vendor charts in `kube-system` still use `:latest`. In Audit mode that is only noise. Before switching to Deny, exclude them with `matchConstraints.namespaceSelector` or a narrow PolicyException.
- **Jobs created by operators.** Operators sometimes create pods from images you do not control. Check PolicyReports for them before enforcing.
- **Other mutable tags.** `:stable`, `:main` or `:dev` are just as mutable as `:latest`. If your teams use them, add them to the check with another `!img.endsWith(...)` clause.

## Next steps

- Pair it with [require CPU/memory requests and limits](/guides/kyverno-require-requests-limits/).
- Plan the switch to blocking: [Audit to Enforce, safely](/guides/kyverno-audit-to-enforce/).
- A free, MIT-licensed version of this policy with fixtures lives in the [kubernetes-hardening-baseline](https://github.com/Fractal-Techware/kubernetes-hardening-baseline) repo.
