---
sidebar_position: 10
title: "Operations, Deployment & Reliability"
---

# Operations, Deployment & Reliability

Family **OPS** (OPS-01…OPS-52). Owning chapter: [13-security.md](../Architecture/13-security.md). Verified by: [05-deployment-and-performance-tests.md](../Testing/05-deployment-and-performance-tests.md).

This chapter specifies the operational, deployment, and Site Reliability Engineering (SRE) requirements for operating the federated digital twin platform in production Kubernetes environments.

The family runs OPS-01…OPS-53 with two holes: no OPS-24 and no OPS-25 were ever issued.

## 1. Helmfile Component Architecture

- **OPS-01** — The platform deployment MUST be managed using Helmfile with modular component definitions adhering to the structure in `joinedcontext-deployment`:
  - `components/<component>/component.yaml` — Component metadata, validated against `component.schema.json`.
  - `components/<component>/charts.yaml` — Pinned chart versions.
  - `components/<component>/images.yaml` — Pinned image tags and digests.
  - `components/<component>/values/` — Environment values.
- **OPS-02** — Environment-specific overrides MUST reside strictly within the `deployment/` directory. Upstream default configurations in `defaults/` and `components/` MUST remain unmodified.
  > Note: `deployment/` is the operator's own checkout, not a directory of this repository: values live in `deployment/environments/<env>/`, and `.ci/example-deployments/` holds the layout. The defaults they override are in `defaults/environment/global.yaml`.
- **OPS-03** — The platform MUST support single-namespace deployment (`global.singleNamespace: true`) and multi-namespace deployment (`global.singleNamespace: false`).

## 2. Deployment Profiles and Resource Governance

- **OPS-04** — The platform MUST provide two distinct deployment profiles via `global.profile`:
  - `development`: Minimal resource requests, single replicas, zero autoscaling, relaxed disruption budgets.
  - `production`: High availability (≥ 2 replicas), PodDisruptionBudgets, HorizontalPodAutoscalers, strict Linkerd mTLS, and Enforce-mode runtime policies.
- **OPS-05** — All production workloads MUST declare explicit CPU and memory resource requests and limits. Workloads omitting resource declarations MUST be rejected by admission policies.

## 3. High Availability and Disruption Tolerances

- **OPS-06** — Stateless core components (Context Gateway, Portal API, Portal UI, APISIX, Gitea) MUST run with a minimum of 2 replicas in production.
- **OPS-07** — Every production deployment MUST define a `PodDisruptionBudget` ensuring `minAvailable: 1` during node draining and rolling updates.
- **OPS-08** — Rolling updates MUST configure `maxUnavailable: 0` and `maxSurge: 25%` to guarantee zero-downtime service upgrades.

## 4. Disaster Recovery, Backup, and Restoration

- **OPS-09** — PostgreSQL clusters managed by CloudNativePG (CNPG) MUST configure automated continuous WAL archiving and daily full backups to S3-compatible object storage.
- **OPS-10** — Point-in-Time Recovery (PITR): The database backup subsystem MUST support recovery to any arbitrary timestamp within a 30-day retention window.
- **OPS-11** — Declarative State Recovery: In the event of catastrophic cluster loss, restoring the platform MUST require only:
  1. Restoring the PostgreSQL database cluster (for live entity state and audit logs).
  2. Restoring the organization's configuration repository into the instance's forge from its mirror, which is the
     organization's whole configuration export (CC-49); no bundle is built and nothing is copied by hand.
  3. Applying that repository via `jcctl apply` per CC-50.
  4. Reconnecting DNS to the ingress controller.
- **OPS-12** — Restoration drills MUST be executed and verified automatically in CI/CD on a scheduled monthly cadence.

## 5. Blue/Green Platform Upgrades

- **OPS-13** — Major version platform upgrades (e.g., upgrading the context broker engine or gateway core) MUST support blue/green deployment topologies (CC-51).
- **OPS-14** — The new version environment ("green") MUST be populated by replaying the organization Git repository using `jcctl apply` against the green broker, verifying zero plan diff, and executing automated smoke tests before switching gateway traffic.

## 6. Observability, Metrics, and Service Level Objectives

- **OPS-15** — All components MUST write structured JSON logs exclusively to `stdout` and `stderr`. Writing logs to local container filesystems is prohibited.
- **OPS-16** — Every core component MUST expose Prometheus metrics on a `/metrics` HTTP endpoint. ServiceMonitor and PodMonitor resources MUST be provided for automated discovery.
- **OPS-17** — Distributed tracing headers (`traceparent`, W3C Trace Context) MUST be propagated through APISIX, Context Gateway, Context Broker, and Bento pipelines.
- **OPS-18** — Service Level Objectives (SLOs): In production profile, the platform MUST meet or exceed the following targets:
  - **Availability**: 99.9% uptime for Context Gateway and Endpoint read/write APIs.
  - **Ingress Latency**: P95 latency ≤ 50 ms for cached entity reads.
  - **Notification Latency**: P95 end-to-end delivery latency ≤ 500 ms from entity update to subscriber webhook.

## 7. Air-Gapped and Sovereign Infrastructure

- **OPS-19** — The entire platform MUST be deployable in completely air-gapped environments with no outbound Internet access.
- **OPS-20** — Container images MUST be mirrorable to private container registries, and Helm charts MUST be packageable as local archive files.
- **OPS-21** — The platform MUST NOT include telemetry calls, tracking scripts, or mandatory external SaaS dependencies.
- **OPS-22** — All cryptographic algorithms and TLS parameters utilized for platform communication MUST conform to BSI TR-02102 recommendations.
- **OPS-23** — Incident Runbooks: Every core component MUST provide documented troubleshooting runbooks covering pod crash recovery, database failover, broker unresponsiveness, and certificate renewal.

## 8. Deployment Security Baseline

- **OPS-26** [S] — All platform namespaces MUST enforce a default-deny NetworkPolicy for both Ingress and Egress traffic, permitting communication exclusively through explicit per-component allow rules.
- **OPS-27** [S] — Every workload container MUST run under a dedicated Kubernetes ServiceAccount with `automountServiceAccountToken: false`, unless direct Kubernetes API communication is explicitly required by the component architecture.
- **OPS-28** [S] — Container images deployed across all environments MUST be pinned to immutable SHA-256 cryptographic digests with `pullPolicy: IfNotPresent`; mutable tags and `latest` references MUST be rejected during manifest validation.
- **OPS-29** [S] — Kyverno Pod Security Standard baseline policies and platform runtime policies MUST operate in `failureAction: Enforce` in production profiles; any workload exemption MUST be documented via the `mesh.joinedcontext.com/opt-out-reason` annotation, which the `justify-linkerd-inject-opt-out` policy reads.
- **OPS-30** [S] — Inter-service communication across all instance namespaces MUST be authorized and encrypted via Linkerd mutual TLS under a `cluster-authenticated` inbound policy, with the public APISIX data-plane ingress port explicitly scoped via a Linkerd `Server` resource.
- **OPS-31** [S] — The APISIX Admin API MUST be physically disabled (`admin.enabled: false`) with etcd removed from core; routing configurations MUST be rendered exclusively by `jcctl` into declarative standalone `apisix.yaml` files and validated prior to ConfigMap deployment.
- **OPS-32** [S] — The edge gateway MUST unconditionally sanitize inbound request headers by stripping `NGSILD-Tenant`, `X-Userinfo`, `X-Access-Token`, `X-Allowed-Scope-Ids`, `X-Endpoint-Slug`, `X-Consumer-Identity`, and untrusted `X-Forwarded-*` headers before forwarding traffic to upstream services.
- **OPS-33** [S] — Token authentication MUST happen in the receiving service (Portal, Context Gateway): OpenID Connect JWT signatures (ES256) validated against the Keycloak JSON Web Key Set, cached and refreshed in the background, no per-request introspection. The edge gateway MUST forward `Authorization` untouched and MUST NOT be configured as a token verifier (its `openid-connect` plugin cannot verify ES256); a route whose upstream does not verify tokens MUST NOT be exposed as authenticated.
- **OPS-34** [S] — The edge gateway MUST inject HTTP security headers on all outbound responses via the `response-rewrite` plugin, including HSTS with preload, `X-Content-Type-Options: nosniff`, `X-Frame-Options`, `Referrer-Policy`, Content Security Policy, and `Cache-Control: no-store` on authenticated API endpoints.
- **OPS-35** [S] — The edge gateway MUST enforce tiered rate limiting across all routes using distinct rate-limiting classes for anonymous public traffic, authenticated API consumers, and high-throughput telemetry ingestion pipelines.
- **OPS-36** [S] — Public TLS listeners MUST require TLS 1.2 or higher with BSI TR-02102 approved ciphers and MUST enforce HTTP Strict Transport Security with a minimum duration of one year (`max-age=31536000`).
- **OPS-37** [S] — Platform secrets MUST be generated once using cryptographically secure random generators with persistent retention flags, encrypted at rest via SOPS with age or OpenBao, and rotated according to an enforced lifecycle schedule.
- **OPS-38** [S] — The NetworkPolicy template engine MUST resolve cross-component namespace references in a fail-closed manner, rejecting manifest rendering if a targeted component namespace cannot be resolved unambiguously.
- **OPS-39** [S] — Unencrypted plaintext HTTP communication between platform components MUST NOT occur outside the Linkerd service mesh trust boundary.
- **OPS-40** [S] — CI/CD pipelines MUST execute shift-left policy validation using `kyverno apply` against rendered Helmfile manifests before any pull request or deployment merge is admitted.
- **OPS-41** [S] — Every container image the platform builds MUST ship with a CycloneDX Software Bill of Materials (SBOM) attested with `cosign attest --type cyclonedx` to the digest it is signed and pushed under. No vulnerability remediation deadline is promised until the platform runs in production under a support contract.
- **OPS-42** [S] — Platform audit logs from the Context Gateway, Keycloak, and Gitea MUST be persisted in append-only storage with a minimum retention period of 90 calendar days.
- **OPS-43** [S] — An end-to-end penetration test and threat modeling audit MUST be successfully completed and remediated prior to exposing public Endpoints in production environments.
- **OPS-44** [S] — Ephemeral test environments and preview sandboxes MUST define automated Time-To-Live (TTL) expiration limits not exceeding 14 calendar days, with deletion cascading cleanly to all provisioned resources.
- **OPS-45** [S] — Emergency revocation of a compromised credential, service account, or security policy MUST propagate to all Context Gateway and edge enforcement points within a hard bound of 5 seconds.

## 9. Branding and Naming

- **OPS-46** — Every name, colour, logo, contact and default licence an installation shows MUST come from one `global.branding` block in the environment's values; no chart, image, template or user-facing string may carry a city-specific literal.
- **OPS-47** — The CKAN theme MUST render any branding block, holding templates and colour tokens only, so a second installation reuses it without a file change (OPS-46).
- **OPS-48** [S] — An activity event MUST carry only attributes named on the collector's allow-list, and MUST NOT carry a request body, a header, a credential or an entity attribute value; a failing pipeline sample MUST be masked by its Data Model's own rules before it is emitted.
- **OPS-49** — The activity store MUST be derived from the audit trail, the structured logs and the OpenTelemetry traces and MUST NOT be a second source of truth, so trimming it after seven days of events and ninety days of counters loses nothing those sources still hold.

## 10. The Action Inspector

- **OPS-50** [H] — The conversation with the assistant MUST show every `tool` event as an expandable step: the summary line carries the tool's name, its status and its duration; the expanded step shows the input, the output or the error and the diff as text blocks, never as markup (AG-56); a failed step offers "ask the assistant to fix it", which sends the error back into the run as a message, and every step offers its trace as copyable JSON.

## 11. Readiness

- **OPS-51** [H] — The Portal MUST answer `GET /api/v1/ready` with 503 until its mirror holds the configuration repository (the first successful sync of this replica, leader or follower) and 200 afterwards, MUST keep `GET /api/v1/health` unconditional for liveness, and its readiness probe MUST read the ready route, so traffic never reaches a replica that would list an empty project or refuse a check against a project it has not loaded; a follower loads the repository read-only (no stream, app or roles convergence), so a rolling update never waits on the leader's lock, and the answer carries nothing but the state (OPS-06, MF-04).

## 12. Vulnerability reporting

- **OPS-52** [S] — Every host the edge serves MUST answer `GET /.well-known/security.txt` (RFC 9116) itself, as `text/plain; charset=utf-8`, with the installation's `Contact` and an `Expires` at most a year ahead, from `global.securityTxt`; a production render without both MUST fail, and the render test of `dev` MUST fail 30 days before its `Expires` passes, so the file is renewed before a reporter reads an expired one (T-1721).

## 13. Validation Health

- **OPS-53** [H][S] — The Portal MUST show the organization's administrators one page, `/organization/health`, with a row per validation check (deployment drift and supply chain, conformance, the authorization matrix, performance budgets, backup and restore, the live sweep and the others that publish): its state (green, red, stale when it missed two of its runs, unreadable), its last run, its verdict counts, a seven-day trend and the failing results with the task each one filed, under one summary line; a result MUST carry only check keys, titles, verdicts, counts and task ids, never a detail, an evidence path, a secret or a person's data, and anyone who is not an administrator of the organization MUST be refused.

## Traceability

| Requirements | Section | Architecture | Tests |
|---|---|---|---|
| OPS-01…OPS-03 | Helmfile Component Architecture | [13-security.md](../Architecture/13-security.md) | [05-deployment-and-performance-tests.md](../Testing/05-deployment-and-performance-tests.md) |
| OPS-04…OPS-05 | Deployment Profiles and Resource Governance | [13-security.md](../Architecture/13-security.md) | [05-deployment-and-performance-tests.md](../Testing/05-deployment-and-performance-tests.md) |
| OPS-06…OPS-08 | High Availability and Disruption Tolerances | [13-security.md](../Architecture/13-security.md) | [05-deployment-and-performance-tests.md](../Testing/05-deployment-and-performance-tests.md) |
| OPS-09…OPS-12 | Disaster Recovery, Backup, and Restoration | [13-security.md](../Architecture/13-security.md) | [05-deployment-and-performance-tests.md](../Testing/05-deployment-and-performance-tests.md) |
| OPS-13…OPS-14 | Blue/Green Platform Upgrades | [13-security.md](../Architecture/13-security.md) | [05-deployment-and-performance-tests.md](../Testing/05-deployment-and-performance-tests.md) |
| OPS-15…OPS-18 | Observability, Metrics, and Service Level Objectives | [13-security.md](../Architecture/13-security.md) | [05-deployment-and-performance-tests.md](../Testing/05-deployment-and-performance-tests.md) |
| OPS-19…OPS-23 | Air-Gapped and Sovereign Infrastructure | [13-security.md](../Architecture/13-security.md) | [05-deployment-and-performance-tests.md](../Testing/05-deployment-and-performance-tests.md) |
| OPS-26…OPS-45 | Deployment Security Baseline | [13-security.md](../Architecture/13-security.md) | [05-deployment-and-performance-tests.md](../Testing/05-deployment-and-performance-tests.md) |
| OPS-46…OPS-47 | Branding and Naming | [../Deployment/12-branding-and-naming.md](../Deployment/12-branding-and-naming.md) | [05-deployment-and-performance-tests.md](../Testing/05-deployment-and-performance-tests.md) |
| OPS-48…OPS-49 | Activity pipeline | [../Deployment/05-monitoring-logging.md#5-the-activity-pipeline](../Deployment/05-monitoring-logging.md#5-the-activity-pipeline) | [05-deployment-and-performance-tests.md](../Testing/05-deployment-and-performance-tests.md) |
| OPS-50 | The Action Inspector | [../Architecture/19-agent-runner.md#7-attribution-and-audit](../Architecture/19-agent-runner.md#7-attribution-and-audit) | [03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| OPS-51 | Readiness | [../Architecture/09-portal.md#1-portal-api-specification](../Architecture/09-portal.md#1-portal-api-specification) | [05-deployment-and-performance-tests.md](../Testing/05-deployment-and-performance-tests.md) |
| OPS-52 | Vulnerability reporting | [../Deployment/10-edge-routing-apisix.md](../Deployment/10-edge-routing-apisix.md#2-public-url-surface-and-path-based-route-table) | [06-security-tests.md](../Testing/06-security-tests.md) |
| OPS-53 | Validation Health | [../API/01-portal-api.md#25-validation-health-ops-53](../API/01-portal-api.md#25-validation-health-ops-53) | [03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |

## Related

- [Security Hardening & Phase-1 Baseline](../Deployment/08-security-hardening.md) — implementation guide for the deployment security baseline.
- [Edge Routing & APISIX Standalone Specification](../Deployment/10-edge-routing-apisix.md) — declarative edge gateway configuration.
- [Legacy Security Research](../Research/legacy-deployment-security-and-routing.md) — empirical research report on legacy security controls.
- [Requirements Index](00-index.md) — platform requirements taxonomy and overview.
