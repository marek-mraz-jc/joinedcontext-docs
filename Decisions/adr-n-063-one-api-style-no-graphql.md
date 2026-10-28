---
sidebar_position: 64
title: "ADR-N-063: One API Style for the Platform, No GraphQL"
---

# ADR-N-063: One API Style for the Platform, No GraphQL

Date: 2026-10-28  
Status: Proposed  
Decision Makers: product owner (2026-10-28: "how to unify the apis and mcp ... What do you recommend about ODATA or graphql? Because this application will be huge"); decided by the supervisor, drafted by worker-t5964 (T-5964), owner may override

This record fixes which API styles the platform serves and forbids adding another. [API/13](../API/13-api-conventions.md) carries the conventions every kind and route follows; T-5965 brings today's list routes onto them and T-5948 builds the operation registry they are generated from.

## 1. Context

The platform has two planes and grows on both.

- **Data plane.** Context data lives in Antares and is read and written through an Endpoint's view (ADR-N-050). Antares serves NGSI-LD (ETSI GS CIM 009) as the native API and eight read representations beside it: `ical`, `feed`, `ogc`, `geojson`, `csv`, `gbfs`, `sta`, `odata` (`REPRESENTATIONS` in the broker's `antares-ops` views). Each speaks the standard its consumers already know: QGIS reads OGC API Features, Excel and Power BI read OData, a SensorThings client reads STA.
- **Control plane.** Configuration (kinds such as Endpoint, Pipeline, Policy, DataModel) lives in Git and is served by the Portal as resource REST under `/api/v1/projects/{project}/{plural}`, every write a reviewed Change (ADR-N-004, [API/01 §4](../API/01-portal-api.md#4-resource-api-mf-11mf-15)). On 2026-10-28 the Portal's OpenAPI document (`joinedcontext-portal/ui/openapi.json`) held 229 paths and 264 operations.
- **Agents.** MCP tools reach both planes: the data MCP of an Endpoint and the hub `/api/mcp` in the gateway, and the Portal MCP at `/api/v1/mcp` over the operation registry (ADR-N-021). The connectors epic (`tasks/GOAL-connectors.md`) moves every AI client onto one generic tool set over the same registry.

The Portal grew route by route. Its list routes page three ways (`limit` with `continue`, `cursor`, `page`), filter in four (`labelSelector` and `fieldSelector`, `q`, `search`, per-field parameters), and no resource route answers an `ETag` (`joinedcontext-portal/src/api/resources.rs`). Each new route a client, jcctl or a tool learns separately. At the size the owner expects, that cost grows with every kind.

## 2. Options

| Option | What it gives | Cost on this platform | Verdict |
|---|---|---|---|
| A. GraphQL beside or instead of REST | one query for nested reads, a typed schema | a second authorization path at field level beside the Endpoint views that already decide data (ADR-N-050); query cost is set by the client, so a nested query is a denial-of-service lever on one 16 GB node at the 10-20k requests per second target unless a cost model is built and kept; every query is a `POST`, so APISIX caching and `ETag`/`If-None-Match` stop working; control-plane writes are Git merge requests, which gain nothing from mutations; no public-sector or data-space standard the platform implements asks for it | **refused** |
| B. OData as the control-plane API | `$filter`, `$select`, `$expand` on every kind | OData's metadata and batch model do not fit Git-backed reviewed writes; the control plane would inherit a query language larger than any kind needs | **refused**; OData stays a data-read view |
| C. Each team picks a style per feature | fast for the first route | what the platform has today: three paging styles and four filter styles for one client to learn | **refused** |
| D. One style per plane, one convention set, generated from one registry | NGSI-LD and its standard views for data; resource REST for configuration; generic MCP tools over both | the existing routes move onto the conventions (T-5965); the conventions page is kept | **chosen** |

## 3. Decision

1. **Data plane: NGSI-LD plus standard views.** Context data is NGSI-LD in Antares. A consumer that needs another standard gets a representation of the same view (OData, OGC API Features, STA, GeoJSON, CSV, iCal, feeds, GBFS); each answers what its standard defines, reads through the same view and policy decision, and adds no data of its own. OData is one of these read views, for Excel and Power BI. It never serves configuration.
2. **Control plane: resource REST.** Every configuration kind is a resource collection under `/api/v1/projects/{project}/{plural}` with the same verbs, the same list filter, the same cursor paging, `ETag` and `If-Match`, the same problem+json errors, the same validate-only form and the same long-running shape ([API/13](../API/13-api-conventions.md)). A kind changes shape only as a new version of that kind; the URL prefix does not move.
3. **Agents: generic MCP tools.** MCP tools are generic over kind (`get_schema`, `list`, `get`, `query_data`, `plan_change`, `apply_change`, and the pipeline tools), generated from the same registry as the REST routes, never one tool per route. A tool call is the REST operation under another transport.
4. **One registry is the source.** The operation registry (`joinedcontext-portal/src/ops/mod.rs`, ADR-N-021) defines each operation once: its input and output schema, its permission and its lane. The REST routes, the OpenAPI document, the per-kind JSON Schemas, the MCP tool definitions, jcctl and the UI forms are generated from it (T-5948, T-5966).
5. **No new style.** A new feature is a new kind, a new operation of the registry or a new data view. A new API style (GraphQL, gRPC on the public edge, a second RPC dialect, a per-feature JSON shape) needs a decision record that supersedes this one.

## 4. Security

One authorization path serves REST, MCP and the UI. A configuration read or write reaches `Effective::may` and `Effective::may_read_manifest` in `joinedcontext-portal/src/permissions.rs` whatever transport carried it, because the REST handler, the MCP tool and the UI form call the same registry operation, and the registry's `Caller::grants` check runs before its handler. A data read or write is decided by the Endpoint's view in Antares, for NGSI-LD and every representation alike. A second style would need a second copy of these checks, and two copies drift: the REST item-by-item short cut that leaked a one-space grant to every space (T-5698) is the kind of gap a parallel GraphQL resolver layer would multiply, per field.

The conventions keep the controls that GraphQL would weaken: reads stay `GET` so the edge can cache and rate-limit by route class; a list never counts or pages over objects the caller cannot read; a write stays a reviewed Change, with `If-Match` against lost updates and validate-only before it.

## 5. Consequences

- [API/13](../API/13-api-conventions.md) is the convention page; a route that departs from it says why in its own API section.
- T-5965 measures today's list routes against API/13 and moves them onto generic handlers; `labelSelector`, `fieldSelector` and `continue` stay accepted until a resource API `v2` or the 90-day notice of [API/10](../API/10-api-change-policy.md), whichever a public consumer needs.
- T-5966 generates jcctl's resource commands from the OpenAPI document.
- A request for GraphQL, or for OData on configuration, is answered with this record.

## Related

- [API/13](../API/13-api-conventions.md): the conventions this record orders.
- [ADR-N-021](adr-n-021-one-operation-registry-behind-ui-api-assistant-and-mcp.md): the operation registry the routes and tools come from.
- [ADR-N-050](adr-n-050-broker-views-decide-context-data.md): the broker's views decide context data on every surface.
- [ADR-N-004](adr-n-004-configuration-as-code-and-gitea.md): configuration in Git, writes as reviewed Changes.
- [API/02](../API/02-endpoint-representations.md): the data representations of an Endpoint.
- [Architecture/07](../Architecture/07-agents-and-mcp.md): the MCP surfaces.
