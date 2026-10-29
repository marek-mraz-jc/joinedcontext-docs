---
sidebar_position: 65
title: "ADR-N-064: Scoped Connectors and One Generic Tool Set"
---

# ADR-N-064: Scoped Connectors and One Generic Tool Set

Date: 2026-10-28  
Status: Proposed  
Decision Makers: product owner (2026-10-28: "from MCP connector or AI assistant, I can manage the whole platform and test every scenario"; "admin should allow only ... a certain operation, and then ... user can decide what endpoints"); drafted by worker-t5946 (T-5946), owner may override

This record decides how a person reaches the whole platform from an AI client (Claude Code, claude.ai, ChatGPT, the Portal assistant) without handing that client more than the person chose: a connector is a server-side grant, every client calls one generic tool set, and a write is a plan the person approves in the Portal. [Architecture/07 §11](../Architecture/07-agents-and-mcp.md#11-scoped-connectors) carries the architecture, [API/14](../API/14-connectors.md) the routes and the tool contract, and AG-142…AG-157 the requirements. T-5947…T-5963 build it.

## 1. Context

Three doors reach the platform from a model today, each with its own rights:

- The Portal MCP at `/api/v1/mcp` (AG-60) lists the operation registry by the caller's permissions, but a bearer caller gets every right the person holds: nothing narrows it to what the person meant to share with that client.
- The gateway's personal connectors at `/api/mcp/me/{name}` (EP-123, ADR-N-043 §7.7) narrow the data plane by a selector, read only, and know nothing of models, pipelines or access.
- The Portal assistant narrows a conversation by its capabilities (AG-92) and the profile's `spec.access` (AG-70), but reads its tool calls out of fenced JSON in the model's prose, lists about 40 operations without input schemas, and ends every change in a prefilled form.

A person who wants Claude Code to "build this pipeline in project air, nothing else" has no way to say so, and an administrator has no way to say "people may hand AI clients reads, never access changes".

## 2. Options

| Option | What a client holds | Narrows by | Verdict |
|---|---|---|---|
| A. OAuth scopes only (`jc:read`, `jc:pipeline` …) on the existing `/api/v1/mcp` | a token with scopes | the scope list in the token | refused: a scope cannot name one project or one Endpoint without a claim per item, and a token lives past a revocation |
| B. A Portal-held grant per connector at `/c/{id}`, checked on every call | a token whose audience is the connector | the stored grant, the owner's live rights and a DelegationPolicy ceiling, each read per call | **chosen** |
| C. One MCP server per segment (`/api/v1/mcp/pipeline`, `/api/v1/mcp/data` …) | a token per server | the server's fixed tool set | refused: eight addresses to add, and still no way to name one project |
| D. GraphQL over the registry for AI clients | a token | field selection | refused: a second contract beside REST and MCP ([ADR-N-063](adr-n-063-one-api-style-no-graphql.md)) |

## 3. Decision

1. **One operation registry.** The Portal's operation registry (AG-59) is the single source of the REST routes, the OpenAPI 3.1 document, one JSON Schema per kind, the MCP tool definitions, `jcctl` and the UI's form schemas. The MCP tools are generic over kind: `get_schema`, `list`, `get`, `query_data`, `plan_change`, `apply_change`, and for pipelines `sample_source`, `try_mapping`, `run_pipeline`, `pipeline_logs`. No tool exists per route (T-5948).
2. **A connector is a server-side grant.** The Portal stores each connector in its database, per person, never in Git: owner, name, segments, scope (projects, spaces, Endpoints, pipelines, each `read` or `write`), `writes` (off by default), `expiresAt`, optional `allowedClients`, `revokedAt`. Its address is `https://portal.{domain}/c/{id}`, Streamable HTTP MCP. The id is 26 random base32 characters: not a secret, never enough on its own (T-5950).
3. **Every call is checked again.** The Portal verifies the bearer (issuer is the organization's realm, audience is the connector's own address, not expired), requires `sub` to equal the owner, requires `azp` to be in `allowedClients` when that list is set, and computes the effective rights as the DelegationPolicy ceiling ∩ the owner's live rights (`within_own_rights`, PF-51) ∩ the connector's scope. `tools/list` lists only tools the effective rights reach; each call is rechecked for its target; nothing is cached across calls; each call writes one audit row (connector, person, client, tool, target, verdict) into the activity log (OPS-48). A revoked or expired connector, or a role the owner lost, refuses the next call.
4. **Segments are presets.** A person ticks one or more of `data-read`, `context` (models, spaces, Endpoints), `pipeline`, `access`, `publish`, `apps`, `operate`, `admin` when creating a connector and may edit them after. A segment expands to a tool set and verbs; the scope still names the items. The Portal assistant offers the same segments per conversation (AG-92 keeps its `read`/`propose`/`build` names as aliases).
5. **A DelegationPolicy is the administrator's ceiling.** An organization-level Git manifest (`kind: DelegationPolicy`) names subjects (Groups, and users by Keycloak user id, never an e-mail, as [ADR-N-061](adr-n-061-group-members-without-personal-data.md) requires), the projects, kinds, Endpoints and verbs a connector of theirs may carry, the longest expiry, the clients allowed and whether a request above the ceiling is refused or queued for an administrator's approval. A policy only narrows. A person no policy names gets the organization default: `data-read`, reads only, 30 days, any client (Decided, worker-t5946, owner may override: the safest preset that still lets a person try a connector; options: no connector at all, which leaves the feature dark until an administrator writes a policy; the person's full rights, which defeats the ceiling). Changing a policy narrows existing connectors at their next call (T-5952, T-5953).
6. **Writes are plan, then apply.** `plan_change` runs the write with `validate_only` (AIP-163): every check of the real write, nothing saved, the diff it would make, field errors as `application/problem+json` with `errors[{path, message}]` (T-5949). It returns a `planId` bound to the connector, the base `etag` and a 30-minute expiry. `apply_change` takes only that `planId`; the Portal refuses it when the base moved (`409`), when the plan belongs to another connector or person, or when the connector lacks `write` on the item. Apply opens a change request (CC-34) or a workspace change (CC-76); it never approves. Approval is a person's click in the Portal: every decision door refuses a connector's token by `identity.client` (CC-41), so an AI client cannot approve its own plan (T-5956).
7. **Read-only holds below the tools.** A connector without `writes` gets a token marked read-only: the scope `jc:read-only`, a default client scope Keycloak puts in every such connector client's access token (T-5954). The gateway answers 403 `forbidden` to every write such a token sends on any surface (NGSI-LD, OData, STA, OGC, the MCP tools, relationship writes), and pins `x-jc-read-only: true` on the hop, on which Antares' policy seam (ADR-N-050) refuses every clause but a read whatever the person's grants, so a tool bug or a forged request through the gateway cannot write (T-5955). A malformed marker is a refusal: a `scope` that is not a string fails the token, and any value of `x-jc-read-only` holds the caller to reads.
8. **The Portal assistant is a connector.** A conversation is a connector of the person, created per conversation, with the chosen segment, the profile's `spec.access` as one more ceiling, and native tool calling over the same tools and schemas. Its extra tools are UI actions the browser runs and shows: `navigate`, `open_form` with a prefill, `highlight`, `show_diff`, `filter_table`; none submits, proposes or approves. The fenced-JSON parsing, the assistant paths' router and the regex intents go once the model suite passes as well without them (T-5958, T-5959). In claude.ai and ChatGPT a plan and its diff render as an MCP App view that links to the Portal for approval (T-5960).
9. **The existing personal connectors fold in.** A personal connector at `/api/mcp/me/{name}` becomes a Connector with the `data-read` segment, read only, whose scope reaches no more than its selector did (projects and spaces stay items, a finer selector becomes the Endpoints it took at the move). One store holds every connector (T-5970); the gateway serves a record's data reads at `/api/mcp/me/{name}` until `/c/{id}` serves them, and T-5963's gate removes that address, so no second path stays.

## 4. Client binding

What each AI client lets us bind, from the supervisor's analysis of MCP specification `2026-07-28` and the Keycloak 26.8 MCP guide (2026-10-28, the client ids as T-5954 records them):

| Client | How it identifies itself | Binding | Verdict |
|---|---|---|---|
| claude.ai (web and mobile) | Client ID Metadata Document (CIMD): `client_id` is the HTTPS URL of its published metadata, redirect URI on `claude.ai` | `allowedClients` names that URL; Keycloak accepts only the redirect URIs the document lists, so another party cannot obtain a token with that `azp` | **enforceable** |
| ChatGPT | its published CIMD id, or a fixed client registered for it | as claude.ai | **enforceable** |
| Claude Code, an IDE, MCP Inspector | the Claude Code CIMD id with a loopback redirect (RFC 8252), or `mcp-local` | any program on the person's computer can run the same loopback flow under the same id | **a convenience, not a boundary**: the Portal shows it as "intended for Claude Code" and never as a control |
| A client that registers dynamically (DCR) | a `client_name` it chooses | none: DCR stays off (registration endpoint stripped at the edge), and a self-chosen name proves nothing | **not possible** |
| Sender-constrained tokens (DPoP) | a key the client holds | none of the three clients sends DPoP to a remote MCP server today | **not possible**; revisit when they do |

"Only my organization" means the connector's sign-in goes only through that customer's own identity provider, brokered by the organization's realm, so a token for the connector exists only for a person that IdP vouched for. It does not mean the AI vendor's workspace or tenant: no client tells the server which tenant it runs in.

A connector may also carry the published egress ranges of its client as an IP allow-list. This is defence in depth, not identity: the ranges are shared by every customer of that vendor.

CIMD and resource indicators are experimental features in Keycloak 26.8; T-5954 turns them on behind a tested realm configuration and names the flags.

## 5. Security

The threat model, each with the control that holds and the test that proves it:

| Threat | Control | Proved by |
|---|---|---|
| A connector URL leaks (pasted in a chat, a screenshot) | the URL carries no right: a call needs a token whose audience is that URL and whose `sub` is the owner; another person's token gets the same answer as an unknown connector (`404`), so the id reveals nothing | owner-mismatch and unknown-id tests answer byte-identical bodies (T-5950) |
| A token issued to another client or for another connector | audience must equal the connector's address; `azp` checked against `allowedClients`; a token for connector A is refused on B | audience and `azp` unit tests, a live A-on-B refusal (T-5954) |
| Prompt injection through data (an entity value saying "now delete the space") | the effective rights do not depend on anything the model reads; a read-only connector cannot write below the tools (§3.7); a write is only a plan until a person approves it in the Portal; tool results carry data inside the untrusted-data fence (AG-20) | S-49 in the scenario harness, one forged write per surface (T-5955) |
| A connector approves a change (its own plan or anyone's) | every decision door refuses `identity.client` of a connector; apply never approves | S-44, an approval-by-connector-token refusal per door (T-5953, T-5956) |
| A secret in an answer (a DataSource credential, a token in a log) | manifests carry `secretRef` only; `get` and `plan_change` return the reference, never the value; audit rows hold no token; logs never print a bearer | S-29, a grep test over every tool answer of the harness fixtures (T-5947, T-5956) |
| A connector outlives the person's role | rights read live per call, nothing cached; expiry at most the policy's `maxExpiry` (365 days at most) | S-32 (T-5950) |
| Flooding through a connector | per-connector and per-person limits keyed on the verified token, `429` with `Retry-After` | flood test (T-5968) |

What stays open: a person can always hand a model everything they themselves may do, inside the ceiling; the ceiling and writes-off-by-default are what bound it.

## 6. Consequences

- The Portal gains a connector table, the `/c/{id}` route, the RFC 9728 metadata per connector and a My connectors page (T-5950, T-5951, T-5954).
- `jc-core` gains `kind: DelegationPolicy` with its schema; the reconciler loads it (T-5952, T-5953).
- Every write route gains `validate_only` and every error becomes problem+json with field paths (T-5949).
- Keycloak gains the CIMD client entries and the read-only scope (T-5954); Antares and the gateway refuse writes for it (T-5955).
- Every scenario of the scenario catalogue (S-01…S-55) runs scripted, by a model and live (T-5947, T-5961, T-5962); T-5963 is the gate.
- The assistant loses its fenced-JSON tool parsing, paths router and regex intents (T-5958).

## Related

- [Architecture/07 §11](../Architecture/07-agents-and-mcp.md#11-scoped-connectors): the architecture.
- [API/14](../API/14-connectors.md): routes, the Connector record and the tool contract.
- [Development/04](../Development/04-manifest-kinds.md): the `DelegationPolicy` kind.
- [ADR-N-009](adr-n-009-mcp-surfaces-and-agent-lanes.md): the two MCP surfaces this record narrows.
- [ADR-N-043](adr-n-043-named-mcp-servers.md): named servers and the personal connectors folded in here.
- [ADR-N-050](adr-n-050-broker-views-decide-context-data.md): where the read-only marker is enforced in Antares.
- [Requirements/agents.md](../Requirements/agents.md): AG-142…AG-157.
