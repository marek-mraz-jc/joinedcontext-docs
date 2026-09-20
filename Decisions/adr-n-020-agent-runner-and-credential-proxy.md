---
sidebar_position: 21
title: "ADR-N-020: The Agent Runner and the Credential-Free Internal Proxy"
---

# ADR-N-020: The Agent Runner and the Credential-Free Internal Proxy

Date: 2026-09-12  
Status: Accepted  
Decision Makers: product owner

## 1. Context

Autonomous AI agents generate purpose-built applications on demand by inspecting published LinkML schemas, AuthZEN access rules, and live NGSI-LD data. Giving an autonomous agent direct possession of platform credentials introduces catastrophic security risks:

1. **Credential Exfiltration**: A language model tricked by indirect prompt injection embedded in municipal sensor feeds could output platform credentials, forge tokens, or provider API keys into code, logs, commit trailers, or model context windows.
2. **Target Ambiguity and Privilege Escalation**: An agent with a broad cluster or forge token could target branches outside its assigned application scope, push unreviewed manifests to default branches, or query unauthorized context spaces.
3. **Audit Invalidation**: If agents execute actions under shared credentials or direct tokens without mediation, per-run token accounting and verifiable human co-attribution break down.

The platform requires an architecture where agents autonomously scaffold, code, test, and repair applications, while never possessing any credential for the model provider, the context broker, the Context Gateway, or the Git forge.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | Leverages the open-source OpenHands agent runtime in Kubernetes Jobs while mediating all upstream calls through a dedicated internal proxy service. |
| Technological consistency | **Full** | The proxy is implemented in Rust (`axum`), matching the Context Gateway and Portal API core stack. |
| Security by design | **Full** | Workspaces hold zero secrets; all tokens are injected per request by `jc-agent-proxy`. |
| Modular design | **Full** | The runner is packaged as an optional deployment addon; core context serving operates independently. |
| Multi-tenancy | **Full** | Workspace execution is isolated to dedicated namespaces; proxy routes enforce strict run-scoped parameters. |

## 3. Decision

1. **OpenHands Runtime as an Optional Addon**: The execution engine is based on the OpenHands agent runtime, deployed as an optional addon (`components/agent-runner`), pinned strictly by cryptographic container digest and signed.
2. **One Ephemeral Kubernetes Job per Run**: The Portal schedules one Kubernetes Job per run in a dedicated `agents` namespace. The Job pod enforces `automountServiceAccountToken: false`, runs with a read-only root filesystem, mounts a single `emptyDir` workspace volume, adheres to the restricted Pod Security Standard, and sets explicit resource requests, limits, and deadlines (`activeDeadlineSeconds`, `ttlSecondsAfterFinished`).
3. **Zero Credentials in the Workspace**: The workspace container receives no Kubernetes tokens, Secret mounts, or platform credentials. Its entire external environment is configured via `JC_PROXY_BASE` and `JC_RUN_TICKET`. The run ticket is generated per run, stored exclusively as an Argon2id hash in the Portal database, is invalidated upon run completion, and is unusable outside the internal proxy.
4. **Network Isolation via `jc-agent-proxy`**: The workspace pod is isolated by default-deny NetworkPolicies admitting egress only to `jc-agent-proxy` and cluster DNS (`kube-dns`). The proxy resolves credentials (`secretRef` for Keycloak client secret, forge token, and model API key) and injects them dynamically into upstream calls.
5. **Target Derivation by the Proxy**: The agent cannot choose or alter target parameters. Outbound requests to `/v1/data/*` omit slugs; the proxy injects the run's bound endpoint slug. Requests to `/v1/forge/*` are constrained strictly to the run's branch (`agent/app-{name}/{runId}`) and repository path (`projects/{project}/apps/{name}/`).
6. **Outward Event Streaming via Proxy**: The workspace does not communicate directly with the Portal. It posts lifecycle and conversation events to `/v1/runs/events`, which the proxy validates, enriches with run metadata, and forwards to the Portal's internal event endpoint under the proxy's authenticated service account.
7. **Read-Only Real Endpoint Access, Sandboxes for Writes**: Read-only applications consume live data directly through their generated, narrowed Endpoint. If an application declares a write operation (`updateAttrs`, `createEntity`), the reconciler provisions an isolated ephemeral sandbox space, ensuring production data cannot be modified during development.
8. **Token Metering and Model Gateway**: Model provider calls pass exclusively through `/v1/llm/*`. The proxy meters token consumption, enforces per-run budgets, and terminates execution upon budget exhaustion.
9. **Merge Requests for Publication**: The agent cannot push directly to `main` or auto-approve pull requests (AG-11). Publication creates a Gitea merge request classified into Green, Yellow, or Red interaction lanes.

### Alternatives Considered and Rejected

- **Direct Audience-Bound Tokens in Workspace**: Rejected because credentials in workspace memory can be exfiltrated via shell commands, core dumps, or prompt injection.
- **In-Browser Agent Execution**: Rejected because provider credentials would reside on client machines and compilation toolchains (`cargo`, `pnpm`) cannot run natively in standard browsers.
- **Egress-Only Host Allowlist**: Rejected because restricting IP destinations does not prevent an agent from using its valid bearer token to access unauthorized tenant resources on permitted hosts.
- **Configuration MCP as Source Write Path**: Rejected because Configuration MCP manages declarative platform manifests, not raw application source trees, and cannot provide directory-level commit isolation.

## 4. Consequences

### Positive

- **Absolute Credential Containment**: Compromise of an agent workspace exposes no durable keys, database passwords, or platform tokens.
- **Deterministic Blast Radius**: An agent can modify files only within its assigned application directory on its dedicated branch.
- **Auditable Provenance**: Every commit and API interaction is mapped to a discrete run record, agent identity, and human initiator.

### Negative / Trade-offs

- **Proxy Latency**: Upstream requests incur an additional in-cluster network hop through `jc-agent-proxy`.
- **Resource Footprint**: Running ephemeral builder jobs requires memory and CPU allocations for compilers and container sandboxes.

## 5. See Also

- Architecture: [19-agent-runner.md](../Architecture/19-agent-runner.md), [16-apps-on-demand.md](../Architecture/16-apps-on-demand.md).
- Requirements: [AG-33…AG-52](../Requirements/agents.md), [AP-42…AP-55](../Requirements/apps.md).
- Decisions: [ADR-N-014](adr-n-014-agent-runner-openhands-optional.md), [ADR-N-017](adr-n-017-fullstack-apps-oauth2-proxy-builder-agent.md), [ADR-N-019](adr-n-019-login-at-the-edge-apisix-openid-connect.md).

## Related

- [19-agent-runner.md](../Architecture/19-agent-runner.md) — architectural specification of the runner and proxy.
- [04-agent-runs.md](../API/04-agent-runs.md) — REST API contract for agent runs and streaming events.
- [00-register.md](00-register.md) — master architecture decision register.
