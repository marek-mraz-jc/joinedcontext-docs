---
sidebar_position: 5
title: "Components & Optional Add-ons"
---

# Components & Optional Add-ons

Every directory under `components/` in `joinedcontext-deployment`, what it deploys, and which ones an installation adds rather than gets. The list below is that directory, so a component not in it is not deployable today.

## 1. The Components

Twelve are in the shipped `components` list of `defaults/environment/global.yaml` and make up a working installation; the rest are added to that list by an environment that wants them.

| Component | In the default list | Engine | What it deploys |
|---|---|---|---|
| **prepare** | yes | helmfile hooks | Creates the namespaces and annotates them for Linkerd injection and the inbound policy |
| **secrets** | yes | helm + SOPS | Generates every password the platform owns and resolves the ones an operator supplies |
| **networkpolicies** | yes | NetworkPolicy | The default-deny and per-component policies, and their Linkerd counterparts |
| **runtime-policies** | yes | Kyverno | Admission and runtime policies, `Audit` or `Enforce` per `global.runtimePolicies.failureAction` |
| **postgres** | yes | CloudNativePG | The operator and one PostgreSQL cluster with the platform's databases |
| **artifact-store** | yes | Rust (RustFS, S3 API) | Object-locked store for rendered schemas, compiled mappings, dumps, exports, app builds and the gateway's file cache ([ADR-N-015](../Decisions/adr-n-015-artifact-store-rustfs.md)) |
| **keycloak** | yes | Java | The realm, its clients and its client scopes, including `mcp:portal` |
| **apisix** | yes | Lua / NGINX | The standalone edge: the rendered route table, TLS, rate limiting, and the `openid-connect` plugin in session mode that logs every person in through the `edge` client ([ADR-N-019](../Decisions/adr-n-019-login-at-the-edge-apisix-openid-connect.md)) |
| **gitea** | yes | Go | The in-cluster forge, plus a bootstrap Job that creates the configuration repository, the teams and the tokens the Portal and the gateway read. Gitea Actions is off: the component deploys no runner |
| **context-broker** | yes | Rust (Antares) | The NGSI-LD broker over the shared schema with row-level security |
| **pipeline-runner** | yes | Bento | The resident streams runner and the CronJobs for scheduled pipelines |
| **context-gateway** | yes | Rust (axum) | The Policy Enforcement Point, the query rewriter, the representation translators and the Data MCP server |
| **model-tools** | yes | Python (LinkML) | Stateless generator behind the model editor: LinkML artifacts, schema-automator imports, mapping compilation |
| **portal** | yes | Rust + React | One process: the Portal API, the embedded UI and the reconciler |
| **observability** | yes | OpenTelemetry Collector | Fills the Portal's Activity stream |
| **audit-logging** | yes | Rust (Vector) | Ships the audit stream of the gateway, Keycloak and the forge to object-locked storage, 90 days (OPS-42) |
| **sandbox-reaper** | yes | CronJob (kubectl) | Deletes sandbox namespaces past their TTL, 14 day ceiling (OPS-44, PF-19) |
| **monitoring** | yes | Prometheus Operator | Scrape configuration and edge alerting, last in the list because it scrapes the components above it (OPS-16, TS-22) |
| **ckan** | added | Python | The open-data catalogue on `data.<domain>`, with DCAT-AP publication |
| **grafana** | added | Go | Infrastructure observability and public data dashboards |
| **agent-runner** | added | Rust | `jc-agent-proxy` from the platform image: the credential-free internal proxy an agent run reaches ([ADR-N-020](../Decisions/adr-n-020-agent-runner-and-credential-proxy.md), [Architecture/19](../Architecture/19-agent-runner.md)) |
| **functions** | added | Rust | `jc-functions`, the QuickJS runtime of a generated application's serverless functions, called by the Portal alone ([Architecture/20](../Architecture/20-app-sdk.md) §3) |
| **demo-feeds** | added | NATS | A demo broker and live publisher for a development cluster. Not a platform component and never in a production list |

There is no `jcctl` component: the reconciler is part of the Portal, and `jcctl` is the CLI over the same manifests ([00-intro.md](00-intro.md) §1).

### Named in the architecture, not deployable yet

These have a decision or a requirement behind them and no directory under `components/`, so adding one to a `components` list fails the render: **frost** (a dedicated SensorThings broker for high-volume IoT), **geoserver** (WFS and WMS), **superset** (BI and SQL reporting), **masterportal** (a 2D and 3D geoportal), **openbao** (Vault-compatible secret management), and **dataspace-connector** (the Dataspace Protocol catalogue, negotiation and transfer, whose engine is not chosen and which is not shipped until a data-space partner appears, [ADR-N-016](../Decisions/adr-n-016-data-space-connector.md), DS-06).

## 2. Enabling an Add-on

An added component goes into the `components` list of `deployment/environments/<env>/global.yaml.gotmpl`. That list replaces the shipped one rather than extending it, and its order is the deploy order, so copy the shipped list and add to it:

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
  - functions   # before portal if the Portal is to be told its address
  - monitoring  # last: it scrapes everything above
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

The component deploys one release: **`proxy`**, the Rust `jc-agent-proxy` daemon, one replica in `development` and two in `production`. It reads its Keycloak, Gitea and model-provider credentials by `secretRef` and holds none of them in its values.

The workspace namespace with its quotas and policies, and the seeded `app-builder` `AgentProfile` and `app-from-prompt` `Blueprint`, are not separate releases of this component: the namespace is prepared by `prepare` and `networkpolicies`, and the seed manifests live in the configuration repository the Portal reconciles.

### Configuration Parameters

The component has one release, `proxy`, from `charts/workload`. Its whole environment surface is six keys:

```yaml
agent-runner:
  proxy:
    enabled: true
    # Defaults to the instance namespace, or `{instanceSlug}-agent-runner` when
    # singleNamespace is false.
    namespace: dev
    # The project whose endpoints the proxy's own client may read. Its Keycloak client is
    # `{project}-agent-proxy` and the ServiceAccount manifest of that name in that project is
    # what the gateway resolves its token to (PF-46).
    project: helsinki
    # An OpenAI-compatible API by default; `anthropic` switches the proxy to the Messages API.
    modelBase: https://openrouter.ai/api/v1
    modelProvider: openai-compatible
    # One key, `key`, in this Secret in the proxy's namespace. Operator-supplied: never
    # generated, never committed. Declare it through the `secrets` component and SOPS.
    modelKeySecret: agent-runner-model-key
```

The image is the platform image (`ghcr.io/marek-mraz-jc/joinedcontext-platform`, pinned by digest in `components/agent-runner/images.yaml`), which carries `jc-agent-proxy` beside the gateway and `jcctl`. Resources come from `components/agent-runner/values/proxy/<profile>-values.yaml.gotmpl`: 50m CPU and 64Mi requested in `development`, 100m and 128Mi in `production` with two replicas.

### Network Policies & Isolation

- **Workspace Pods**: Egress is strictly limited to the `jc-agent-proxy` Service on port 8080 and `kube-dns` on port 53. Ingress is completely blocked.
- **Agent Proxy**: Ingress is permitted only from pods within the `agents` namespace. Egress is permitted to Context Gateway, Gitea, Keycloak, Portal API, and the designated model provider address.
- **Edge Routing**: The proxy is an internal service only; it is not published in `apisix.yaml` and cannot be reached from outside the cluster.

### Verification

```bash
kubectl exec deploy/portal -c portal -- wget -qO- http://jc-agent-proxy:8080/healthz
kubectl get networkpolicies
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

- [00-intro](00-intro.md) — the stack these components make up.
- [03-configuration](03-configuration.md) — the values each component reads.
- [02-installation](02-installation.md) — where the `components` list is written.
- [19-agent-runner](../Architecture/19-agent-runner.md) — what the agent-runner proxy refuses and why.
- [01-runbooks](../Operations/01-runbooks.md) — what to do when it breaks.
- [13-security](../Architecture/13-security.md) — the security model being deployed.
