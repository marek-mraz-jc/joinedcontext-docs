---
sidebar_position: 13
title: "Security Architecture & Trust Zones"
---

# Security Architecture & Trust Zones

joinedcontext platform is engineered to conform with BSI TR-03187 (Level 1+) for Urban Data Platforms. Security controls operate across strict trust boundaries with complete defense in depth.

```text
+---------------------------------------------------------------------------------------------------+
|                                       TRUST ZONE PERIMETER                                        |
|                                                                                                   |
|  [ ZONE 1: Public Untrusted Edge ]  (Internet, External Sensors, Public Consumers)                |
|         |                                                                                         |
|         v (TLS 1.3 Termination, Rate Limiting, DDoS Shield)                                      |
|  [ ZONE 2: Gateway DMZ (APISIX + Context Gateway PEP) ]                                           |
|         |                                                                                         |
|         v (Mandatory Linkerd mTLS with cluster-authenticated policy)                               |
|  [ ZONE 3: Core Data Plane (Antares Broker, PostgreSQL CNPG with RLS) ]                           |
|         ^                                                                                         |
|         | (Reconcile Loop / Scoped Service Accounts)                                              |
|  [ ZONE 4: Configuration & CI Plane (Gitea Forge, Gitea Actions, Portal reconciler) ]              |
|                                                                                                   |
|  [ ZONE 5: Workload Runners (Isolated Bento Streams & OpenHands Agent Sandboxes) ]               |
+---------------------------------------------------------------------------------------------------+
```

## 1. Trust Zone Model & Threat Assessment

| Trust Zone | Components | Threat Scenarios | Enforced Mitigations |
|---|---|---|---|
| **Zone 1: Public Edge** | Public DNS, Ingress | Volumetric DDoS, credential stuffing, URI tampering, TLS downgrade. | APISIX rate-limiting, TLS 1.3 ciphers only, IP connection throttling, WAF filtering. |
| **Zone 2: Gateway DMZ** | APISIX, Context Gateway (PEP + in-process PDP), Keycloak. FIWARE VCVerifier belongs to this zone in the identity design ([12 §1](12-identity-and-access.md)) and no environment deploys it yet. | Token forging, header spoofing, query injection, privilege bleed. | Strict JWT signature verification, mandatory tenant header stripping (GW20), antares-ql AST sanitization, fail-closed policy evaluation (GW5). |
| **Zone 3: Core Data Plane** | Antares Broker, PostgreSQL, TimescaleDB | Direct broker access, cross-tenant data leakage, SQL injection. | Broker is unroutable except via Context Gateway (R1); Linkerd mTLS enforced; row-level security on the broker's tenant tables, `ENABLE` and `FORCE`, with the session tenant pinned on every pooled connection (GW23, `antares-sql`). |
| **Zone 4: Config & CI Plane** | Gitea, Gitea Actions, the Portal's reconciler | Unauthorized commits, CI pipeline escape, unreviewed manifest merges. | Protected Git branches, CODEOWNERS validation (CC-41), Conftest policy checks, non-root runner isolation. |
| **Zone 5: Workload Runners** | Bento Stream Runners, Agent Runners | Malicious pipeline configs, indirect prompt injection, data exfiltration. | Runners execute with non-root security contexts (`readOnlyRootFilesystem`), NetworkPolicies block east-west traffic, agent elicitation prompts (CC-63). |

---

## 2. BSI TR-03187 Conformance Matrix

The following table documents conformance against BSI TR-03187 architectural requirements:

| Requirement ID | Requirement Description | Implementation in joinedcontext platform | Conformance Status |
|---|---|---|---|
| **AR-1** | Principle of Least Privilege | Dedicated Kubernetes ServiceAccounts per component; non-root execution (UID 1000); fail-closed policy evaluation (GW5); granular attribute-level masking. | **CONFORMANT** |
| **AR-2** | Deprecate Insecure Client Tech | Zero Flash/Java-applets/ActiveX; the Portal ships one HTML5 bundle and no plugin runtime. The edge sets HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` and `Referrer-Policy`; it sets no `Content-Security-Policy`, so the frontend's own script origins are unrestricted. | **PARTIAL** |
| **AR-3** | Prune Unused Dependencies | Rust single-binary compilation with `cargo-deny`; multi-stage Dockerfiles shipping zero build compilers or package managers. | **CONFORMANT** |
| **AR-4** | Version Pinning | All container images pinned by cryptographic SHA-256 digest; Rust dependencies locked via `Cargo.lock`; npm packages via `pnpm-lock.yaml`. | **CONFORMANT** |
| **AR-9** | Updatable Secrets | Secrets externalized into SOPS-encrypted files or OpenBao; automatic runtime rotation without image rebuilds. | **CONFORMANT** |
| **AR-11**| Approved Cryptography | BSI TR-02102 compliant ciphers: TLS 1.3 with AES-GCM and ChaCha20-Poly1305; Ed25519 and ECDSA P-256 signing keys. | **CONFORMANT** |
| **AR-12**| Standard Frameworks for Security | OIDC via Keycloak; `Policy` entities evaluated by the gateway's tested PDP crate; Linkerd for service-to-service mTLS; standard cryptography crates (`ring`, `rustls`). | **CONFORMANT** |
| **AR-15**| Transport Encryption | Mandatory Linkerd service mesh mTLS with `defaultInboundPolicy: cluster-authenticated` enforced across all pods. | **CONFORMANT** |
| **AR-16**| Trust Zone Isolation | Namespace and NetworkPolicy default-deny barriers between Ingress, Gateway, Broker, and Configuration planes. | **CONFORMANT** |

---

## 3. Secrets Management Architecture (S6, CC-06)

- **No Plaintext in Git:** Committing unencrypted secrets to the Org Repository is strictly prohibited (CC-06) and blocked by pre-commit hooks and CI secret scanners.
- **SOPS + Age Encryption (Default):** For organisational deployments, secrets are stored in Git as SOPS-encrypted files using `age` public keys. Only the Portal holds the corresponding private key, read from the file `JC_PORTAL_SOPS_AGE_KEY_FILE` names, and it decrypts a credential while it reconciles the sync wave that needs it.
- **OpenBao Integration (Regional Scale):** the Portal resolves a `secretRef` through OpenBao (the MPL 2.0 fork of Vault) when `JC_PORTAL_OPENBAO_ADDR`, `JC_PORTAL_OPENBAO_ROLE` and `JC_PORTAL_OPENBAO_JWT_PATH` name one, authenticating with its own Kubernetes ServiceAccount token. A manifest names the reference (`secretRef: db-password`) either way, so a deployment moves between SOPS and OpenBao without a manifest changing. No environment in `joinedcontext-deployment` deploys OpenBao today; the SOPS path is what runs.

---

## 4. End-to-End Audit Trail (CC-44, CC-58)

Three logs together answer who changed what, who read what, and who signed in. None of them is signed or write-once, so each is as trustworthy as the system that keeps it — Gitea, the gateway's log sink, Keycloak's database:

1. **Configuration Audit (Git):** Every platform modification is permanently recorded in Gitea Git commits, with the merge approvers and, for a commit an agent proposed, the `Co-Proposed-By:` trailer naming the person whose run it was (AG-18, `agent-proxy` `routes/forge.rs`). Nothing signs these commits: the record is Gitea's, and a reader trusts the forge rather than a signature.
2. **Access & Decision Logs (Context Gateway):** The Context Gateway emits structured JSON audit events to `stdout` capturing caller identities, requested URIs, decision reasons, and matched `Policy` IDs (GW6). Sensitive headers and credentials are automatically masked.
3. **Identity Audit (Keycloak):** Keycloak logs all login attempts, MFA challenges, token exchanges, and administrative user modifications to persistent audit tables.

The Activity stream of [09 §6](09-portal.md#6-activity-what-is-happening) is a readable
projection of these three logs and of the OpenTelemetry traces, never a fourth one. It is
derived, it is trimmed after seven days, and where it disagrees with a log the log is right
(OPS-49).

## 5. Inherited controls and their changes

The joinedcontext platform reuses the battle-tested infrastructure layers from the legacy platform (`civitas-core-deployment`) while modernizing the application and policy enforcement layers:

- **Cluster Operators and Infrastructure:** The CloudNativePG operator and Linkerd service mesh are inherited directly. Kyverno ClusterPolicies are retained and expanded with mandatory `failureAction: Enforce` in production.
- **Namespace Preparation:** The legacy `prepare` hook is retained to automate namespace creation, Linkerd proxy injection annotations, and in-cluster CA certificate distribution.
- **Cryptographic Secrets:** The in-tree `secrets-generator` chart is retained for random cluster-internal bootstrap secrets. Declarative configuration secrets are modernized to use SOPS with age encryption and OpenBao (ADR-N-012).
- **Network Boundaries:** The legacy network policies defined ingress-only default-deny rules. The joinedcontext platform extends network policy automation to dual Ingress and Egress default-deny across all namespaces, backed by a fail-closed namespace resolver.
- **Edge API Gateway:** Apache APISIX is retained for edge routing and TLS termination, but transformed from a mutable, etcd-dependent architecture to a declarative standalone file mode (`apisix.yaml`) rendered by `jcctl` (ADR-N-007). Response security headers and strict header sanitization are enforced at the gateway.
- **Policy Enforcement:** The legacy multi-hop authorization chain (APISIX calling external OPA calling Spring Boot AuthZ repository calling PostgreSQL) is completely replaced by the Context Gateway with an in-process Rust Policy Decision Point (PDP) executing native AST query rewriting (ADR-N-003).
- **Identity Provider:** Keycloak is retained as the standard OIDC and OID4VCI provider. Insecure HTTP token introspection is replaced by JWKS signature validation (ES256) inside the receiving services, the Portal and the Context Gateway; the APISIX edge forwards tokens without verifying them ([Deployment 10 §4](../Deployment/10-edge-routing-apisix.md)).
- **Workload Execution:** Legacy Apache NiFi and Kafka event buses are replaced by lightweight Bento pipeline runners operating in sandboxed streams mode with strict network egress controls (ADR-N-006).

## 6. The Portal's internal listener (PF-46, AG-52)

The Portal binds a second listener beside the one the edge routes. Nothing of the public URL scheme
reaches it, and the NetworkPolicy of the `portal` component admits only the workloads that need it.
That policy is the second control and never the only one: every route of this listener names the
identity it accepts, because a pod that reached the port through a policy mistake must still be
refused by the route.

| Route | Caller | What authenticates it |
|---|---|---|
| `POST /internal/agent-runs/…` (the run callbacks) | the credential proxy | a bearer the Portal and the proxy share, from the proxy's own secret. The one credential between cluster services that is not an identity; it is to become one. |
| `POST /internal/pipeline-tests/{id}` | the pipeline test harness | the `{id}` itself: 130 random bits minted for one test, held by the harness the Portal started and by nobody else. A message naming a test that is not running is dropped. |
| `GET /internal/previews` | the Context Gateway | a Keycloak ServiceAccount token: issuer, audience `portal-internal`, and `azp` naming the gateway's own client. |

A workload's token comes from `client_credentials` on its own confidential client, with an audience
mapper that binds the token to `portal-internal` — the pattern the endpoint surface already uses to
bind a token to one endpoint slug. No static key is added for a new caller of this listener, and a
caller that presents no token is refused before the handler reads the body.

- **PF-46** [portal][identity] — every route of the internal listener names the identity it accepts;
  a NetworkPolicy is the second control, never the only one.
- **AG-52** [agents][identity] — the run callbacks carry the proxy's bearer, and the proxy presents
  the run's own mesh identity to reach them.

## Related

- [Security Hardening & Phase-1 Baseline](../Deployment/08-security-hardening.md) — actionable deployment hardening layers and verification commands.
- [Edge Routing & APISIX Standalone Specification](../Deployment/10-edge-routing-apisix.md) — technical specification of APISIX standalone routing and plugin chains.
- [Legacy Security Research](../Research/legacy-deployment-security-and-routing.md) — detailed research report analyzing the legacy security posture.
- [ADR-N-003 Context Gateway in Rust](../Decisions/adr-n-003-context-gateway-in-rust.md) — decision establishing the in-process PEP/PDP architecture.
