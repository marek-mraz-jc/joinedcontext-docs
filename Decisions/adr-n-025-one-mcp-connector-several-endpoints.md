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

- **The space comes from the URL.** SP-14 and AG-05 say the Context Space is determined by the path and confirmed by the token, and a `space` or `tenant` argument is refused, never ignored. The façade's handlers take the Endpoint the path resolved (`crates/context-gateway/src/mcp/endpoint_facade.rs`).
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

## Related

- [ADR-N-021](adr-n-021-one-operation-registry-behind-ui-api-assistant-and-mcp.md) — the Portal's Configuration MCP, which this does not touch.
- [Architecture/07-agents-and-mcp.md](../Architecture/07-agents-and-mcp.md) — §1 and §2, the Data MCP and its catalogue; §7, connecting from a phone.
- [Requirements/space-surface.md](../Requirements/space-surface.md) — SP-14…SP-20.
- [Requirements/endpoints.md](../Requirements/endpoints.md) — EP-24, EP-25, EP-87, EP-88.
- [Requirements/agents.md](../Requirements/agents.md) — AG-04, AG-05.
