---
sidebar_position: 14
title: Component Reference & Technology Matrix
description: Architectural specifications, responsibilities, interfaces, and failure behaviors for all core services and addons.
---

# Component Reference & Technology Matrix

This reference documents every software component comprising the joinedcontext platform, detailing its implementation language, scaling properties, interfaces, and failure modes. For container resource allocations and profile sizing tables, see [Deployment/04-components-and-addons.md](../Deployment/04-components-and-addons.md).

## 1. Component Architecture & Matrix Reference

Platform components are cleanly partitioned between core services and pluggable addons. The authoritative component matrix specifying technology languages, profile allocations, and licensing is defined in [Deployment/04-components-and-addons.md](../Deployment/04-components-and-addons.md).

## 2. Core Platform Components

### Context Gateway (`context-gateway`)

- **Primary Role:** Policy Enforcement Point (PEP), query AST rewriter via `antares-ql`, representation translation engine, and MCP façade.
- **Interfaces:** Inbound HTTPS from APISIX; outbound HTTP/2 to Context Broker; outbound HTTPS to Keycloak JWKS; policy space subscription for in-process PDP updates.
- **State & Failure Behavior:** Completely stateless. Horizontally scalable via Kubernetes HPA. If the in-process PDP grant cache is stale or uninitialized, the gateway fails closed, returning HTTP 503 (GW5, R48).

### Antares Context Broker (`context-broker`)

- **Primary Role:** Spec-native ETSI GS CIM 009 context broker managing current entity state, temporal records, and context subscriptions.
- **Interfaces:** HTTP/2 CIM 009 REST endpoints; TCP PostgreSQL protocol with CNPG.
- **State & Failure Behavior:** Stateless broker workers backed by PostgreSQL. Scale-out read replicas supported via streaming replication. Unreachable database triggers HTTP 503 on incoming broker requests.

### jcctl (`jcctl`)

- **Primary Role:** the configuration plane as a command, shipped by `joinedcontext-platform` and deployed as no workload of its own: `validate`, `plan`, `apply`, `drift`, `export`, `import`, `sync`, `model`, `roles`, `pipeline test`, `artifacts rebuild`, `publish ckan` (`crates/jcctl/src/main.rs`). A person or a CI lane runs it against a repository checkout. The kubectl-shaped verbs `get`, `describe`, `apply -f`, `diff -f` and `delete -f` are a client of the Portal resource API instead, with an OIDC token, and every write they make is a proposed `Change` (MF-14, [API/03 §2a](../API/03-jcctl.md#2a-talking-to-the-portal-get-describe-apply--f-diff--f-delete--f)).
- **Interfaces:** the repository on disk; CIM 009 management calls to the Context Gateway and the broker.
- **State & Failure Behavior:** one verb, one exit code, no daemon and no lease. The reconciling loop that runs *inside* the cluster is the Portal's (`portal` component, `src/reconciler/`), which is where leader election, the waves and CC-18's "a transient failure pauses without rolling back the waves already converged" live.

### Portal (one application) (`portal`)

- **Primary Role:** One Rust binary (`joinedcontext-portal`) serving the embedded React UI (schema forms, flow galleries, map dashboards, approval reviews), the administrative REST and resource APIs, and the in-process reconciler loop.
- **Interfaces:** HTTPS from APISIX on port 8080 (UI, `/api/v1` incl. the resource collections, `/apps/{name}/` static apps); PostgreSQL pool (`portal` database); Gitea API; Context Gateway Endpoints from the browser.
- **State & Failure Behavior:** Stateless except the preferences database; horizontally scalable, reconciler leader-elected. Database failures reject preference mutations while live context browsing continues through the gateway.

### Edge login (APISIX `openid-connect`)

- **Primary Role:** Login front of the Portal (`portal.{domain}`) and of every App on Demand host (`{name}.apps.{domain}`, ADR-N-037): one confidential OIDC client `edge` per realm, Keycloak code flow and session in APISIX, `X-Userinfo` and `X-Access-Token` to the upstream (ADR-N-019).
- **Interfaces:** the APISIX routes themselves; OIDC to Keycloak; HTTP 8080 to the Portal and to every app container.
- **State & Failure Behavior:** Stateless (encrypted cookie session). Keycloak outage blocks new logins; existing sessions live until cookie expiry. See [Architecture/16 §5](16-apps-on-demand.md#5-login-in-front-of-the-portal-and-every-app-apisix-openid-connect).

### Bento Pipeline Runner (`pipeline-runner`)

- **Primary Role:** Resident telemetry stream processor operating in Bento Streams Mode.
- **Interfaces:** Inbound MQTT, WebSockets, Kafka, HTTP; outbound HTTPS to Context Gateway Endpoints.
- **State & Failure Behavior:** one Deployment per project, one replica (PL-08, PL-12): a project is scaled by its own runner pool and not by replicas of one pool, so the production values set `replicaCount: 1` and no autoscaler. Bento streams mode keeps one stream's failure inside that stream; the runner's other streams carry on, and a failed message is retried and then dropped with a log line — there is no dead-letter sink in the rendered stream today.

### APISIX Edge Gateway (`apisix`)

- **Primary Role:** Perimeter edge ingress, TLS termination, rate limiting, header sanitization and route mapping; bearer tokens pass through to the verifying service (Portal, Context Gateway).
- **Interfaces:** Inbound HTTPS ports 80/443; outbound HTTP to internal cluster Services over Linkerd mTLS.
- **State & Failure Behavior:** Fully stateless data plane. The routes are a ConfigMap the `configuration` chart renders, mounted into the container's own `/usr/local/apisix/conf` (a path inside the APISIX image, not in this platform's tree). APISIX polls that file every second; a missing `#END` marker makes it refuse the reload and keep the routes it already has.

### Keycloak IAM (`keycloak`)

- **Primary Role:** Central Identity Provider managing users, groups, OIDC tokens, and Verifiable Credentials.
- **Interfaces:** HTTPS browser console, OIDC endpoints, JWKS discovery endpoint.
- **State & Failure Behavior:** Clustered Quarkus deployment backed by CloudNativePG PostgreSQL. Pod outages fail over to active replicas.

### Gitea Forge (`gitea`)

- **Primary Role:** In-cluster Git repository, pull request review, protected branches, and the Actions and package registry the application repositories build and publish through (ADR-N-028).
- **Interfaces:** Web UI, Git over SSH/HTTPS, webhook dispatches to the Portal (`/api/v1/.../sync-sources` webhook routes, signed with the shared HMAC secret).
- **State & Failure Behavior:** A single-replica Deployment holding one ReadWriteOnce volume for the bare repositories, with metadata in PostgreSQL. One replica is the ceiling: the volume cannot be shared, so the forge fails over rather than scaling out, which is why OPS-06's two-replica floor covers the stateless core and not this. Outages freeze configuration changes while data serving continues unaffected (CC-55).

### Forge Actions Runner (`gitea-runner`)

- **Primary Role:** Runs the Portal-owned `.gitea/workflows/build.yml` of every application repository: tests, build, `integrity.json`, the package `app-{name}@{commit}` and the proposal of `status.build` (AP-80, [ADR-N-028](../Decisions/adr-n-028-applications-build-on-the-forge.md)).
- **Interfaces:** Registers with the forge using the organization's registration token and takes jobs from it; reaches the forge and the Portal API and nothing else (AP-81).
- **State & Failure Behavior:** Stateless: `act_runner` in host mode on the signed builder image (AP-82), with no container runtime socket and no Kubernetes token, a work directory wiped after every job, and a wall-clock and memory limit per job. While it is down, builds wait in the forge's queue and every application keeps serving its last build.

### Artifact Store (RustFS) (`artifact-store`)

- **Primary Role:** S3-compatible object store persisting rendered schema artifacts, compiled Bloblang mappings, RDF dumps, export bundles, and app builds.
- **Interfaces:** S3 REST API over in-mesh Linkerd mTLS.
- **State & Failure Behavior:** Deployed with persistent volume storage and object locking. All artifacts are fully rebuildable from Git via `jcctl artifacts rebuild` (PF-29…PF-33, ADR-N-015).

### Model Tools (`model-tools`)

- **Primary Role:** Stateless OCI image executing LinkML generators, schema-automator, and mapping compilers.
- **Interfaces:** Short-lived HTTP RPC from Portal API; container command-line execution in CI pipelines.
- **State & Failure Behavior:** Completely stateless and credential-free. Replicas restart instantly upon node eviction without data loss (DM-18).

### PostgreSQL (`postgres`)

- **Primary Role:** Clustered relational store behind the broker, the Portal and Gitea, operated by the CloudNativePG operator.
- **Interfaces:** TCP PostgreSQL protocol inside the mesh; WAL archiving to the artifact store; the operator's Kubernetes API calls.
- **State & Failure Behavior:** The only stateful core component. Primary failure promotes a replica; a lost primary without a replica needs a restore from the WAL archive (OPS-20, [Deployment/07-backup-restore.md](../Deployment/07-backup-restore.md)).

### Audit Log Collector (`audit-logging`)

- **Primary Role:** A collector on every node, splitting the structured JSON of every pod into an operational stream and an audit stream, and shipping the audit stream to object-locked storage for 90 calendar days (OPS-42, R42, AG-19).
- **Interfaces:** Reads the container log files of its own node; writes S3 `PutObject` and nothing else.
- **State & Failure Behavior:** Stateless apart from its read positions on disk. A collector that cannot reach the sink buffers on the node and retries; records are never dropped to make room, so a long outage backs the buffer up rather than losing evidence. See [Deployment/05 §3](../Deployment/05-monitoring-logging.md#3-centralized-logging).

### Sandbox Reaper (`sandbox-reaper`)

- **Primary Role:** Scheduled job deleting sandbox namespaces whose age has passed their Time-To-Live, ceiling 14 calendar days (OPS-44, PF-19, CC-67).
- **Interfaces:** Kubernetes API, restricted to listing namespaces and deleting the labelled ones.
- **State & Failure Behavior:** Stateless; age comes from `metadata.creationTimestamp` on each run, so a missed run reaps late and never reaps twice. An unlabelled namespace is never a candidate, which is the direction the failure has to go. See [Architecture/06 §4](06-configuration-as-code.md#4-risk-classified-interaction-lanes-cc-63cc-66).

### Namespace Preparation (`prepare`)

- **Primary Role:** Runs before every other component: creates the namespaces an installation needs when `global.createNamespaces` is set, annotates each for Linkerd injection and for the inbound policy `global.serviceMesh.defaultInboundPolicy` names, and distributes the `custom-ca-cert` Secret where a self-signed issuer needs it.
- **Interfaces:** Helmfile hooks calling the Kubernetes API with `kubectl`; nothing serves a port.
- **State & Failure Behavior:** Stateless and idempotent. A hook that cannot create a namespace fails the sync rather than letting the components above it install into nothing, and a namespace whose inbound policy cannot be set is caught a second time at admission by `require-meshed-namespace-inbound-policy`. See [Deployment/08 §2](../Deployment/08-security-hardening.md#2-sequential-hardening-layers).

### Secret Generation and Resolution (`secrets`)

- **Primary Role:** The two kinds of credential an installation holds. Passwords no person needs to know (the Keycloak administrator, the databases, the APISIX session key, the Keycloak client secrets) are generated in the cluster on first install and never leave it; credentials only an operator can supply (mail, an object store, a model provider) are resolved from SOPS-encrypted references at render time.
- **Interfaces:** Kubernetes Secret objects in the namespace of each consumer; `ref+sops://` references read with the age key in the environment of whoever runs `helmfile`.
- **State & Failure Behavior:** A generated Secret carries `helm.sh/resource-policy: keep`, so an uninstall does not take the password of a database that outlives it. A missing age key fails the render before anything is installed, which is the direction this has to fail: the alternative is a cluster coming up with a generated stand-in where a real credential belongs. See [Deployment/07 §3](../Deployment/07-backup-restore.md#3-disaster-recovery-procedure).

### Network Policies (`networkpolicies`)

- **Primary Role:** One `default-deny` policy per component, in both directions, plus the explicit allows each component declares for itself. Ingress alone would leave a compromised pod free to reach the database, the identity provider or an address on the internet, which is the half of the blast radius that matters after a break-in (OPS-38).
- **Interfaces:** Kubernetes `NetworkPolicy`, and the Linkerd `Server` and authorization objects that carve out the unmeshed ingress edge.
- **State & Failure Behavior:** Declarative and stateless. Because egress is denied by default, a component that forgets to declare a call it makes fails closed, visibly, at the call. Policies targeting the shared operators namespace are created once per cluster by the operators layer, so two instances syncing at the same time cannot fight over one release. See [Deployment/08 §2](../Deployment/08-security-hardening.md#2-sequential-hardening-layers).

### Runtime Policies (`runtime-policies`)

- **Primary Role:** The Kyverno `ClusterPolicy` objects that validate what only exists at runtime: the mesh sidecar, a namespace's inbound policy, an operator's labels, a mounted API token, and the four Pod Security Standards controls vendored from upstream.
- **Interfaces:** Kyverno admission review; `ClusterPolicyReport` for what it found.
- **State & Failure Behavior:** Stateless. Every policy takes its action from `global.runtimePolicies.failureAction`, `Enforce` by default and `Audit` for a rollout that should log before it blocks, so the same policies can be watched before they are trusted. See [Deployment/08 §4](../Deployment/08-security-hardening.md#4-runtime-kyverno-policy-enforcement).

### Activity Collector (`observability`)

- **Primary Role:** The OpenTelemetry Collector that fills the Portal's Activity stream: it accepts OTLP log records from the broker, the gateway and the Bento runners, drops every attribute outside its allow-list, and forwards what is left to the Portal's ingest route.
- **Interfaces:** OTLP in; OTLP over HTTP to the Portal, authenticated as its own Keycloak client.
- **State & Failure Behavior:** Stateless and deliberately thin. It holds no database credential, writes no row and decides nothing about what an event means, so a collector that is down loses activity records and cannot corrupt the stream. See [Deployment/05 §5](../Deployment/05-monitoring-logging.md#5-the-activity-pipeline).

### Metrics Configuration (`monitoring`)

- **Primary Role:** Deploys no workload. It renders one `ServiceMonitor` per component that exports Prometheus metrics on its Service and has none of its own, and the `PrometheusRule` of the edge runbook (OPS-16, TS-22).
- **Interfaces:** Prometheus Operator custom resources only.
- **State & Failure Behavior:** Stateless. It is last in the `components` list because it scrapes the components above it, so it is rendered once they are known. APISIX is deliberately absent from its targets: that chart renders its own monitor for port 9091, and a second one would double every edge counter. See [Deployment/05 §1](../Deployment/05-monitoring-logging.md#1-metrics-architecture).

## 3. Pluggable Addon Ecosystem

Specialized workloads connect to the platform strictly through standard Endpoints. An addon is opt-in per installation and is registered by naming it in an environment's `components` list; the `addons` render surface of `joinedcontext-deployment` is what proves one still renders. Of the addons below, only `agent-runner` (with its proxy), `functions` and `grafana` are components in that repository today — the rest of this list is the integration contract each addon has to meet when it is packaged, not something an operator can switch on now:

- **Apache Superset** (`superset`): Advanced business intelligence consuming data via Endpoint SQL or CSV representations.
- **Grafana** (`grafana`): Operational metrics and timeseries visualizations querying Endpoint STA representations.
- **Masterportal** (`masterportal`): Specialized 2D/3D geoportal consuming Endpoint OGC Features representations.
- **OpenHands Agent Runner** (`agent-runner`): Autonomous agent execution runtime communicating via the platform's Data MCP and Configuration MCP surfaces; the `builder` profile adds coding tools in an ephemeral workspace mediated by `jc-agent-proxy` to build Apps on Demand autonomously (AG-26…AG-28, AG-33…AG-52, ADR-N-020, Architecture/19).
- **Agent Proxy** (part of `agent-runner`): Internal Rust proxy holding the platform credentials and injecting them into workspace requests, so a runner pod never holds a token, and enforcing the per-run rate, byte and model-token limits (ADR-N-020, Architecture/19).
- **FROST-Server** (`frost`): dedicated SensorThings API broker for high-volume IoT series, fed through Endpoint STA representations.
- **GeoServer** (`geoserver`): legacy WFS and WMS services for clients that cannot speak OGC API Features.
- **Data Space Connector** (`dataspace-connector`): Dataspace Protocol catalog, contract negotiation and transfer; agreed ODRL policies become Endpoint grants ([18-data-space-connector.md](18-data-space-connector.md)).
- **OpenBao** (`openbao`): the Portal resolves a `secretRef` through OpenBao when `JC_PORTAL_OPENBAO_ADDR`, `JC_PORTAL_OPENBAO_ROLE` and `JC_PORTAL_OPENBAO_JWT_PATH` name one. No chart for it ships in `joinedcontext-deployment` yet, so SOPS with age is the path every environment runs today (13 §3).
- **CKAN** (`ckan`): the open-data catalogue on `data.<domain>`, the public face of every Endpoint a project chooses to publish (EP-62…EP-67). `jcctl` writes its datasets and resources through the Action API and the Portal reads their status back.
- **Demo Feeds** (`demo-feeds`): a NATS broker and a live publisher for a development cluster, so the demo pipelines have something to read. Not a platform component and never in a production `components` list.
- **Application Functions Runtime** (`functions`): `jc-functions`, a Rust service embedding QuickJS that runs one generated application function per invocation in a fresh context (64 MiB, 5 s, 16 concurrent per replica). It holds no credential and no code of its own. Only the Portal calls it, with a token of audience `jc-functions`, and it reaches only the Context Gateway, so a function reads and writes through the application's endpoint and that endpoint's Policy ([20-app-sdk.md §3](20-app-sdk.md#3-functions-and-their-runtime), SDK-21…SDK-23).

For detailed addon integration patterns and deployment configurations, see [Deployment/04-components-and-addons.md](../Deployment/04-components-and-addons.md).

## Related

- [01-overview.md](01-overview.md) — high-level platform architecture and operational areas.
- [05-context-gateway.md](05-context-gateway.md) — Context Gateway internals and query rewriting.
- [17-artifact-store.md](17-artifact-store.md) — S3-compatible artifact store architecture.
- [../Deployment/04-components-and-addons.md](../Deployment/04-components-and-addons.md) — component packaging, language matrix, and resource sizing.
- [../Deployment/10-edge-routing-apisix.md](../Deployment/10-edge-routing-apisix.md) — edge routing and APISIX standalone configuration.
