---
sidebar_position: 52
title: "ADR-N-051: The Context Gateway Is a Policy Edge and Holds No Format Code"
---

# ADR-N-051: The Context Gateway Is a Policy Edge and Holds No Format Code

Date: 2026-10-18  
Status: Accepted  
Decision Makers: product owner (order of 2026-10-17 via the supervisor: "make the gateway a thin policy edge with no format code"); recorded by worker-2 (T-4475), owner may override

This record follows [ADR-N-050](adr-n-050-broker-views-decide-context-data.md). ADR-N-050 put the access decision in the broker's views. This record moves the data formats and query languages the gateway still renders into Antares as well.

## 1. Context

`crates/context-gateway/src` holds 33,826 lines on platform main `8d0400b` (`wc -l`, 83 files). 7,380 of them, about a fifth, translate data rather than guard it:

- SensorThings resources;
- CSV, XLSX, GeoJSON and zip downloads;
- Parquet;
- a query-string parser of its own;
- the execution of the MCP data tools.

Antares serves each of these, or will, as a surface of the Endpoint's view behind a cargo feature (Antares ADR-0027, surfaces). Every format kept in the gateway is a second implementation of a standard. It must agree with the broker's copy on every filter, page and count, and T-4464 and T-4467 test exactly that disagreement.

## 2. Decision

1. **The gateway is a policy edge.** It does identity (Keycloak tokens, audience), Endpoint lookup (slug to view, ADR-N-047), Policy, quotas and rate limits, forwarding to the broker's view, and edge transport: the WebSocket fan-out ([ADR-N-049](adr-n-049-websocket-fan-out-per-endpoint.md)) and previews. It also keeps the write checks of ADR-N-050 decision 2.
2. **No format code in the gateway.** The gateway parses, renders and translates no data format and no query language of its own. When it must inspect or rewrite a query for Policy, it uses the AST of `antares-ql`, a dependency it already has. Each standard and each export is a surface of the broker's view behind a feature, and the gateway forwards to it.
3. **The catalogue stays at the edge, the record leaves the handler.** The MCP hub's catalogue (`list_endpoints`, `search`, `get_endpoint`) answers across Endpoints, which no single view can do, so it stays. The DCAT-AP record of an Endpoint moves into the `jc-dcat` crate (T-4499), with national profiles behind features. The gateway route calls it.
4. **A ratchet enforces it.** CI fails when a format module or a format crate comes back into `context-gateway`. The baseline is the file list in section 3 and only shrinks (T-4476).

## 3. Classification

One row per module of `crates/context-gateway/src` on platform main `8d0400b` (lines from `wc -l`). The verdicts:

- **keep**: the module is edge work under decision 1;
- **move**: the module leaves the gateway, under the named task;
- **decided**: the module was open, and the row records why it went where it did.

| Module | Lines | Verdict |
|---|---|---|
| `translators/sta.rs` | 638 | move: the broker's `antares-sta` surface (T-4463) |
| `handlers/sta.rs` | 421 | move: becomes a forward to `antares-sta` (T-4463) |
| `translators/tabular.rs` | 697 | move: CSV and XLSX to the broker's encodings (T-4478); Parquet to `antares-ogc` (T-4466) |
| `translators/geojson.rs` | 206 | move: the broker's GeoJSON encoding (T-4478) |
| `translators/zip_export.rs` | 166 | move: the broker's zip export (T-4478) |
| `handlers/files.rs` | 473 | move: every `file.*` becomes a forward (T-4478, T-4466) |
| `handlers/reads.rs` | 585 | move: `view_fallback` and its per-type fan-out go once Antares reads typeless views in one request (T-4456); the capped page walk goes with the files (T-4478) |
| `query.rs` | 794 | move: its own query-string parser gives way to `antares-ql`'s AST (T-4479) |
| `mcp/tools.rs` | 1,837 | move: data tools run through the view's `antares-mcp`; the hub keeps the tool catalogue (T-4480) |
| `mcp/units.rs` | 121 | move: the unit labels go to `antares-mcp` (T-4480) |
| `handlers/endpoint_surface.rs` | 1,063 | move: the DCAT-AP record to `jc-dcat` (T-4499); the route stays |
| `translators/view_mapping.rs` | 379 | decided, move: antares-views already runs the Mapping IR (T-3799); the gateway keeps a version check at load and deletes its interpreter (T-4547) |
| `units.rs` | 513 | decided, keep: a write check (DM-06), the unit a write's quantity must carry, under ADR-N-050 decision 2; it reads the model's codes and renders no format |
| `quality.rs` | 508 | decided, keep: the space's quality rules and slot constraints on every write (DM-86..DM-93), a write check under ADR-N-050 decision 2 |
| `relationships.rs` | 1,062 | decided, keep: the model's relationships held at every write (DM-70), a write check under ADR-N-050 decision 2 |
| `auth/*` | 1,591 | keep: identity |
| `resolver.rs`, `store.rs` | 1,454 | keep: Endpoint lookup and the table built from the repository |
| `pdp/*` | 2,629 | keep: the four PDP answers of ADR-N-050 decision 3 and the write guard |
| `middleware/*` | 970 | keep: tenancy headers, response headers, rate limits |
| `proxy.rs`, `operations.rs` | 726 | keep: forwarding, and naming the operation a Policy grants |
| `fanout.rs`, `fanout/*`, `handlers/ws.rs` | 3,342 | keep: WebSocket fan-out (ADR-N-049) |
| `previews.rs` | 305 | keep: edge transport |
| `federation.rs`, `federation/exchange.rs` | 416 | keep: token exchange to member Endpoints |
| `mcp/hub.rs`, `mcp/search.rs`, `mcp/catalog.rs`, `mcp/server.rs`, `mcp/endpoint.rs`, `mcp/describe.rs`, `mcp/jsonrpc.rs`, `mcp/mod.rs` | 3,954 | keep: the hub catalogue, named servers, forwarding to the view's MCP, and the access and schema descriptions no broker tool answers |
| `mcp/personal.rs`, `mcp/hub_lead.md`, `mcp/primer.md` | 287 | keep: a caller's personal connectors, and the hub's own instructions text |
| `handlers/ogc.rs` | 678 | keep: a forward to `antares-ogc` (T-3752) |
| `handlers/ngsi_ld.rs`, `handlers/writes.rs`, `handlers/respond.rs` | 2,273 | keep: forwards and write checks |
| `handlers/schema.rs`, `handlers/schema_routes.rs`, `handlers/mappings.rs` | 1,239 | keep: schema visibility (ADR-N-050 decision 3), and the repository's Mapping files served as they are |
| `handlers/view_access.rs`, `handlers/view_access/odrl.rs` | 851 | keep: the access document, answered by the broker's engine |
| `handlers/space_surface.rs`, `handlers/space_routes.rs`, `handlers/catalog.rs`, `handlers/openapi_doc.rs` | 801 | keep: discovery (SP-11); the space record calls `jc-dcat` once it exists (T-4499) |
| `creates.rs`, `domain_gate.rs`, `context_guard.rs`, `notification_target.rs` | 835 | keep: write checks, the verified domain, the contexts a caller may send, notification targets |
| `mqtt.rs` | 398 | keep: the CONNECT check of the MQTT edge brokers (ADR-N-048) |
| `app.rs`, `config.rs`, `main.rs`, `lib.rs`, `telemetry.rs`, `handlers/mod.rs`, `translators/mod.rs` | 1,614 | keep: wiring |

## 4. Migration Order

1. T-4472: the `app.rs` split (done).
2. T-4476: the ratchet, with the move rows above as its baseline.
3. T-4463 (STA), T-4466 (Parquet) and T-4478 (CSV, XLSX, GeoJSON, zip), in any order. Each deletes its rows from the baseline.
4. T-4479 (query parser), T-4480 (MCP data tools), T-4456 (`view_fallback`), T-4547 (view mapping), T-4499 (DCAT-AP record).

## 5. Alternatives Considered

- **Keep the gateway's formats and test them against the broker.** Rejected. Two implementations of each standard drift, and every filter, page and count has to be checked twice (T-4464, T-4467).
- **Move the write checks too.** Not decided here. Units, quality rules and relationships are checks, not formats, and the broker's views have no write-time model check yet. They stay until the broker offers one.

## 6. Consequences

- The gateway sheds 7,380 lines of format code, by the counts above. A new standard is an Antares surface plus a forward, never a gateway translator.
- `file.*` downloads, STA and the MCP data tools depend on the broker's surfaces. A replacement broker must offer them as well as the views (ADR-N-050 decision 4).
- Until each move lands, the ratchet lists the remaining modules, and the list only shrinks.

## 7. Requirements

- [ADR-N-050](adr-n-050-broker-views-decide-context-data.md): the broker decides; this record moves the formats as well.
- GOAL-antares-surfaces point 11: every standard is a surface of the view.

## Related

- [ADR-N-050](adr-n-050-broker-views-decide-context-data.md) — the decision point this record builds on.
- [ADR-N-049](adr-n-049-websocket-fan-out-per-endpoint.md) — the WebSocket fan-out, which stays at the edge.
- [ADR-N-047](adr-n-047-many-context-brokers.md) — the slug-to-view mapping the gateway keeps.
- [05-context-gateway](../Architecture/05-context-gateway.md) — the gateway's request stages.
- [00-register](00-register.md) — all decisions and their status.
