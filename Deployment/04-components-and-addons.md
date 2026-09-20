---
sidebar_position: 5
title: "Components & Optional Add-ons"
---

# Components & Optional Add-ons

The platform cleanly separates the core runtime from optional functional add-ons. Core components provide identity, context storage, API translation, CaC reconciliation, and basic pipeline execution. Add-ons extend visualization, BI, legacy OGC compatibility, and automated agent workflows.

## 1. Core Components vs. Add-ons Matrix

| Component | Class | Language / Engine | Responsibility |
|---|---|---|---|
| **context-broker** | Core | Rust (Antares) | Canonical NGSI-LD Context Broker & RLS data store |
| **context-gateway** | Core | Rust (Axum) | PEP firewall, AST rewriter, representation translator, MCP |
| **portal** | Core | Rust + React | Portal API (Axum) & Portal UI (Vite/TS/MapLibre) |
| **jcctl** | Core | Rust | Reconciler daemon, plan/apply/drift engine, CaC MCP |
| **gitea** | Core | Go | In-cluster Git forge, CODEOWNERS engine, Gitea Actions |
| **pipeline-runner**| Core | Go (Bento) | Resident streams runner & CronJob batch executor |
| **apisix** | Core | Lua / NGINX | Standalone edge routing, TLS, rate-limiting, OIDC ingress |
| **keycloak** | Core | Java (Standard) | Central IAM, OIDC, OID4VCI status lists |
| **postgres** | Core | CNPG Operator | High-availability PostgreSQL database clusters |
| **openid-connect** | Core | APISIX plugin | `openid-connect` in session mode on the Portal and every App on Demand route, one confidential OIDC client `edge` per realm (ADR-N-019) |
| **model-tools** | Core | Python (LinkML) | Stateless generator image: LinkML artifacts, schema-automator imports, mapping compilation |
| **artifact-store** | Core | Rust (RustFS, S3 API) | Object-locked store for rendered schema artifacts, compiled mappings, dumps, exports, app builds, file cache (ADR-N-015) |
| **audit-logging** | Core | Rust (Vector) | Node collector shipping the audit stream to object-locked storage, 90 day retention (OPS-42) |
| **sandbox-reaper** | Core | CronJob (kubectl) | Deletes sandbox namespaces past their TTL, 14 day ceiling (OPS-44, PF-19) |
| **frost** | Add-on | Java | Dedicated SensorThings API (STA) broker for high-volume IoT |
| **geoserver** | Add-on | Java | Legacy WFS/WMS mapping services |
| **grafana** | Add-on | Go | Infrastructure observability and public data dashboards |
| **superset** | Add-on | Python | Business intelligence, OLAP, and SQL reporting |
| **masterportal** | Add-on | JavaScript | Modular 2D/3D geoportal interface |
| **agent-runner** | Add-on | Python / Rust | OpenHands agent runtime in isolated workspace Jobs and `jc-agent-proxy` credential-free internal proxy (ADR-N-014, ADR-N-020, Architecture/19) |
| **functions** | Add-on | Rust | `jc-functions`, the QuickJS runtime of generated applications' serverless functions, called by the Portal alone (Architecture/20 §3) |
| **dataspace-connector** | Add-on | post-MVP, engine not chosen | Dataspace Protocol catalog, negotiation, transfer; ODRL agreements → Policy changes (ADR-N-016, DS-06); not shipped until a data-space partner appears; requires OpenBao |
| **openbao** | Add-on | Go | Vault-compatible secrets management engine (MPL 2.0) |

## 2. Enabling an Add-on

Add-ons are registered in `deployment/environments/<env>/global.yaml.gotmpl` under the `components` list:

```yaml
components:
  # ... core components ...
  - frost          # Enables FROST-Server
  - grafana        # Enables Grafana Add-on
  - agent-runner   # Enables OpenHands Agent Runner
```

## 3. How Add-ons Consume Platform Endpoints

Add-ons **never** access the internal database or bypass the security firewall. Add-ons interact with context spaces exclusively through **Endpoints** via standard protocols:

```mermaid
flowchart LR
    Grafana[Grafana Add-on] -->|HTTP JSON / STA| EP[Endpoint: /api/endpoint/{endpointSlug}/sta/v1.1]
    QGIS[QGIS / GeoServer] -->|OGC Features| EP2[Endpoint: /api/endpoint/{endpointSlug}/ogc/features]
    Agent[Agent Runner] -->|MCP Streamable HTTP| EP3[Endpoint: /api/endpoint/{endpointSlug}/mcp]
    
    EP --> Gateway[Context Gateway PEP]
    EP2 --> Gateway
    EP3 --> Gateway
    Gateway --> Antares[Antares Broker]
```

1. **Grafana**: Consumes time-series observations through the Endpoint's SensorThings API representation (`/api/endpoint/{endpointSlug}/sta/v1.1`) or direct Infinity datasource query against `/api/endpoint/{endpointSlug}/ngsi-ld/v1/entities`.
2. **QGIS & Map Clients**: Consume spatial feature collections through the OGC API Features endpoint (`/api/endpoint/{endpointSlug}/ogc/features/collections/{type}/items`).
3. **Agent Runner**: Automatically binds to `/api/endpoint/{endpointSlug}/mcp` with scoped Bearer tokens to execute read and write operations permitted by the Endpoint's audience policy.

## 4. Agent Runner and Credential Proxy Add-on (`agent-runner`)

The `agent-runner` component packages the autonomous builder infrastructure specified in ADR-N-020 and Architecture/19.

### Deployed Workloads

1. **`proxy` (`jc-agent-proxy`)**: A single-replica Deployment in the instance namespace executing the Rust proxy daemon. It holds references to Keycloak, Gitea, and model provider credentials via `secretRef`.
2. **`workspaces`**: Configuration for the dedicated `agents` execution namespace, including default-deny NetworkPolicies, resource quotas, and RBAC granting the Portal service account permissions to schedule and delete workspace Jobs.
3. **`seed`**: Declarative seed manifests providing the `app-builder` `AgentProfile` and `app-from-prompt` `Blueprint`.

### Configuration Parameters

```yaml
agent-runner:
  enabled: true
  namespace: "dev-agents"
  proxy:
    image:
      repository: ghcr.io/marek-mraz/jc-agent-proxy
      tag: "v0.1.0"
      digest: "sha256:1a2b3c..."
    replicas: 1
    resources:
      requests: { cpu: 100m, memory: 128Mi }
      limits: { cpu: 500m, memory: 512Mi }
    model:
      provider: anthropic
      baseUrl: "https://api.anthropic.com"
      secretRef: model-provider-key
  workspaces:
    quota:
      maxJobs: 5
      maxCpu: "8"
      maxMemory: "16Gi"
```

### Network Policies & Isolation

- **Workspace Pods**: Egress is strictly limited to the `jc-agent-proxy` Service on port 8080 and `kube-dns` on port 53. Ingress is completely blocked.
- **Agent Proxy**: Ingress is permitted only from pods within the `agents` namespace. Egress is permitted to Context Gateway, Gitea, Keycloak, Portal API, and the designated model provider address.
- **Edge Routing**: The proxy is an internal service only; it is not published in `apisix.yaml` and cannot be reached from outside the cluster.

### Verification

```bash
# Verify proxy health
kubectl exec -it deploy/portal -c portal -- curl -s http://jc-agent-proxy:8080/healthz

# Verify workspace namespace isolation
kubectl get networkpolicies -n dev-agents
```

## 5. Application Functions Runtime (`functions`)

The `functions` component runs `jc-functions` from the platform image (Architecture/20 §3, SDK-21…SDK-23): one Deployment and a ClusterIP Service on port 8080, in the instance namespace, listed in `components` before `portal`.

- **Identity.** The runtime holds no credential. It verifies the Portal's token against the realm's JWKS (in-cluster Keycloak Service): audience `jc-functions`, `azp` the Portal's client `portal-api`. The `portal-api` client carries the `jc-functions` audience mapper; the Portal gets its token with the client-credentials grant of that client.
- **Portal.** With the component in the list, the portal values set `JC_FUNCTIONS_URL` to the Service; without it the Portal answers the function route with `503`.
- **Network.** Ingress on 8080 from the Portal's pod only; egress to the Context Gateway on 8080, Keycloak on 8080 (the JWKS) and CoreDNS. Nothing else, the internet included. It is not published through APISIX.
- **Resources.** A request of 50m CPU and 96Mi. The limit is 1 CPU and 1Gi, because each of the 16 concurrent invocations may use 64 MiB. One replica in `development`, two with a PodDisruptionBudget in `production`.

### Verification

`just dev-smoke` gets the Portal client's token from the realm, sends one invocation to the Service over a port-forward and expects the function's answer; a probe pod without the Portal's labels must fail to connect to the Service port.

## Related

- [00-intro](00-intro.md) — deployment chapter order.
- [01-runbooks](../Operations/01-runbooks.md) — what to do when it breaks.
- [13-security](../Architecture/13-security.md) — the security model being deployed.
