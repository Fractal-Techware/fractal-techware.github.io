---
title: "Rolling out Kyverno policies from Audit to Enforce safely (PolicyReports, PolicyExceptions)"
description: "Move Kyverno ValidatingPolicies from Audit to Warn to Deny without breaking deploys, with PolicyReport queries and a tested PolicyException."
permalink: /guides/kyverno-audit-to-enforce/
breadcrumb: {title: Guides, url: /guides/}
tested_with: "Kyverno CLI 1.19.1"
cta:
  title: "21 Kyverno policies with a ready-made rollout path"
  text: "The hardening kit packages this process: Warn and Enforce overlays, a Helm chart with per-policy modes, an exceptions guide with review workflow, a migration guide and an audit CLI to size the work up front."
  button: See the hardening kit
  url: https://fractaltechware.gumroad.com/l/k8s-hardening-kit?utm_source=site&utm_medium=guide&utm_campaign=kyverno-audit-to-enforce
  free: https://github.com/Fractal-Techware/kubernetes-hardening-baseline
---
# Rolling out Kyverno from Audit to Enforce safely

*Policy and PolicyException tested with `ghcr.io/kyverno/kyverno-cli:v1.19.1` (`kyverno test`: 3 of 3 pass). Manifests checked with kubeconform against the Kyverno schemas. The `kubectl` report queries are standard Kyverno and Kubernetes commands; run them against your own cluster.*

Turning on a new admission policy in `Deny` mode on a live cluster is how a platform team finds out, at 17:55 on a Friday, that the ingress controller's DaemonSet used `:latest`. The safe path takes a few weeks, and most of that time is waiting while reports fill up.

```text
Phase 0  CI only        kyverno test / apply against manifests in Git
Phase 1  Audit          violations recorded in PolicyReports, nothing blocked
Phase 2  Audit + Warn   developers see warnings on every kubectl apply / CI deploy
Phase 3  Deny           violations rejected; exceptions handled explicitly
```

## Phase 0: test in CI before anything reaches the cluster

Every policy gets a `kyverno test` suite with passing and failing resources. See the examples for [disallowing :latest](/guides/kyverno-disallow-latest-tag/) and [requiring requests and limits](/guides/kyverno-require-requests-limits/). Also run `kyverno apply` against your real rendered manifests (Helm template or Kustomize output) to find violations before they are deployed:

```bash
helm template my-app ./chart | \
  kyverno apply policies/ --resource - --remove-color
```

This is the cheapest phase. Every violation found here never becomes a production incident.

## Phase 1: Audit

Install the policies with `validationActions: [Audit]`. Two things happen:

1. **Admission**: new and updated pods are evaluated and the result is recorded, but nothing is blocked.
2. **Background scan**: existing resources are evaluated too (`spec.evaluation.background.enabled` defaults to `true`). You see violations from workloads deployed months ago, not just new ones.

Results land in namespaced `PolicyReport` objects (short name `polr`), one per resource:

```bash
# Overview: pass/fail counts per resource
kubectl get polr -A

# Every failure as resource, policy, message
kubectl get polr -A -o json | jq -r '
  .items[] | (.scope.kind + " " + .metadata.namespace + "/" + .scope.name) as $res
  | .results[]? | select(.result == "fail")
  | [$res, .policy, .message] | @tsv'
```

Stay in Audit for at least a full release cycle, and a week at minimum, so that batch jobs, CronJobs and rarely deployed services show up. Then work through the list:

- **Fix** the manifest. This should be most cases.
- **Exempt** the workload with a PolicyException if it legitimately cannot comply (see below).
- **Change the policy** if it flags something that is not actually a risk. A policy that produces mostly exceptions is the wrong policy.

## Phase 2: Audit + Warn

```yaml
spec:
  validationActions: [Audit, Warn]
```

With `Warn`, the API server returns the policy message as a warning on every create or update. `kubectl apply` prints it, and so do Helm, Argo CD and most CI tools. Nothing is blocked yet, but the people who own the manifests now see the problem in their own workflow, without anyone opening a ticket.

`Deny` and `Warn` cannot be combined. The API rejects that pair because a denial already returns the message. `Audit` works with either.

## Phase 3: Deny

When the failure count in PolicyReports is zero, or every remaining failure is covered by an exception, switch:

```yaml
spec:
  validationActions: [Deny]
```

Roll this out **one policy at a time**, starting with the ones that had the fewest findings. Keep the previous mode in Git so reverting is a one-line change.

Two things to know about enforcement:

- **Existing pods are not evicted.** `Deny` applies at admission. A running pod that violates the policy keeps running until something recreates it, for example a node drain or a rollout. That is when it fails. Background scan results tell you which workloads will break on their next restart.
- **Controllers fail at the controller level.** Kyverno autogen applies the pod checks to Deployments, StatefulSets, DaemonSets, Jobs and CronJobs, so `kubectl apply` of a bad Deployment is rejected directly. That is much easier to debug than a ReplicaSet that silently cannot create pods.

## PolicyExceptions: exempt one workload, not a namespace

Some workloads really need what a policy forbids: a node exporter, a CNI agent, a vendor image you cannot rebuild. Instead of weakening the policy for everyone, create a narrow `PolicyException` (saved as `exception.yaml` for the test below):

```yaml
apiVersion: policies.kyverno.io/v1
kind: PolicyException
metadata:
  name: legacy-exporter-latest-tag
  namespace: policy-exceptions
spec:
  expiresAt: "2027-03-31T00:00:00Z"
  policyRefs:
    - name: disallow-latest-tag
      kind: ValidatingPolicy
  matchConditions:
    - name: only-legacy-exporter-in-monitoring
      expression: >-
        object.metadata.?namespace.orValue('') == 'monitoring' &&
        object.metadata.name.startsWith('legacy-exporter')
```

Key points:

- **Scope by namespace and name** in `matchConditions`. An exception for "all pods in `monitoring`" quietly turns into a hole.
- **`expiresAt`** makes the exception stop applying on that date. Exceptions without an end date become permanent.
- **Restrict who can create exceptions.** Anyone who can create a PolicyException can switch a policy off for their workload. Enable exceptions explicitly, limit them to one namespace, and give only the platform team RBAC to write there:

```bash
helm upgrade --install kyverno kyverno/kyverno -n kyverno \
  --set features.policyExceptions.enabled=true \
  --set features.policyExceptions.namespace=policy-exceptions
```

Test exceptions exactly like policies. With the `disallow-latest-tag` policy from [the earlier guide](/guides/kyverno-disallow-latest-tag/), this suite proves the exception covers the one pod it should, and nothing else:

```yaml
# resources.yaml
apiVersion: v1
kind: Pod
metadata: {name: legacy-exporter, namespace: monitoring}
spec:
  containers:
    - {name: exporter, image: "vendor/exporter:latest"}
---
apiVersion: v1
kind: Pod
metadata: {name: legacy-exporter, namespace: team-a}
spec:
  containers:
    - {name: exporter, image: "vendor/exporter:latest"}
---
apiVersion: v1
kind: Pod
metadata: {name: other-app, namespace: monitoring}
spec:
  containers:
    - {name: app, image: "vendor/app:latest"}
```

```yaml
# kyverno-test.yaml
apiVersion: cli.kyverno.io/v1alpha1
kind: Test
metadata:
  name: latest-tag-with-exception
policies:
  - disallow-latest-tag.yaml
exceptions:
  - exception.yaml
resources:
  - resources.yaml
results:
  - isValidatingPolicy: true
    policy: disallow-latest-tag
    kind: Pod
    resources: [monitoring/legacy-exporter]
    result: skip
  - isValidatingPolicy: true
    policy: disallow-latest-tag
    kind: Pod
    resources: [team-a/legacy-exporter, monitoring/other-app]
    result: fail
```

```bash
docker run --rm -v "$PWD:/work" -w /work ghcr.io/kyverno/kyverno-cli:v1.19.1 test . --remove-color
# Test Summary: 3 tests passed and 0 tests failed
```

The same pod name in another namespace, and another pod in the same namespace, still fail. That is the property you want to lock in with a test.

## Pitfalls

- **Enforcing in `kube-system` and Kyverno's own namespace.** Exclude system namespaces with `matchConstraints.namespaceSelector` before `Deny`. A policy that blocks the CNI or Kyverno itself can make the cluster hard to recover.
- **Webhook failure policy.** If Kyverno is down, admission requests either fail (safe, but blocks deploys) or are allowed (available, but unchecked). Run Kyverno with several replicas and a PodDisruptionBudget before enforcing anything.
- **Reports that never update.** Background scanning needs the Kyverno reports controller running. If `kubectl get polr -A` is empty after an hour, check that controller's logs first.
- **Flipping everything at once.** Twenty policies in `Deny` on the same day means you cannot tell which one broke a deploy. Stagger them.
- **Warn fatigue.** If Phase 2 produces hundreds of warnings per deploy, people stop reading them. Fix the bulk in Phase 1 first.

## Next steps

- Add a network baseline alongside admission policies: [default-deny NetworkPolicy that still allows DNS](/guides/kubernetes-default-deny-networkpolicy-dns/).
- Built-in pod hardening without Kyverno: [Pod Security Admission restricted migration](/guides/pod-security-admission-restricted-migration/).
