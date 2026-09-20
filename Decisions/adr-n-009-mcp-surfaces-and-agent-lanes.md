---
sidebar_position: 10
title: "ADR-N-009: Model Context Protocol Surfaces and Agent Governance"
---

# ADR-N-009: Model Context Protocol Surfaces and Agent Governance

Date: 2026-09-05  
Status: Superseded  
Superseded by: [ADR-N-021](adr-n-021-one-operation-registry-behind-ui-api-assistant-and-mcp.md)  
Decision Makers: Architecture Board

:::note Read this with ADR-N-021
Decision 2 names two MCP surfaces. The Data MCP is what the gateway serves today, at
`/cs/{space}/mcp` and `/api/endpoint/{endpointSlug}/mcp`, exactly as written. The
Configuration MCP is not: `jcctl serve --mcp` was never built — `crates/jcctl/src` has no MCP
module — and the configuration surface is the Portal's `POST /api/v1/mcp`, one adapter over
the operation registry
([ADR-N-021](adr-n-021-one-operation-registry-behind-ui-api-assistant-and-mcp.md)). The agent
lanes of decision 3 and the principal rules of decision 1 stand unchanged and are enforced
today. Nothing below is rewritten: this is the decision as it was taken on 2026-09-05, and
what replaced half of it (T-2228).
:::

## 1. Context

Autonomous AI agents (large language models operating via tools) increasingly interact with organisational data platforms as analysts, operational assistants, and integration developers.

Allowing AI agents to access organisational platforms introduces grave security risks:

1. **Prompt Injection**: Malicious instructions embedded in sensor observations or external payloads could hijack an agent with elevated platform privileges.
2. **Accidental Deletion / Corruption**: Unbounded agents issuing direct API write calls can cause rapid, catastrophic data loss.
3. **Privilege Creep**: Treating agents as superusers bypasses the platform's relationship-based access control and audit accountability.

We need a standardized, secure architecture for AI agent integration that preserves digital sovereignty.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Model-driven data flow | **Full** | Tool surfaces generated dynamically from LinkML schemas and Policy entities. |
| Distributed architecture with unified UX | **Full** | Portal surfaces agent proposals and elicitation prompts to human operators. |
| Modular design | **Full** | MCP servers operate as standard protocol adapters over core APIs. |
| Integrability via defined interfaces | **Full** | Conforms to Anthropic Model Context Protocol (MCP) 2026-07-28 specification. |
| Open source as default | **Full** | Uses open-source `rmcp` Rust SDK and OpenHands SDK. |
| Cloud-native architecture | **Full** | Stateless Streamable HTTP transport integrates with standard API gateways. |
| Standard solutions before custom code | **Full** | Implements standard MCP Elicitation and RFC 9728 OAuth metadata. |
| Self-contained deployment | **Full** | MCP servers run in-cluster with zero third-party AI cloud dependencies. |
| Technological consistency | **Full** | Server implemented in Rust as part of Context Gateway and `jcctl`. |
| Multi-tenancy | **Full** | Data MCP strictly scoped per Context Space / Endpoint slug. |
| Security by design | **Full** | Agents are ordinary principals; destructive actions gated by human elicitation. |

## 3. Decision

1. **Agents as Ordinary Principals**:
   - AI agents MUST authenticate under distinct Keycloak identities or delegated user sessions (OAuth 2.1 RFC 8693 token exchange). Ambient administrative privileges are prohibited (AG-01).
2. **Dual Decoupled MCP Surfaces**:
   - **Data MCP Façade** (`/cs/{space}/mcp` and `/api/endpoint/{endpointSlug}/mcp`): Serves data-plane queries, schema descriptions, and subscriptions. Scope is hard-bound to the path/token; cross-space enumeration is impossible (SP-14, AG-04).
   - **Configuration MCP** (`jcctl serve --mcp`): Exposes management tools (`plan`, `propose_change`, `get_live_state`). Direct writes to the broker are banned; all changes are proposed as Git merge requests (CC-46, AG-06).
3. **Interaction Approval Lanes (CC-63, AG-10)**:
   - *Green Lane*: Read queries, local scratch sandbox experiments, auto-approved.
   - *Yellow Lane*: Project-level pipelines, data models, endpoints. Requires 1 human domain approver.
   - *Red Lane*: Federation topologies, access policies, deletions, public endpoints. Requires formal multi-party sign-off.
4. **Tool Annotations and Elicitation**:
   - Tools carry `readOnlyHint` and `destructiveHint` attributes. High-risk operations trigger the MCP Elicitation Protocol, pausing execution until approved by a human operator in the Portal UI (AG-08, AG-09).
5. **Attribution**:
   - Agent Git commits carry the agent's identity as author, plus `Co-Proposed-By` trailers identifying the initiating human user (AG-18).

## 4. Consequences

### Positive

- **Prompt Injection Containment**: Ingested data payloads can never execute arbitrary commands; agents cannot bypass Git review lanes regardless of their prompt instructions.
- **Standardized Tool Integration**: Any compliant MCP client (Claude Code, OpenHands, custom agents) can operate the platform without proprietary SDKs.
- **Complete Audit Trail**: Every agent proposal is diffable and tracked in Git history (CC-44).

### Negative / Trade-offs

- Interactive agent operations in the Yellow and Red lanes cannot complete synchronously; the agent must handle asynchronous approval pauses.

## 5. See Also

- Requirements: [AG-01…AG-28 (Agents)](../Requirements/agents.md), [SP-14…SP-20 (Space MCP)](../Requirements/space-surface.md).
- Decisions: [ADR-N-014 (Agent Runner Addon)](adr-n-014-agent-runner-openhands-optional.md).

## Related

- [AG-01…AG-28 (Agents)](../Requirements/agents.md) — referenced above.
- [SP-14…SP-20 (Space MCP)](../Requirements/space-surface.md) — referenced above.
- [ADR-N-014 (Agent Runner Addon)](adr-n-014-agent-runner-openhands-optional.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
