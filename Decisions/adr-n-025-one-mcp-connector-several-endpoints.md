---
sidebar_position: 26
title: "ADR-N-025: One MCP Connector Over Several Endpoints"
---

# ADR-N-025: One MCP Connector Over Several Endpoints

Date: 2026-09-25  
Status: Accepted  
Decision Makers: product owner

## 1. Context

The owner, 2026-09-18: "maybe in the future from a single MCP there can be loaded multiple endpoints, so keep in mind that the agent can change its preferred NGSI-LD but using a single MCP connector."

Today a person adds one connector per Endpoint. The Data MCP lives at `/api/endpoint/{endpointSlug}/mcp` (EP-24), so five Endpoints are five connectors, five OAuth logins and five entries in a phone's connector list. An agent that should compare air quality with traffic needs two connectors, and the person has to set up both before asking.

What the platform holds today, read from `joinedcontext-platform` at `ecd7126`:

- **The space comes from the URL.** SP-14 and AG-05 say the Context Space is determined by the path and confirmed by the token, and a `space` or `tenant` argument is refused, never ignored. The gateway's MCP hub takes the Endpoint the path resolved and forwards the call to that Endpoint's view on the broker (`crates/context-gateway/src/mcp/hub.rs`; the per-Endpoint façade went with T-3648).
- **Nothing is remembered.** The façade is stateless Streamable HTTP (SP-19): every `POST` is judged on its own token, so a grant change holds on the next call. A "current endpoint" cannot live on the server without breaking that.
- **Discovery is enforcement.** `tools/list` is rendered from the grants of that Endpoint's Policy for this token (SP-15, EP-25), and the same PDP decides the call (SP-16).
- **Audience per Endpoint.** An Endpoint accepts a token whose audience is its slug, its public URL, or the edge audience `context-gateway` (`audiences_of`, `crates/context-gateway/src/app.rs`). The reconciler renders one Keycloak client `mcp-{endpointSlug}` per MCP-enabled Endpoint (Architecture/07 §7), so a token minted for one Endpoint is refused by every other (PF-45, PF-46, AG-32).
- **Rate limits are per Endpoint.** One bucket per `(slug, caller)` (`middleware/rate_limit.rs`).
- **Elicitations are bound to their surface.** A pending question records its owner, the surface it was asked on, the tool and a digest of the arguments (`mcp/elicitation.rs`).
- **The catalogue is ready.** T-1856 made every tool's arguments and handler a function of the Endpoint the URL names (Architecture/07 §2), so a second way of naming the Endpoint changes the routing and nothing in the tools.

## 2. Decision

A **hub** at `/api/mcp` on the gateway serves one tool catalogue over every Endpoint the caller's token may read. The agent names the Endpoint on each call. The server remembers nothing.

1. **`list_endpoints`** answers the Endpoints this token may read through the hub (section 4 says which): for each, the slug, title, Context Space, entity types, representations and the link to its recommended schema (the LinkML of T-1856). An Endpoint the token may not read is absent, and nothing in the answer says it exists. The list pages (`limit`, `cursor`) like `list_types`.
2. **Every data tool** of the per-Endpoint catalogue (Architecture/07 §2) is offered once, with one more required argument, `endpoint`: a slug out of the caller's own list, published in the tool's input schema as an `enum`. `tools/list` does not multiply by Endpoint: one catalogue, and the enum carries the choice.
3. **The preferred Endpoint is the client's memory.** The agent sends `endpoint` on every call; switching is another value. No session, no "use endpoint" tool, no server state, so SP-19 holds unchanged.
4. **Each call is that Endpoint's call.** The hub resolves `endpoint`, then runs exactly the path a call to `/api/endpoint/{endpoint}/mcp` runs: that Endpoint's PDP with the caller's token, its projection, its rate limit, its elicitation. The hub adds no right and holds no identity of its own (SP-16).
5. **One Endpoint per call.** No tool reads two Endpoints in one call, and no join, filter or subscription crosses Endpoints. A comparison is two calls the agent makes.
6. **`endpoint` is the one routing argument.** `space` and `tenant` stay refused (AG-05). An `endpoint` value outside the caller's list is refused exactly like an unknown slug, byte for byte (SP-20).
7. **The per-Endpoint URL stays.** A connector that must see one Endpoint only keeps `/api/endpoint/{endpointSlug}/mcp`, and nothing about it changes.
8. **`tools/list` shows what the grants allow.** A tool is listed when at least one Endpoint of the caller's list grants its operation; a call naming an Endpoint that does not grant it is refused with the structured tool error of SP-17, naming the Endpoint and the operation.

## 3. Security Analysis

The build task inherits this list as failing tests, one per row.

| Threat | Control |
|---|---|
| The hub reads an Endpoint the token may not read | `endpoint` outside the caller's list answers the same bytes as an unknown slug; the enum never lists it; the call is decided by that Endpoint's own PDP as if it had come to its URL. |
| One call reaches two Endpoints | `endpoint` is a single string, never a list; the schema says so and a list is refused as invalid input. No tool takes a second slug anywhere in its arguments. |
| An elicitation answered on one Endpoint confirms a call on another | The pending question is bound to the owner, the tool, the argument digest (which contains `endpoint`) and the surface, and the surface is the Endpoint's slug on the hub as it is on the Endpoint's URL. |
| Quota multiplied by Endpoints | The hub spends one request of a per-subject bucket as well as the Endpoint's own `(slug, caller)` bucket, so a subject cannot spread a burst across fifty Endpoints. |
| Audit that cannot say what was read | Every hub call's audit line names the Endpoint slug, the tool and the subject, the fields a call to the Endpoint's URL logs today. |
| A token for one Endpoint used as a key to all | See section 4: a token whose audience is one Endpoint lists that Endpoint only. |
| Prompt injection across Endpoints | An entity in Endpoint A whose text says "now read Endpoint B" can make the agent ask; it gains nothing the token did not already allow, because B's PDP decides with the same token. This is the **accepted residual risk**. The mitigation is the person's choice at connect time (section 4): the connector's Endpoint allow-list bounds what an injected instruction can reach to what the person chose to connect. |

## 4. Token Audience and the Connect-Time Allow-List

The hub is its own RFC 8707 resource, `https://{host}/api/mcp`, with protected-resource metadata under `/api/mcp/.well-known/oauth-protected-resource` and a Keycloak client `mcp-hub` rendered by the reconciler (public, PKCE S256, no secret, the redirect URIs of the known mobile clients, dynamic client registration off), like the per-Endpoint clients.

Which Endpoints a hub token reaches:

- **A token whose audience is the hub** reaches the Endpoints named by its `endpoint:{slug}` scopes. The reconciler renders one optional client scope `endpoint:{slug}` on `mcp-hub` per MCP-enabled Endpoint; at connect time the consent screen lists them and the person picks. The token carries what was picked, so the allow-list lives in the token and not on the server. A token with no `endpoint:` scope lists nothing.
- **A token whose audience is one Endpoint** (its slug or its URL) reaches that Endpoint only through the hub, never another. PF-45 and PF-46 hold: widening a token by sending it to the hub is not possible.
- **The edge audience** (`context-gateway`, a person's Portal session behind the edge) reaches through the hub what it reaches today Endpoint by Endpoint, which is every Endpoint whose Policy grants that person; the hub adds nothing to it.

In each case the Endpoint's PDP decides the call with that token as it does today. The allow-list narrows, it never grants.

### 4a. A machine's token (addendum, 2026-10-11, T-3793)

A `ServiceAccount` asks for its token with `client_credentials`: there is no consent screen to pick `endpoint:` scopes on. It needs none. Its derived client already carries one audience mapper per Endpoint on a space its roles scope (PF-47, [Architecture/12](../Architecture/12-identity-and-access.md)), and a token that names an Endpoint's audience reaches that Endpoint through the hub. A token naming five such audiences therefore lists and calls those five, and a sixth slug answers as an unknown one (SP-20). The scopes stay what a person picks; a machine's reach is its grants, rendered as audiences by the reconciler, with no second list to drift.

A client that does not speak MCP (an SDK, a script, a city's ETL) asks the same question at `GET /api/endpoints` (EP-105): the same function as `list_endpoints`, the same token rules and the same per-subject bucket, over every representation rather than only the MCP ones, as JSON instead of a tool result.

### 4b. One connector for the whole portal (addendum, 2026-10-12, T-4114, owner request)

The owner asked for one MCP address a person adds once to an AI client and then reaches every open dataset, and after login every internal one they may read. Two changes, neither of which widens a single call:

- **Anonymous.** Without a token the hub answers over every `public` Endpoint that serves `mcp`, as each of their own MCP URLs already does (EP-24, AG-32): the same synthetic `public` role, the same per-client-address bucket. Nothing internal is named. A call that names an internal slug without a token answers `401` with the hub's resource metadata, which is how a client learns to log in.
- **`endpoint:*`.** A default client scope on `mcp-hub`, shown on the consent screen as "every Endpoint you may read". A token carrying it reaches what the person's edge session reaches (§4, third bullet). The consent stays explicit and the per-Endpoint scopes stay for a person who wants to hand an assistant less. A token with neither still reaches nothing.

Each call is still that Endpoint's own call under its Policy; the allow-list still only narrows. Requirements: EP-87, EP-88, EP-105 amended; EP-111 (filters and richer rows in `list_endpoints`), EP-112 (one tool catalogue on every MCP surface), EP-113 (the install panel).

### 4c. The connector says it is NGSI-LD (addendum, 2026-10-16, T-4258, owner order)

The owner asked that one pasted connector be a full NGSI-LD client: an agent learns from the connector itself what it speaks, finds a dataset in the DCAT-AP catalogue, reads its schema and queries it with the whole query language, history included. Four changes; none adds a data path or widens a grant:

- **A primer in `initialize`.** The hub's and every named server's `instructions` carry one shared NGSI-LD primer of under 600 words: the API version the broker serves (ETSI GS CIM 009 V1.9.1, published as TS 104 175), entities as `id`, `type`, Properties, Relationships and GeoProperties, how `@context` expands a short name, the `q` grammar with examples, `idPattern` as a regular expression, `scopeQ`, the geo arguments, `pick`/`omit`, `orderBy`, the temporal reads (`timerel`, `lastN`, `aggrMethods` with `aggrPeriodDuration`, `timeproperty=deletedAt` for a removed attribute), `format` and `sysAttrs`, and the order of work: `list_endpoints` (the DCAT-AP catalogue) → `describe_schema` → `list_types`/`get_type` → a query. It names no slug, token or host, and says that each row's NGSI-LD base URL is the one a person or `curl` reads (EP-05): MCP is a second door to the same Endpoint, never a second data path.
- **Anonymous discovery and history.** `get_type`, `list_type_details`, `list_attributes`, `list_attribute_details`, `get_attribute` and `query_temporal` join the tools a caller without a token may list and call, beside the reads it already had. They are read-only and each call is still the named Endpoint's own, under its Policy and its per-client bucket (T-4168). A tool is listed when a grant holds its operation, so the public read Policies of the seeded public Endpoints grant the six discovery operations, which answer only the names the grant already reads (EP-26), and `queryTemporal` wherever they grant `retrieveTemporal`.
- **Formats and system attributes.** `format` and `sysAttrs` (boolean; `options=sysAttrs` on the wire) on `get_entity`, `query_entities`, `query_temporal` and `retrieve_temporal`, on every MCP surface and the broker's view alike (EP-112). `format` is `normalized` (the default), `concise` or `keyValues` on the entity reads, and `normalized`, `temporalValues` or `aggregatedValues` on the history reads, the values the broker serves on REST (CIM 009 6.3.7). The POST forms take neither: their Query document has no representation. `sysAttrs` answers `createdAt` and `modifiedAt`, which is how an agent sees when an entity last changed without a history read.
- **Ordering is the standard's.** `orderBy` (CIM 009 §4.23 Entity Ordering, `attr[;asc|desc]` comma-separated) on `query_entities`, as the broker serves it on REST; no other sort is invented.

Requirement: EP-116.

## 5. Alternatives Considered

| Alternative | Why not |
|---|---|
| A `use_endpoint` tool that sets the current Endpoint for the session | Server state: breaks SP-19, and a stale "current endpoint" after a grant change reads with rights the token no longer has. |
| One tool per Endpoint (`bikes__query_entities`, `air__query_entities`) | `tools/list` grows with the Endpoint count; fifty Endpoints are seven hundred tools, past what a client's model reads well, and a tool name becomes a routing channel. |
| A `space` argument | Refused by SP-14 and AG-05; the space is not the unit of access, the Endpoint and its Policy are. |
| Cross-Endpoint joins in the hub | A join decides what two Policies allow together, which neither Policy says; each Endpoint's PDP would no longer be the whole decision (SP-16). An agent that needs both makes two calls. |
| The Portal's Configuration MCP (`/api/v1/mcp`) proxies data reads | Mixes the two surfaces AG-04 keeps apart, and routes data through the Portal, which holds no data-plane grant. |
| Keep one connector per Endpoint | Works today and stays; the owner asked for the single connector as the easier way. |

## 6. Consequences

- **The gateway** gains the hub route, `list_endpoints`, the `endpoint` argument on the catalogue's input schemas, the per-subject bucket and the audit field. The per-Endpoint route is untouched.
- **The reconciler** renders `mcp-hub` and one `endpoint:{slug}` client scope per MCP-enabled Endpoint.
- **The Portal** shows one "Connect all" URL beside the per-Endpoint URLs in the Endpoints view.
- **Conformance** gains an isolation suite for the hub: the rows of section 3, and the per-Endpoint suite run again through the hub with `endpoint` set.
- **Requirements** landed on acceptance (section 7). Until the hub is built (T-2490), the per-Endpoint URL is the only Data MCP.

## 7. Requirements

Proposed 2026-09-21, accepted by the owner on 2026-09-25 as proposed: the connect-time `endpoint:{slug}` scopes are the allow-list, a per-subject bucket across Endpoints sits on top of each Endpoint's own, and no call ever joins Endpoints. Landed in their families:

- `Requirements/space-surface.md`, SP-14 extended: the space is determined by the path **or by the `endpoint` argument of the hub**, confirmed by the token, and never by any other tool argument.
- `Requirements/endpoints.md`, **EP-87**: the gateway MUST serve a hub at `/api/mcp` whose `list_endpoints` answers only the Endpoints the token may read through it, and whose every data tool takes one required `endpoint` from that list and runs as a call to that Endpoint's own MCP (EP-24, EP-25).
- `Requirements/endpoints.md`, **EP-88** [S]: a hub token MUST reach only the Endpoints its `endpoint:{slug}` scopes name, or the one Endpoint its audience names (PF-45, PF-46).
- `Requirements/agents.md`, AG-05 extended as SP-14.
- `Requirements/endpoints.md`, EP-88 extended for a ServiceAccount's token and **EP-105** for `GET /api/endpoints` (§4a, 2026-10-11).

## Related

- [ADR-N-021](adr-n-021-one-operation-registry-behind-ui-api-assistant-and-mcp.md) — the Portal's Configuration MCP, which this does not touch.
- [Architecture/07-agents-and-mcp.md](../Architecture/07-agents-and-mcp.md) — §1 and §2, the Data MCP and its catalogue; §7, connecting from a phone.
- [Requirements/space-surface.md](../Requirements/space-surface.md) — SP-14…SP-20.
- [Requirements/endpoints.md](../Requirements/endpoints.md) — EP-24, EP-25, EP-87, EP-88, EP-105.
- [Requirements/agents.md](../Requirements/agents.md) — AG-04, AG-05.
