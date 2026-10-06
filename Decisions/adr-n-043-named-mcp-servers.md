---
sidebar_position: 44
title: "ADR-N-043: Named MCP Servers over Chosen Endpoints"
---

# ADR-N-043: Named MCP Servers over Chosen Endpoints

Date: 2026-10-06  
Status: Accepted  
Decision Makers: product owner (order of 2026-10-06, T-3154; the choices of section 2 were delegated in the order)

## 1. Context

The owner, 2026-10-06: "one MCP can have under the hood multiple NGSI-LD endpoints, like an aggregator", and "create UI also for managing it".

Two Data MCP surfaces exist today, both on the gateway:

- **One Endpoint, one URL** (`/api/endpoint/{slug}/mcp`, EP-24, EP-25): every tool reads the one Endpoint the path names.
- **The hub** (`/api/mcp`, [ADR-N-025](adr-n-025-one-mcp-connector-several-endpoints.md), EP-87, EP-88): one connector over every Endpoint a token may read, the Endpoint named by a required `endpoint` argument on every call, one Endpoint per call.

What neither gives: a server somebody **curates** — "the city's mobility data" as one address over the four Endpoints that hold it, across projects and spaces — that an AI client configures once, whose tool list speaks only of those Endpoints, and which answers "every bus stop" from all of them in one call. The hub lists whatever the token reaches and makes the agent fan out itself; a person handing a city's mobility data to an assistant should not have to hand over everything else they may read with it.

## 2. Decision

A **named MCP server** is a manifest, `kind: McpServer`, that a project (or the organization) declares over a list of member Endpoints. The gateway serves it at its own address with the hub's catalogue narrowed to its members, and a read may fan out across them.

1. **The kind.** `McpServer` lives in a project (`projects/{p}/mcp/{name}.yaml`) or in the organization (`mcp/{name}.yaml`, namespace `org`). Its `metadata.title` and `metadata.description` are what an AI client reads (`initialize.instructions` and `serverInfo`). `spec.members` names one to ten Endpoints by typed reference (`{kind: Endpoint, name, namespace}`; a member of another project names its project). `spec.audience` is `public`, `organization` or `project-list` (with `allowedProjects`), and may be no wider than the narrowest member's own audience: a public server only over public Endpoints. Declaring or widening a server to `public` takes the red lane and a publisher's approval (EP-16, PF-71).
2. **The address.** `https://{host}/api/mcp/{project}/{name}` (`org` for the organization's), stateless Streamable HTTP like the other two (SP-19). It is its own RFC 8707 resource, with protected-resource metadata (RFC 9728) under `/api/mcp/{project}/{name}/.well-known/oauth-protected-resource` and a Keycloak client `mcp-{project}-{name}` the reconciler renders like the per-Endpoint clients (public, PKCE S256, no secret, dynamic registration off). A token whose audience is the server reaches its members only; the edge audience (`context-gateway`) reaches the members its person's Policies grant; a public server answers an anonymous caller with each member's public grants. A token for one Endpoint or for the hub is refused here.
3. **The tools.** The hub's catalogue (ADR-N-025 §2): `list_endpoints` answers the members this caller may read, and every data tool takes `endpoint`, published as an `enum` of those members. `tools/list` lists a tool when at least one such member grants its operation.
4. **A read may fan out.** On the read tools (`query_entities`, `list_types`, `describe_schema`) `endpoint` is optional: absent, the call runs once per member this caller may read, in parallel, each run exactly as a call to that member's own MCP URL runs (its PDP with the caller's token, its projection, its rate limit). The answer is grouped, never blended: `structuredContent.results` holds one entry per member, `{endpoint, space, entities, total, nextCursor}`, in the order of `spec.members`. The same URN in two members' spaces is two entities in two entries ([ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md)). `limit` holds per member and paging is per member: `cursor` is then an object keyed by member slug, each value that member's own `nextCursor`. No filter, join, sort or count is computed across members: what one member's Policy allows is never combined with what another's allows.
5. **Writes never fan out.** Every tool that writes, subscribes or asks an elicitation requires `endpoint`, as on the hub.
6. **A member the caller may not read is silent.** It is absent from `list_endpoints` and the enum, the fan-out skips it, and no answer names it: naming it would tell a stranger it exists (SP-20). A member the caller may read that fails (timeout, unavailable, a refused operation) is named: the answer is `partial: true` with `failed: [{endpoint, reason}]` beside the members that answered.
7. **Limits.** At most ten members. Each member call has ten seconds and the whole call fifteen; a member past its time is a `failed` entry, not an error of the call. A call spends one request of the server's per-subject bucket and one of each member's own `(slug, caller)` bucket it touches, so a fan-out cannot be used to spend ten Endpoints' quota for the price of one.
8. **Audit.** Every member call writes the line a call to that member's URL writes, with the server's address beside the Endpoint slug, the tool and the subject.
9. **This amends ADR-N-025 §2.5 for named servers only.** The hub keeps one Endpoint per call; a named server's read may visit several, each visit an Endpoint's own call, answered apart. The joins, cross-Endpoint filters and blended results ADR-N-025 refused stay refused everywhere.

## 3. Security Analysis

The gateway's build task (T-3155) inherits each row as a failing test.

| Threat | Control |
|---|---|
| The server widens what a caller reads | Every member call is that Endpoint's own call with the caller's token: its PDP decides, its projection narrows. The server holds no identity and no grant of its own; a server over Endpoints the caller may not read answers nothing. Attack test: for every member and every tool, the server's answer is a subset of what the member's URL answers the same caller. |
| Privilege union across members | No computation crosses members (§2.4): results are grouped per member, never filtered, joined, sorted or counted together, so no answer depends on two Policies at once. |
| A refused member leaks its existence | Absent from `list_endpoints`, the enum and every answer; an `endpoint` outside the caller's list is answered with the bytes of an unknown slug (SP-20). |
| Data of one space shown as another's | Each result entry carries its `endpoint` and `space`; the same URN in two spaces stays two entities. |
| A token for one Endpoint used as a key to many | A token whose audience is one Endpoint, or the hub, is refused at a named server; a server token reaches its members only (PF-45, PF-46). |
| Quota multiplied by members | The server's per-subject bucket and each member's own bucket are both spent (§2.7). |
| A public server over non-public data | Validation refuses `audience` wider than the narrowest member; `public` takes the red lane and a publisher's approval; and each member call is still decided by that member's Policy, so a later narrowing of a member narrows the server at once. |
| A slow member stalls every call | Per-member and per-call deadlines; a member past its deadline is a `failed` entry and the rest still answer. |
| Prompt injection across members | An entity's text can make the agent ask another member; it gains nothing the token did not allow, and the curated member list bounds what it can reach. Accepted residual risk, as on the hub. |

## 4. Alternatives Considered

| Alternative | Why not |
|---|---|
| Blend the members' entities into one list | A list sorted or counted across members is a decision two Policies made together; grouping keeps each answer one Policy's. A client that wants one list concatenates. |
| One tool per member (`bikes__query_entities`) | The tool list grows with the members and a tool name becomes a routing channel (ADR-N-025 §5); the `endpoint` enum keeps one catalogue. |
| The hub with a saved allow-list per person | The allow-list is the person's at connect time; a curated server is the organization's statement of what belongs together, reviewed as a Change, and the same for everyone it admits. |
| Name a refused member in a partial answer | Tells a caller that an Endpoint exists that they may not read; the hub's rule (SP-20) holds here too. |
| Serve it from the Portal | Routes data through the Portal, which holds no data-plane grant (AG-04); the gateway already holds every member's PDP. |

## 5. Consequences

- **`jc-core`** gains `McpServer` (MF-53) with its validation; `jcctl` places it, waves it after Endpoints and validates its members and audience.
- **The gateway** serves `/api/mcp/{project}/{name}` from the McpServer manifests it loads beside the Endpoints, with the fan-out, the buckets and the audit field (T-3155).
- **The reconciler** renders `mcp-{project}-{name}`.
- **The Portal** lists, creates and edits servers as Changes, previews the merged tool list, and shows the address with a copy-ready client configuration (T-3156).
- **Conformance** gains the isolation suite of section 3 for a named server.

## 6. Requirements

Landed with this decision:

- `Requirements/endpoints.md`: **EP-92**…**EP-96**.
- `Requirements/manifests.md`: **MF-53**.

## Related

- [ADR-N-025](adr-n-025-one-mcp-connector-several-endpoints.md) — the hub, amended in §2.5 for named servers.
- [ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md) — an entity is its space and its URN.
- [Architecture/07-agents-and-mcp.md](../Architecture/07-agents-and-mcp.md) — the Data MCP surfaces.
- [Requirements/endpoints.md](../Requirements/endpoints.md) — EP-24, EP-25, EP-87, EP-88, EP-92…EP-96.
- [Requirements/space-surface.md](../Requirements/space-surface.md) — SP-14…SP-20.
