---
sidebar_position: 5
title: "Components & Optional Add-ons"
---

# Components & Optional Add-ons

Every component this platform has, whether it is deployed by default, and what each one puts on the cluster. The `Class` column is the one [Architecture/14](../Architecture/14-components.md) uses; the column beside it answers the question a deployment actually asks, which is whether an installation gets this without asking for it.

## 1. Core Components vs. Add-ons Matrix

A **Core** component makes up a working installation and is in the shipped `components` list of `defaults/environment/global.yaml`. An **Add-on** is opt-in: `no` in the last column means the code is there and no environment has enabled it, and `not shipped` means there is no directory under `components/` yet, so naming it in a `components` list fails the render.

| Component | Class | Language / Engine | In the default list | What it deploys |
|---|---|---|---|---|
| **prepare** | Core | helmfile hooks | yes | Creates the namespaces and annotates them for Linkerd injection and the inbound policy |
| **secrets** | Core | helm, SOPS | yes | Generates every password the platform owns and resolves the ones an operator supplies |
| **networkpolicies** | Core | NetworkPolicy | yes | One default-deny per component in both directions, plus the allows each declares |
| **runtime-policies** | Core | Kyverno | yes | The runtime `ClusterPolicy` objects, `Audit` or `Enforce` per `global.runtimePolicies.failureAction` |
| **postgres** | Core | CNPG Operator | yes | The CloudNativePG operator and one PostgreSQL cluster with the platform's databases |
| **artifact-store** | Core | Rust (RustFS, S3 API) | yes | Object-locked store for rendered schemas, compiled mappings, dumps, exports, app builds and the gateway's file cache ([ADR-N-015](../Decisions/adr-n-015-artifact-store-rustfs.md)) |
| **keycloak** | Core | Java | yes | The realm, its clients and its client scopes, including `mcp:portal` |
| **apisix** | Core | Lua / NGINX | yes | The standalone edge: the rendered route table, TLS, rate limiting |
| **openid-connect** | Core | APISIX plugin | yes | Part of `apisix`: the `openid-connect` plugin in session mode on the Portal host and every App on Demand route, through one confidential `edge` client per realm ([ADR-N-019](../Decisions/adr-n-019-login-at-the-edge-apisix-openid-connect.md)) |
| **gitea** | Core | Go | yes | The in-cluster forge, plus a bootstrap Job that creates the configuration repository, the teams and the tokens the Portal and the gateway read. Gitea Actions and the package registry are on for the application repositories, whose workflows run on `gitea-runner` (ADR-N-028) |
| **context-broker** | Core | Rust (Antares) | yes | The NGSI-LD broker over the shared schema with row-level security |
| **pipeline-runner** | Core | Bento | yes | The resident streams runner and the CronJobs for scheduled pipelines |
| **context-gateway** | Core | Rust (Axum) | yes | The Policy Enforcement Point, the query rewriter, the representation translators and the Data MCP server |
| **model-tools** | Core | Python (LinkML) | yes | Stateless generator behind the model editor: LinkML artifacts, schema-automator imports, mapping compilation |
| **portal** | Core | Rust + React | yes | One process: the Portal API, the embedded UI and the reconciler |
| **jcctl** | Core | Rust | part of `portal` | No workload of its own. The reconciler runs inside the Portal process, and `jcctl` is the CLI over the same manifests, shipped in the platform image |
| **observability** | Core | OpenTelemetry Collector | yes | Accepts OTLP, drops what is not on the allow-list, forwards the rest to the Portal's Activity stream |
| **audit-logging** | Core | Rust (Vector) | yes | Node collector shipping the audit stream of the gateway, Keycloak and the forge to object-locked storage, 90 days (OPS-42) |
| **sandbox-reaper** | Core | CronJob (kubectl) | yes | Deletes sandbox namespaces past their TTL, 14 day ceiling (OPS-44, PF-19) |
| **monitoring** | Core | Prometheus Operator | yes | No workload: one ServiceMonitor per component that exports metrics, and the edge PrometheusRule. Last in the list, because it scrapes the ones above it (OPS-16, TS-22) |
| **ckan** | Add-on | Python | no | The open-data catalogue on `data.<domain>`, with DCAT-AP publication (EP-62…EP-67) |
| **grafana** | Add-on | Go | no | Infrastructure observability and public data dashboards over Endpoint STA representations |
| **agent-runner** | Add-on | Rust | no | `jc-agent-proxy` from the platform image: the credential-free internal proxy an agent run reaches ([ADR-N-020](../Decisions/adr-n-020-agent-runner-and-credential-proxy.md), [Architecture/19](../Architecture/19-agent-runner.md)) |
| **functions** | Add-on | Rust | no | `jc-functions`, the QuickJS runtime of a generated application's serverless functions, called by the Portal alone ([Architecture/20 §3](../Architecture/20-app-sdk.md#3-functions-and-their-runtime)) |
| **demo-feeds** | Add-on | NATS | no | A demo broker and live publisher for a development cluster. Never in a production list |
| **frost** | Add-on | Java | not shipped | A dedicated SensorThings API broker for high-volume IoT series, fed through Endpoint STA representations |
| **geoserver** | Add-on | Java | not shipped | WFS and WMS for clients that cannot speak OGC API Features |
| **superset** | Add-on | Python | not shipped | Business intelligence over Endpoint SQL or CSV representations |
| **masterportal** | Add-on | JavaScript | not shipped | A 2D and 3D geoportal over Endpoint OGC Features representations |
| **openbao** | Add-on | Go | not shipped | Vault-compatible secret management. The Portal resolves a `secretRef` through it when `JC_PORTAL_OPENBAO_ADDR` names one; with no chart shipped, SOPS with age is the path every environment runs today |
| **dataspace-connector** | Add-on | not chosen | not shipped | Dataspace Protocol catalogue, negotiation and transfer; agreed ODRL policies become Endpoint grants ([ADR-N-016](../Decisions/adr-n-016-data-space-connector.md), DS-06). Not shipped until a data-space partner appears |

## 2. Enabling an Add-on

An add-on goes into the `components` list of `deployment/environments/<env>/global.yaml.gotmpl`. That list replaces the shipped one rather than extending it, and its order is the deploy order, so copy the shipped list and add to it:

```yaml
components:
  # the shipped list of defaults/environment/global.yaml, in its order
  - prepare
  # ...
  - portal
  # then what this environment adds
  - ckan
  - grafana
  - agent-runner
  - functions   # before portal, so the Portal is told its address
  - monitoring  # last: it scrapes everything above
```

A component in the last column as `not shipped` has no directory under `components/`, so naming it here fails the render rather than deploying nothing.

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
