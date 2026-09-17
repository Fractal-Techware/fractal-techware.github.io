---
title: "Migrate a namespace to Pod Security Admission restricted without breaking workloads"
description: "Move a live Kubernetes namespace to Pod Security Admission restricted safely: dry runs, warn and audit first, a compliant Deployment, then enforce."
permalink: /guides/pod-security-admission-restricted-migration/
breadcrumb: {title: Guides, url: /guides/}
tested_with: "kubeconform -strict (Kubernetes 1.35 and 1.37 schemas)"
cta:
  title: "Pod Security plus 21 Kyverno policies and a hardening checklist"
  text: "The hardening kit goes beyond PSA: Kyverno policies for images, resources, probes and service exposure, NetworkPolicy allow rules, least-privilege RBAC and a CIS/NSA-mapped checklist."
  button: See the hardening kit
  url: https://fractaltechware.gumroad.com/l/k8s-hardening-kit?utm_source=site&utm_medium=guide&utm_campaign=pod-security-admission-restricted-migration
  free: https://github.com/Fractal-Techware/kubernetes-hardening-baseline
---
# Migrate a namespace to Pod Security Admission `restricted`

*Manifests validated with `kubeconform -strict` against the Kubernetes 1.35 and 1.37 schemas. The Deployment was checked against the `restricted` profile offline, and its image was run with the same constraints (non-root, read-only root filesystem, all capabilities dropped) to confirm it starts. The `kubectl` commands are standard; run them against your cluster.*

Pod Security Admission (PSA) is built into Kubernetes and needs no extra software. You label a namespace, and the API server checks every pod against one of three profiles: `privileged` (no checks), `baseline` (blocks the obviously dangerous: privileged containers, host namespaces, hostPath) and `restricted` (non-root, no privilege escalation, dropped capabilities, seccomp).

Setting `enforce: restricted` on a busy namespace in one step usually breaks something. This is the order that doesn't.

## Step 1: find out what would break (no changes)

A server-side dry run of the label evaluates every **existing** pod in the namespace against the profile and prints the violations. Nothing is changed:

```bash
kubectl label --dry-run=server --overwrite ns shop \
  pod-security.kubernetes.io/enforce=restricted
```

The output looks roughly like this:

```text
Warning: existing pods in namespace "shop" violate the new PodSecurity enforce level "restricted:latest"
Warning: web-7d9c...: allowPrivilegeEscalation != false, unrestricted capabilities, runAsNonRoot != true, seccompProfile
namespace/shop labeled (server dry run)
```

Run it for every namespace to get a quick inventory:

```bash
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  echo "== $ns"
  kubectl label --dry-run=server --overwrite ns "$ns" pod-security.kubernetes.io/enforce=restricted 2>&1 | grep Warning
done
```

## Step 2: enforce baseline, warn and audit on restricted

Most workloads already pass `baseline`. Enforce that now and turn on `restricted` as warn and audit only:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: shop
  labels:
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
```

- **enforce** rejects violating pods.
- **warn** returns a warning to whoever applies the manifest (`kubectl`, Helm, Argo CD). The pod is still admitted.
- **audit** adds an annotation to the API server audit log event. It is only useful if your cluster has audit logging, which managed clusters usually expose through their logging product.

Run step 1 with `enforce=baseline` first. If that dry run shows warnings, fix those pods before applying this.

`warn` and `audit` also check **workload resources** (Deployments, StatefulSets, Jobs and so on), so `kubectl apply` of a Deployment shows the warning immediately. `enforce` checks **pods only**, as the next steps explain.

## Step 3: make workloads compliant

A Deployment that passes `restricted`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: shop
spec:
  replicas: 2
  selector:
    matchLabels: {app: web}
  template:
    metadata:
      labels: {app: web}
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: web
          image: nginxinc/nginx-unprivileged:1.31-alpine
          ports:
            - containerPort: 8080
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
          resources:
            requests: {cpu: 50m, memory: 64Mi}
            limits: {memory: 128Mi}
          volumeMounts:
            - {name: tmp, mountPath: /tmp}
      volumes:
        - name: tmp
          emptyDir: {}
```

What `restricted` actually requires, and the field that satisfies it:

| Requirement | Field |
|---|---|
| Must not run as root | `runAsNonRoot: true` (and an image or `runAsUser` with a non-zero UID) |
| No privilege escalation | `allowPrivilegeEscalation: false` on every container |
| Drop all capabilities | `capabilities.drop: [ALL]` (only `NET_BIND_SERVICE` may be added back) |
| Seccomp profile | `seccompProfile.type: RuntimeDefault` (or `Localhost`) |
| Restricted volume types | configMap, secret, emptyDir, projected, downwardAPI, persistentVolumeClaim, ephemeral, csi |

`readOnlyRootFilesystem` and resources are **not** required by PSA. They are included because they are good practice, and the `/tmp` emptyDir is what makes a read-only root filesystem work for nginx.

Common fixes:

- **Image runs as root** (most official images, including `nginx`). Switch to an unprivileged variant (`nginxinc/nginx-unprivileged`, Bitnami images, distroless `:nonroot`) or build with a `USER` line. Setting `runAsUser` on an image that expects root usually fails on file permissions.
- **App binds to port 80.** Non-root processes cannot bind ports below 1024 without `NET_BIND_SERVICE`. Listen on 8080 and map it in the Service.
- **Init containers** need the same container-level `securityContext`. They are checked too.
- **Helm charts.** Most charts expose `podSecurityContext` and `securityContext` values. Set them per release.

## Step 4: enforce restricted, pinned

When the warnings stop, re-run the dry run from step 1. When it prints no warnings, switch:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: shop
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: latest
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: latest
```

**Pin `enforce-version`** to the Kubernetes minor you tested against. If a future release tightens the `restricted` profile, an upgrade will not start rejecting pods. **Set warn and audit to `latest`** so you see what the next version would reject before you bump the pinned version.

Existing pods keep running when you change the label. PSA only checks pods when they are created. The dry run in step 1 is how you find pods that would fail on their next restart.

Because `enforce` only checks pods, a non-compliant Deployment is still **accepted** by the API server. Its ReplicaSet then fails to create pods. `kubectl apply` succeeds (with a warning), but the rollout hangs. Look for `FailedCreate` events with `kubectl -n shop get events` or `kubectl -n shop describe rs`.

## Validate before applying

```bash
kubeconform -strict -summary -kubernetes-version 1.35.0 namespace.yaml deployment.yaml
```

Kubeconform checks the schema, not the security profile. For the profile itself, use the server-side dry run in a real cluster:

```bash
kubectl apply --dry-run=server -f deployment.yaml
```

In a namespace with `warn: restricted`, a non-compliant Deployment prints `Warning: would violate PodSecurity "restricted:..."` followed by each failing field.

## Pitfalls

- **Exempting namespaces.** `kube-system` and some operators (CNI, CSI drivers, node exporters) legitimately need `privileged`. Label those namespaces `enforce: privileged` explicitly, and keep application workloads out of them.
- **Cluster-wide defaults.** The `AdmissionConfiguration` for the PodSecurity plugin can set defaults for unlabelled namespaces. Managed clusters often do not let you change it, so label namespaces explicitly.
- **Warnings hidden by CI.** Some deploy tools swallow API warnings. Check your pipeline actually prints them during step 2.
- **Windows pods** skip several checks. The profile is mostly Linux-specific.
- **PSA cannot express everything.** It has no image tag rules, no resource requirements, no label requirements and no exceptions per workload. Use Kyverno for those. See [disallow :latest](/guides/kyverno-disallow-latest-tag/) and [Audit to Enforce](/guides/kyverno-audit-to-enforce/).

## Next steps

- Lock down traffic too: [default-deny NetworkPolicy that still allows DNS](/guides/kubernetes-default-deny-networkpolicy-dns/).
- Require resources on every pod: [Kyverno requests and limits policy](/guides/kyverno-require-requests-limits/).
