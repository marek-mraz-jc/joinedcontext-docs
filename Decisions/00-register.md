---
sidebar_position: 1
title: "Architecture Decision Register"
---

# Architecture Decision Register

This register records all foundational Architecture Decision Records (ADRs) governing the next-generation federated digital twin platform (`ADR-N-001` through `ADR-N-030`), along with explicit status mapping of legacy decision records from preceding platform generations.

## 1. Target Architecture Decisions (`ADR-N` Series)

| ADR ID | Title | Status | Date | Decision Summary |
|---|---|---|---|---|
| [ADR-N-001](adr-n-001-rust-typescript-stack.md) | Standardize Core Stack on Rust and React/TypeScript | **Accepted** | 2026-09-05 | Replaces custom Java microservices with Rust (Axum, SQLx) and React 19/TypeScript. Retains Keycloak as an external OSS identity provider. |
| [ADR-N-002](adr-n-002-context-space-and-endpoint-model.md) | Context Space and Multi-Representation Endpoint Model | **Accepted** | 2026-09-05 | Implements `/cs/{space}` base and `/api/endpoint/{endpointSlug}` opaque endpoints with strict representation parity across NGSI-LD, GeoJSON, OGC, and STA. |
| [ADR-N-003](adr-n-003-context-gateway-in-rust.md) | Context Gateway in Rust with Embedded Policy Evaluation | **Accepted** | 2026-09-05 | Develops a unified Context Gateway in Rust using `antares-ql` for AST query rewriting and embedded `Policy` evaluation; rejects Pingora. |
| [ADR-N-004](adr-n-004-configuration-as-code-and-gitea.md) | Configuration-as-Code Configuration Plane with Gitea | **Accepted** | 2026-09-05 | Adopts declarative Git-driven configuration plane (Approach A) using Gitea, superseding message-bus configuration sync. |
| [ADR-N-005](adr-n-005-reconciler-jcctl-in-rust.md) | Reconciler `jcctl` in Rust with Minijinja Templating | **Accepted** | 2026-09-05 | Builds `jcctl` CLI and server in Rust using Minijinja sandboxed templates and JSON-LD structural diffing; supersedes Go/CUE. |
| [ADR-N-006](adr-n-006-bento-pipelines-supersede-nifi.md) | Bento Pipelines Superseding Apache NiFi | **Accepted** | 2026-09-05 | Adopts Bento (`warpstreamlabs/bento`, MIT) in resident streams mode and scheduled CronJobs, reversing legacy NiFi selection. |
| [ADR-N-007](adr-n-007-apisix-standalone-no-etcd.md) | Apache APISIX in Declarative Standalone Mode | **Accepted** | 2026-09-05 | Operates APISIX in standalone file mode (`apisix.yaml`), eliminating etcd cluster dependencies and the mutable Admin API. |
| [ADR-N-008](adr-n-008-antares-default-broker.md) | Antares as Default Context Broker | **Accepted** | 2026-09-05 | Selects Antares (Rust) as default NGSI-LD broker; maintains drop-in compatibility for Scorpio and Stellio via vanilla CIM 009. |
| [ADR-N-009](adr-n-009-mcp-surfaces-and-agent-lanes.md) | Model Context Protocol Surfaces and Agent Governance | **Superseded** | 2026-09-05 | Deploys dual MCP surfaces (Data MCP and Config MCP) with Green/Yellow/Red approval lanes and interactive elicitation prompts. |
| [ADR-N-010](adr-n-010-linkml-data-models.md) | Canonical Data Modeling with LinkML | **Accepted** | 2026-09-05 | Adopts LinkML as single modeling truth, generating JSON Schema draft-07 contracts and JSON-LD `@context`; supersedes JSONata. |
| [ADR-N-011](adr-n-011-maplibre-deckgl-dashboards.md) | MapLibre and deck.gl In-Portal Visualization Engine | **Accepted** | 2026-09-05 | Integrates MapLibre GL JS and deck.gl (<50k feature threshold) for native dashboards; moves Superset and Masterportal to addons. |
| [ADR-N-012](adr-n-012-secrets-sops-openbao.md) | Secrets Management via SOPS and OpenBao | **Accepted** | 2026-09-05 | Employs SOPS+age for localized deployments and OpenBao (MPL 2.0) for multi-tenant deployments; manifests store named references only. |
| [ADR-N-013](adr-n-013-multi-language-model.md) | Multilingual Architecture with ICU MessageFormat | **Accepted** | 2026-09-05 | Enforces four core locales (sk, en, de, cs) via versioned ICU bundles in Git and language maps on all manifest metadata. |
| [ADR-N-014](adr-n-014-agent-runner-openhands-optional.md) | Optional Agent Runner Addon with OpenHands SDK | **Accepted** | 2026-09-05 | Packages OpenHands Software Agent runtime as an optional deployment addon enforcing `ConfirmRisky` human-in-the-loop policies. |
| [ADR-N-015](adr-n-015-artifact-store-rustfs.md) | S3-compatible Artifact Store with RustFS as Default | **Accepted** | 2026-09-05 | Rendered schema artifacts (LinkML, JSON Schema, SHACL, OWL, RDF), compiled mappings, dumps, exports and app builds live in one object-locked S3 store; RustFS default, any S3 service pluggable. |
| [ADR-N-016](adr-n-016-data-space-connector.md) | Data Space Connector behind the Endpoint Layer | **Accepted** | 2026-09-05 | DSP/DCP connector addon negotiates ODRL agreements that compile into Policy entities and agreement-bound Endpoint tokens; never a second data plane; post-MVP, engine chosen when a partner appears. |
| [ADR-N-017](adr-n-017-fullstack-apps-oauth2-proxy-builder-agent.md) | Full-Stack Apps behind oauth2-proxy, built by the Builder Agent | **Accepted** | 2026-09-05 | Agent-built apps are Rust `axum` + React images with an oauth2-proxy sidecar doing the Keycloak login; the Agent Runner `builder` profile (coding tools, allow-listed internet) runs build, test, preview and repair without a person. |
| [ADR-N-018](adr-n-018-token-verification-in-the-peps.md) | Bearer tokens are verified in the PEPs, not at the edge | **Accepted** | 2026-09-06 | The realm signs ES256 and APISIX's `openid-connect` plugin cannot verify EC signatures at any version, so the Portal and the Context Gateway verify issuer, signature, audience, `exp` and `nbf` against a cached realm JWKS; the edge keeps routing, rate limiting and header hygiene and a route without a verifying upstream stays closed. |
| [ADR-N-019](adr-n-019-login-at-the-edge-apisix-openid-connect.md) | Login at the edge: APISIX openid-connect for the Portal and every app, Portal on portal.{domain} | **Accepted** | 2026-09-07 | One login front: the `openid-connect` plugin in session mode on the Portal routes (`portal.{domain}`) and on every app route, one confidential `edge` client with RS256 tokens, identity in `X-Userinfo`/`X-Access-Token`; no sidecar, no login code in apps, generated ones included. |
| [ADR-N-020](adr-n-020-agent-runner-and-credential-proxy.md) | The Agent Runner and the Credential-Free Internal Proxy | **Accepted** | 2026-09-12 | Workspaces hold zero secrets; all upstream tokens and keys are injected per request by `jc-agent-proxy` from hashed run tickets, enforcing strict path and branch scoping. |
| [ADR-N-021](adr-n-021-one-operation-registry-behind-ui-api-assistant-and-mcp.md) | One Operation Registry Behind the UI, the API, the Assistant, the Agents and MCP | **Proposed** | 2026-09-13 | Every action is a registered operation with one function, one schema and one permission check; the REST route, the assistant tool, the agent tool and a Portal MCP server at `/api/v1/mcp` are adapters; drafts are server-side state every window shares; every check answers one Verdict and a strict installation proposes nothing without a fresh green one. |
| [ADR-N-022](adr-n-022-generated-applications-are-code-on-the-app-sdk.md) | Generated Applications Are Code on the App SDK, Not a Specification for a Renderer | **Accepted** | 2026-09-14 | A `static` application is React code and serverless JavaScript functions on `@joinedcontext/sdk`, starting from a complete tested template app (pages, forms, filters, ECharts and Recharts charts, MapLibre and deck.gl maps, functions) with types rendered from LinkML by `gen-typescript`; functions run in a QuickJS runtime with the caller's grants; one shot with every file writes the first version, an editing agent with file tools handles every later instruction; the Portal previews it in the sandboxed frame with reads and writes through the host page; the `spec.json` kit pass retires. |
| [ADR-N-023](adr-n-023-pipeline-sources-steps-outputs.md) | A Pipeline Is Bento's Own Shape: Sources, Steps, Outputs | **Accepted** | 2026-09-18 | A `Pipeline` at `v1alpha2` carries `sources[]`, an ordered `steps[]` and `outputs[]`, rendered as Bento `broker` inputs, `pipeline.processors` and `broker` outputs; branching stays inside a step (`branch`, `switch`, `workflow`), no edges are stored; a `v1alpha1` Pipeline reads as the `v1alpha2` one with the same rendered stream and migrates when edited; the write guard applies per source and per output. |
| [ADR-N-024](adr-n-024-workspaces-branch-and-preview.md) | Workspaces: Copy, Change, Test and Bring Back, Renamed at Render and Never at Rest | **Accepted** | 2026-09-18 | A workspace is a branch of the Organization repository recorded beside the drafts; manifests keep their names; a preview is the branch rendered with a `ws-{name}-` prefix on the organization-unique identities, limited and paused on `dev`; bringing it back is the branch's pull request, one Change approved as any other; Save as and the import door cover plain copies. |
| [ADR-N-026](adr-n-026-the-build-lane-runs-in-the-cluster.md) | The Build Lane Runs in the Cluster, and a Static Application May Have No Build Step | **Superseded** | 2026-09-22 | A published `static` App is built by a Kubernetes Job the Portal reconciler starts in the apps namespace: the Portal release's builder image clones the app's repository at the approved commit, installs the baked SDK offline, tests, builds, uploads to the artifact store and proposes `status.build`; the Job holds no platform credential; `build: {}` is plain HTML with no build step; functions stay on QuickJS and are served on `POST /apps/{name}/api/functions/{fn}`. |
| [ADR-N-027](adr-n-027-application-roles.md) | Application Roles, Declared in the App and Held on Its Endpoint Only | **Accepted** | 2026-09-22 | An App declares `spec.roles` and `spec.access` (users by e-mail, `Group` manifests); the gateway gives a caller the app's roles only on the app's own Endpoint, so every grant stays inside the application; `visibility: roles` gates opening with a `403` page that names the roles; `#jc-config.user` and `request.user` carry the person's roles; `dataNeeds[].roles` compiles to one Policy per role; the App page lists and edits members through a Change. |
| [ADR-N-028](adr-n-028-applications-build-on-the-forge.md) | Applications Build on the Forge: Gitea Actions, Its Package Registry and One Runner on the Builder Image | **Accepted** | 2026-09-22 | Every application repository carries a Portal-owned `.gitea/workflows/build.yml` that builds on a push to the default branch, publishes the bundle as the generic package `app-{name}@{commit}` of the organization's Gitea registry and proposes `status.build`; one `gitea-runner` (`act_runner` in host mode on the builder image, no Docker, no Kubernetes token) runs it; the static host fetches and verifies the package; the catalog reads the workflow runs; Rebuild is a dispatch. Replaces ADR-N-026 decisions 1, 2, 4 and 8. |
| [ADR-N-029](adr-n-029-one-repository-per-project.md) | One Repository per Project, Assembled Through the Organization's Project Registry | **Accepted** | 2026-09-22 | An Organization has an organization repository and one repository per project; `projects/{slug}.yaml` is the registry every loader assembles from, each project has a version and parameters, and membership is forge-team membership per repository (PF-85…PF-89, CC-85…CC-90). Supersedes the one-repository half of ADR-N-004 and amends ADR-N-024. |
| [ADR-N-030](adr-n-030-every-application-is-a-keycloak-client.md) | Every Application Is a Keycloak Client of Its Own, with Its Roles as Client Roles | **Accepted** | 2026-09-24 | Each published App is the confidential client `app-{name}` the Portal manages; the Portal composes the edge file from helm's base and writes it as a Secret, one session per app on `/apps/{name}/`; `spec.roles` are client roles mapped from `spec.access`, still granted only on the App's own Endpoint; names are unique in the organization at every door; each project's app pods get a namespace of their own. Supersedes parts of ADR-N-027 and amends ADR-N-019 and AP-27.|

## 2. Status of Preceding Decision Records

The following table explicitly categorizes the disposition of all historical decisions from CIVITAS/CORE v2 (`civitas-core-docs_v2/Architecture/Architecture_Decisions/`) and preliminary research ADRs (`docs/adr/`):

### CIVITAS/CORE v2 Architecture Decisions

| Legacy ID | Title | Status | Superseded By / Reason |
|---|---|---|---|
| ADR 001 | Select Component Library (shadcn) | **Superseded** | [ADR-N-001](adr-n-001-rust-typescript-stack.md): React 19 UI stack uses AG Grid + Radix/Tailwind directly. |
| ADR 002 | Frontend Tech Stack (Next.js App Router) | **Superseded** | [ADR-N-001](adr-n-001-rust-typescript-stack.md): Switched to Vite + React 19 + TanStack Router client SPA. |
| ADR 003 | Select STA Tech Stack (FROST-Server) | **Dropped / Addon** | Core now serves STA v1.1 read representations via Gateway (EP-12); FROST moved to optional addon. |
| ADR 004 | Postgres Operator (CloudNativePG) | **Kept** | Retained as standard database operator across all profiles. |
| ADR 005 | Tool for Keycloak configuration | **Superseded** | [ADR-N-004](adr-n-004-configuration-as-code-and-gitea.md): `jcctl` manages Keycloak state via declarative manifests. |
| ADR 006 | GatewayAPI vs Std Ingress | **Kept** | NGINX / standard Ingress with cert-manager remains platform ingress standard. |
| ADR 007 | Select IAM Tool (Keycloak) | **Kept** | Keycloak retained as standard OIDC/OID4VCI identity provider. |
| ADR 008 | Select Dashboard Tool (Superset) | **Dropped / Addon** | [ADR-N-011](adr-n-011-maplibre-deckgl-dashboards.md): Replaced by in-portal MapLibre/deck.gl; Superset moved to addon. |
| ADR 009 | Data Mgmt Portal Backend (Spring Boot) | **Superseded** | [ADR-N-001](adr-n-001-rust-typescript-stack.md): Custom Java backend eliminated; replaced by Portal API (Rust, Axum). |
| ADR 010 | Select DBMS (PostgreSQL) | **Kept** | PostgreSQL remains authoritative persistence layer for portal, broker, and keycloak. |
| ADR 011 | Select Observability Dashboard (Grafana) | **Dropped / Addon** | Core monitoring utilizes Prometheus/OpenTelemetry; Grafana retained as optional addon. |
| ADR 012 | Deployment Strategy (Helmfile) | **Kept** | Helmfile component model remains the foundation. |
| ADR 013 | CloudEvents for Bus Configuration | **Superseded** | [ADR-N-004](adr-n-004-configuration-as-code-and-gitea.md): Kafka message bus eliminated; configuration uses Git-as-code. |
| ADR 014 | Select API Management (APISIX) | **Modified** | [ADR-N-007](adr-n-007-apisix-standalone-no-etcd.md): APISIX retained but shifted to standalone declarative mode (no etcd). |
| ADR 015 | TimescaleDB | **Kept** | PostgreSQL with Timescale extension supported for temporal storage in Antares/Stellio. |
| ADR 016 | Config Adapter SDK Language (Java) | **Superseded** | [ADR-N-004](adr-n-004-configuration-as-code-and-gitea.md): Config adapters eliminated; replaced by `jcctl` reconciler in Rust. |
| ADR 017 | Graph vs Relational Database | **Kept** | Relational PostgreSQL with JSONB/RLS retained. |
| ADR 018 | Modeling Component (EMF/Ecore) | **Superseded** | [ADR-N-010](adr-n-010-linkml-data-models.md): Replaced by LinkML data modeling. |
| ADR 019 | Select Geoportal (Masterportal) | **Dropped / Addon** | [ADR-N-011](adr-n-011-maplibre-deckgl-dashboards.md): Replaced by in-portal MapLibre engine; Masterportal moved to addon. |
| ADR 020 | Security Concept for Sharing | **Superseded** | [ADR-N-002](adr-n-002-context-space-and-endpoint-model.md): Sharing managed via Endpoint manifests and SharedSpaceReferences. |
| ADR 021 | Configuration Events Definition | **Superseded** | [ADR-N-004](adr-n-004-configuration-as-code-and-gitea.md): Kafka config events replaced by Git commits. |
| ADR 022 | Backend JSON-LD API for Datasets | **Superseded** | [ADR-N-002](adr-n-002-context-space-and-endpoint-model.md): Standardized on NGSI-LD /cs/{space} surface. |
| ADR 023 | OPA backed by AuthZ DB adapter | **Superseded** | [ADR-N-003](adr-n-003-context-gateway-in-rust.md): Java AuthZ adapter removed; gateway embeds native policy evaluator. |
| ADR 024 | Use of Linkerd Service Mesh | **Kept** | Mandatory Linkerd mTLS with `cluster-authenticated` policy retained. |
| ADR 025 | GeoServer Cloud | **Dropped / Addon** | Core geospatial serving handled via OGC Features endpoint; GeoServer moved to addon. |
| ADR 026 | Select Message Bus (Kafka) | **Dropped** | Kafka bus removed from core platform architecture. |
| ADR 027 | Credential Mgmt in Pipelines (Vault) | **Superseded** | [ADR-N-012](adr-n-012-secrets-sops-openbao.md): Vault replaced by OpenBao (MPL 2.0) and SOPS+age. |
| ADR 028 | Interim Datasource Encryption | **Superseded** | [ADR-N-012](adr-n-012-secrets-sops-openbao.md): Plaintext secrets in DB eliminated; credentials reside in secret store. |
| ADR 029 | Collection Auth Filtering via Headers | **Superseded** | [ADR-N-003](adr-n-003-context-gateway-in-rust.md): AST query rewriting (R10–R13) in gateway replaces header passing. |
| ADR 030 | Asynchronous Outbox for Config | **Superseded** | [ADR-N-004](adr-n-004-configuration-as-code-and-gitea.md): Outbox pattern eliminated along with Kafka. |
| ADR 031 | Orchestrated Saga for Provisioning | **Superseded** | [ADR-N-004](adr-n-004-configuration-as-code-and-gitea.md): Sagas eliminated; `jcctl` handles wave reconciliation. |
| ADR 032 | State-Dependent Authorization | **Superseded** | [ADR-N-003](adr-n-003-context-gateway-in-rust.md): Gateway enforces state policies via conditional HTTP writes (R45). |
| ADR 033 | Grafana as Second Dashboard Tool | **Dropped / Addon** | Grafana remains an optional addon consuming Endpoints. |
| ADR 034 | Logging Rules for Platform Components | **Kept** | Structured JSON logging to stdout/stderr enforced across all Rust services. |
| ADR 035 | Interface Standards throughout Platform | **Kept** | Strict reliance on open standards (NGSI-LD, OGC, ODRL). |
| ADR 036 | Event-driven Communication / Bus | **Dropped** | Inter-component messaging bus removed in favor of direct APIs and declarative Git reconciliation. |
| ADR 037 | Redpanda Connect as ETL Runtime | **Superseded** | [ADR-N-006](adr-n-006-bento-pipelines-supersede-nifi.md): Redpanda Connect disqualified on licensing; Bento (MIT) selected. |
| ADR 038 | Apache NiFi as Pipeline Engine | **Superseded** | [ADR-N-006](adr-n-006-bento-pipelines-supersede-nifi.md): NiFi eliminated due to resource footprint; Bento selected. |
| ADR 039 | Dataset API Standard | **Superseded** | [ADR-N-002](adr-n-002-context-space-and-endpoint-model.md): Multi-representation endpoints supersede explicit API types. |
| ADR 040 | Subdomain Separation of APIs | **Superseded** | [ADR-N-002](adr-n-002-context-space-and-endpoint-model.md): Path-based routing (`/cs/` and `/api/`) replaces subdomain splitting. |
| ADR 041 | Topic Naming Convention | **Dropped** | Kafka topic naming irrelevant following bus removal. |
| ADR 042 | Kafka AuthZ via OPA | **Dropped** | Kafka authorization irrelevant following bus removal. |
| ADR 043 | Kafka AuthN via SASL/SCRAM | **Dropped** | Kafka authentication irrelevant following bus removal. |
| ADR 044 | Backend Authorization Enforcement | **Superseded** | [ADR-N-003](adr-n-003-context-gateway-in-rust.md): Context Gateway handles all PEP/PDP policy checks. |
| ADR 045 | JSON Schema and JSONata for Models | **Superseded** | [ADR-N-010](adr-n-010-linkml-data-models.md): LinkML supersedes raw JSON Schema/JSONata authoring. |

### Preliminary Research ADRs (`docs/adr`)

| Research ID | Title | Status | Target Disposition |
|---|---|---|---|
| ADR 001 | URN Standard | **Kept** | Adopted as normative platform URN syntax (`PF-10`). |
| ADR 002 | NGSI-LD Security Policies | **Kept** | Adopted as normative `Policy` entity specification. |
| ADR 003 | Policy Mapping to W3C ODRL | **Kept** | Adopted for DSP connector contract negotiation (`R52`). |
| ADR 004 | Hierarchy of Spaces (Scopes) | **Kept** | Adopted as multidimensional scope taxonomy (`/geo`, `/domain`, `/admin`). |
| ADR 005 | Scope Representation in NGSI-LD | **Kept** | Adopted as `ScopeDefinition` entity specification. |
| ADR 006 | Privilege Bleed Prevention | **Kept** | Adopted as normative AST regex folding rule (`R12`, `R13`). |
| ADR 007 | Default @context Discovery | **Kept** | Adopted via spec-native Link headers and `/jsonldContexts`. |
| ADR 008 | Semantic Remapping via Expansion | **Kept** | Adopted for vocabulary harmonization across peer twins. |
| ADR 009 | Secured Subscriptions in FDT | **Kept** | Adopted via `receiverInfo` and `contextSourceInfo` slots. |
| ADR 010 | Open API (LOD) over NGSI-LD | **Kept** | Implemented as public Endpoint representation (`EP-14`). |
| ADR 011 | Open API (LOD) over MQTT | **Kept** | Implemented via public broker bridge with state/event trees. |
| ADR 012 | NGSI-LD WebSocket Binding | **Kept** | Published as official platform WebSocket binding specification. |
| ADR 013 | Context Space Addressing Scheme | **Kept / Extended** | [ADR-N-002](adr-n-002-context-space-and-endpoint-model.md): Extended to include `/api/endpoint/{endpointSlug}` endpoints. |

## Related

- [ADR-N-001](adr-n-001-rust-typescript-stack.md) — referenced above.
- [ADR-N-002](adr-n-002-context-space-and-endpoint-model.md) — referenced above.
- [ADR-N-003](adr-n-003-context-gateway-in-rust.md) — referenced above.
- [ADR-N-004](adr-n-004-configuration-as-code-and-gitea.md) — referenced above.
- [ADR-N-021](adr-n-021-one-operation-registry-behind-ui-api-assistant-and-mcp.md) — referenced above.
- [ADR-N-022](adr-n-022-generated-applications-are-code-on-the-app-sdk.md) — referenced above.
- [ADR-N-023](adr-n-023-pipeline-sources-steps-outputs.md) — referenced above.
- [ADR-N-024](adr-n-024-workspaces-branch-and-preview.md) — referenced above.
- [ADR-N-026](adr-n-026-the-build-lane-runs-in-the-cluster.md) — referenced above.
- [ADR-N-029](adr-n-029-one-repository-per-project.md) — referenced above.
- [ADR-N-030](adr-n-030-every-application-is-a-keycloak-client.md) — referenced above.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
