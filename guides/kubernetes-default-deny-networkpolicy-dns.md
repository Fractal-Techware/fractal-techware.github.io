---
title: "Kubernetes default-deny NetworkPolicy that still allows DNS (and how to test it)"
description: "Default-deny ingress and egress for a Kubernetes namespace without breaking DNS: working NetworkPolicy YAML, an allow rule, and how to test it."
permalink: /guides/kubernetes-default-deny-networkpolicy-dns/
breadcrumb: {title: Guides, url: /guides/}
tested_with: "kubeconform -strict, Kubernetes 1.35 and 1.37 schemas"
cta:
  title: "Default-deny plus the allow rules you will need next"
  text: "The hardening kit includes tested allow policies for ingress controllers, Prometheus scraping, app-to-app traffic, the Kubernetes API and external CIDRs, next to 21 Kyverno policies."
  button: See the hardening kit
  url: https://store.fractaltechware.com/l/k8s-hardening-kit?utm_source=site&utm_medium=guide&utm_campaign=kubernetes-default-deny-networkpolicy-dns
  free: https://github.com/Fractal-Techware/kubernetes-hardening-baseline
---
# Kubernetes default-deny NetworkPolicy that still allows DNS

*Manifests validated with `kubeconform -strict` against the Kubernetes 1.35 and 1.37 schemas. The connectivity checks below need a CNI that enforces NetworkPolicy; run them in your own cluster.*

By default, every pod in a Kubernetes cluster can talk to every other pod and to the internet. A compromised pod in one namespace can reach your database in another. The standard fix is **default deny**: block all traffic in a namespace, then allow only the paths you need.

The first thing that breaks is almost always **DNS**. Egress is blocked, so pods cannot reach CoreDNS, and every connection fails with `could not resolve host`, including the ones you meant to allow. Here is the pair of policies that avoids that.

## The policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: shop
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: shop
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - {protocol: UDP, port: 53}
        - {protocol: TCP, port: 53}
```

## How it works

**NetworkPolicies are additive allow lists.** As soon as *any* policy selects a pod for a direction (Ingress or Egress), that direction becomes deny-by-default for the pod, and only traffic allowed by *some* policy passes. There is no "deny" rule, and policy order does not matter.

**`podSelector: {}` selects every pod in the namespace**, including pods created later. `policyTypes: [Ingress, Egress]` with no rules means nothing is allowed in either direction.

**The DNS rule has one `to` entry with both selectors.** `namespaceSelector` and `podSelector` are in the *same* list item (no `-` before `podSelector`), so the rule means "pods labelled `k8s-app: kube-dns` **in** `kube-system`". If you add a dash before `podSelector`, it becomes two separate items: "any pod in kube-system **or** any pod labelled kube-dns in *this* namespace". That is a very common and much broader mistake.

**`kubernetes.io/metadata.name`** is set automatically on every namespace (Kubernetes 1.22+), so you do not need to label `kube-system` yourself.

**Both UDP and TCP 53.** DNS normally uses UDP, but falls back to TCP for large responses. Without TCP you get intermittent failures that are hard to reproduce.

## Allowing real traffic

Now add one policy per real path. For example, allowing the ingress controller to reach the `web` pods on port 8080:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ingress-to-web
  namespace: shop
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes: [Ingress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
      ports:
        - {protocol: TCP, port: 8080}
```

Remember that the port is the **container port** the pod listens on, not the Service port. NetworkPolicy is evaluated after Service translation.

Traffic between two pods needs to be allowed on **both** sides when both namespaces use default deny: egress from the client and ingress to the server.

## Validate the YAML

```bash
kubeconform -strict -summary -kubernetes-version 1.35.0 netpol.yaml allow-web.yaml
# Summary: 3 resources found in 2 files - Valid: 3, Invalid: 0, Errors: 0, Skipped: 0
```

`-strict` rejects unknown fields, which catches indentation mistakes that would otherwise silently produce a different policy.

## Test that it actually works

Schema validation does not tell you whether traffic is blocked. Test in the cluster after applying:

```bash
kubectl apply -f netpol.yaml

# 1. DNS still resolves (expect an address)
kubectl -n shop run dnstest --rm -it --restart=Never --image=busybox:1.37 -- \
  nslookup kubernetes.default.svc.cluster.local

# 2. Egress to the internet is blocked (expect a timeout)
kubectl -n shop run egresstest --rm -it --restart=Never --image=busybox:1.37 -- \
  wget -qO- -T 5 http://example.com

# 3. Ingress from another namespace is blocked (expect a timeout)
kubectl -n shop run target --image=nginxinc/nginx-unprivileged:1.31-alpine --port=8080
kubectl -n shop wait --for=condition=Ready pod/target
TARGET_IP=$(kubectl -n shop get pod target -o jsonpath='{.status.podIP}')
kubectl -n default run probe --rm -it --restart=Never --image=busybox:1.37 -- \
  wget -qO- -T 5 "http://$TARGET_IP:8080"
kubectl -n shop delete pod target
```

If check 2 or 3 **succeeds**, your CNI does not enforce NetworkPolicy. The API server happily stores policies that nothing enforces. Flannel does not enforce them. Neither does kindnet in older kind releases, and some managed clusters need a network-policy add-on enabled. Calico, Cilium and Antrea do enforce them.

If check 1 fails, see the pitfalls below.

## Pitfalls

- **DNS pods are labelled differently.** Most clusters use `k8s-app: kube-dns` even when running CoreDNS, but check with `kubectl -n kube-system get pods --show-labels`. OpenShift uses the `openshift-dns` namespace and different labels.
- **NodeLocal DNSCache.** Pods send DNS to a link-local IP (usually `169.254.20.10`) served by a node-level agent, not a pod. Add an `ipBlock` egress rule for that address on port 53.
- **Egress to the API server.** Operators, service meshes and anything using a Kubernetes client need to reach the API server. It is not a pod, so selectors do not match it. Allow its IPs with `ipBlock` (find them with `kubectl get endpointslices -n default -l kubernetes.io/service-name=kubernetes`).
- **Health checks from the kubelet.** Liveness and readiness probes come from the node, and most CNIs always allow them. A few do not, and then pods restart after you apply default deny.
- **Prometheus scraping.** Metrics endpoints need an ingress rule from the monitoring namespace, or your targets go down right after the rollout.
- **Rolling out to a live namespace.** Apply the allow rules *first*, then default deny. Doing it the other way round causes an outage between the two applies.

## Next steps

- Harden the pods themselves: [Pod Security Admission restricted migration](/guides/pod-security-admission-restricted-migration/).
- Enforce image and resource rules at admission: [Kyverno Audit to Enforce](/guides/kyverno-audit-to-enforce/).
- A free default-deny manifest set is in [kubernetes-hardening-baseline](https://github.com/Fractal-Techware/kubernetes-hardening-baseline).
