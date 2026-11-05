---
sidebar_position: 8
title: "Next Platform: Management API and Testing"
description: GraphQL against OData as the one management and query language, field-level authorization and query cost limits, and the test plan that proves isolation, idle cost and quotas.
---

# Next Platform: Management API and Testing

This page decides the one language through which organizations, members, data, quotas and the deployment are managed and queried, and sets the test plan for the next platform: cross-organization attacks on every surface, parser fuzzing, conformance suites, idle-cost and quota load tests, and upgrade and restore drills. Readers: the agents building `jc-control` and the conformance suites.

## 1. One management language

The owner named GraphQL and OData. Today's platform serves OData as a read view of context data in Antares and resource REST for configuration, and ADR-N-063 refused both GraphQL and OData for the control plane.

| Criterion | GraphQL | OData 4.01 |
|---|---|---|
| Typed schema | SDL, introspection | CSDL (XML and JSON), `$metadata` |
| Already built here | nothing | Antares crates `odata-url` (bounded parser), `odata-csdl`, `odata-json`, `odata-batch`, `odata-axum`, and `$metadata` built per caller from schema ∩ view (Part E) |
| Reads over HTTP `GET` | by convention only; clients send `POST` | always `GET`; cacheable, `ETag`, rate limit by route class |
| Query cost | set by the client: nested selections multiply; needs a cost model the server keeps | bounded by the server: `$expand` depth, `$top`, `$filter` node count, all in the parser's limits |
| Field-level authorization | one resolver per field, each a place to forget a check | `$metadata` per caller lists only fields the caller may read; a `$select` of an unlisted field is the same 400 as an unknown field |
| Writes | mutations | entity `PATCH`, or bound actions |
| Tools that read it | GraphQL clients | Excel, Power BI, Tableau, .NET and Java OData clients (ADR-N-063 §1) |
| Public standard in the sector | none the platform implements | OASIS standard; used by SAP and Microsoft services (public source: OASIS OData 4.01 specification) |

Decided (worker-t6588, owner may override): OData 4.01 is the one management and query language, for reads of both planes, and GraphQL stays out, because the parser, the CSDL writer and per-caller `$metadata` already exist in Rust here, every read stays a cacheable `GET` with server-set cost limits, and field-level authorization falls out of the per-caller `$metadata` instead of a check per resolver. This supersedes ADR-N-063 §3.2 in part: the control plane gains an OData read service beside resource REST, generated from the same operation registry. Options: GraphQL (refused, for the cost and authorization reasons above), resource REST only (today; keeps two query styles for a client), OData for reads and actions for writes (chosen).

### Shape

- Service root `/api/v2/odata/` per organization, entity sets `Organizations` (only the caller's), `Members`, `Groups`, `Projects`, `ContextSpaces`, `Endpoints`, `Pipelines`, `Apps`, `Changes`, `Usage`, `Quotas`, `AuditEvents`.
- Writes stay reviewed: an entity `PATCH` on a configuration kind opens a Change and answers `202` with the Change; bound actions `Approve`, `Reject`, `Apply` on `Changes`. Membership and quota writes that need no review (an administrator adding a member) are plain `PATCH`/`POST` checked by `Check`.
- The operator's deployment service `/api/v2/odata/operator/` lists organizations, plans and health, and never tenant data.
- Context data stays NGSI-LD and its representations, the OData data view included (ADR-N-050).

### Authorization of every field

Each entity type and property names the permission that reads it in the registry. `$metadata` is generated per request from `ListObjects` and the registry; a property the caller may not read is absent from `$metadata`, from `$select` and from `$filter` and `$orderby`, so a filter cannot test a hidden field's value. `$count` counts only rows the caller may read (keeps ADR-N-063 §4: a list never counts objects the caller cannot read).

### Cost limits

| Limit | Default |
|---|---|
| `$expand` depth | 2 |
| `$top` | 1000, `@odata.nextLink` beyond |
| `$filter` nodes | 64 |
| `$search` terms | 8 |
| Statement time | 2 s per request in the shared edition |
| `$batch` requests | 20, each counted against the rate limit |
| Requests | the organization's bucket ([02 §6](02-architecture.md#6-quotas-and-fair-share)) |

A request over a limit answers `400` naming the option and the limit, before any query runs.

## 2. Internal contracts

Services call each other over gRPC with protobuf messages generated from `jc-types` (NP-72); bulk data (exports, pipeline batches, history ranges) moves as Arrow record batches over Arrow Flight (NP-71). Google's internal RPC system and protocol buffers are the public-source model (gRPC project, "About gRPC" history of Stubby; Protocol Buffers documentation). One contract crate removes today's four-repository pin chain ([01 §6.4](01-analysis.md#64-merge-latency-across-repositories)): the services live in one workspace and one repository.

## 3. Test families

| Family | What | Where | When |
|---|---|---|---|
| Isolation | the `isolation_*` tests of [04 §2](04-isolation-threat-model.md#2-threats-controls-tests), two organizations with the same names and ids, every route class and every surface (NGSI-LD, OData data and management, OGC, STA, MCP, WebSocket, MQTT, files, catalogue, assistant, Apps) | conformance `tests/isolation`, a throwaway stack | every release; per push for the touched service's routes |
| Authorization properties | random tuple sets and grants, `Check` against a reference evaluator; no rule crosses `org` | `jc-identity` crate tests | per push |
| Parser fuzzing | NGSI-LD `q`, `scopeQ`, `geoQ`; OData URL and `$batch`; CQL2; JWT; JSON-LD; MQTT packets; OIDC request parameters | `cargo fuzz` targets, nightly | nightly, 30 minutes per target |
| Conformance | ETSI NGSI-LD (TTF suite against a throwaway broker), OGC API Features ETS, OGC SensorThings ETS, OData (the NLstn suite today), MCP, OpenID Foundation conformance for `jc-identity` | conformance repository | per release; ETSI never against dev (owner rule) |
| Idle cost | create 1000 empty organizations; assert pods, connections, memory and caches unchanged within 2 % | conformance `tests/k6` plus a probe script | per release |
| Quotas and fairness | `isolation_fairness`; each limit of [02 §6](02-architecture.md#6-quotas-and-fair-share) hit and refused with `429` | k6 | per release |
| Upgrade | install release N-1 with seeded data, upgrade to N under read load, assert no failed read and no lost row | CI job on a throwaway cluster | per release |
| Restore | export one organization, restore into a fresh deployment, compare row counts and checksums; physical restore of the whole database to a point in time | monthly drill on dev | monthly |
| Deletion | delete an organization, assert no row, object or decryptable blob remains | conformance | per release |

## 4. Test plan

1. Phase 1 builds the isolation harness (NP1-10) and the fairness test (NP1-11) against today's stack, so every later phase is measured against the same tests.
2. A release ships only with every isolation, authorization and conformance family green (NP-85).
3. The idle-cost test is the acceptance test of NP-10 to NP-12: its numbers go into the release notes.
4. A new route or surface adds its row to the isolation harness in the same change, the way today's new routes add an authz matrix row (KNOWLEDGE, ROUTE_COVERAGE).
5. Fuzz findings become tests in the crate before the fix.

## Related

- [ADR-N-063](../../Decisions/adr-n-063-one-api-style-no-graphql.md) — the decision this page supersedes in part.
- [API/13](../../API/13-api-conventions.md) — today's resource REST conventions, kept for writes.
- [04-isolation-threat-model.md](04-isolation-threat-model.md) — the threats behind the isolation family.
- [07-editions-and-migration.md](07-editions-and-migration.md) — where each test family starts.
