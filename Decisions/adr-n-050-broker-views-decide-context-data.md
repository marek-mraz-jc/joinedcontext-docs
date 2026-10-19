---
sidebar_position: 51
title: "ADR-N-050: The Broker's Views and Policy Engine Decide Context Data"
---

# ADR-N-050: The Broker's Views and Policy Engine Decide Context Data

Date: 2026-10-16  
Status: Accepted  
Decision Makers: product owner (order of 2026-10-16 ~14:00Z: "run analysis of the whole architecture with CG and with context gateway and context broker, because i think this is too much"); recorded by worker-6 from the supervisor's code-graph analysis (platform 3c50417, Antares 10766ea4), owner may override

This record writes down where an access decision on context data is taken since T-3643 and T-3644, and so supersedes the part of [ADR-N-003](adr-n-003-context-gateway-in-rust.md) that put the decision and the projection in the gateway, and amends [ADR-N-008](adr-n-008-antares-default-broker.md), whose broker was policy-free.

## 1. Context

ADR-N-003 made the Context Gateway the Policy Decision Point: it parsed the caller's query, intersected it with the grants and projected the answer. Since T-3643 every Endpoint has a view in the broker, `/x/views/{slug}` (or `/x/views/cs-{space}` for a space's canonical surface), and the broker runs the `joinedcontext` policy engine (`ANTARES_POLICY=joinedcontext`). The Portal's reconciler writes each tenant's rule documents to the broker (`/q/policy`, `/q/schemas`, `/q/retention`, `/q/quality`; `src/reconciler/views.rs` in joinedcontext-portal). The gateway forwards an NGSI-LD request to the view with the caller's query as sent, and names the verified caller in the `x-jc-*` headers (`ANTARES_POLICY_SUBJECT_HEADERS`). The broker decides and narrows the request.

The documents still described the earlier split: `ARCHITECTURE.md`, the overview, the components chapter and the glossary said the gateway rewrites the query and projects the answer, and ADR-N-008 said any CIM 009 broker may replace Antares. A replacement broker would have neither the views nor the engine, so it would serve unfiltered data.

## 2. Decision

1. **The broker decides.** The broker's view of an Endpoint and its policy engine are the decision point for context data: they decide every NGSI-LD read and write, and narrow what an answer holds, under the subject the gateway verified. The same view serves the broker's other surfaces of that Endpoint (MCP, OGC, OData, LinkML, access, WebSocket views).
2. **The gateway verifies, maps and checks writes.** The gateway verifies the token (Keycloak only), strips client-sent `x-jc-*` and tenant headers, maps the slug to the view and the broker (ADR-N-047), and keeps the checks that are not grant decisions: the identifier and type of a write (PF-43, PF-44, DM-61), the model's units and relationships (DM-70, DM-71), minted ids and daily creates of a form, the domain gate and the media type. It serves `file.*`, STA and DCAT and forwards everything else.
3. **What the gateway still decides, until it moves.** The gateway's in-process PDP still answers three questions: which spaces a caller may discover (SP-11), which schema a caller sees, and whether a write rule may touch an entity the caller could not have changed by hand (DM-71). Each moves to the broker in its own task or stays by an owner decision; none of them projects or rewrites an NGSI-LD answer. The WebSocket fan-out moved in T-4755: its upstream speaks as the caller and the broker cuts each notification ([ADR-N-049](adr-n-049-websocket-fan-out-per-endpoint.md) §7).
4. **A replacement broker offers the views and the engine.** Antares stays the default broker. A broker that replaces it MUST offer the views, the rule documents and the subject headers above; a vanilla CIM 009 broker alone is not enough (amends ADR-N-008).

## 3. Alternatives Considered

- **Keep the decision in the gateway (ADR-N-003 as written).** Rejected: two decision points read the same grants, and the broker's own surfaces (MCP, OGC, OData, WebSocket views) would need the gateway in front of each.
- **Move every remaining gateway decision to the broker now.** Not decided here: the WebSocket fan-out is ADR-N-049, an owner decision, and discovery and schema visibility have no broker surface yet.

## 4. Consequences

- One place decides a data request, and every broker surface of an Endpoint is filtered the same way.
- The platform depends on Antares-specific surfaces (`/x/views`, `/q/*`, `x-jc-*`). CC-01's "vanilla, replaceable broker" no longer holds as written; the requirement needs the owner's amendment.
- The gateway's PDP code that only served the old read path can be removed once the code graph shows no production caller (T-4361 starts with the dead view mapping); the four uses in decision 3 stay until they move.

## 5. Requirements

- [CC-01](../Requirements/city-as-code.md) (vanilla broker): contradicted on `dev`, see the note there.
- [GW1…GW30](../Requirements/gateway-firewall.md): enforced by the broker's engine for reads and writes, by the gateway for the write checks of decision 2.

## Related

- [ADR-N-003](adr-n-003-context-gateway-in-rust.md) — the gateway decision this record supersedes in part.
- [ADR-N-008](adr-n-008-antares-default-broker.md) — the default broker, amended by decision 4.
- [ADR-N-049](adr-n-049-websocket-fan-out-per-endpoint.md) — the WebSocket fan-out, decided by the broker since T-4755.
- [05-context-gateway](../Architecture/05-context-gateway.md) — the gateway's request stages, forwarding to the view.
- [00-register](00-register.md) — all decisions and their status.
