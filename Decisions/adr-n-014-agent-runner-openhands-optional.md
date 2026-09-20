---
sidebar_position: 15
title: "ADR-N-014: Optional Agent Runner Addon with OpenHands SDK"
---

# ADR-N-014: Optional Agent Runner Addon with OpenHands SDK

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

## 1. Context

Autonomous AI agents can perform routine data stewardship, anomaly analysis, pipeline troubleshooting, and blueprint creation. However, running autonomous agents within organisational environments poses acute security challenges:

1. Agents require an isolated sandbox runtime to execute tools without exposing the underlying Kubernetes node or host network.
2. The platform must avoid coupling itself to proprietary cloud AI services or specific closed-source agent runtimes.
3. Organizations with strict air-gapped or non-AI compliance postures must be able to deploy the platform with zero agent infrastructure installed.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Model-driven data flow | **Full** | Agent operates strictly over declarative manifests and standard MCP endpoints. |
| Distributed architecture with unified UX | **Full** | Agent confirmations surface directly in the Portal UI. |
| Modular design | **Full** | Completely decoupled addon; platform functions 100% without it. |
| Integrability via defined interfaces | **Full** | Connects to platform exclusively via standard MCP Streamable HTTP. |
| Open source as default | **Full** | OpenHands is open source under MIT. |
| Cloud-native architecture | **Full** | Containerized sandbox deployment with network isolation. |
| Standard solutions before custom code | **Full** | Uses established OpenHands Software Agent SDK rather than bespoke agent loops. |
| Self-contained deployment | **Full** | Can connect to self-hosted LLMs (vLLM, Ollama) or external APIs. |
| Technological consistency | **Full** | Addon deployed via standard Helmfile component packaging. |
| Multi-tenancy | **Full** | Agent runners provisioned per project or organization with strict token boundaries. |
| Security by design | **Full** | `ConfirmRisky` policy halts execution for human sign-off on any dangerous action. |

## 3. Decision

1. **Agent Runner as an Optional Addon**:
   - The agent execution runtime is decoupled from the platform core and packaged as an optional addon (`addons/agent-runner`).
   - Deployments that do not require autonomous agent features omit the addon entirely with zero impact on core functionality.
2. **OpenHands Software Agent SDK Foundation**:
   - The addon deploys a sandboxed runtime based on the **OpenHands Software Agent SDK** (MIT License).
   - Pre-configured with the platform's two MCP endpoints: Data MCP and Configuration MCP.
3. **Enforce `ConfirmRisky` Policy**:
   - The runtime enforces OpenHands' `ConfirmRisky(threshold=HIGH)` policy.
   - Any agent action involving Red-lane operations, destructive changes, or unexpected tool invocations is intercepted and routed to the Portal UI via the MCP Elicitation Protocol (AG-08, AG-09).
4. **Two runner profiles**:
   - `steward`: MCP only, egress to the LLM endpoint and the platform gateway.
   - `builder`: adds coding tools (shell, `cargo`, `pnpm`, `git`, test runners, headless browser) in an ephemeral workspace and internet access through the platform egress proxy with an allow-list (package registries, documentation hosts) and per-request logging; used by the `app-from-prompt` blueprint to build, test and repair apps without a person (AG-26…AG-28, AP-30…AP-33, [ADR-N-017](adr-n-017-fullstack-apps-oauth2-proxy-builder-agent.md)).
5. **Network and Workload Isolation**:
   - Agent runner pods execute with restricted non-root security contexts, read-only root filesystems, dropped capabilities, and strict egress NetworkPolicies allowing connections only to the LLM endpoint and the platform gateway.

## 4. Consequences

### Positive

- **Zero Core AI Bloat**: The platform core remains a deterministic, lean data infrastructure without heavy Python AI dependencies.
- **Human-in-the-Loop Safety**: Critical organisational infrastructure cannot be modified autonomously; high-risk actions always require human sign-off.
- **Provider Agnostic**: Operates with any OpenAI-compatible API, allowing organisationalities to switch between local sovereign LLMs (e.g., European open models via vLLM) and commercial APIs.

### Negative / Trade-offs

- Deploying the Agent Runner addon requires additional container resources (Python runtime, sandbox container).

## 5. See Also

- Decisions: [ADR-N-009 (MCP Surfaces & Agent Governance)](adr-n-009-mcp-surfaces-and-agent-lanes.md).
- Requirements: [AG-23…AG-28 (Agent Runner Addon and builder profile)](../Requirements/agents.md).
- Decisions: [ADR-N-017 (full-stack apps, oauth2-proxy, builder agent)](adr-n-017-fullstack-apps-oauth2-proxy-builder-agent.md).

## Related

- [ADR-N-009 (MCP Surfaces & Agent Governance)](adr-n-009-mcp-surfaces-and-agent-lanes.md) — referenced above.
- [AG-23…AG-28 (Agent Runner Addon and builder profile)](../Requirements/agents.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
