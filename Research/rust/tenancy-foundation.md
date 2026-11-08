---
sidebar_position: 1
title: "Rust Research: Tenancy, Identity, Permission and Data Foundation"
description: One foundation every Rust module of the jc binary calls for organizations, instances, identity, decisions, audit, storage under forced RLS, quotas, server-rendered pages and one operation registry for REST, OData, MCP and CLI.
---

# Rust Research: Tenancy, Identity, Permission and Data Foundation

This page is the shared foundation the product documents of `Research/rust/` (Bento for ekiben, Keycloak for wardkeep, Gitea for shako, CKAN for dataroom) build on, and it replaces their section 5 where they disagree. It inventories what decides tenancy, identity and permission today, then designs the crates every module calls: `jc-auth` (identity, decision, audit), the store layer under forced row-level security, `jc-ops` (one operation registry generating REST with OData, MCP and the CLI) and `jc-web` (server-rendered HTML). Readers: the owner, the agents that write the Argon packs, and the workers that build the modules. Written by worker-t6640 for T-6640 on 2026-11-07.

Trees read (every `path:line` below is at these commits):

| Tree | Commit | Where |
|---|---|---|
| joinedcontext-platform | `e59ceb9f` (2026-11-05) | `/workspace/.cache/cg-main/joinedcontext-platform` |
| joinedcontext-portal | `d7f91eb2` (2026-11-05) | `/workspace/.cache/cg-main/joinedcontext-portal` |
| Antares-NGSI-LD-Context-Broker | `b683bfc3` (dev, 2026-11-05) | `/workspace/.cache/cg-main/Antares-NGSI-LD-Context-Broker` |
| ekiben | `1bacb1e` | `github.com/marek-mraz-jc/ekiben` |
| joinedcontext-docs | `149d9b1` | this repository |

A bare `crates/` path is in the platform and a bare `src/` or `migrations/` path in the Portal, unless the cell or sentence names Antares or ekiben first: in a cell that opens with an `Antares-NGSI-LD-Context-Broker/` or `ekiben/` path, or a row about Antares, the following short paths are in that repository. The earlier design set [Next Platform](../next-platform/02-architecture.md) (T-6588) proposed separate services (`jc-edge`, `jc-identity`, `jc-data`, ...); the owner's 2026-11-07 direction is one `jc` binary of modules that can also run alone. This page keeps that set's tenancy key, Zanzibar-style model and threat model and recasts them as libraries inside one process.

## 1. Capability inventory

What decides tenancy, identity and permission today, one row per capability. "Today" cites the code; "Platform" says whether the foundation keeps it.

### 1.1 Kinds and their checks (jc-core)

| Capability | Today | Platform |
|---|---|---|
| Organization, `spec.domain` as `{orgDomain}`, `spec.installation`, `spec.limits` (ADR-N-035) | `crates/jc-core/src/kinds/organization.rs:14` (spec), `:46` installation, `:203` validate, `:257` `owns_domain` accepts the domain or a subdomain | needed: becomes an `organizations` row; `installation` retires (no organization owns the deployment) |
| Project with `organizationRef`, `domain`, `quotas`, `visibility` | `crates/jc-core/src/kinds/space.rs:15`, validate `:96-158`, reserved names `d`, `me` `:78-83` | needed: a row keyed by `(org_id, id)` |
| ContextSpace with `urnSegment`, retention, quality, `brokerRef` | `crates/jc-core/src/kinds/space.rs:285`, broker Tenant name `{project}-{name}` or the pin, `space.rs:731-736` | needed: the broker's partition is `(org_id, instance_id, space_id)`, the segment stays an attribute (ADR-N-041) |
| Role (rules of kind and verb), project roles may not name org-only kinds | `crates/jc-core/src/kinds/role.rs:179`, `:213`, `:244` | needed: permission sets in the decision schema |
| RoleBinding with `RoleScope` (exactly one of `contextSpace`, `project`, `organization`) | `role.rs:411`, `service_account.rs:84`, validate `service_account.rs:98-106` | needed: relation tuples |
| Group (members by Keycloak UUID only, ADR-N-061) | `crates/jc-core/src/kinds/group.rs:28`, `:61` | needed: `group#member` tuples |
| ServiceAccount (`pl-`, `appjob-` prefixes refused, MQTT grant scoped to own project) | `crates/jc-core/src/kinds/service_account.rs:15`, `:344-388` | needed: client rows of wardkeep |
| Policy: assignee kinds `User`, `Group`, `Role`, `ServiceAccount`, `Did`, `Organization` (no id, means the Policy's own Organization) | `crates/jc-core/src/kinds/policy.rs:741`, `PrincipalKind` `:500-516`, org assignee without id `:1019-1039` | needed: the attribute half of a data grant (§5.4) |
| DelegationPolicy (subjects, projects, segments, kinds, endpoints, writes, `personalData`, `maxExpiry` P1D..P365D, `allowedClients`, `aboveCeiling`) | `crates/jc-core/src/kinds/delegation_policy.rs:182`, `:270-330` | needed: the connector ceiling (§5.8) |
| Endpoint audience `organization`, `public`, `project-list`; `policyRef(s)` | `crates/jc-core/src/kinds/endpoint.rs:479`, `:755`, `:991` | needed |
| `orgDomain` resolution: Environment overlay, else the installation Organization's domain; none or several claiming installation renders no domain | `crates/jc-manifest/src/loader.rs:909-943`, `:1162-1172`; refusals `crates/jc-manifest/src/validate.rs:583-627` | changes: a domain is per organization and per instance (§5.6), never one per deployment |

### 1.2 Decisions

| Who decides | Today | Platform |
|---|---|---|
| Portal configuration rights: `Effective::may(kind, verb)`, `may_read_in(kind, space)`, `check(kind, verb, target)` | `src/permissions.rs:247`, `:350`, `:372`; bindings from the org namespace `in_force` `:928`, subject match `names_caller` `:976`; realm roles count as groups `:1691` | replaced by `jc-auth::Decide::check` |
| Organization admin of a non-installation Organization narrowed to its own settings | `src/permissions.rs:596` `organization_reaches`, `:667` `narrowed_to_own_settings`, `:613` `without_organization_kinds` | kept as a rule: an organization's admin holds nothing outside it (ADR-N-058 §2.4) |
| Gateway PDP: MCP tool listing, discovery, schema projection, write guards, quality and relationship checks | `crates/context-gateway/src/pdp/mod.rs:28-121`; tools `mcp/tools.rs:1085-1096`; discovery `auth/subject.rs:768-775`; writes `handlers/writes.rs:311`, `:592`, `:663`; guards `pdp/write_guard.rs:75-249` | folded into `Decide` (listing, discovery, projection) and into the broker module (write guards) |
| Antares view engine decides every NGSI-LD read and write through an Endpoint (ADR-N-050) | `Antares-NGSI-LD-Context-Broker/addons/joinedcontext-policy/src/lib.rs:100-134`, `decide.rs:51`; fail-closed seam with timeout `crates/antares-api/src/policy.rs:1310-1346` | kept: the broker module compiles `Decide::grant` into its query, as today |
| Antares trusts subject headers only from a vouched caller | `Antares-NGSI-LD-Context-Broker/crates/antares-api/src/admin_auth.rs:146-170`; mesh identity `provenance.rs:145-152`; eight headers `addons/joinedcontext-policy/src/subject.rs:11-20` | retired inside one process: the decision context is a Rust value, not headers (§2.2) |
| Gateway subject: `jc_org` membership, `/{org}/g` groups, fallback to plain `groups` | `crates/context-gateway/src/auth/subject.rs:20-81`, `:607-637` | replaced by `Principal` (§2.2) |
| Gateway strips client `x-jc-*` and `l5d-*` headers, pins caller | `crates/context-gateway/src/middleware/tenancy.rs:22-183` | kept at the edge of a standalone module; unneeded in-process |
| Connector ceiling `Ceiling::admits` | `src/connectors.rs:263`, `:353`, `:556`; default policy data-read, reads only, 30 days `:276` | kept, moved into `Decide` as a ceiling relation |

### 1.3 Copies the foundation removes

The reconciler copies permissions into three upstream products every 60 s (`JC_PORTAL_SYNC_INTERVAL`, `src/config.rs:91`; leader lease 60 s, `src/reconciler/leader.rs:37`; `do_sync` `src/reconciler/daemon.rs:1150-1320`).

| Copy | Today | After |
|---|---|---|
| Keycloak groups from Group manifests, `{slug}-readers`/`-writers` from RoleBindings, `{organization}_bound` with `jc_org` | `src/reconciler/groups.rs:66`, `:188` | gone: wardkeep reads the tuple store directly |
| Keycloak clients per App (`app-{name}`), per McpServer (`mcp-{project}-{name}`), per ServiceAccount (`{project}-{name}`), per Endpoint MCP scope | `src/reconciler/app_clients.rs:651`, `:1018`; `mcp_clients.rs:113`; `workload_clients.rs:578-727`; `hub_scopes.rs:123` | gone: clients are rows of wardkeep made in the same transaction as their manifest |
| Gitea teams per project from Keycloak groups; repositories and branch protection only at create | `src/reconciler/project_teams.rs:63`; `src/api/projects.rs:670-710` | gone: shako asks `Decide` per request |
| CKAN organizations and datasets per published Endpoint, every 3600 s; no member sync | `src/reconciler/ckan.rs:216`, `:467-469`, `:655` | gone: dataroom reads Endpoints and decisions in-process |

Each copy is a place where tenancy can drift: KNOWLEDGE records a bare group name matched across organizations (T-6408), a realm default scope linked to every client (T-6301) and a cache keyed without `jc_org` (T-6414).

### 1.4 Storage isolation today

| Store | Today | Platform |
|---|---|---|
| Antares: `tenant_id text` on every row, `ENABLE` + `FORCE` RLS, policy `tenant_id = current_setting('antares.tenant', true)` | `Antares-NGSI-LD-Context-Broker/crates/antares-sql/migrations/0001_init.sql:250-273`; set per transaction by `set_config('antares.tenant', $1, true)`, `crates/antares-sql/src/lib.rs:30-32`, `src/store/pg/mod.rs:328-340` | kept, re-keyed to `(org_id, instance_id)` uuids |
| Antares service escape `antares.service = 'on'` for read and delete only | `migrations/0005_service_escape_by_command.sql:15-40` | kept as a pattern: maintenance reads, never maintenance writes |
| Antares refuses to boot when its role bypasses RLS (`ANTARES_REQUIRE_RLS`) | `crates/antares-sql/src/store/pg/mod.rs:342-357`, `crates/antares-broker/src/main.rs:948-965` | kept for every module, on by default |
| Antares RLS coverage and pentest tests | `Antares-NGSI-LD-Context-Broker/crates/antares-sql/tests/rls_covers_every_table.rs`, `tests/pg_rls_pentest.rs` | kept as the template for every module (§7) |
| Antares leakproof index paths: geohash cell, `COLLATE "C"` byte keys | `migrations/0015_rls_index_paths.sql:1-10`, `0024_entity_values.sql:2-6`, `0027_entities_id_bytes.sql:1-12` | kept as rules (§5.3) |
| Assistant: `project = current_setting('jc.project', true)` on every table, `FORCE` | `crates/assistant/migrations/0001_store.up.sql:126-140`, `crates/assistant/src/lib.rs:105-120` | re-keyed to `(org_id, instance_id, project_id)` |
| Portal `activity` table: `project NOT NULL`, no organization column, 7 days | `migrations/0012_activity.sql:3`, `src/activity.rs:61` | changes: one activity log with org and instance ids (§5.9) |
| Portal `connector_calls`: no project or organization column | `migrations/0051_connectors.sql:20` | changes: same log |

### 1.5 Limits today

| Limit | Today | Platform |
|---|---|---|
| Organization limits `edge`, `gateway`, `sign_in`, `people`, `agents.spend_per_day/month`, `pipelines`, `data`, `apps`, `mqtt` | `crates/jc-core/src/kinds/org_settings.rs:108`, `:206` | kept as plan fields (ADR-N-035) |
| `agents.spend_per_day/month` | no consumer outside jc-core | needed: the AI module enforces it |
| Project quota falls back to the organization default | `src/quotas.rs:30-49`: `organization_default` takes the first Organization with `projects.quota`, not the project's own | defect with several Organizations; the foundation keys every quota by `org_id` |
| wasm-host: 64 MiB memory, 5 s wall, fuel 2e11, 2 MiB request, 8 MiB response, 16 per App, 64 per project; overrides only lower | `crates/wasm-host/src/limits.rs:33-90` | kept, keyed by `(org_id, instance_id)` |
| Assistant budget per AssistantDeployment, `costPerDayUsd` 0.01..1000 | `crates/jc-core/src/kinds/assistant.rs:743-751` | kept, summed per organization |

## 2. Internals: the foundation crates

```text
crates/shared/
  jc-types   OrgId, InstanceId, ProjectId, SpaceId, ObjectRef, RequestCtx (no I/O)
  jc-auth    Identity, Decide, Audit traits; tuple engine; standalone defaults
  jc-store   Postgres pool per module, tenant transaction, RLS boot checks, migrations
  jc-ops     operation registry; REST, OData, MCP and CLI generated from it
  jc-odata   OData URL and CSDL over the Antares odata-* crates, mapped to SQL under RLS
  jc-web     layout, components, forms, CSP nonces, page registration (askama)
  jc-quota   token buckets and weighted fair queues keyed by org and instance
crates/modules/{broker,ekiben,wardkeep,shako,dataroom,control,assistant,factory}
crates/jc    the one binary: `jc run --modules broker,ekiben,...`
```

Rule: a module depends on `crates/shared/*` and on other modules' `*-api` crates only (the rule `ekiben/REPOSITORY.md` already states). A module never opens another module's schema.

### 2.1 Tenancy types (`jc-types`)

| Type | Form | Constructors |
|---|---|---|
| `OrgId` | UUIDv7, 128 bit | parsed only from a verified `RequestCtx` or a row of `wardkeep.organizations`; no `Default`, no `From<&str>` |
| `InstanceId` | UUIDv7 | one per running copy of a product per organization (two catalogues = two ids) |
| `ProjectId`, `SpaceId` | UUIDv7 | rows of `control`; names stay attributes |
| `ObjectRef` | `(type, OrgId, InstanceId, id)` | the only key a decision accepts |
| `RequestCtx` | `{ principal, org, instance, request_id, deadline, consistency }` | built by `jc-auth::Identity::verify` |

ekiben today has `pub struct OrgId(pub String)` with `impl Default` returning `"default"` (`ekiben/crates/ekiben-core/src/org.rs:16-22`) and a test building one with `OrgId::default()` (`ekiben/crates/ekiben-server/src/unit_test.rs:743`). A public field and a default make a call without a tenant compile; the foundation type forbids both, and ekiben moves to it in its first foundation task.

### 2.2 `jc-auth`: identity, decision, audit

Three traits, one struct per role, every module calls them in-process. A module running alone gets the standalone implementations.

```rust
pub enum Subject {
    Person { id: PersonId, acr: Acr },
    Workload { client: ClientId },
    Connector { id: ConnectorId, owner: PersonId, client: ClientId },
    Participant { did: Did },
    Anonymous,
}

pub struct Principal {
    pub org: OrgId,            // the organization this request acts in
    pub subject: Subject,
    pub groups: GroupSet,      // group ids of `org` only, never names
    pub read_only: bool,       // connector without writes (ADR-N-064 §7)
}

#[async_trait]
pub trait Identity: Send + Sync {
    /// Verifies the bearer, session cookie or mTLS peer of one request and resolves the
    /// organization and instance from the host name (§5.6). Never reads `x-jc-*` headers.
    async fn verify(&self, req: &http::request::Parts) -> Result<RequestCtx, AuthError>;
}

#[async_trait]
pub trait Decide: Send + Sync {
    async fn check(&self, ctx: &RequestCtx, perm: Permission, obj: &ObjectRef) -> Decision;
    /// Ids the caller reaches, filtered before paging and counting (§5.7).
    async fn list(&self, ctx: &RequestCtx, perm: Permission, ty: ObjectType, page: PageReq)
        -> Page<ObjectId>;
    /// The compiled data grant of one Endpoint: types, attributes, operations, q, geo, time.
    async fn grant(&self, ctx: &RequestCtx, endpoint: &ObjectRef) -> DataGrant;
    async fn explain(&self, ctx: &RequestCtx, perm: Permission, obj: &ObjectRef) -> Explanation;
}

pub trait Audit: Send + Sync {
    /// Appends one row to the activity log in the caller's transaction (§5.9).
    fn record(&self, tx: &mut TenantTx<'_>, event: AuditEvent);
}
```

`Decision` is `Allow { reason }` or `Deny { reason, visible: bool }`. `visible: false` means the caller may not learn the object exists; every interface turns it into the same answer as a missing object (404 on REST, an empty list on OData, "not found" on MCP), the rule today's Portal applies by hand per route.

| Implementation | In the `jc` binary | Module alone |
|---|---|---|
| `Identity` | wardkeep verifies its own sessions and tokens; keys in memory, no network hop | `jc-auth` OIDC verifier against any issuer (wardkeep, Keycloak during migration), JWKS cached, `iss`/`aud`/`exp`/`azp` checked |
| `Decide` | tuple engine over schema `auth` (§2.3), cache keyed `(org, subject, groups digest, consistency)` | the same engine over the module's own `auth` schema, seeded from a YAML file; or a remote `Decide` client of a `jc` deployment |
| `Audit` | rows in schema `audit` in the caller's transaction | the same table in the module's database |

Decided (worker-t6640, owner may override): the decision engine is a library, not a service, because in one binary a network hop on every request buys nothing and the next-platform design's `Check` hop ([03 §3](../next-platform/03-identity-and-authz.md#3-authorization-model)) was the largest per-request cost it named. Options: a separate authorization service (needed only when modules run on different hosts; the remote `Decide` client covers that), a policy language engine such as Cedar or OPA (a second language for rules the tuple model already expresses, and no per-row geo or time narrowing).

### 2.3 Decision model

The model is the next-platform hybrid: Zanzibar-style tuples for "who holds which role where", attribute rules for "what a data grant narrows" ([03 §3](../next-platform/03-identity-and-authz.md#3-authorization-model)). Schema `auth`, owned by role `jc_auth`:

| Table | Key | Content |
|---|---|---|
| `tuples` | `(org_id, object_type, object_id, relation, subject_type, subject_id, subject_relation)` | relations `admin`, `steward`, `editor`, `viewer`, `member`, `parent`, `ceiling`, `audience` |
| `roles` | `(org_id, id)` | custom permission sets of the organization; seeded roles are schema constants |
| `grants` | `(org_id, instance_id, endpoint_id, id)` | compiled Policy rules (types, attributes, operations, q, geo, time, validity) |
| `revision` | `(org_id)` | a counter bumped by every tuple write; the consistency token of a decision |

Inheritance is a rewrite rule (organization covers project covers space covers object), never one tuple per child. A tuple cannot name an object or subject of another organization; sharing across organizations is a tuple whose subject is `organization:{other}#member` or an Endpoint audience, written only by an admin of the owning organization in a red-lane change (next-platform [03 §4](../next-platform/03-identity-and-authz.md#4-todays-kinds-on-the-new-model), row SharedSpaceReference).

Today's kinds map one to one as next-platform 03 §4 lists them. Two corrections from this inventory:

- `Policy.assignee {kind: organization}` (`policy.rs:1019-1039`) becomes `organization:{own}#member`; it cannot name another organization, as today.
- `DelegationPolicy.personalData` exists in jc-core but the Portal ceiling never reads it (`src/connectors.rs:270`, `:286`, `:393`: always `false`), so every `personalData` tick is refused (`:1755`). The ceiling relation carries it.

### 2.4 Store layer (`jc-store`)

One Postgres database, one schema and one role per module (§5.3). The only way to run a statement on a tenant table is a `TenantTx`:

```rust
impl ModuleStore {
    /// BEGIN; set_config('jc.org', $1, true); set_config('jc.instance', $2, true).
    pub async fn tenant(&self, ctx: &RequestCtx) -> Result<TenantTx<'_>, StoreError>;
    /// Maintenance: sets `jc.service = 'on'`, which the read and delete policies honour and
    /// the insert and update policies do not (Antares 0005's split).
    pub async fn maintenance(&self, why: &'static str) -> Result<MaintTx<'_>, StoreError>;
}
```

At start the store refuses to serve when the module role is superuser or `BYPASSRLS`, or when any table of the schema lacks `relforcerowsecurity` (the check `rls_covers_every_table.rs` makes in Antares, run at boot instead of only in tests).

### 2.5 Operation registry (`jc-ops`)

Today the Portal declares 91 operations once (`struct Operation`, `src/ops/mod.rs:428`: name, title, description, input and output schema functions, annotations, kind, verb, lane, validate, run; collected by `init_registry` `:749-774`; called through `ops::call` `:480`, which runs secret scan, permission, schema check, validate, run and MCP masking in that order). Count: `grep -rhoE '"jc_[a-z_]+"' src/ops | sort -u | wc -l` prints 93 distinct `jc_*` names, of which 91 are registered operations and the rest test fixtures (inventory agent count: 69 literal names, 16 constant names, 6 `read(` helpers). ADR-N-064 §3.1 already makes this registry the source of REST, OpenAPI, MCP, `jcctl` and UI form schemas.

The foundation generalises it across modules:

```rust
pub struct Operation {
    pub name: &'static str,                  // "catalogue.dataset.list"
    pub module: Module,
    pub input: fn() -> schemars::Schema,
    pub output: fn() -> schemars::Schema,
    pub permission: Permission,              // checked by Decide before `run`
    pub object: ObjectSelector,              // which input field names the ObjectRef
    pub lane: Lane,                          // green, yellow, red (review lanes)
    pub list: Option<ListSpec>,              // present: REST and OData list over a table
    pub run: for<'a> fn(&'a OpCtx, Value) -> BoxFuture<'a, Result<Value, OpError>>,
}

inventory::collect!(Operation);              // each module registers with `inventory::submit!`
```

Generated from the one registry:

| Interface | Form | Generated by |
|---|---|---|
| REST | `/api/v1/orgs/{org}/instances/{instance}/{module}/{plural}` plus the host-name form of §5.6 | `jc-ops::rest::router()` |
| OData 4.01 | every `list` operation: `$filter`, `$select`, `$orderby`, `$top`, `$skip`, `$count`; CSDL `$metadata` per module | `jc-odata`, parser from `Antares-NGSI-LD-Context-Broker/crates/odata-url`, CSDL from `crates/odata-csdl`, axum glue from `crates/odata-axum` |
| MCP | one tool per operation; `tools/list` filtered by `Decide` | `jc-ops::mcp` |
| CLI | `jc <module> <operation> --flag value`, absorbing `jcctl` | `jc-ops::cli` with clap built at start from the schemas |
| HTML forms | field list, hint lines and server validation of the input schema | `jc-web::form` |

`$filter` maps to SQL by an allow-list per `ListSpec`: each filterable property names its column and the operators its index serves under RLS (§5.3); any other property or operator answers 400 naming it. The filter is applied inside the `TenantTx`, after RLS and before `LIMIT` and `count(*)`, so totals count only what the caller reads. A list whose rows also need a per-row `Decide` (objects shared one by one) joins `auth.tuples` in the same statement instead of filtering after the page; filtering after paging leaks the count. The pilot T-6632 (`agent/worker-t6632/T-6632`) and the table interface T-6642 (`agent/worker-t6642/T-6642`) are the first two steps of this crate.

CI check: a test walks the registry and fails when an operation lacks its REST route, its MCP tool or its CLI command, or when the three schemas differ; and when a route, tool or command exists that no operation declares. "No tool exists only for MCP and no admin bypass" is that test.

### 2.6 Server-rendered HTML (`jc-web`)

Every module ships pages in the `jc` binary: HTML rendered by the server, templates plus small progressive enhancement, no SPA build.

Template engines measured on 2026-11-07 (rustc 1.99.1, release, host load 10 to 11 on 12 cores; one page: layout, nav, a form with a hint and an error, a 100-row table with escaped text; 10.6 KB output; 20 000 renders, two runs). Sources and the runner: [tenancy-foundation-templating](../../scripts/research/tenancy-foundation-templating/run.sh).

| Engine | Version | Cold release build | Incremental | Binary | Crates | Render |
|---|---|---:|---:|---:|---:|---:|
| askama (Jinja syntax, compiled, typed) | 0.16.1 | 8.0 s | 0.34 s | 488 KB | 24 | 9.2 / 8.9 µs |
| maud (Rust macro DSL, compiled) | 0.27.0 | 3.6 s | 0.23 s | 487 KB | 12 | 7.0 / 7.0 µs |
| minijinja (runtime Jinja, serde values) | 3.0.5 | 11.8 s | 0.46 s | 2.34 MB | 12 | 53.8 / 52.2 µs |

At 100 req/s every engine costs under 0.6 % of one core. The choice is about checks and authors:

Decided (worker-t6640, owner may override): askama for every built-in page, because templates are HTML files a designer can read, the compiler checks every field and type, and escaping is on by default; minijinja (with its `fuel` feature) only for pages a WASM plugin brings at run time (§3), where templates cannot be compiled in. Options: maud (fastest, smallest, but markup lives in Rust macros nobody outside Rust edits), minijinja everywhere (6x slower and template errors surface at run time).

Shared parts, owned by `jc-web`:

| Part | Design |
|---|---|
| Layout | one `base.html`: skip link, landmark regions, organization switcher, module nav built from the registry, breadcrumb, `<main>` with one `h1` and a purpose line (the Portal walker rule, KNOWLEDGE T-6105) |
| Components | askama macros: table with sort and paging links (OData query string), form field with label, hint line with an example and error slot (`aria-describedby`), select whose options come from `Decide::list`, empty state with the next action, problem banner (`role="alert"`) |
| Forms | POST, server validation by the operation's input schema; a refused field re-renders with its message beside it (422 naming the field); a select's submitted value is checked again by `Decide` (403 naming the field); CSRF token per session, `SameSite=Lax` cookie |
| CSP | `default-src 'self'; script-src 'nonce-{n}'; style-src 'self' 'nonce-{n}'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`, one random nonce per answer (today's Portal does the same, `src/csp.rs`) |
| Progressive enhancement | one small script per behaviour (sortable header, live run log by server-sent events), each page usable without it |
| Pages of a module | `jc_web::page!(module, path, permission, Template)` registers a route, its nav entry and its permission; the nav shows only pages `Decide` allows |
| Phone | one CSS file, layout by grid, 400 px tested by Playwright on every page |

## 3. Extension system

| Kind | How it hooks in | What it may touch | Isolation |
|---|---|---|---|
| Built-in module | a crate behind a cargo feature of `jc`; registers operations, pages, migrations, background jobs through `inventory` | its own schema and role, the shared crates, other modules' `*-api` | Rust types (no `OrgId` without a verified context), Postgres role and forced RLS |
| WASM component | a component on the platform wasm-host (`crates/wasm-host`), WIT world `jc:app` today (`crates/wasm-host/wit/jc-app.wit:167-173`): `sql` on its own schema, `blob`, `identity.caller`, `email.send`, `ai.complete` | only what the host functions give; outbound HTTP only to the gateway under the caller's token (`crates/wasm-host/src/host.rs:143-197`) | fuel, 64 MiB memory, 5 s wall, concurrency caps (`limits.rs:33-48`); per `(org_id, instance_id)` |
| Plugin page | a WASM component exports `render(page, input) -> html` or ships a minijinja template rendered by the host | the page frame `jc-web` gives; never the layout, nav or CSP | escaping on, fuel limit on minijinja, CSP nonce owned by the host |

A plugin registers operations the same way as a module (a WIT `operations` export listing name, schemas, permission), so it appears in REST, OData, MCP and CLI and passes `Decide`. A plugin never receives a database connection, a token of its own or another organization's id; `identity.caller` returns the `Principal` of the request.

## 4. Security

### 4.1 Flows

```mermaid
sequenceDiagram
  participant B as Browser
  participant J as jc (module + jc-auth)
  participant W as wardkeep (same process)
  participant P as Postgres
  B->>J: GET https://catalogue.example.org/datasets
  J->>J: host name -> (org, instance) from wardkeep.domains (cached)
  J->>W: no session cookie: redirect to /authorize of the org's issuer
  B->>W: sign in (password + TOTP or passkey, or upstream IdP)
  W->>B: session cookie (host-only, Secure, HttpOnly, SameSite=Lax)
  B->>J: GET /datasets with cookie
  J->>W: Identity::verify -> RequestCtx{org, instance, principal}
  J->>P: BEGIN; set_config jc.org, jc.instance; SELECT ... LIMIT
  J->>J: Decide::list filters before LIMIT; Audit::record for writes
  J->>B: HTML
```

| Flow | Sequence | Notes |
|---|---|---|
| Person in the browser | above: authorization code with PKCE at the organization's issuer, session cookie per host | wardkeep's research (T-6637) owns the protocol detail |
| Person's CLI | `jc login` runs device authorization or a loopback PKCE flow, stores a refresh token in the OS keyring; each call sends a bearer of audience `jc-cli` | a local `jc` (module alone) accepts the same token when its issuer is configured |
| MCP connector | token bound to one connector by the `connector:{id}` scope (ADR-N-064 §3.3), `sub` equals the owner, `azp` in `allowedClients` when set | rate per person, revocable, every call audited with the connector id |
| Workload (pipeline, App job) | client credentials of a wardkeep client row, audience per module; in-process calls pass the `RequestCtx` | no static keys between modules |
| Module to module on other hosts | mTLS with certificates from wardkeep's internal CA plus the signed `RequestCtx` (next-platform [03 §5](../next-platform/03-identity-and-authz.md#5-tokens-on-the-wire-inside)) | only when modules run apart |

### 4.2 Classes of failure and the design's answer

| Class (seen in this platform or its upstreams) | Example | Design answer |
|---|---|---|
| Missing tenant filter | a cache keyed without `jc_org` served one member's reach to another (KNOWLEDGE T-6414) | `OrgId` required by the cache type; RLS under every query; isolation tests per module (§7) |
| Name used as identity | bare group names matched across organizations (T-6408); a tenant derived from a URN segment (ADR-N-041) | ids, never names; names are unique only inside `(org_id, instance_id)` |
| Default that widens | a realm default scope linked to every client (T-6301); a Policy without `policyRef` binds every Endpoint (T-6455) | no realm-wide defaults; an Endpoint without a grant reads nothing |
| Copy drift | the reconciler's Keycloak, Gitea and CKAN copies (§1.3) | no copies: every module asks `Decide` |
| Header trust | client-sent `x-jc-*`, `l5d-client-id` | in-process context; at a module's own edge every `x-jc-*` from a client is dropped |
| Existence leak | counts, 403 vs 404, timing | filter before count; `Deny { visible: false }` answers as absence; constant work for a refused id (next-platform [04 §3](../next-platform/04-isolation-threat-model.md#3-noise-bound-and-timing)) |
| Privilege by role attribute | an application role with `BYPASSRLS` (Antares only warns unless `ANTARES_REQUIRE_RLS`) | boot refusal on by default (§2.4) |
| Quota crossing organizations | `src/quotas.rs:40` takes the first Organization's quota for every project | quotas keyed by `org_id` in `jc-quota`; a test with two organizations of different quotas |
| Injection through tool results | tenant data steering an agent | the untrusted-data fence on every MCP text result (KNOWLEDGE T-5559); writes need a person's approval where the lane asks |
| Secret in logs | a token in a log line | redaction at write time in the tracing layer (§6.4); `secretRef` only |

Secrets: wardkeep keys and module database passwords come from the secrets mount; OIDC client secrets are stored hashed (argon2id) when wardkeep issues them; tokens compared in constant time (`subtle`). Input limits: request body 2 MiB by default per route class, OData `$top` at most 1000, `$filter` depth at most 16 nodes, page token signed and bound to `(org, instance, query digest)`.

## 5. Tenancy

### 5.1 How the upstreams model it

| Product | Upstream unit | Limit for us | Source |
|---|---|---|---|
| Keycloak | realm per tenant; organizations feature inside a realm | a realm per organization costs memory and a client list per realm; one realm today (PF-01) | wardkeep research T-6637 |
| Gitea | organization and team inside one instance | one instance per deployment; no per-organization domain | shako research T-6639 |
| CKAN | organization inside one site | one site, one domain, one Solr; two catalogues of one organization need two sites | dataroom research T-6638 |
| Bento | none: one process per stream set | tenancy is the runner's job; today one runner per deployment | ekiben research T-6636 |
| Antares | Tenant per Context Space, `tenant_id` text with RLS | one broker per deployment; Tenant names `{project}-{space}` | §1.4 |

### 5.2 The model

| Level | Id | Holds | Example |
|---|---|---|---|
| Deployment | none | modules, Postgres, object store, the operator | `jc` on one node |
| Organization | `OrgId` | people, groups, roles, domains, plan and quotas | City of Helsinki |
| Instance | `InstanceId` | one running copy of one product for one organization | Helsinki's open data catalogue and its internal catalogue: two dataroom instances |
| Project | `ProjectId` | configuration repository, apps, budget (ADR-N-059) | `helsinki` |
| Context Space, Endpoint, Pipeline, App, Repository, Dataset | object ids | the things people work on | `mobility` space |

An instance belongs to exactly one organization and one module. A module that has no notion of several copies (the broker) still has one instance per organization, so every table carries both ids and one policy shape serves all modules.

### 5.3 One Postgres, a schema and role per module

| Schema | Owner role | Module |
|---|---|---|
| `auth` | `jc_auth` | jc-auth tuples, grants, revision |
| `audit` | `jc_audit` | activity log (§5.9) |
| `identity` | `jc_wardkeep` | organizations, domains, people, clients, sessions, keys |
| `control` | `jc_control` | projects, manifests, changes, review lanes |
| `broker` | `jc_broker` | entities, history (today's Antares tables) |
| `pipeline` | `jc_ekiben` | streams, runs, run logs |
| `forge` | `jc_shako` | repositories, pull requests, reviews (packs in the object store) |
| `catalogue` | `jc_dataroom` | datasets, resources, harvest sources |
| `assistant` | `jc_assistant` | sites, chunks, conversations |

Rules:

1. Every tenant table has `org_id uuid NOT NULL, instance_id uuid NOT NULL` leading its primary key and every index; `ENABLE` and `FORCE ROW LEVEL SECURITY`; one policy `org_id = current_setting('jc.org', true)::uuid AND instance_id = current_setting('jc.instance', true)::uuid` for `USING` and `WITH CHECK`. Tables of the organization level (`identity.people`) use `org_id` alone.
2. Each module logs in as `jc_<module>_app`, member of its NOLOGIN owner role, never superuser, never `BYPASSRLS`, `USAGE` on its own schema only.
3. A cross-module read goes through the other module's `*-api` crate, which opens its own `TenantTx` with the same `RequestCtx`.
4. Index conditions use leakproof operators only.

Measured on PostgreSQL 17.11 (docker `postgres:17`, 2026-11-07; 100 organizations x 2 instances x 1000 rows; queries as `jc_catalogue_app` with `jc.org` and `jc.instance` set; script [tenancy-foundation-rls.sql](../../scripts/research/tenancy-foundation-rls.sql)):

| Operator | Function | `proleakproof` |
|---|---|---|
| `uuid = uuid` | `uuid_eq` | true |
| `text = text`, `text < text` | `texteq`, `text_lt` | true |
| `int8 = int8`, `timestamptz < timestamptz` | `int8eq`, `timestamptz_lt` | true |
| `text ~~ text` (LIKE), `text ~ text` | `textlike`, `textregexeq` | false |
| `jsonb @> jsonb`, `jsonb ? text` | `jsonb_contains`, `jsonb_exists` | false |
| `anyarray @> anyarray` | `arraycontains` | false |
| `tsvector @@ tsquery` | `ts_match_vq` | false |

| Query under RLS | Plan |
|---|---|
| `count(*)` with org 1 set | 1000 rows |
| `WHERE org_id = <org 2>` with org 1 set | 0 rows |
| `INSERT` a row of org 2 with org 1 set | `new row violates row-level security policy` |
| any query with `jc.org` unset | `invalid input syntax for type uuid: ""`: fails closed with an error |
| `name = 'ds-7'` (default collation) over an index on `name COLLATE "C"` | bitmap scan on `(org_id, instance_id)`, `name` as filter: the index is not used |
| `name COLLATE "C" = 'ds-7'` | index scan with all three columns as index condition |
| `name LIKE 'ds-7%'` | filter only (`textlike` not leakproof) |
| `doc @> '{"theme":"theme-3"}'` with a GIN index | filter only: the GIN index is never used |
| `theme = 'theme-3'` on a stored generated column `doc->>'theme'` with a btree `(org_id, instance_id, theme)` | index scan, `theme` in the index condition |

Rules taken from it: index keys are columns of leakproof types compared in the collation the index was built with (`COLLATE "C"` on both sides, the Antares 0027 pattern); a prefix search is a range `>= p AND < p'` over that key, never `LIKE`; a JSON field that is filtered becomes a stored generated column with a btree index; full-text search (dataroom, assistant) is a separate read that runs as the module role in a function marked `SECURITY INVOKER` with the tenant columns in its own `WHERE`, proved by `EXPLAIN` as the module role (KNOWLEDGE T-5773). A missing tenant setting is an error the store turns into a 500 with a log line, never an empty answer.

### 5.4 Data grants

The broker module keeps the view engine. `Decide::grant(ctx, endpoint)` returns the compiled rules of the Endpoint's Policies for the caller (today Antares compiles the rule document per Tenant, `addons/joinedcontext-policy/src/document.rs:390-395`); the broker turns it into its query as today. What changes: the rule document is a row set in `auth.grants` keyed by `(org_id, instance_id, endpoint_id)` instead of a JSON document pushed to `/q/policy/{tenant}`, and the subject is the `Principal` value instead of the eight `x-jc-*` headers.

### 5.5 Identity per organization

wardkeep holds people per organization: `identity.people (org_id, id)`. A person who works for two organizations has two person rows, linked by a verified e-mail or an upstream IdP subject when the person chooses to link them; a session acts in one organization at a time and the organization switcher re-issues the session for the other. Decided (worker-t6640, owner may override): one person row per organization, because it keeps every query of a module inside one `org_id` and makes deleting an organization a delete by key; options: one global person with memberships (simpler sign-in, but every people query crosses organizations and a person row outlives the organizations that named it).

Upstream IdPs (an organization's Entra ID, a national eID) are per organization and per identity domain: `identity.idps (org_id, id)`; an organization may run several identity domains (staff and residents) as several wardkeep instances.

### 5.6 Domains and TLS per organization and instance

| Table | Key | Content |
|---|---|---|
| `identity.domains` | `(host)` unique across the deployment | `org_id`, `instance_id`, `module`, `verified_at`, `tls: acme or uploaded secretRef` |

A request's organization and instance come from its host name: `catalogue.hel.example` resolves to `(hel, catalogue-public)`. Paths under a platform host (`/o/{org}/i/{instance}/...`) serve deployments without custom domains. A host is claimed by a red-lane change of the organization's admin and verified by a DNS TXT record `_jc-verify.{host}` holding a token wardkeep issued; until verified it serves nothing. TLS: ACME HTTP-01 per host name (the way dev gets certificates today, CLAUDE.md "Cluster"), or a certificate the organization uploads by `secretRef`; rustls with SNI picks the certificate per host. Session cookies are host-only, so a session on one organization's domain is never sent to another's.

### 5.7 Lists, counts and absence

Every list operation runs as one SQL statement inside the `TenantTx` with the per-object check joined in (§2.5); totals come from the same statement. A request for an id the caller may not see gets the same status, body and work as a missing id. The isolation tests (§7.2) assert this per operation with two organizations holding same-named objects.

### 5.8 The platform through MCP, strictly separated

Today: 91 operations, 93 `jc_*` names, segments `data-read`, `context`, `pipeline`, `access`, `publish`, `apps`, `operate`, `knowledge` plus `admin` (`src/connectors.rs:50`, `:199`), `Ceiling::admits` (`:556`), doors `/c/{id}` (ADR-N-064 §3.2), the personal-data filter `personal_data::withhold` (`src/personal_data.rs:117`, callers `src/mcp/connector.rs:876`, `src/agents/oneshot/connector_turn.rs:79`, `tools_data.rs:337`), connector activity (`src/api/connectors.rs:802`, 200 rows of 30 days), `jc_pipeline_logs` (`src/ops/pipeline_runs.rs:286`) over the Portal's runner outcome lines.

Read tools exist for pipeline runs, logs and metrics, `jc_activity_list` (`src/ops/views.rs:380`), `jc_ckan_status` (`views.rs:602`), sync sources, knowledge status, MQTT capture, agent runs, change history, space governance. No tool reads:

| Source | Today | Module that owns it after |
|---|---|---|
| gateway and broker logs | Loki only, no client in the Portal | broker |
| Keycloak events, sign-in failures | admin console only | wardkeep |
| Gitea Actions runs, queued jobs | `src/git/gitea.rs:1283` `latest_runs`, not an operation | shako |
| CKAN beyond publish status | none | dataroom |
| Endpoint usage | REST only (`src/endpoint_usage.rs`) | broker |
| health log, pipeline health, alerts | REST or none | control |
| connector audit `connector_calls` | REST only | audit |

Operations with no tool, per module (to be declared in the registry when the module lands): wardkeep (people, groups, identity providers, domains, sessions, revoke), shako (repositories, branches, pull requests, reviews, merge), dataroom (instances, datasets, harvest sources, themes), ekiben (streams, runs, schedules, run replay), factory and deploy (builds, deploys, rollbacks), Antares operations today served only by its admin API (`/q/tenants`, retention, quality sweeps).

Mapping rule: a UI action is an operation of the registry; MCP, REST, OData, CLI and the page call the same `run` after the same `Decide::check`; a red-lane change still opens a change for its approver; a connector token can never approve (today: every decision door refuses `identity.client` of a connector, ADR-N-064 §3.6).

Logs and telemetry carry ids at write time: the tracing layer reads `org`, `instance`, `project`, `space` and `object` from the `RequestCtx` and the operation input, and refuses to emit a record of a tenant code path without `org`. A read tool filters by `Decide::list` on the object ids before paging and counting; a log line written by a pipeline of organization B carries B's `org_id` and never matches a query of A.

### 5.9 One activity log

`audit.activity (org_id, instance_id, id, at, actor, connector, client, module, operation, object_type, object_id, project_id, space_id, verdict, fingerprint, summary, details jsonb)`, forced RLS on `org_id` (instance filter in the query, so an organization admin reads all instances), partitioned by week, retention a plan field (today 7 days, `src/activity.rs:61`). It replaces the Portal `activity` and `connector_calls` tables and the per-product logs of Keycloak, Gitea and CKAN. `fingerprint` groups errors (§6.5).

### 5.10 One per-person admin page

`/me` in `jc-web`: the person's organizations (switcher), sessions and devices (revoke), connectors (segments, scope, expiry, last calls from the activity log, revoke), tokens of the CLI, role bindings per organization (read-only, with the admin to ask), and their own activity. One page, served by wardkeep and control operations, each a registry operation.

### 5.11 Quotas

`jc-quota` holds token buckets and weighted fair queues keyed by `(org_id, instance_id)` with the plan fields of ADR-N-035 as limits. Enforcement points: request rate per route class at the edge layer; concurrency per module's worker slots (deficit round robin, next-platform [02 §6](../next-platform/02-architecture.md#6-quotas-and-fair-share)); database share per module pool; storage bytes before a write; wasm-host fuel and memory per run; AI tokens per day. A refusal is 429 with `Retry-After` and a problem document naming the limit and the use. Counters live in memory per process and are written every 60 s to `audit.usage (org_id, instance_id, period, dimension, value)`; a deployment with several `jc` processes shares the bucket through that table with a lease per organization.

## 6. Operations

### 6.1 Config as code and migrations

Organization configuration stays in each project's repository (now in shako) and in the organization repository; the control module is the only writer of `auth` tuples, from approved changes. Migrations: one `sqlx` migrator per module schema, run at start under advisory lock `hashtext('jc-migrate-' || module)`; a migration may not touch another schema (a test greps every migration for schema names). Never rewrite an applied migration (KNOWLEDGE T-5105).

### 6.2 Backups and upgrades

One database, so one `pg_dump` or one base backup covers every module; an organization export is `COPY ... WHERE org_id = $1` per tenant table plus its object-store prefix `org/{org_id}/`, and an organization delete is the same set of deletes, tested by counting rows per schema after it.

### 6.3 Memory budget at 100 req/s, embedder excluded

Today dev runs about 7.5 GB of pods (task body, `kubectl top` 2026-11-07), 9.7 GB on 2026-11-05 ([01 §3](../next-platform/01-analysis.md#3-measured-on-dev)). Target: the whole platform under 2 GB.

| Part | Today on dev (2026-11-05) | Budget | Holds it by |
|---|---:|---:|---|
| PostgreSQL | 1765 MiB, 33 connections of 55 | 640 MiB | `shared_buffers` 192 MiB; 20 backends (one pool, per-module shares) at about 19 MiB each (KNOWLEDGE T-4933) |
| broker module | 966 MiB (Antares) + 519 MiB (gateway) | 400 MiB | one router per process instead of per view (KNOWLEDGE T-5896), page streaming |
| ekiben | 695 MiB (Bento) | 160 MiB | messages streamed, one batch per input in memory |
| wasm-host | part of Apps | 160 MiB | two 64 MiB instances at once plus compiled cache |
| control (Portal) | 569 MiB | 128 MiB | no React bundle in memory; askama pages |
| shako | 203 MiB (Gitea) | 96 MiB | packs streamed from the object store |
| dataroom | 825 MiB (CKAN + Solr) | 64 MiB | Postgres full-text search, no Solr |
| wardkeep | 630 MiB (Keycloak) | 48 MiB | no JVM |
| assistant (no embedder) | 705 MiB | 64 MiB | embedder out of scope |
| jc-auth, jc-web, jc-quota, allocator headroom | none | 160 MiB | decision cache bounded at 10 000 entries |
| object store client | 603 MiB (RustFS) | 0 | S3 or filesystem driver in process |
| **Total** | **9729 MiB** | **1920 MiB** | 128 MiB margin to 2048 |

Each module's budget becomes a test: a load run at 100 req/s of its mix for 60 s with jemalloc statistics, failing when the peak resident set passes the budget (the method T-6628 used for the broker at 10 000 req/s).

### 6.4 Observability by ids

Every span and log record: `org`, `instance`, `module`, `operation`, `object`, `request_id`, `fingerprint` on errors; names from OpenTelemetry semantic conventions (`http.request.method`, `db.system.name`, `error.type`). Per-organization counters live in `audit.usage`, never as Prometheus labels (cardinality). Redaction at write time: the tracing layer drops fields named in a deny-list (`authorization`, `cookie`, `password`, `token`, `secret`) and values matching the secret scanner the Portal already runs (`ops::call` step one, `src/ops/mod.rs:480`).

### 6.5 What an AI agent reads first

Measured in calls, tokens and seconds, for the caller's scope only:

| Tool (proposed) | Answers | Budget |
|---|---|---|
| `jc_situation` | since the connector's last cursor: failing now (grouped by fingerprint), runs in progress, pending approvals, recent deploys and config changes, quota and budget use; ranked by severity, each item with its object id | about 2000 tokens, 1 call |
| `jc_explain` | one object: status, last events, last error with its fingerprint group and cause link, recent changes and who made them, linked objects (pipeline, Endpoint, space, deploy), next actions the caller may take | about 1500 tokens |
| `jc_errors` | one line per fingerprint: count, first and last seen, example ids; filters object, level, time | counts before lines |
| `jc_logs` | structured search (object, level, time, fingerprint), counts first, lines on request, at most 200 | |
| resource `jc://runs/{id}` | MCP resource subscription: run events and log tail of one object, rate-bounded, scoped per caller | no polling |

A fingerprint is a hash of the error type, the operation and the normalized message (numbers, ids and quoted values replaced), Sentry's grouping idea. Cause links: an error group whose first event follows a deploy, config change or upstream failure of a linked object within 15 minutes carries a `caused_by` candidate (time and object correlation, the BubbleUp idea of comparing the failing slice with the rest). Prior art read: antares-mcp `summarize` profiles one type within a row and byte budget that shrinks under host load (`Antares-NGSI-LD-Context-Broker/crates/antares-mcp/src/server.rs:328-395`, `src/budget.rs:66-124`: Normal 1000 rows and 32 MiB, Busy 250 and 8 MiB, Tight 0) and `area_overview` reads up to 64 types 8 at a time and omits refused types silently (`server.rs:398-468`, `src/area.rs:14-31`). Both budget rows and bytes, not tokens; `jc_situation` budgets tokens.

## 7. Test oracles

### 7.1 Oracles per crate

| Crate | Oracle |
|---|---|
| jc-auth `Identity` | OpenID Foundation conformance suite against wardkeep (wardkeep research); JWT test vectors of RFC 7515 and RFC 7519 |
| jc-auth `Decide` | a table of today's decisions: `Effective::may` cases from `src/permissions.rs` tests and the gateway PDP tests, replayed against the tuple engine; same answer required |
| jc-store | per module: `rls_covers_every_table` and `pg_rls_pentest` copied from Antares; the RLS script of §5.3 as a test with `EXPLAIN` assertions |
| jc-ops | registry parity test (§2.5); OData: the Antares odata conformance runs (NLstn suite, .NET client, KNOWLEDGE T-5906, T-5907) against one module list |
| jc-web | Playwright: every page at 1440 and 400 px, axe accessibility, one journey per form through the real flow; CSP violation report count 0 |

### 7.2 Isolation suite (every module, every operation)

Fixture: organizations A and B, each with two instances, same-named projects, spaces, pipelines, Apps, repositories, datasets; a person, a connector and a workload per organization. For every registry operation, as A's person, A's connector and A's workload:

1. List, search, count, read, explain and log-read return only A's objects; totals equal A's count.
2. Probing each of B's ids returns the same status, body shape and order of time as an id that never existed (timing compared over 200 tries, next-platform [04 §3](../next-platform/04-isolation-threat-model.md#3-noise-bound-and-timing)).
3. A write naming a B id is refused as absent; nothing changes in B (row counts per schema before and after).
4. A log line and an error injected by B's pipeline never reach A's `jc_logs`, `jc_errors` or `jc_situation`.
5. A's instance 1 does not see instance 2 except through an operation that names both and a permission on both.

The suite is generated from the registry, so a new operation is tested without a new test.

### 7.3 Agent eval

Seed in both organizations: a failing pipeline mapping, a refused write, an expired secret, a bad deploy, a quota hit. An agent with A's connector must name each of A's causes and fixes in at most 3 calls, 5000 tokens of tool output and 10 s of tool time, and must not mention any of B's faults. Baseline to record before the build: today's tools (`jc_activity_list`, `jc_pipeline_logs`, `jc_pipeline_metrics`, `jc_change_list`) on the same faults, with calls, tokens and seconds per fault.

## 8. Argon pack plan

Measured with repomix 1.18.1 by [tenancy-foundation-sources.sh](../../scripts/research/tenancy-foundation-sources.sh) on 2026-11-07 over the trees of the table at the top. The script prints the same table; rerun it after this page or a tree moves.

| Run | Part | Files | Tokens |
|---|---|---|---:|
| A | docs | this page, next-platform 02, 03, 04, Architecture 12, 13, ADR-N-035, 041, 050, 058, 061, 064, 066, 067 | 63 189 |
| A | jc-core kinds | `crates/jc-core/src/kinds/` organization, org_settings, space, role, service_account, group, policy, delegation_policy, endpoint; `crates/jc-core/src/auth/` | 68 849 |
| A | gateway auth | `crates/context-gateway/src/auth/subject.rs`, `middleware/tenancy.rs`, `pdp/mod.rs`, `pdp/evaluator.rs`, `pdp/write_guard.rs` | 32 498 |
| A | assistant RLS, wasm limits | `crates/assistant/migrations/`, `crates/assistant/src/lib.rs`, `crates/wasm-host/src/limits.rs` | 20 492 |
| A | Portal authz | `src/permissions.rs`, `src/connectors.rs`, `src/personal_data.rs`, `src/quotas.rs`, `src/activity.rs`, migrations 0012, 0051 | 78 204 |
| A | Antares policy | `addons/joinedcontext-policy/src/`, `Antares-NGSI-LD-Context-Broker/crates/antares-api/src/admin_auth.rs`, `provenance.rs` | 62 334 |
| A | Antares RLS | migrations 0001, 0005, 0015, 0024, 0027, `Antares-NGSI-LD-Context-Broker/crates/antares-sql/src/lib.rs`, the two RLS tests | 23 902 |
| A | ekiben | `REPOSITORY.md`, `ekiben/crates/ekiben-core/src/org.rs`, `ekiben/crates/ekiben-server/src/api.rs`, READMEs of jc-auth, jc-core, identity | 13 572 |
| A | **total** | | **363 040** |
| B | docs | this page, ADR-N-063, ADR-N-064, next-platform 08 | 24 356 |
| B | Portal ops | `src/ops/mod.rs`, `src/ops/views.rs`, `src/ops/pipeline_runs.rs`, `src/mcp/connector.rs`, `src/api/connectors.rs`, `src/personal_data.rs` | 63 711 |
| B | Antares OData | `crates/odata-url/src/`, `crates/odata-csdl/src/`, `crates/odata-axum/src/` | 115 110 |
| B | antares-mcp | `tools.rs`, `server.rs`, `summary.rs`, `area.rs`, `budget.rs` | 60 354 |
| B | jcctl | `crates/jcctl/src/main.rs` | 26 486 |
| B | **total** | | **290 017** |
| C | docs | this page, the templating benchmark | 18 503 |
| C | Portal CSP | `src/csp.rs`, `ui/src/cspNonce.ts`, `ui/src/index.css` | 5 727 |
| C | askama 0.16.1 | crate `src/`, README | 45 630 |
| C | **total** | | **69 860** |

The docs rows include this page (about 15 800 tokens). Every run stays under 500 000; the largest, A, leaves 137 000 for the generated output's context.

| Run | Generates | Contract file | Expected output |
|---|---|---|---|
| A | `jc-types`, `jc-auth` (traits, tuple engine, standalone OIDC verifier, YAML seed), `jc-store` (TenantTx, boot checks, migrator), `jc-quota`; the isolation-suite generator; schema `auth` and `audit` migrations | §2.1 to §2.4, §5.3, §5.9, §5.11, §7.2 of this page | about 9 000 lines with tests |
| B | `jc-ops` (registry, REST, MCP, CLI generators, parity test), `jc-odata` (filter allow-list to SQL under RLS), `jc_situation`, `jc_explain`, `jc_errors`, `jc_logs` | §2.5, §5.7, §5.8, §6.5, §7.3 | about 7 000 lines |
| C | `jc-web` (layout, components, forms, CSP, page macro, `/me`) | §2.6, §5.10 | about 3 000 lines plus templates |

Order: A, then B and C in parallel (both stack on A's `jc-types` and `jc-auth` traits). The module packs of T-6633 to T-6635 add A's output as their contract.

## 9. Decisions and owner questions

Decided (worker-t6640, owner may override):

1. The decision engine is a library inside the binary, with a remote client for modules on other hosts (§2.2).
2. Zanzibar-style tuples plus compiled attribute grants, kept from next-platform 03 (§2.3).
3. One Postgres database, one schema and one role per module, forced RLS on `(org_id, instance_id)`, boot refusal when a role bypasses RLS or a table lacks forced RLS (§2.4, §5.3).
4. Every tenant table carries an instance id, also for modules with one copy per organization (§5.2).
5. One person row per organization, linked across organizations only by the person (§5.5).
6. A request's organization and instance come from the host name; custom domains verified by DNS TXT; ACME HTTP-01 or an uploaded certificate (§5.6).
7. askama for built-in pages, minijinja only for plugin pages (§2.6).
8. One activity log with org and instance ids at write time replaces the Portal activity and connector tables and the upstream logs (§5.9).
9. Per-organization counters live in a usage table, never as Prometheus labels (§6.4).
10. Missing tenant setting is an error, not an empty answer (§5.3).

Questions only the owner can answer:

1. Does one person row per organization match how cities want shared staff (a regional body serving five towns) to sign in, or should a person be global with memberships?
2. May an organization bring its own upstream IdP for residents (eID) on the platform deployment, and who pays for its certification?
3. Custom domains: is a DNS TXT verification enough, or must an operator approve each domain?
4. Is the 2 GB budget for the hosted deployment with all modules on, or per module set an organization uses?

Findings outside this task, filed as one line each in `/workspace/chyby.md`: the quota fallback across Organizations (`src/quotas.rs:40`), the unread `DelegationPolicy.personalData` (`src/connectors.rs:286`), `OrgId::default()` in ekiben (`ekiben/crates/ekiben-core/src/org.rs:18`).

## Related

- [Next Platform: Target Architecture](../next-platform/02-architecture.md): the tenancy key and quotas this page recasts as crates.
- [Next Platform: Identity and Authorization](../next-platform/03-identity-and-authz.md): the authorization model kept here.
- [Next Platform: Isolation Threat Model](../next-platform/04-isolation-threat-model.md): the threats the isolation suite tests.
- [ADR-N-050](../../Decisions/adr-n-050-broker-views-decide-context-data.md): the broker decides context data.
- [ADR-N-058](../../Decisions/adr-n-058-several-organizations-per-installation.md): several Organizations per installation.
- [ADR-N-064](../../Decisions/adr-n-064-scoped-connectors.md): scoped connectors and the operation registry.
