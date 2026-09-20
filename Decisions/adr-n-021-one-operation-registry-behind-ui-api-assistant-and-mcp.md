---
sidebar_position: 22
title: "ADR-N-021: One Operation Registry Behind the UI, the API, the Assistant, the Agents and MCP"
---

# ADR-N-021: One Operation Registry Behind the UI, the API, the Assistant, the Agents and MCP

Date: 2026-09-13  
Status: Proposed  
Decision Makers: product owner

## 1. Context

The 60-second units (find, share, analyse, load, build, model) must work the same way whoever drives them: a person clicking in the Portal, a script on the REST API, the in-process assistant, an autonomous agent in the runner, or an MCP client on a phone or in an IDE. Today each door has its own implementation:

1. The Portal UI calls kind-specific routes (`/projects/{p}/datasources`, `/pipelines/test`, `/changes/{id}/approve`, dry runs) and keeps the state of a half-filled form in the browser tab. A second window, a second Portal instance, or the assistant cannot see that state; a hand-off is a `prefill` blob pushed over SSE (UI-45) and lost on reload.
2. The in-process assistant (`src/agents/oneshot.rs`, 1 300 lines) recognises intents by hand (`search_catalog`, `propose_endpoint`, `compute_kpi`, the kit) and renders each result with its own code path. A new unit means a new branch in that file, a new card and a new API route, three times the same validation.
3. The Data MCP exists on the gateway per endpoint (SP-14…SP-16, AG-31, AG-32) and is the model for what works: the tool list is projected from the caller's grants, every call is validated against a published schema, tokens are audience-bound. The Configuration MCP (`jcctl serve --mcp`, CC-45, Architecture/07 §1.2) was specified and never built; `jcctl` has no MCP code and the configuration API lives in the Portal (changes, dry runs, git, permissions), not in the CLI.
4. Validation is scattered: dry run for manifests, `pipelines/test` for a pipeline, the model tools for a LinkML source, the reconciler for a change. A strict installation has no single place to say "nothing is proposed without a fresh green check".

The user's requirement (2026-09-13): MCP through the whole application, data source to context space to LinkML validation, futureproof; several windows and instances that can take a hand-off; the UI state and the validation gate shared by the agent, the assistant, MCP and the API; parts of the software may go.

What the field settled on in 2025-26, checked for this decision: one service layer with thin adapters so REST and MCP have feature parity ([Stainless](https://www.stainless.com/mcp/api-mcp-server-architecture-guide/), [compendium #50](https://github.com/brylie/compendium/issues/50)); few, workflow-shaped, namespaced tools with meaningful, token-cheap results rather than one tool per endpoint ([Anthropic, writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)); tools presented as a code API with progressive disclosure for agents that execute code ([Anthropic, code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)); generated MCP from OpenAPI is a start, curated tools perform better ([Speakeasy](https://www.speakeasy.com/mcp/tool-design/generate-mcp-tools-from-openapi), [FastMCP](https://gofastmcp.com/integrations/openapi)); MCP 2026-07-28 is stateless per request, with `server/discover`, structured tool output, tool annotations, elicitation in form and URL mode, resources and prompts, opt-in subscriptions and a Tasks extension for long-running calls ([MCP architecture](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture)); authorization is OAuth 2.1 with audience-bound tokens and RFC 9728 protected-resource metadata ([MCP authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)), which Keycloak covers today with a client scope carrying an audience mapper, RFC 8707 not yet ([Keycloak](https://www.keycloak.org/securing-apps/mcp-authz-server)).

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | MCP as published (Streamable HTTP, `server/discover`, elicitation, resources, prompts, Tasks), OAuth 2.1 on Keycloak, utoipa's JSON Schemas; no bespoke tool protocol. |
| Technological consistency | **Full** | One Rust module in the Portal (axum, serde `deny_unknown_fields`, sqlx); the UI stays a client of the plane (CC-48). |
| Security by design | **Full** | Every door runs the same permission check (PF-50), the same validation, the same lanes (CC-46); MCP tokens are audience-bound and the agent runner still sees no credential (ADR-N-020). |
| Modular design | **Full** | Operations are registered per kind; a unit adds operations, not doors. |
| Multi-tenancy | **Full** | Every operation is scoped by project and evaluated against the caller's bindings; drafts are per project. |

## 3. Decision

1. **One operation registry in the Portal.** Every action a person can take is an *operation*: a name (`jc_datasource_check`, `jc_datasource_propose`, `jc_pipeline_test`, `jc_pipeline_propose`, `jc_model_infer`, `jc_model_validate`, `jc_endpoint_propose`, `jc_change_approve`, `jc_kpi_compute`, `jc_catalog_search`, `jc_draft_put`, …), a JSON Schema draft-07 input and output (utoipa, the same schemas the OpenAPI document publishes), annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`), the roles it needs (PF-50) and the lane it takes (CC-70). One Rust function per operation in the service layer. The REST route, the assistant's tool, the agent proxy's tool and the MCP tool are adapters generated from the registry: they parse, resolve the caller, call the function, format. No door has a private implementation (CC-48). Operations are workflow-shaped (check, propose, approve, test, infer), not one per HTTP verb; the list stays short and namespaced `jc_`.
2. **A Portal MCP server at `/api/v1/mcp`** (Streamable HTTP, stateless, protocol 2026-07-28, `server/discover`): `tools/list` is the registry filtered by the caller's effective permissions, the way the Data MCP filters by grants; `resources/read` serves what a caller may read anyway (manifests, kinds' JSON Schemas, a model's LinkML and artifacts, a draft, a change's plan) so a model reads context without a tool call; `prompts/list` carries the units (load, share, analyse, model) as guided workflows. Results are structured (`structuredContent`, CC-47). Long calls (a pipeline test, a model inference, an agent run) answer through the Tasks extension. Authorization: bearer only, `aud` must name the Portal (a Keycloak client scope `mcp:portal` with an audience mapper until RFC 8707 lands), RFC 9728 protected-resource metadata and `WWW-Authenticate` as on the Data MCP (AG-32); the edge session is not accepted on this route. Rate and byte limits per token as on the endpoint façade.
3. **Drafts are shared state.** A `Draft` (Postgres, per project, kind and name) holds the manifest being worked on, its last `Verdict`, who last touched it (person, assistant run, MCP client id, API key) and a version. `jc_draft_put`, `jc_*_check` and `jc_*_propose` read and write drafts; the UI edits a draft, not local component state, and every window or instance subscribes to draft changes over the existing SSE activity stream (Architecture/09 §6) so a form the assistant filled appears in the open tab, a check the MCP client ran shows in the Portal, and the person can pick up or hand off at any step. `navigate`/`prefill` (UI-45) becomes "open this draft". A draft dies when its change is proposed or after an idle ceiling.
4. **One verdict, one gate.** Every check operation returns the same `Verdict {ok, findings[{level, path, message}], trace?, checkedAt, inputDigest}`: a manifest dry run, a pipeline test (PL-43), a LinkML validation (model tools), a schema validation, an endpoint access check. A propose operation refuses a draft whose verdict is missing, red or older than the draft's version with a structured error naming the check to run. In a **strict installation** (`platform.validation: strict` in the instance values) that refusal has no override; in a lax one a Green-lane draft may propose with a warning. Every door gets the same answer: the UI's button is disabled with the reason (UI-44), the assistant tells the person which check failed, the MCP client gets the error object, and an MCP call that needs a person (Yellow and Red lanes, `destructiveHint`) asks through elicitation (URL mode opening the draft in the Portal) rather than proceeding.
5. **The assistant and the agents use the registry, nothing else.** The in-process assistant becomes a model loop over the registry's tools (the model chooses `jc_catalog_search`, `jc_endpoint_propose`, …; the timeline records every call, AG-56). The agent runner reaches the Portal MCP through the proxy as its one tool server, with the tools presented as a code API (progressive disclosure; the runner writes scripts that call operations and filters data in its sandbox), which keeps AG-34…AG-41: the proxy injects the audience-bound token, the workspace holds none.
6. **What goes.** The hand-written intent switch and per-intent rendering in `oneshot.rs`; the browser-only form state and the `prefill` blob; the `jcctl serve --mcp` surface (CC-45 moves to the Portal MCP; `jcctl` stays the offline renderer and reconciler); the per-kind assistant routes (`/assistant/catalog`, `/assistant/propose-endpoint`) once their operations answer on the generic `POST /api/v1/projects/{p}/ops/{name}` route and the kind routes it keeps. Removal is one bigshot de-bloat pass per repository after the registry lands.

## 4. Alternatives Considered

- **Generate the MCP server from the OpenAPI document.** Cheapest start, but it produces one tool per route (about 80), which the field measures as worse for models than a curated dozen, and it leaves the assistant, the agents and the UI on their own paths. Rejected; the registry generates the OpenAPI *and* the MCP from one curated list instead.
- **Keep the Configuration MCP in `jcctl`.** The CLI has no session, no permissions model, no database and no reconciler state; every write would still have to go through the Portal's changes. Rejected; the Portal already is the configuration plane.
- **Client-side hand-off only (broadcast between tabs, `localStorage`).** Does not cross instances, users or the assistant; nothing to audit. Rejected.
- **Two validation regimes, one per door.** The reason the units drift today. Rejected.

## 5. Consequences

- Positive: one place to add a unit; every door proves the same behaviour, so one Playwright journey and one MCP conformance run cover the UI, the API and the agents; the recordings can hand off between the assistant and the form in the same take; strict installations have one switch.
- Negative: a migration (`drafts`), a registry to keep honest (a route that bypasses it is a defect), one more OAuth client scope in every realm; MCP clients that speak only 2025-06-18 need the compatibility shim the SDK ships.
- Requirements: AG-59…AG-64 (Requirements/agents.md §7), UI-47, UI-48 (Requirements/portal-and-ui.md), PF-57 (strict validation), CC-45 reworded to name the Portal MCP.
- Tasks: T-0635 (docs), T-0636 (registry and REST adapter), T-0637 (Portal MCP server and realm scope), T-0638 (drafts and UI subscription), T-0639 (verdicts and the strict gate), T-0640 (assistant and agents over the registry, de-bloat), T-0641 (MCP conformance and journeys).

## Related

- [Architecture/07-agents-and-mcp.md](../Architecture/07-agents-and-mcp.md)
- [Architecture/09-portal.md](../Architecture/09-portal.md)
- [Architecture/19-agent-runner.md](../Architecture/19-agent-runner.md)
- [Requirements/agents.md](../Requirements/agents.md)
- [Requirements/city-as-code.md](../Requirements/city-as-code.md)
- [ADR-N-020](adr-n-020-agent-runner-and-credential-proxy.md)
