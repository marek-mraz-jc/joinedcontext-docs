---
sidebar_position: 9
title: Security Hardening & Phase-1 Baseline
description: Comprehensive security architecture, ordered hardening layers, and verification commands for the joinedcontext platform deployment.
---

# Security Hardening & Phase-1 Baseline

This document specifies the phase-1 security baseline and sequential hardening layers for deploying the joinedcontext platform on Kubernetes. It establishes the defense-in-depth architecture across cluster infrastructure, shared operators, network policies, service mesh mutual TLS, identity management, edge gateway routing, and in-process policy enforcement. Every layer documents the controls inherited from the legacy platform (`civitas-core-deployment`), the architectural modifications introduced in joinedcontext, configuration value keys, concrete verification commands, and the specific security findings addressed. Written for platform engineers, Site Reliability Engineers, and security compliance officers.

## 1. Security Architecture and Trust Zones

The platform enforces five isolated trust zones adhering to BSI TR-03187 recommendations:

- **Zone 1: Public Untrusted Edge:** External traffic terminating on cluster ingress controllers or load balancers over TLS 1.3/1.2.
- **Zone 2: Gateway DMZ:** Apache APISIX operating in standalone declarative file mode, enforcing rate limits, sanitizing HTTP headers, and setting response security headers.
- **Zone 3: Core Data Plane:** The Context Gateway Policy Enforcement Point (PEP), Antares Context Broker, and CloudNativePG PostgreSQL clusters running with Row-Level Security (RLS).
- **Zone 4: Configuration and CI Plane:** The internal Gitea forge, Gitea Actions runners, and the `jcctl` reconciler daemon managing platform state from Git.
- **Zone 5: Workload Runners:** Bento pipeline runners executing stream processing in sandboxed, non-root runtimes.

In the legacy platform documentation, network isolation was described as enforcing default-deny on both ingress and egress. Inspection of `civitas-core-deployment/defaults/environment/networkpolicies.yaml.gotmpl` revealed that the legacy template configured `policyTypes: [Ingress]` only. Pods had unrestricted egress access to cluster networks and the public internet. The joinedcontext platform baseline corrects this gap: all namespaces enforce dual Ingress and Egress default-deny policies.

## 2. Sequential Hardening Layers

Deployment hardening must execute in the twelve sequential layers defined below. Each layer builds upon the controls established by preceding layers.

### Layer 1: Cluster Prerequisites and Node Hardening

- **Inherited Baseline:** Kubernetes 1.28+ with standard Linux cNI (Calico or Cilium) supporting `NetworkPolicy` v1 evaluation.
- **joinedcontext Enhancements:** Nodes must enable the `RuntimeDefault` seccomp profile at the container runtime level (containerd/CRI-O). API server audit logging must be active.
- **Configuration Keys:** `global.storage.storageClass.rwo` mapped to high-IOPS storage.
- **Verification Command:**

  ```bash
  kubectl get nodes -o custom-columns=NAME:.metadata.name,KERNEL:.status.nodeInfo.kernelVersion,CRI:.status.nodeInfo.containerRuntimeVersion
  ```

- **Gaps Closed:** Foundation for SEC-GAP-05 (NetworkPolicy egress support) and CT-6 compliance.

### Layer 2: Shared Cluster Operators Layer (`deployLayer: operators`)

- **Inherited Baseline:** CloudNativePG operator and Kyverno admission controller deployed once per cluster into the shared operators namespace (`civitas-core-deployment/deployment/helmfile-operators.yaml`).
- **joinedcontext Enhancements:** Cluster-scoped Kyverno policies (`ClusterPolicy`) deploy with `failureAction: Enforce` by default in production profiles.
- **Configuration Keys:** `global.operators.namespace: "jc-operators"`, `global.runtimePolicies.failureAction: "Enforce"`.
- **Verification Command:**

  ```bash
  kubectl get pods -n jc-operators
  kubectl get clusterpolicies
  ```

- **Gaps Closed:** Prevents multi-instance release collisions; enforces SEC-GAP-04 anti-spoofing policies across all nodes.

### Layer 3: Namespace Preparation and Trust Distribution

- **Inherited Baseline:** The `prepare` Helmfile hook (`civitas-core-deployment/components/prepare/helmfile.yaml.gotmpl`) creates required namespaces, annotates them for Linkerd injection (`linkerd.io/inject: enabled`), sets `config.linkerd.io/default-inbound-policy`, and distributes `custom-ca-cert` Secrets when using self-signed certificate issuers.
- **joinedcontext Enhancements:** The hook validates that the operator namespace exists and fails immediately if namespace creation fails, rather than continuing execution.
- **Configuration Keys:** `global.createNamespaces: true`, `global.serviceMesh.patchNamespaces: true`, `global.serviceMesh.defaultInboundPolicy: "cluster-authenticated"`.
- **Verification Command:**

  ```bash
  kubectl get namespaces -o custom-columns='NAME:.metadata.name,INJECT:.metadata.annotations.linkerd\.io/inject,INBOUND:.metadata.annotations.config\.linkerd\.io/default-inbound-policy'
  ```

  Both are annotations, not labels, so `-L` prints empty columns for them. CHK-06 reads the same
  two the same way.

- **Gaps Closed:** Preconditions for Linkerd mutual TLS authorization across all workloads.

### Layer 4: Cryptographic Secrets Management

- **Inherited Baseline:** In-tree chart `components/secrets` generates cryptographically random passwords during initial installation, stores them as Kubernetes Secret objects, and replicates them to dependent namespaces (`civitas-core-deployment/components/secrets/charts/secrets-generator/templates/secrets.yaml`). Secrets carry `helm.sh/resource-policy: keep`.
- **joinedcontext Enhancements:** Administrative credentials, database passwords, and client secrets are decoupled from Git commits. Configuration-as-Code secrets utilize SOPS with `age` encryption keys or OpenBao (ADR-N-012). The legacy plaintext secrets generator is retained solely for cluster-internal bootstrap secrets.
- **Configuration Keys:** `managedSecrets` map in `defaults/environment/secrets.yaml.gotmpl`.
- **Verification Command:**

  ```bash
  kubectl get secrets -n prod -l app.kubernetes.io/managed-by=Helm
  ```

- **Gaps Closed:** Enforces BSI TR-03187 AR-9 and DH-2 (secrets modifiable and stored outside source repositories).

#### Rotating the Portal's session key

The session cookie key is the Portal's alone, but every signed-in person's cookie is sealed with
it, so replacing it in one step signs everybody out. `JC_PORTAL_COOKIE_KEY_PREVIOUS` holds the
keys a rotation is still letting in — comma-separated, each at least 64 bytes like the active
one. The active key seals every cookie the Portal writes; a previous key only opens one, and a
session that refreshes during the window is re-sealed with the active key by itself.

| Step | What is done | Who stays signed in |
|---|---|---|
| 1 | The new key becomes `JC_PORTAL_COOKIE_KEY`, the old one moves to `JC_PORTAL_COOKIE_KEY_PREVIOUS` | everybody |
| 2 | The window passes: longer than a session lives, so every cookie has been re-sealed or has expired | everybody |
| 3 | `JC_PORTAL_COOKIE_KEY_PREVIOUS` is removed | everybody, on the new key |

A key removed before the window has passed signs out whoever was idle through it, which costs a
login and nothing else; a key left there for ever is a key that is never retired, which is what
the rotation is for. The window is the session lifetime, not a fixed day.

#### Rotating a secret that two sides share

A secret only one component holds is rotated by writing the new value and restarting it. A
secret shared with another component cannot change in the same instant on both sides, so it is
rotated in three steps, and the Portal accepts two values while it happens:

| Step | What is done | What is accepted |
|---|---|---|
| 1 | The new value is written as `JC_GITEA_WEBHOOK_SECRET`, the old one moves to `JC_GITEA_WEBHOOK_SECRET_PREVIOUS` | both |
| 2 | The forge's own hook is updated to the new value | both |
| 3 | `JC_GITEA_WEBHOOK_SECRET_PREVIOUS` is removed | the new one only |

Between steps 1 and 3 a push signed with either value is accepted, and one signed with neither
is refused as before; after step 3 the retired value is a stranger's. Without the overlap a
rotation is a window in which every push is refused, which is why an unrotatable secret stays
unrotated. A Portal with no webhook secret configured at all refuses every webhook with `503`
and syncs the repository on its interval instead (T-0982).

### Layer 5: Pod Security Standards Baseline

- **Inherited Baseline:** Restrictive execution defaults in `civitas-core-deployment/defaults/environment/security.yaml.gotmpl` defining `runAsNonRoot: true`, `runAsUser: 1000`, `fsGroup: 1000`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`, `readOnlyRootFilesystem: true`, and `seccompProfile.type: RuntimeDefault`.
- **joinedcontext Enhancements:** All components must declare dedicated ServiceAccounts with `automountServiceAccountToken: false` (closing legacy issue deployment#209). Workloads requiring writable temporary storage must mount bounded `emptyDir` volumes to `/tmp`. Container images must be pinned to explicit SHA-256 digests with `pullPolicy: IfNotPresent`.
- **Configuration Keys:** `securityDefaults` in `defaults/environment/security.yaml.gotmpl`.
- **Verification Command:**

  ```bash
  kubectl get pods -n prod -o jsonpath='{range .items[*]}{.metadata.name}{"\tSA:"}{.spec.serviceAccountName}{"\tToken:"}{.spec.automountServiceAccountToken}{"\n"}{end}'
  ```

- **Gaps Closed:** SEC-GAP-02 (ServiceAccount token exposure) and SEC-GAP-03 (mutable image tags).

### Layer 6: Ingress and Egress Network Policies

- **Inherited Baseline:** Component network policy templates in `civitas-core-deployment/components/*/networkpolicies.yaml` specifying ingress rules.
- **joinedcontext Enhancements:** Every namespace automatically applies a default-deny policy for both Ingress and Egress (`policyTypes: [Ingress, Egress]`). Egress is restricted to explicit destinations: kube-dns (port 53 UDP/TCP), Context Gateway (:8080), Keycloak (:8080), PostgreSQL (:5432), and Linkerd control proxies (:4143, :4191). The template helper `resolveComponentNamespace` is updated to fail closed: if a target component namespace cannot be resolved, manifest compilation halts with an error instead of generating a permissive allow-all rule.
- **Configuration Keys:** `networkpolicies` map in `defaults/environment/networkpolicies.yaml.gotmpl`.
- **Verification Command:**

  ```bash
  kubectl get networkpolicies -n prod
  ```

- **Gaps Closed:** SEC-GAP-04 (NetworkPolicy resolver fail-open). SEC-GAP-05 is closed **in the manifests**; whether it is closed on a cluster depends on that cluster's network plugin — see below.

#### Egress enforcement depends on the network plugin, and on *when* you ask

A NetworkPolicy is a request, not a mechanism. The plugin decides whether to honour it, and
several honour ingress rules while ignoring egress ones — the manifests then look right,
`kubectl get networkpolicies` lists the egress rules, and nothing enforces them. Verify the
control on any cluster before relying on it.

**How to ask, because the obvious probe gives the wrong answer.** A pod's egress chains are
programmed by the controller *after* the pod is running, not before it joins the network. On
the single-node k3s this platform runs on (k3s v1.33.13+k3s2, flannel vxlan, the embedded
controller) that gap has been measured between 4 and 25 seconds across runs. A probe that
calls out at container start therefore measures the gap and reports "not enforced" on a cluster where
egress is enforced perfectly well a moment later. An earlier measurement here concluded from
exactly such a probe that the plugin ignores egress rules altogether; that conclusion was
wrong, and this section replaces it.

So probe twice — once at start, once after the controller has caught up — and read the two
answers as two different facts:

```bash
kubectl run egress-probe -n "$NS" --restart=Never --quiet --attach --rm \
  --image=docker.io/busybox:1.38 --command -- sh -c '
    nc -w 3 -z 1.1.1.1 443 && echo OPEN-AT-START
    sleep 30
    nc -w 5 -z 1.1.1.1 443 && echo NOT-ENFORCED || echo enforced'
```

`NOT-ENFORCED` is the plugin ignoring egress and SEC-GAP-05 open on that cluster whatever the
manifests say; closing it needs a plugin that enforces egress, and Cilium and Calico both do.
`OPEN-AT-START` followed by `enforced` is the startup window below.

Two details that turn a correct policy into a false negative. Probe a raw address, not a
Service name: DNS resolution is itself egress, so a failed name lookup and an enforced policy
look identical. And if the namespace is meshed, annotate the probe `linkerd.io/inject:
disabled` with a `mesh.joinedcontext.com/opt-out-reason`, or the Linkerd inbound policy will
refuse it and read as enforcement that is not there.

`scripts/smoke.sh` in the deployment repository runs this on every `just dev-smoke` and prints
both facts, so neither has to be remembered.

#### The startup window: a new pod is unfiltered outbound for its first seconds

This is a real hole and it is currently accepted rather than closed. Between the moment a pod
starts running and the moment the embedded controller programs its egress chains, the pod may
call anywhere. Measured on the development cluster with the full policy set applied and all
twelve `default-deny-*` policies covering the pod: reachable immediately, twice out of two
attempts, and blocked by 25 seconds. A later run of the settling probe reported four
seconds, so the length varies and the number to trust is the one the current smoke run prints.

What it means in practice: **anything that runs at container start is outside the egress
policy.** An image entrypoint, an init container, a compromised sidecar phoning home in its
first second — none of them is stopped, and nothing in the manifests or in
`kubectl get networkpolicies` shows it. Ingress is not affected: the destination's chains were
programmed long before the caller existed, which is why the database probe in the smoke suite
has always been correct.

Why it is accepted for now: closing it means replacing the network plugin. k3s would start
with `--disable-network-policy` and a CNI that programs policy before the pod is admitted to
the network — Cilium is the candidate already raised for enforcing egress at all. That is a
cluster rebuild, not a manifest change, and it is the same decision as the plugin choice above
rather than a second one.

What holds it in the meantime: `just dev-smoke` measures the window on every run and holds it
to a ceiling. The pass line carries both numbers (`settled after 8s, ceiling 30s`), and a
window over the ceiling is a failed run naming the measured seconds and the allowed seconds,
so a controller that has got slower stops the smoke suite instead of printing a larger number
on a green line.

The ceiling is `JC_NETPOL_SETTLE`, in whole seconds, default 30, read by
`scripts/smoke.sh` in the deployment repository. Two values it refuses rather than accepts:
anything that is not a whole number of seconds, because a typo that read as zero or as
infinity would invert the check; and anything at or above 72 seconds, which is the probe's own
upper bound on how long it waits, so a larger ceiling could never be exceeded and would switch
the bound off while still printing one.

Raising it on a cluster is a decision, not a fix: the gap is accepted at 30 seconds, and a
cluster that needs more gets a line in `AI_shared_folder.md` saying what was seen and for how
long the larger number stands. Lowering it is free.

### Layer 7: Admission and Runtime Policy Enforcement

- **Inherited Baseline:** Cluster-scoped Kyverno policies (`civitas-core-deployment/components/runtime-policies/charts/runtime-policies/files/*`) validating Linkerd sidecar injection, inbound policy presence, and operator label protection. Shift-left validation runs in CI via `kyverno apply .ci/policies/base/`.
- **joinedcontext Enhancements:** Production environments operate Kyverno in `failureAction: Enforce`. Workloads that intentionally run unmeshed must declare the annotation `mesh.joinedcontext.com/opt-out-reason`. The CI pipeline evaluates both base and production policy sets against rendered manifests.
- **Configuration Keys:** `global.runtimePolicies.enabled: true`, `global.runtimePolicies.failureAction: "Enforce"`.
- **Verification Command:**

  ```bash
  kubectl get clusterpolicyreports,policyreports -A
  ```

- **Gaps Closed:** Enforces runtime invariants and closes SEC-GAP-04 label spoofing attack vectors.

### Layer 8: Service Mesh Mutual TLS Authorization

- **Inherited Baseline:** Linkerd service mesh enforcing `config.linkerd.io/default-inbound-policy: cluster-authenticated` (`civitas-core-deployment/defaults/environment/global.yaml`). Public ingress edges are governed by Linkerd `Server` resources (`components/apisix/charts/configuration/templates/linkerd-policy.yaml`).
- **joinedcontext Enhancements:** Every pod identity is cryptographically validated at admission and transport layers. Direct unmeshed pod-to-pod communication is rejected by the Linkerd proxy.
- **Configuration Keys:** `global.serviceMesh.enable: true`, `global.serviceMesh.type: "linkerd"`, `global.serviceMesh.defaultInboundPolicy: "cluster-authenticated"`.
- **Verification Command:**

  ```bash
  kubectl get ns prod -o jsonpath='{.metadata.annotations.config\.linkerd\.io/default-inbound-policy}{"\n"}'
  ```

- **Gaps Closed:** Enforces BSI TR-03187 AR-13 and CT-9 (cryptographic transport encryption and pod authentication).

### Layer 9: Ingress TLS and Certificate Automation

- **Inherited Baseline:** `cert-manager` automating TLS certificate issuance for public ingress routes (`civitas-core-deployment/components/apisix/values/apisix/base-values.yaml.gotmpl`).
- **joinedcontext Enhancements:** Ingress controllers enforce TLS 1.3 and TLS 1.2 with modern forward-secret ciphers. Ingress TLS certificates must cover the base domain and all configured service subdomains (`api.`, `portal.`, `idm.`).
- **Configuration Keys:** `global.ingress.clusterIssuer: "letsencrypt-prod"`, `global.ingress.ingressClass: "nginx"`.
- **Verification Command:**

  ```bash
  kubectl get certificate,clusterissuer -A
  ```

- **Gaps Closed:** Enforces BSI TR-02102 cryptographic cipher compliance and transport security.

### Layer 10: Identity Management Hardening

- **Inherited Baseline:** Keycloak deployed with PostgreSQL persistence, Argon2id password hashing, and ES256 token signing (`civitas-core-deployment/components/keycloak/values/config/base-values.yaml.gotmpl`).
- **joinedcontext Enhancements:** Tokens are verified by the receiving service (Portal, Context Gateway) against the Keycloak JSON Web Key Set (ES256, cached, refreshed in the background), eliminating synchronous HTTP token introspection; the APISIX edge forwards `Authorization` untouched because its `openid-connect` plugin cannot verify ES256 signatures ([10 §4](10-edge-routing-apisix.md)). Token audiences are verified against requested endpoints (`aud` claim verification).
- **Configuration Keys:** Realm configuration inline in `components/keycloak/values/config/base-values.yaml.gotmpl`.
- **Verification Command:**

  ```bash
  kubectl exec -n prod deploy/keycloak-app-keycloakx -- /opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password "$ADMIN_PASSWORD"
  ```

- **Gaps Closed:** SEC-GAP-06 (insecure plaintext introspection) and BSI TR-03187 AR-11/AUT-7.

### Layer 11: Edge API Gateway Lockdown

- **Inherited Baseline:** Apache APISIX operating as the central gateway. In the legacy platform, APISIX ran with an active Admin API on port 9180, an external etcd cluster, and curl-based route deployment jobs (`civitas-core-deployment/components/apisix/charts/configuration/templates/configuration.yaml`).
- **joinedcontext Enhancements:** APISIX operates strictly in standalone declarative file mode (ADR-N-007). The Admin API is disabled (`admin.enabled: false`) and etcd is eliminated. Route definitions are mounted into `/usr/local/apisix/conf/apisix.yaml` by `jcctl` with the mandatory terminal `#END` marker. The `serverless-pre-function` plugin sanitizes inbound headers, while the `response-rewrite` plugin injects HSTS, CSP, and X-Content-Type-Options headers.
- **Configuration Keys:** `apisix.apisix.deployment.role: "data_plane"`, `apisix.apisix.deployment.role_data_plane.config_provider: "yaml"`, `apisix.apisix.admin.enabled: false`.
- **Verification Command:**

  ```bash
  kubectl exec -n prod deploy/apisix -c apisix -- tail -n 5 /usr/local/apisix/conf/apisix.yaml
  ```

- **Gaps Closed:** SEC-GAP-01 (missing security headers), SEC-GAP-07 (exposed Admin API), and SEC-GAP-08 (etcd state drift).

### Layer 12: Context Gateway Policy Firewall and Artifact Storage

- **Inherited Baseline:** Legacy external OPA sidecars and Java AuthZ adapters queried PostgreSQL tables dynamically on every request (`civitas-core-deployment/components/authz/charts/authz/templates/opa-deployment.yaml`).
- **joinedcontext Enhancements:** The Context Gateway compiles `Policy` entities into an in-process Rust Policy Decision Point (PDP), rewriting incoming NGSI-LD query ASTs and clamping scopes natively (ADR-N-003, GW1–GW31). The artifact store (RustFS, S3 API) stores immutable rendered schemas and export bundles with compliance-mode object locking (ADR-N-015, PF-29–PF-33). Direct access to internal brokers or databases is physically blocked by network policies.
- **Configuration Keys:** `context-gateway.gateway.upstreamBrokerUrl: "http://context-broker:8080"`.
- **Verification Command:**

  ```bash
  curl -s -o /dev/null -w "%{http_code}" http://context-gateway.prod.svc.cluster.local:8080/health
  ```

- **Gaps Closed:** SEC-GAP-10 (multi-hop decision latency and privilege bleed).

## 3. Service Mesh Authorization Model

Service-to-service communication relies on Linkerd mutual TLS.

### Default Inbound Policy Mechanics

Every instance namespace is annotated with `config.linkerd.io/default-inbound-policy: cluster-authenticated`. Under this policy:

1. Inbound connections must present a valid TLS certificate issued by the Linkerd trust anchor.
2. The connecting client must originate from within the same Kubernetes cluster trust domain.
3. Unauthenticated plaintext traffic is terminated by the Linkerd proxy before reaching the application container.
4. Kubelet liveness and readiness health probes bypass mTLS checks automatically via Linkerd probe handling.

### Public Ingress Edge Policy Scoping

The APISIX gateway data plane receives external client traffic. Its inbound port (9080) must be explicitly authorized using a Linkerd `Server` resource (`components/apisix/charts/configuration/templates/linkerd-policy.yaml`):

```yaml
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: apisix-gateway
  namespace: prod
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: apisix
  port: 9080
  proxyProtocol: HTTP/1
  accessPolicy: all-authenticated
```

If the cluster Ingress Controller is meshed (annotated with `linkerd.io/inject: enabled`), the `accessPolicy` is set to `all-authenticated`. When operating with an unmeshed ingress controller (e.g. host-level ingress in virtual clusters), setting `global.serviceMesh.allowUnauthenticatedIngress: true` adjusts `accessPolicy` to `all-unauthenticated`. All other APISIX ports (control, metrics) remain governed by the namespace-wide `cluster-authenticated` policy.

## 4. Runtime Kyverno Policy Enforcement

In-cluster runtime security policies are deployed by the `runtime-policies` Helm chart. These policies validate state that exists only at runtime.

### Runtime Policy Inventory

Eleven `ClusterPolicy` objects, one per file in `components/runtime-policies/charts/runtime-policies/files/`. The failure action of every one of them is `global.runtimePolicies.failureAction`, `Enforce` by default and `Audit` for a rollout that should log before it blocks, so the column below says where it comes from rather than repeating one word eleven times.

| Policy name | Target | Invariant |
|---|---|---|
| `require-linkerd-sidecar` | Pod | A `linkerd-proxy` container exists, in the namespaces this deployment owns |
| `require-meshed-namespace-inbound-policy` | Namespace | `config.linkerd.io/default-inbound-policy` is non-empty, so a meshed namespace cannot be left on the opportunistic default |
| `justify-linkerd-inject-opt-out` | Pod | A Pod that disables injection declares `mesh.joinedcontext.com/opt-out-reason` |
| `exclude-acme-solver-from-mesh` | Pod | cert-manager's short-lived HTTP-01 solver Pod stays out of the mesh, so a challenge is answerable without weakening the namespace's inbound policy |
| `justify-api-token-access` | Pod | No service account token is mounted unless the Pod declares why in `security.joinedcontext.com/api-access-reason`. A mounted token turns one compromised container into a Kubernetes API client (TR-03187 AUT-3) |
| `restrict-cnpg-operator-pod-labels` | Pod | Only the CloudNativePG operator may carry its own `cloudnative-pg` and `postgresql` labels |
| `protect-operator-owned-labels` | Pod | An operator's labels cannot be claimed by another ServiceAccount |
| `require-run-as-nonroot` | Pod | `runAsNonRoot: true` on the pod or on every container |
| `require-run-as-non-root-user` | Pod | No `runAsUser: 0`, on the pod or on any container |
| `drop-all-capabilities` | Pod | Every container drops all Linux capabilities |
| `require-ro-rootfs` | Pod | `readOnlyRootFilesystem: true` on every container |

There is no Strimzi policy: the platform deploys no Kafka, so there is no Strimzi operator whose labels would need restricting.

The last four are the Pod Security Standards controls, vendored verbatim from
`github.com/kyverno/policies` at the ref pinned in `.ci/policies/vendor-upstream-policies.sh`
and deployed by the same chart, so the manifests CI evaluates and the manifests admission
evaluates are the same file. Two consequences worth stating.

They are scoped to the namespaces the platform owns, the instance namespace and the shared
operators namespace, passed to the chart as `podSecurity.namespaces`. Pod Security Standards
for the workloads this platform deploys is a control it can honour; enforcing them on the
namespaces the cluster distribution owns (`linkerd`, `traefik`, `cert-manager`,
`system-upgrade`) would block that distribution's own upgrades, and Kyverno's global
`resourceFilters` already exclude `kube-system`, `kube-public`, `kube-node-lease` and
`kyverno`.

`drop-all-capabilities` (upstream `best-practices/require-drop-all`) is the capabilities control rather than the stricter
`disallow-capabilities-strict` that CI applies to rendered manifests. The strict policy also
forbids adding capabilities, and Linkerd's `linkerd-init` container legitimately adds
`NET_ADMIN` and `NET_RAW` to program the pod's iptables, so enforcing it at admission would
reject every meshed pod on the cluster. Rendered manifests carry no init container of that
kind, which is why CI can hold the stricter line.

### Policy Inspection and Audit

When validating policies or auditing warnings, inspect the generated `ClusterPolicyReport`:

```bash
# Every policy and its current action, which is the first thing to check when a
# deploy is refused or, worse, is not:
kubectl get clusterpolicy -o custom-columns=NAME:.metadata.name,ACTION:.spec.rules[0].validate.failureAction

# What is failing, with the resource that failed it:
kubectl get clusterpolicyreport -o json \
  | jq -r '.items[].results[] | select(.result=="fail") | "\(.policy) \(.resources[0].namespace)/\(.resources[0].name)"'
```

## 5. Phase-1 Security Acceptance Checklist

Before promoting a platform deployment to production, execute the verification checklist below. Every test must pass with the expected result.

| Check ID | Hardening Layer | Verification Command | Expected Passing Result | Security Standard Reference |
|---|---|---|---|---|
| **CHK-01** | Pod Security | `kubectl get pods -n prod -o jsonpath='{range .items[*]}{.spec.securityContext.runAsNonRoot}{" "}{range .spec.containers[*]}{.securityContext.readOnlyRootFilesystem}{" "}{end}{"\n"}{end}'` | Every value printed is `true`. `runAsNonRoot` is read from the pod, where charts set it; a container may inherit it without repeating it. | BSI TR-03187 CT-1, CT-8 |
| **CHK-02** | Linux Capabilities | `kubectl get pods -n prod -o jsonpath='{range .items[*].spec.containers[*]}{.securityContext.capabilities.drop}{"\n"}{end}'` | Every container outputs `["ALL"]`. | BSI TR-03187 CT-1 |
| **CHK-03** | Service Accounts | `kubectl get pods -n prod -o custom-columns='A:.spec.automountServiceAccountToken,R:.metadata.annotations.security\.joinedcontext\.com/api-access-reason' --no-headers \| grep '<none>$' \| awk '{print $1}'` | Every value printed is `false`. The second column drops the pods that declare why they need the API, so what remains is the pods that never asked for a token. | BSI TR-03187 AUT-3 |
| **CHK-04** | Ingress Lockdown | `kubectl get netpol -n prod -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.policyTypes}{"\n"}{end}' \| grep '^default-deny'` | At least one `default-deny-*` policy, and every one of them lists `Ingress` and `Egress`. The deployment ships one per component, not a single `default-deny-all`. | BSI TR-03187 AR-16 |
| **CHK-05** | Service Mesh | `kubectl get pods -n prod --field-selector=status.phase=Running -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.initContainers[*].name}{" "}{.spec.containers[*].name}{"\n"}{end}'` | Every running pod names `linkerd-proxy`. The proxy is a native sidecar, so it is an init container; both lists are read. | BSI TR-03187 CT-9, AR-15 |
| **CHK-06** | Inbound mTLS | `kubectl get ns prod -o jsonpath='{.metadata.annotations.linkerd\.io/inject}{" "}{.metadata.annotations.config\.linkerd\.io/default-inbound-policy}{"\n"}'` | `enabled` followed by `cluster-authenticated` or `all-authenticated`: the namespace is meshed and every proxy in it refuses an unauthenticated inbound connection. | BSI TR-03187 AR-13 |
| **CHK-07** | Runtime Policies | `kubectl get clusterpolicyreport -o jsonpath='{.items[*].summary.fail}'` | Returns `0`. | BSI TR-03187 AR-14 |
| **CHK-08** | APISIX Admin Port | `kubectl get pods -n prod -l app.kubernetes.io/name=apisix -o jsonpath='{range .items[*].spec.containers[*].ports[*]}{.containerPort}{"\n"}{end}'` | The list is not empty and never contains `9180`. The APISIX image carries no `nc`, so the declared ports are the probe. | ADR-N-007, SEC-GAP-07 |
| **CHK-09** | APISIX Config Marker | `kubectl exec -n prod deploy/apisix -c apisix -- tail -n 1 /usr/local/apisix/conf/apisix.yaml` | Output is exactly `#END`. | ADR-N-007, Seam S7 |
| **CHK-10** | Header Stripping | `curl -s -I -H "NGSILD-Tenant: malicious" https://city.example.com/api/endpoint/test/ngsi-ld/v1/entities` | Inbound tenant header is stripped; response includes `x-request-id`. | GW20, SP-05 |
| **CHK-11** | Response Headers | `curl -s -I https://city.example.com/api/endpoint/test/ngsi-ld/v1/entities` | Headers contain `strict-transport-security` and `x-content-type-options: nosniff`. | SEC-GAP-01, W-23 |
| **CHK-12** | Database Encryption | `kubectl exec -n prod postgres-cluster-1 -c postgres -- psql -U postgres -c "SHOW ssl;"` | Output displays `on`. | BSI TR-03187 CT-9 |
| **CHK-13** | Keycloak Password | `kubectl get secret -n prod keycloak-admin-user -o jsonpath='{.data.password}' \| base64 -d \| wc -c` | Output is ≥ 32 characters. | BSI TR-03187 AUT-7 |
| **CHK-14** | Image Pinning | `kubectl get pods -n prod -o jsonpath='{range .items[*].spec.containers[*]}{.image}{"\n"}{end}' \| grep -v '@sha256:'` | Returns empty (all images pinned by digest). | BSI TR-03187 AR-4 |
| **CHK-15** | Production is not dev | `JC_PRODUCTION_ENVIRONMENT=<environment> pytest tests/test_production_is_not_dev.py` in `joinedcontext-deployment` | Every case passes: the render names its own `domain` and `orgDomain`, and carries no demo person, demo city account, demo feed, sslip.io host, `dev` namespace or realm, debug switch, open CORS, verbose error or written model key. The render itself stops on a placeholder domain or an unnamed runner project. | CC-73, CC-75 |

A person signs the checklist before the first production apply: their name, the date, the
commit of `joinedcontext-deployment` that was rendered, the environment's name, and CHK-01 to
CHK-15 each marked passed. The signed list goes into the description of the Change that
promotes the environment, where the approver reads it before approving. A check that did not
pass is not signed around: the promotion waits for it.

### Pods that may keep their API token

`justify-api-token-access`, deployed with the runtime policies, sets
`automountServiceAccountToken: false` on every Pod created in the namespaces this deployment
owns. Most upstream charts expose no such field, so the mutation is what puts it there; a Pod
that asks for a token explicitly is refused rather than quietly rewritten.

A workload that genuinely calls the Kubernetes API keeps its token by saying why, in the
annotation `security.joinedcontext.com/api-access-reason`. Two do today, both CloudNativePG:
the operator, which reconciles Cluster resources, and the instance manager in each database
pod, which watches its own Cluster and reports status back. The instance pods and the
operator's initdb Jobs are created by the operator, not by a chart, so the annotation reaches
them through the operator's `INHERITED_ANNOTATIONS`. CHK-03 reads the same annotation: an
exemption is visible in the checklist rather than hidden from it.

CHK-14 reads `spec.containers` and not `spec.initContainers` on purpose. On a meshed cluster
the proxy injector adds two init containers whose images are pinned by the Linkerd control
plane, not by this deployment. The manifests this deployment renders are gated on the way in
instead, where init containers are covered: `require-image-checksum` in `.ci/policies/base`
refuses a Pod whose containers, init containers or ephemeral containers name an image without
a digest, and the CloudNativePG `Cluster` resource, which no admission policy judges, is
checked by `tests/test_postgres_backup.py` in the deployment repository.

### What the two mesh rows read, and what stays unverified

CHK-05 and CHK-06 read the cluster with `kubectl` rather than with the Linkerd CLI, because
neither CLI command the rows used to name runs on this deployment.

`linkerd check --proxy` stops at its first hard failure, `× Gateway API CRDs are installed`.
The `linkerd-crds` chart installs those CRDs only when it is asked to, and this cluster does
not ask: nothing here routes through `HTTPRoute` or `GRPCRoute`. The proxies are running and
hold their certificates, but the check refuses to report on anything past that line.

`linkerd viz auth` is not a subcommand the CLI has. Edge-26.9.1 offers `authz`, `edges` and
`stat`, and the `linkerd-viz` namespace does not exist on this cluster at all. Viz carries its
own Prometheus, so installing it costs memory a single-node cluster has to find, which makes
it a decision for whoever owns the cluster.

The two rows read the same guarantee one step earlier, where a manifest puts it:

- Every running pod names `linkerd-proxy`, so no workload in the namespace speaks off the
  mesh (CHK-05). With native sidecars the proxy is an init container, which is why the row
  reads `initContainers` beside `containers`.
- The namespace is injected and pins `config.linkerd.io/default-inbound-policy` to an
  authenticated value, so each of those proxies refuses an inbound connection that carries no
  mesh identity (CHK-06). The `require-meshed-namespace-inbound-policy` policy refuses a
  namespace that is injected without the annotation, so the value cannot go missing quietly.

Neither row inspects live traffic. Certificate expiry, proxy version drift and the number of
hops that actually negotiated mTLS are not verified by the checklist while the Gateway API
CRDs and `linkerd-viz` are absent. Until they are installed, `linkerd check --proxy -n <ns>`
and `linkerd viz edges deployment -n <ns>` are the fuller picture and have to be read by hand.

## Related

- [Edge Routing Specification](10-edge-routing-apisix.md) — APISIX standalone declarative file mode and plugin chains.
- [Legacy Security Research](../Research/legacy-deployment-security-and-routing.md) — empirical research report on `civitas-core-deployment`.
- [Security Architecture](../Architecture/13-security.md) — conceptual trust zones and TR-03187 compliance framework.
- [Operations Runbooks](../Operations/01-runbooks.md) — step-by-step incident response and credential rotation procedures.
