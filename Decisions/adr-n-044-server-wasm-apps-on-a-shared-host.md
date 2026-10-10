---
sidebar_position: 45
title: "ADR-N-044: Server WASM Apps on a Shared Host, One Database Schema and One Storage Prefix per App"
---

# ADR-N-044: Server WASM Apps on a Shared Host, One Database Schema and One Storage Prefix per App

Date: 2026-10-08  
Status: Accepted  
Decision Makers: product owner (orders of 2026-10-08, T-3339; the design below was decided with the owner and is written down here)

## 1. Context

The owner's order of 2026-10-08: "create these WASM applications on the server with one app one
database; you can also back the applications with RustFS", with the goal of up to 10 000 Apps on a
few shared hosts at near-zero idle cost per App. A second order of the same day: "make the
connection safe so only the application can access the RustFS and Postgres it has access to".

The platform has three App shapes today (ADR-N-036). A `ui` App is a static bundle on the Portal's
static host, and since AP-142 it may compute in the browser with WebAssembly. A `ui-rust` App is
an axum server in a pod of its own: tens of megabytes of memory per App, idle or not, which
10 000 Apps cannot afford. Neither gives an App a server-side store of its own.

## 2. Decision

### 2.1 One shared host, sharded

`jc-wasm-host` is one Rust service embedding wasmtime with the component model. An App's server
is a component built for `wasm32-wasip2` that exports `wasi:http/incoming-handler`. The host runs
as N shards (two to start). Each App is placed on one shard when it is published; the placement is
recorded and stable, and moving an App is an explicit migration. The edge routes
`/apps/{name}/api/*` of an App to its shard; APISIX checks the login for every App, as for every
other route (no proxy per App).

Each request gets a fresh instance from wasmtime's pooling allocator; nothing an instance holds
outlives its request. Compiled components are cached per shard in an LRU, loaded from the object
store by content digest, and refused unless the digest recorded at build matches the bytes.

### 2.2 Storage through host interfaces, never raw connections

The host offers the WIT package `jc:app@0.1.0`:

- `sql`: `query` and `execute` with bound parameters, rows out; no DDL.
- `blob`: `get`, `put`, `list`, `delete` and `presign` under the App's own prefix.

A component never sees a connection string, a password or an object-store key. WASI gives it no
environment, no file system and no sockets; its only outgoing HTTP is to its own App's Endpoint on the
Context Gateway, with the caller's token: it asks for `http://gateway/ngsi-ld/v1/…` (or the Endpoint's
schema, `http://gateway/schema/…`) and the host sends that to `/api/endpoint/<slug>/…`, the slug its
placement records (AP-147).

### 2.3 One App, one database schema, one role

A dedicated Postgres cluster `apps-db` (CNPG, separate from the platform's database) holds one
schema `app_<id>` and two NOLOGIN roles per App: `app_<id>`, which the App runs as, and
`app_<id>_owner`, which owns the schema. The reconciler creates them and runs the App's declared
migrations at publish as the App's own owner, never as a role several Apps share. An App never runs
DDL at run time. A migration defines tables, indexes, views and constraints, and no function,
procedure, `DO` block, trigger or rule.

The host keeps one pool per shard. Every call runs in a transaction that first runs
`select set_config('role', 'app_<id>', true), set_config('jc.app_id', '<id>', true)`. These are
transaction-local settings only, never session ones, so nothing carries over to the next App on
the same connection. `set_config` is not PUBLIC's: in `apps-db` only the NOLOGIN role
`jc_set_config` may execute it, and only the shards' logins and the Portal's login are its
members (T-3362). Once the host has set an App's role, the App cannot switch again by a function.

### 2.4 One storage prefix per App

RustFS holds one bucket `apps`. An App's objects live under `apps/<shard>/<id>/`. The host
normalizes every key: no `..`, no absolute path, nothing outside the prefix. Presigned URLs for
the browser name exactly one key and one method, and expire within five minutes.

### 2.5 Isolation enforced by Postgres and RustFS themselves

The host's checks are the first layer, not the only one:

- **Postgres:** each shard logs in as its own role `wasm_host_<shard>` (LOGIN, NOINHERIT, owns
  nothing, no table rights). It is a member only of the `app_<id>` roles of the Apps placed on that
  shard, granted `WITH INHERIT FALSE, SET TRUE`: it holds none of an App's privileges, only the
  switch, so it must switch role per transaction and can never become an App of another shard.
  `set_config` and the built-ins that run a query given as text (`query_to_xml` and its kin,
  `cursor_to_xml*`, `ts_stat`, `ts_rewrite(tsquery, text)`) are revoked from PUBLIC (T-3362).
  `app_<id>` has rights on schema `app_<id>` alone; `public` is revoked; there is no CREATE at run
  time; `apps-db` has no `dblink`, `postgres_fdw`, untrusted language or file-access function; any
  shared table uses `FORCE ROW LEVEL SECURITY` on `jc.app_id`. Connections need TLS (hostssl only)
  and come from the host pods and the reconciler alone (NetworkPolicy and `pg_hba`).
- **RustFS:** one access key per shard, with an S3 policy limited to `apps/<shard>/*`; a shard's
  key gets 403 on any other shard's prefix.
- **Credentials:** the shard's Postgres password and RustFS key come from the secret store,
  mounted only into that shard's pods, and rotated.

### 2.6 Limits

Per request: 64 MiB of memory, 5 s of wall time (epoch interruption), a CPU fuel budget,
request and response size caps, a concurrency cap per App and per tenant, a 2 s
`statement_timeout` and a row cap. Per App: storage quotas (SQL bytes, blob bytes), checked by the
host.

### 2.7 The host pod

Non-root, read-only root file system, seccomp `RuntimeDefault`, no ServiceAccount token; egress
only to the gateway, `apps-db` and RustFS; one Linkerd sidecar per shard. Metrics carry the top N
Apps by name and totals for the rest, so 10 000 Apps do not become 10 000 label values; logs carry
the App's id.

## 3. Security Analysis

| Threat | Layer that stops it | Layer behind it |
|---|---|---|
| App A reads App B's tables | the host sets only A's role in A's transaction | Postgres: role `app_A` has no right on schema `app_B` |
| An App switches role by a function (`set_config('role', …)`, a query run from text) | Postgres: no App role may execute `set_config` or the query-running built-ins (T-3362) | the host refuses them too, whatever their spelling |
| An App switches role or `search_path` by a statement (`SET ROLE`, `RESET ROLE`, `SET SESSION AUTHORIZATION`) | the host passes exactly one statement whose top-level node is `SELECT`, `INSERT`, `UPDATE`, `DELETE` or `VALUES`, judged by PostgreSQL's own parser (T-3364), and refuses DDL, `LISTEN`, temporary tables, advisory locks and `COPY … PROGRAM` | the shard's login is a member of its own shard's App roles only; no grant can refuse a statement-form switch while that login may switch into each App, so within a shard this layer is the host's alone (a pool per App would move it into Postgres, at 10 000 logins, §4) |
| A setting leaks to the next App on a pooled connection | only `set_config(…, true)`, transaction-local | the transaction ends before the connection is reused |
| A blob key escapes its prefix | the host normalizes and refuses | RustFS: the shard's key is refused outside `apps/<shard>/*` |
| A component swapped in the store after the build | the digest is checked before compiling | the build records the digest; the store's write key is not the host's |
| A component reaches a credential | WASI offers no environment, file system or socket | the credentials are mounted into the host process only |
| A view or function in one App's migration reads another App's tables | migrations run as the App's own owner | Postgres: that owner has no right on another App's schema |
| SQL inside an App's own function switches role within its shard | the reconciler refuses functions, `DO` blocks, triggers and rules in migrations (T-3358) | the host refuses `set_config` in the App's statements, quoted or escaped, and the built-ins that run a query given as text |
| One App exhausts the host | memory, wall time, fuel and concurrency caps per request and per App | the pod's own resource limits |
| An App calls an arbitrary host, or another Endpoint with its caller's token | outgoing HTTP is allowed to the App's own Endpoint on the gateway alone | NetworkPolicy egress; the gateway's Policies for the caller |

Every denied SQL or blob call is logged with the App's id and alerted on; access is logged per
App, reads sampled. Tests prove each layer on its own: with the host's checks switched off,
Postgres still refuses App A on App B's schema and a shard's login role on another shard's App
role, and RustFS still refuses a shard's key on another shard's prefix.

## 4. Alternatives Considered

| Alternative | Why not |
|---|---|
| One `ui-rust` pod per App | tens of megabytes per idle App; 10 000 Apps would need a cluster of their own |
| A database per App | 10 000 databases mean 10 000 connection pools or a pooler per database; a schema and a role per App keep one pool per shard and the same isolation, enforced by Postgres |
| A raw Postgres or S3 connection from the component | the component would hold a credential, and every isolation rule would rest on the App's own code |
| `SET ROLE` per session | a session setting survives the transaction and reaches the next App on the connection |
| Functions-as-a-service in JavaScript (`jc-functions`) | no store of its own; QuickJS is for short scripts, not an App's server |

## 5. Consequences

- A fourth App shape for server WASM Apps follows; its manifest field, build and reconciler steps
  are their own tasks in the `wasm-server-runtime` group.
- The platform gains `apps-db`, a RustFS bucket and the host's shards in the deployment.
- An App's server is written against `jc:app@0.1.0` with the guest SDK `jc-app-sdk`; it cannot be
  moved to another host unchanged, which is the price of never holding a credential.

## 6. Requirements

- AP-143: the shared host, its shards and its per-request instances.
- AP-144: SQL through `jc:app/sql`, one schema and role per App, enforced by Postgres.
- AP-145: blobs through `jc:app/blob`, one prefix per App, enforced by RustFS.
- AP-146: the limits per request and per App.
- AP-147: credentials, outgoing HTTP and audit.
- AP-156: the amendment below.

## 7. Amendment (AP-156)

"Always on" on the shared host means always reachable: a fresh instance for every request
(AP-143) and every job run (AP-154). Nothing of an instance survives between them but the App's
own schema and storage prefix. Work that must keep running between requests, hold a connection
or keep state in memory stays a `ui-rust` App (AP-125), outside this host.

## Related

- [ADR-N-036](adr-n-036-three-app-shapes.md) — the App shapes this adds a server shape beside.
- [ADR-N-026](adr-n-026-the-build-lane-runs-in-the-cluster.md) — the build lane that records a component's digest.
- [Requirements/apps.md](../Requirements/apps.md) — AP-143 to AP-147, and AP-156, the amendment.
- [Architecture/16](../Architecture/16-apps-on-demand.md) — Apps on demand.
