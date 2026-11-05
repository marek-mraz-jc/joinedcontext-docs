---
sidebar_position: 6
title: "Next Platform: Rust Component Plan"
description: For every component of today's stack, the decision (rewrite in Rust, keep, drop), the size, the risk and the order, and why PostgreSQL stays.
---

# Next Platform: Rust Component Plan

This page decides, per component of today's stack, whether the next platform rewrites it in Rust, keeps it or drops it, with a size estimate, the main risk and the build order. Readers: the owner deciding scope and the agents sizing the phases of [07](07-editions-and-migration.md). Sizes are lines of Rust excluding tests; today's counts come from `find <crate>/src -name '*.rs' | xargs cat | wc -l` in the shared graph checkouts on 2026-11-05.

## 1. Rust code that carries over

| Crate (today) | Lines today | Becomes part of |
|---|---:|---|
| Antares, 32 crates (NGSI-LD model, query language, SQL store, views, OData, OGC, STA, MCP, WebSocket, exports) | 214 961 | `jc-data`, nearly whole; `odata-url`, `odata-csdl`, `odata-json`, `odata-axum` also serve `jc-control`'s management API ([08](08-management-api-and-testing.md)) |
| `context-gateway` | 42 690 | `jc-edge` (token check, write checks, routing); its PDP moves to `jc-identity` |
| `jc-core` | 40 870 | the shared type crate `jc-types` (kinds, URN, policy model) plus protobuf definitions |
| `assistant` | 35 314 | `jc-ai` |
| `jcctl` | 20 586 | the reconciler library inside `jc-control`, and the self-hosted CLI |
| `jc-manifest` | 8 904 | `jc-control` (validation, assembly) |
| `agent-proxy` | 6 333 | `jc-ai` (model proxy, budgets) |
| `wasm-host`, `app-sdk` | 7 201 | `jc-work` |
| `jc-dcat` | 2 375 | `jc-control` catalogue |
| `jc-relationships`, `jc-ngsi-input`, `jc-tabular` | 2 431 | `jc-edge` write checks, `jc-data` |
| `token-sidecar` | 375 | dropped: `jc-work` mints a pipeline's context itself |
| Portal (`joinedcontext-portal/src`) | 258 600 | `jc-control`; its operation registry (`joinedcontext-portal/src/ops/mod.rs`) becomes the management API's source |
| Portal UI (TypeScript, `joinedcontext-portal/ui/src`) | 178 110 | stays TypeScript (React); Rust in the browser is not the goal |

About 650 000 lines of Rust exist. The next platform is mostly a re-plumbing of this code under the tenancy key, not a rewrite from nothing.

## 2. Decision per component

| Component | Decision | Size (new Rust) | Risk | Order |
|---|---|---:|---|---:|
| PostgreSQL (CNPG) | **keep** (§3) | 0 | operations of a single primary; held by CNPG and off-node WAL | — |
| Antares broker | **keep, extend**: `org_id`, fair queue, storage quota, mandatory retention | 6 000 | migration of 29 GB of rows with a new key column ([07](07-editions-and-migration.md)) | 1 |
| Context Gateway + APISIX + Traefik routes | **rewrite** as `jc-edge` on hyper, rustls and tower | 12 000 (half from the gateway) | a new edge carries every request; held by running it behind Traefik first, then in front | 2 |
| Keycloak | **rewrite** as `jc-identity` (provider) | 25 000 | security-critical protocol code ([03 §6](03-identity-and-authz.md#6-risks-and-how-they-are-held)) | 4 |
| Authorization (Portal permissions, gateway PDP) | **rewrite** as `jc-identity` (authorization) | 8 000 | one bug reaches every organization; held by property tests against a reference evaluator | 3 |
| Gitea and its runners | **drop** as store and build system; configuration history in `jc-control` tables, Git as import and export (smart-HTTP read of a generated repository) | 6 000 | people who edit YAML in an editor lose push; held by `jcctl apply` and the Git import | 5 |
| CKAN, Solr, Redis | **drop**: DCAT-AP from `jc-dcat`, HTML catalogue pages and search in `jc-control` over PostgreSQL full-text | 5 000 | harvesters that speak the CKAN Action API; held by a read-only `package_search`/`package_show` subset if a harvester needs it | 6 |
| Bento runner | **rewrite** as the pipeline engine of `jc-work`: sources, steps (LinkML-Map compiled to a Rust IR, WASM steps), outputs through `jc-edge` | 15 000 | Bento's long tail of inputs and Bloblang semantics (KNOWLEDGE, Bento entries); held by a Bloblang subset compiler tested against today's 300 pipelines | 5 |
| jc-functions (QuickJS) | **drop**: server Apps are WASM components (ADR-N-044) | 0 | Apps that use the QuickJS functions need a port | 6 |
| jc-wasm-host | **keep, move** into `jc-work` | 2 000 | none new | 3 |
| Agent runner (OpenHands, Python) | **drop**: the agent loop runs in `jc-ai` with the operation registry as tools | 4 000 | builder quality; held by the existing model-lane evals | 6 |
| jc-assistant, agent proxy | **keep, merge** into `jc-ai` | 3 000 | none new | 4 |
| RMQTT per broker | **replace** by one multi-tenant MQTT listener in `jc-edge` (the `rumqttc` client is vendored today, KNOWLEDGE T-5859; the server codec is small) | 5 000 | MQTT 5 edge cases; held by an MQTT conformance test set | 5 |
| RustFS | **keep** as the default S3 store for self-hosted; the shared edition uses the cloud provider's S3 | 0 | none new | — |
| Model Tools (Python LinkML generators) | **keep** as a job image in `jc-work`, rewrite later on Antares's `linkml-model` crate | 0 now | Python in the stack; it runs only per model publish | 7 |
| Linkerd | **drop**: mTLS in process with rustls and `jc-identity`'s internal CA | 1 500 | certificate rotation bugs; held by short lifetimes and a rotation test | 4 |
| Kyverno | **drop** for the shared edition (six images under one chart with fixed security contexts, checked by conftest in CI); **keep optional** for self-hosted clusters that run it anyway | 0 | admission no longer blocks a hand-edited Pod; held by CI policy on the chart | 6 |
| Prometheus Operator, Grafana | **keep** as operator tools, outside the tenant path; per-organization numbers come from the usage store | 0 | none new | — |
| OpenTelemetry Collector | **keep** (logs and traces carry `org` id only, NP-35) | 0 | none new | — |
| cert-manager | **keep** for public certificates on Kubernetes; the single-host installer uses rustls-acme | 500 | none new | 7 |
| oauth2-proxy | **drop**: `jc-edge` handles sign-in for Apps | 0 | none | 6 |
| Decidim (Ruby, addon) | **keep** as an optional addon outside the core, never in the shared edition's tenant path | 0 | none new | — |

New Rust: about 93 000 lines, plus the protobuf definitions. Services after the plan: `jc-edge`, `jc-identity`, `jc-control`, `jc-data`, `jc-work`, `jc-ai`, with PostgreSQL and an S3 store.

## 3. PostgreSQL: keep

Decided (worker-t6588, owner may override): keep PostgreSQL, because a rewrite would be a mistake. A transactional store with row-level security, PostGIS, full-text search, partitioning and point-in-time recovery is decades of work that no small team reproduces with the same safety, and every isolation control in [04](04-isolation-threat-model.md) T1 relies on RLS that PostgreSQL already enforces (measured forced on the broker tables, [01 §3](01-analysis.md#3-measured-on-dev)). Options considered:

| Option | Verdict |
|---|---|
| Keep PostgreSQL, one cluster, a database per service, RLS on `org_id` | **chosen** |
| A Rust storage engine (for example built on an embedded key-value store) | refused: loses RLS, PostGIS, SQL planning and mature backup; years of risk for the data that matters most |
| A distributed SQL database (CockroachDB, YugabyteDB, or Spanner as a public-source model: Corbett et al., "Spanner: Google's Globally-Distributed Database", OSDI 2012) | not now: one region and a few TB fit one PostgreSQL primary with replicas; revisit above that |
| Database or schema per organization | refused for the shared edition: thousands of schemas multiply migrations and connections and break NP-10; kept for the dedicated tier as a deployment of its own |

What changes around PostgreSQL: WAL archived off the node continuously (NP-84, today only a nightly local dump), history in partitions by week dropped by a retention job (NP-23), the data volume separate from the node's system disk ([01 §6.2](01-analysis.md#62-history-tables-fill-the-disk-t-6581)), and the store layer fixed against the rustls close hang (T-6000) with TLS on in every test database.

## 4. Order and why

1. `jc-data` first: the tenancy key and fair share in the broker fix today's worst failures (pool starvation, disk fill) and every other service builds on it.
2. `jc-edge` second: it mints the `RequestCtx` every later service checks.
3. Authorization third, behind today's Keycloak, so the decisions move to one place before the provider changes.
4. Provider, AI merge and mTLS fourth.
5. Configuration store, pipeline engine and MQTT fifth: the per-project costs (repositories, runners, MQTT pods) go away here.
6. Drops sixth: CKAN, QuickJS, OpenHands, oauth2-proxy, Kyverno in the shared edition.
7. Rewrites that can wait: Model Tools, the single-host installer's certificates.

## Related

- [02-architecture.md](02-architecture.md) — the six services this plan builds.
- [07-editions-and-migration.md](07-editions-and-migration.md) — the phases in task form.
- [01-analysis.md](01-analysis.md) — the measured cost of what is dropped.
- [Architecture/14](../../Architecture/14-components.md) — today's component reference.
