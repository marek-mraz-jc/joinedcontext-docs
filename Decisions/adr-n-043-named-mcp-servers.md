---
sidebar_position: 44
title: "ADR-N-043: Named MCP Servers over Chosen Endpoints"
---

# ADR-N-043: Named MCP Servers over Chosen Endpoints

Date: 2026-10-06  
Status: Accepted  
Amended: 2026-10-17 (section 7, connector profiles, T-4504)  
Decision Makers: product owner (order of 2026-10-06, T-3154; the choices of section 2 were delegated in the order)

## 1. Context

The owner, 2026-10-06: "one MCP can have under the hood multiple NGSI-LD endpoints, like an aggregator", and "create UI also for managing it".

Two Data MCP surfaces exist today, both on the gateway:

- **One Endpoint, one URL** (`/api/endpoint/{slug}/mcp`, EP-24, EP-25): every tool reads the one Endpoint the path names.
- **The hub** (`/api/mcp`, [ADR-N-025](adr-n-025-one-mcp-connector-several-endpoints.md), EP-87, EP-88): one connector over every Endpoint a token may read, the Endpoint named by a required `endpoint` argument on every call, one Endpoint per call.

What neither gives: a server somebody **curates** — "the city's mobility data" as one address over the four Endpoints that hold it, across projects and spaces — that an AI client configures once, whose tool list speaks only of those Endpoints, and which answers "every bus stop" from all of them in one call. The hub lists whatever the token reaches and makes the agent fan out itself; a person handing a city's mobility data to an assistant should not have to hand over everything else they may read with it.

## 2. Decision

A **named MCP server** is a manifest, `kind: McpServer`, that a project (or the organization) declares over a list of member Endpoints. The gateway serves it at its own address with the hub's catalogue narrowed to its members, and a read may fan out across them.

1. **The kind.** `McpServer` lives in a project (`projects/{p}/mcp/{name}.yaml`) or in the organization (`mcp/{name}.yaml`, namespace `org`). Its `metadata.title` and `metadata.description` are what an AI client reads (`initialize.instructions` and `serverInfo`). `spec.members` names one to ten Endpoints by typed reference (zero to ten beside a selector since §7) (`{kind: Endpoint, name, namespace}`; a member of another project names its project). `spec.audience` is `public`, `organization` or `project-list` (with `allowedProjects`), and may be no wider than the narrowest member's own audience: a public server only over public Endpoints. Declaring or widening a server to `public` takes the red lane and a publisher's approval (EP-16, PF-71).
2. **The address.** `https://{host}/api/mcp/{project}/{name}` (`org` for the organization's), stateless Streamable HTTP like the other two (SP-19). It is its own RFC 8707 resource, with protected-resource metadata (RFC 9728) under `/api/mcp/{project}/{name}/.well-known/oauth-protected-resource` and a Keycloak client `mcp-{project}-{name}` the reconciler renders like the per-Endpoint clients (public, PKCE S256, no secret, dynamic registration off). A token whose audience is the server reaches its members only; the edge audience (`context-gateway`) reaches the members its person's Policies grant; a public server answers an anonymous caller with each member's public grants. A token for one Endpoint or for the hub is refused here.
3. **The tools.** The hub's catalogue (ADR-N-025 §2): `list_endpoints` answers the members this caller may read, and every data tool takes `endpoint`, a member by its slug, title or space (ADR-N-025 §2), never published as an enum. `tools/list` lists a tool when at least one such member grants its operation.
4. **A read may fan out.** On the read tools (`query_entities`, `list_types`, `describe_schema`) `endpoint` is optional: absent, the call runs once per member this caller may read, in parallel, each run exactly as a call to that member's own MCP URL runs (its PDP with the caller's token, its projection, its rate limit). The answer is grouped, never blended: `structuredContent.results` holds one entry per member, `{endpoint, space, entities, total, nextCursor}`, in the order of `spec.members`. The same URN in two members' spaces is two entities in two entries ([ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md)). `limit` holds per member and paging is per member: `cursor` is then an object keyed by member slug, each value that member's own `nextCursor`. No filter, join, sort or count is computed across members: what one member's Policy allows is never combined with what another's allows.
5. **Writes never fan out.** Every tool that writes, subscribes or asks an elicitation requires `endpoint`, as on the hub.
6. **A member the caller may not read is silent.** It is absent from `list_endpoints`, no name resolves to it, the fan-out skips it, and no answer names it: naming it would tell a stranger it exists (SP-20). A member the caller may read that fails (timeout, unavailable, a refused operation) is named: the answer is `partial: true` with `failed: [{endpoint, reason}]` beside the members that answered.
7. **Limits.** At most ten members. Each member call has ten seconds and the whole call fifteen; a member past its time is a `failed` entry, not an error of the call. A call spends one request of the server's per-subject bucket and one of each member's own `(slug, caller)` bucket it touches, so a fan-out cannot be used to spend ten Endpoints' quota for the price of one.
8. **Audit.** Every member call writes the line a call to that member's URL writes, with the server's address beside the Endpoint slug, the tool and the subject.
9. **This amends ADR-N-025 §2.5 for named servers only.** The hub keeps one Endpoint per call; a named server's read may visit several, each visit an Endpoint's own call, answered apart. The joins, cross-Endpoint filters and blended results ADR-N-025 refused stay refused everywhere.

## 3. Security Analysis

The gateway's build task (T-3155) inherits each row as a failing test.

| Threat | Control |
|---|---|
| The server widens what a caller reads | Every member call is that Endpoint's own call with the caller's token: its PDP decides, its projection narrows. The server holds no identity and no grant of its own; a server over Endpoints the caller may not read answers nothing. Attack test: for every member and every tool, the server's answer is a subset of what the member's URL answers the same caller. |
| Privilege union across members | No computation crosses members (§2.4): results are grouped per member, never filtered, joined, sorted or counted together, so no answer depends on two Policies at once. |
| A refused member leaks its existence | Absent from `list_endpoints` and every answer, and no name resolves to it; an `endpoint` outside the caller's list is answered with the bytes of an unknown slug (SP-20). |
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

Landed with the amendment of section 7:

- `Requirements/endpoints.md`: **EP-120**…**EP-123**.
- `Requirements/manifests.md`: **MF-55**, **MF-56**.
- `Requirements/portal-and-ui.md`: **UI-98**.

Landed with the amendment of section 9:

- `Requirements/endpoints.md`: **EP-141**.

## 7. Amendment 2026-10-17: Connector Profiles (T-4504)

The owner, 2026-10-17: each group of people, each assistant and each agent gets a connector that shows the part of the platform it needs, filtered by access and preference. A hand-kept list of ten members does not reach that at 10,000 Endpoints, and nothing gave an organization or an assistant a connector of its own.

Decided (worker-1, owner may override): selectors on the existing kind, one built-in server per organization, personal connectors held in the person's Portal preferences; options: a new `ConnectorProfile` kind (a second kind for the same address and the same rules), personal connectors as manifests in Git (every reviewer would read a person's choice), favourites carried in the token (a token per change of a star, and a claim that grows with the list).

1. **`spec.select` beside `spec.members`.** A server names `members` (zero to ten, the limit of §2.7 unchanged), `select`, or both; at least one. `select` holds up to five fields, each a list of at most 50 values, and an Endpoint is selected when it matches every field given (one value of a field is enough): `projects` (project names), `spaces` (`{project}/{space}`), `domains` (Smart Data Models domains of the Endpoint's classification, T-4498), `themes` (EU data-theme codes of that classification, `ENVI`, `TRAN`, …) and `accessLevel` (`public`, `organization`, `project`, `grant`, the levels of the per-caller catalogue, T-4503). `select: {}` selects every Endpoint the other bounds admit. A server's reach is the union of its members and its selected Endpoints.
2. **A selector resolves at read time and only narrows.** On every call the gateway takes the Endpoints this caller's token may read (the hub's reach, ADR-N-025), keeps those the selector matches and whose own audience is at least as wide as the server's, and adds the readable members. A public server therefore selects public Endpoints only, an organization server public and organization ones, whatever its selector says. A selector names no Endpoint, so it can never add one the token does not read, and an Endpoint that leaves a selector's match (another theme, a narrower audience) leaves the server at the next reload of the Endpoint table, with no Change to the server.
3. **Validation.** `jcctl validate` refuses an `accessLevel` value wider than the server's audience allows (a `public` server with `organization`, `project` or `grant`; an `organization` server with `project` or `grant`), an unknown domain or theme code, a `spaces` or `projects` value naming nothing the repository declares, and a server with neither `members` nor `select`.
4. **Fan-out stays at ten.** A read without `endpoint` (§2.4) fans out when the caller's resolved reach holds at most ten Endpoints, in the order members first, then selected ones by slug. Above ten it is refused with a sentence naming `list_endpoints` and the `catalog` endpoint (T-4501), so a selector never turns one call into a thousand.
5. **`org/all`, one per organization.** Every organization has a server at `/api/mcp/org/all` with `audience: organization` and `select: {}`, served without a manifest and with its Keycloak client `mcp-org-all` rendered by the reconciler like any other. An organization that declares `mcp/all.yaml` replaces it (its own title, description, selector or audience, never wider than `organization` unless it takes the red lane of §2.1).
6. **An AssistantDeployment names its server.** `spec.mcpServer` names one McpServer (`{project}/{name}` or `org/{name}`); its reach becomes the deployment's data connector beside or instead of `connectors`. A deployment on a channel other than `internal` names a `public` server only.
7. **Personal connectors.** A person creates up to ten connectors in the Portal, each a name and a `select` with one more field, `endpoints` (up to 50 Endpoint slugs, the person's favourites). They live in that person's Portal preferences (API/01 §8), never in Git, are served at `/api/mcp/me/{name}` to that person's token only, and the gateway reads them from the Portal by the token's `sub` (a ServiceAccount call, cached for a minute). Another person's token at that address gets the bytes of an unknown server; no listing, audit view or catalogue shows one person's connectors to another. A favourite the person can no longer read is dropped from the reach like any other.

| Threat | Control |
|---|---|
| A selector widens what a caller reads | The reach starts from the token's own reach and is only filtered; a selector never names an Endpoint. Test: for every selector, the reach is a subset of the hub's reach for the same token. |
| A public server selects internal data | The audience bound of §7.2 holds at read time, and validation refuses an `accessLevel` wider than the audience. |
| A selector reveals an Endpoint outside the grants | Counts, `list_endpoints`, refusals and the over-ten sentence are all computed after the token's reach, so none names or counts an Endpoint the caller cannot read. |
| One person's favourites seen by another | Held per `sub` in the preferences tier; the address answers its owner's token only and an unknown-server answer otherwise. |
| A fan-out over thousands of Endpoints | Fan-out only up to ten (§7.4); above that the caller searches the catalogue first. |

## 8. Amendment 2026-10-18: Knowledge Sources on a Server (T-4659)

The owner, 2026-10-18: the pages and documents the assistants read (the crawled websites of the publishers) are a platform feature anyone can use. Whoever adds a connector queries them with their own model, so the platform spends no model call on that question.

Decided (worker-4, owner may override): the server names its sources, and the gateway asks `jc-assistant` for the passages; options: a source names the servers it joins (a project would place its pages on another's server), the gateway reading the assistant's database itself (a second writer's schema in the gateway), a separate RAG service (a second copy of the index and its embedding model).

1. **`spec.knowledgeSources`.** An McpServer attaches up to 20 `KnowledgeSource`s, `{source}` of its own project or `{project}/{source}` (MF-57). Only `visibility: public` sources may be attached, whatever the server's audience, so no source reaches a caller its own visibility would not. The hub, which has no manifest, attaches the list of the gateway's `JC_GATEWAY_HUB_KNOWLEDGE_SOURCES` setting, which the platform's owner holds in the deployment.
2. **The tool.** A server with at least one source lists `search_documents` (EP-133) beside `search`, which finds Datasets. Its description is built from the attached sources at load: the publishers' names, the passages' languages with their shares, and the advice to ask in the commonest one, because the full-text half of the search matches words of that language best.
3. **The call.** The gateway posts the query and the attached sources to `jc-assistant`'s `/internal/v1/search` (AG-119) on the cluster network. It runs the chat's hybrid search with the local embedding model and no model call, and answers the passages with the metadata of their page or document (AG-120).
4. **Limits.** One call embeds one query on the assistant's CPU. A bucket of 30 calls a minute per caller and one of 600 a minute for the gateway (EP-134) bound that work on the node, beside the server's own bucket.

| Threat | Control |
|---|---|
| A private or test source served to anyone | Only `visibility: public` sources can be attached, validated by `jcctl` and checked again by the assistant on every call; an eval or test source is never attached to a server. |
| Instructions planted in a crawled page | Hits are data: the tool's description and every hit say the text is quoted content of the publishers' pages. The calling assistant's own rules apply, as for a web search. |
| The internal route reached from outside | The edge routes `/api/v1/d/*` alone; the assistant refuses a proxied request with `404`, and a NetworkPolicy admits the gateway alone. |
| CPU spent on embeddings by a burst | The per-caller and global buckets of §8.4. |

## 9. Amendment 2026-10-19: A Public Server Reads Only (T-4750)

The owner, 2026-10-19: a public assistant points at one server whose Endpoints and sources a person picked, and it must not be able to run anything harmful or call out through the `endpoint` argument.

Decided (worker-6, owner may override): a public server is read-only for every caller, and `endpoint` stays a name inside the caller's reach; options: read-only only without a token (today's rule; a steward's token could write through a server built for the public), a per-server `readOnly` flag (one more field whose wrong value opens writes).

1. **Read tools only.** A server with `audience: public` lists the tools an anonymous caller may call and refuses every other tool by name before it resolves an Endpoint, whoever calls. A member that grants writes is written through its own URL, under its own Policy (EP-141).
2. **`endpoint` is a name.** It resolves among the caller's reach alone (§2.6), by slug, title or space; it is never parsed as an address and never fetched. A miss answers the same sentence whether the name is unknown, outside the reach or not a name at all, with the closest names of the reach.
3. **No outbound call.** No tool takes a URL; the gateway asks the member's broker on the cluster network, and an answer or error names no cluster-internal host.

| Threat | Control |
|---|---|
| A write through a public server with a steward's token | §9.1: the tool is refused by name before routing. |
| `endpoint` as a URL, `../`, an IP or another project's slug | §9.2: resolved inside the reach only; a miss sends no broker request. |
| A planted instruction asks the model to call an outside host | §9.3: no tool takes a URL; the model reaches only the server's read tools on its reach. |

## Related

- [ADR-N-025](adr-n-025-one-mcp-connector-several-endpoints.md) — the hub, amended in §2.5 for named servers.
- [ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md) — an entity is its space and its URN.
- [Architecture/07-agents-and-mcp.md](../Architecture/07-agents-and-mcp.md) — the Data MCP surfaces.
- [Requirements/endpoints.md](../Requirements/endpoints.md) — EP-24, EP-25, EP-87, EP-88, EP-92…EP-96, EP-133, EP-134.
- [API/05-knowledge-assistant.md](../API/05-knowledge-assistant.md) — §4, the search the gateway calls.
- [Requirements/space-surface.md](../Requirements/space-surface.md) — SP-14…SP-20.
