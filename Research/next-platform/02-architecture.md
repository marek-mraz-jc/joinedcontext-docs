---
sidebar_position: 2
title: "Next Platform: Target Architecture"
description: The services of the many-organization platform, the tenancy key on every row, request and message, the request path, scale to zero and fair share.
---

# Next Platform: Target Architecture

This page proposes the architecture of the next joinedcontext platform: one deployment serving any number of organizations, an unused organization costing only its stored bytes, and the same artifacts running as a shared online service or self-hosted. It is written for the agents that will build it and for the owner deciding it. The analysis it answers is [01](01-analysis.md); claims about other vendors are marked "public source" with the source named.

## 1. Design rules

1. **No per-organization process, connection, realm, repository, namespace or pod.** An organization is rows and object-store prefixes. Every service is a shared multi-tenant serving process, the model public sources describe for Google's Borg cluster manager (Verma et al., "Large-scale cluster management at Google with Borg", EuroSys 2015) and for Amazon S3, which keeps no per-bucket server and bills by stored bytes and requests (public source: Amazon S3 User Guide and S3 pricing page).
2. **One tenancy key, typed, everywhere.** `OrgId` is a 128-bit opaque id minted at organization creation and never reused. Names, domains and URN segments are attributes of an organization, never its key (keeps ADR-N-041).
3. **Fewer services.** Six Rust services, PostgreSQL and an S3-compatible object store. Each service owns its tables; no service reads another's tables.
4. **Public standards at the edge, one typed contract inside.** NGSI-LD, OGC API Features, SensorThings, OData, MCP, DCAT and OIDC face clients. Inside, services call each other over gRPC with protobuf messages generated from one Rust type crate, and bulk data moves as Apache Arrow record batches over Arrow Flight.
5. **Every hop decides for whoever is on the wire** (keeps Part A §4's invariant), and every decision goes to one authorization service ([03](03-identity-and-authz.md)).

## 2. Services

| Service | Responsibility | Owns (tables, prefixes) | Replaces today |
|---|---|---|---|
| `jc-edge` | TLS, routing by host and path, token verification, rate limits and fair queues per organization, request context minting, the write checks the gateway makes today (URN, type, units, relationships) | route table (derived), rate-limit state in memory | APISIX, Traefik routes, Context Gateway |
| `jc-identity` | OIDC/OAuth 2.1 provider and the authorization service: people, organizations, groups, service accounts, MFA, federation, token exchange, MCP client registration, relationship tuples, `Check`/`ListObjects` | `idn_*` and `authz_*` tables | Keycloak, the Portal's permission resolution, the gateway PDP's grant lookup |
| `jc-control` | the management API, the configuration store (versioned manifests, Changes, review lanes), the reconciler, usage and quota accounting, the catalogue (DCAT and its HTML pages), the Portal UI | `cfg_*`, `chg_*`, `usage_*`, `cat_*` tables | Portal, Gitea (as the config store), jcctl reconciler in process, CKAN |
| `jc-data` | NGSI-LD broker with views and policy engine, history, subscriptions, every read representation (OData, OGC, STA, GeoJSON, CSV, Parquet, feeds) | Antares tables with `org_id` | Antares (kept, extended) |
| `jc-work` | shared worker pool: pipeline runs, WASM App requests and jobs, App builds, assistant crawls and indexing, notification delivery, exports | `job_*` queue tables, object-store prefixes per organization | Bento runner, jc-wasm-host, jc-functions, gitea-runner, assistant crawler, agent runner |
| `jc-ai` | assistant chat, retrieval, the model proxy with per-organization token budgets | `ai_*` tables, vector index rows | jc-assistant service, agent proxy |
| PostgreSQL | rows of every service, one database per service, RLS forced on every tenant table | | CNPG cluster (kept) |
| Object store | blobs under `org/{OrgId}/…` with a per-organization data key | | RustFS (kept or replaced, [06](06-rust-components.md)) |

MQTT ingest becomes a listener of `jc-edge` (one multi-tenant MQTT front, topics prefixed by the organization's id) instead of one RMQTT pod per broker. The decision per component, with sizes and risks, is in [06](06-rust-components.md).

## 3. The tenancy key

| Carrier | Form | Set by | Checked by |
|---|---|---|---|
| Row | `org_id uuid NOT NULL` leading every primary key and index of a tenant table | the writing service | RLS policy `org_id = current_setting('jc.org')::uuid`, forced, application roles without `BYPASSRLS` |
| Database session | `SET LOCAL jc.org` per transaction | the service's store layer, the only function that opens a tenant transaction | a test that every tenant query outside it fails |
| Request | `RequestCtx { org: OrgId, subject, client, scopes, budget }`, signed by `jc-edge` with a key only it holds, carried as a gRPC metadata entry | `jc-edge`, after token verification | each service verifies the signature and refuses a call without it |
| Message and job | the same `RequestCtx` in every queue row and Arrow Flight ticket | the enqueuer | the worker runs the job inside that context and no other |
| Cache entry | key prefixed by `OrgId` and the subject's grant digest | a shared cache type that takes the key parts as arguments | a type that does not compile without `OrgId` |
| Object key | `org/{OrgId}/{service}/…` | the service | object-store policy per service, data key per organization |
| Log record and span | `org` field (the id, never the name) | the tracing layer from `RequestCtx` | the log reader filters by the reader's organization |
| Metric | per-organization counters only in the usage table, never as a Prometheus label | `jc-control` usage writer | an organization reads its own usage through the API |
| Token | `org` claim, audience per service | `jc-identity` | every service, against the `RequestCtx` |

`OrgId` is a newtype in the shared type crate with no `Default`, no `From<&str>` and no public constructor outside the parser of a verified context, so a function that touches tenant data cannot be called without one.

## 4. Request flow

```text
client ──TLS──▶ jc-edge
   1. route by host/path → (service, organization) from the route table (organization from the
      Endpoint slug, the org host or the token, never from a URN)
   2. verify the bearer (signature, issuer, audience, expiry) against jc-identity's keys
   3. admit: per-organization token bucket, then per-organization weighted fair queue
   4. mint RequestCtx {org, subject, client, scopes, budget}, sign it
   5. write checks for NGSI-LD writes (URN, type, units, relationships)
──gRPC + RequestCtx──▶ jc-data
   6. verify RequestCtx; Check(subject, read, endpoint) at jc-identity (cached per ctx)
   7. the view's policy engine narrows the query (ADR-N-050 kept)
   8. tenant transaction: SET LOCAL jc.org; statement_timeout; query
──▶ PostgreSQL (RLS on org_id and space)
   9. answer narrowed, NGSILD-Results-Restricted when narrowed, back through jc-edge
```

A control-plane write takes the same steps to `jc-control`, which opens a Change; the reconciler applies an approved Change by calling the owning service. A pipeline run is a job row in `jc-work` with the pipeline's `RequestCtx`; its writes go back through `jc-edge` like any client's (keeps "every write to context data goes through an Endpoint and its Policy").

## 5. Idle costs nothing

| Resource | At rest for an unused organization |
|---|---|
| Processes, pods | 0: services are shared |
| Database connections | 0: pools are per service, sized by load |
| Identity | rows in `idn_*`; no realm, no warm cache |
| Configuration | rows in `cfg_*`; no repository, no runner |
| Catalogue | rows in `cat_*`; the HTML is rendered on request |
| MQTT | no listener; topics are rows |
| Apps | WASM modules in the object store; loaded on first request, evicted by LRU |
| Pipelines | schedule rows; a run is a job taken from the queue when due |
| Caches | none until a request; entries expire by LRU and TTL |
| Storage | its rows and blobs, billed by byte |

The deployment floor is the six services at one replica plus PostgreSQL. Target for the shared edition: under 2 GiB of service memory at rest on top of PostgreSQL's `shared_buffers`, against 9.7 GiB today ([01 §3](01-analysis.md#3-measured-on-dev)). The test that proves an idle organization adds nothing is in [08 §4](08-management-api-and-testing.md#4-test-plan).

## 6. Quotas and fair share

A busy organization must not starve the others. Each limit is a field of the organization's plan (keeps ADR-N-035: every limit is a field of the Organization), enforced by the service that spends the resource:

| Resource | Limit | Enforced in |
|---|---|---|
| Requests | token bucket per organization and per principal, by route class | `jc-edge` |
| Concurrency | weighted fair queue (deficit round robin) per organization over the service's worker slots | `jc-edge`, `jc-data`, `jc-work` |
| Database | at most a share of each service pool per organization; `statement_timeout` per route class; work-memory cap | each service's store layer |
| Storage | bytes per organization, counted from inserts and history partitions, checked before a write | `jc-data`, `jc-work` |
| History | a retention period per space, required, capped by the plan; partitions per week and organization group are dropped on schedule | `jc-data` |
| Jobs | CPU-seconds and memory per run, runs per hour | `jc-work` (wasmtime fuel and memory limits as `joinedcontext-platform/crates/wasm-host/src/limits.rs` sets them today) |
| AI | tokens per day and per conversation, model allow-list | `jc-ai` |
| Egress | allow-listed hosts per App and pipeline, bytes per day | `jc-work` (keeps ADR-N-037) |

Refusals are `429` with `Retry-After` and a problem document naming the limit and the current use, the shape PF-74 already uses for quota refusals. A limit hit by one organization changes nothing for another: the fair queue gives each organization with work its share before any organization gets a second.

## 7. Data owned per service

| Data | Service | Notes |
|---|---|---|
| Organizations, members, groups, clients, keys, tuples | `jc-identity` | the authoritative membership; [03](03-identity-and-authz.md) |
| Manifests and their versions, Changes, reviews | `jc-control` | Git becomes an export and import format, not the store ([07 §2](07-editions-and-migration.md#2-one-artifact-set)) |
| Context data, history, subscriptions | `jc-data` | NGSI-LD; Context Space stays the unit inside an organization |
| Jobs, run logs, App data (schema per App) | `jc-work` | keeps ADR-N-044's schema per App, now under `org_id` too |
| Knowledge chunks, vectors, conversations | `jc-ai` | vector rows carry `org_id`; one index per organization tier ([04](04-isolation-threat-model.md)) |
| Usage counters, quotas, plans | `jc-control` | metered per organization per hour |

## 8. What stays

- The domain model of [Architecture/03](../../Architecture/03-domain-model.md): Organization, Project, Context Space, Endpoint, Policy, ServiceAccount, Pipeline, DataModel and the rest keep their manifests and meaning.
- The broker's views and policy engine deciding every data request (ADR-N-050).
- Reviewed Changes for configuration with green, yellow and red lanes (ADR-N-004), stored in `jc-control` instead of Gitea.
- LinkML as the modeling truth (ADR-N-010).
- Public surfaces and their URLs: `/api/endpoint/{slug}/…`, `/api/v1/projects/{project}/{plural}`.

## Related

- [01-analysis.md](01-analysis.md) — the costs and failures this design answers.
- [03-identity-and-authz.md](03-identity-and-authz.md) — `jc-identity` and the mapping of today's kinds.
- [04-isolation-threat-model.md](04-isolation-threat-model.md) — the controls on each carrier of §3.
- [06-rust-components.md](06-rust-components.md) — per-component decisions behind §2.
- [08-management-api-and-testing.md](08-management-api-and-testing.md) — the management API and the idle-cost and quota tests.
