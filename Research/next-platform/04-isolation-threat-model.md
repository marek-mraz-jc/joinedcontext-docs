---
sidebar_position: 4
title: "Next Platform: Isolation Threat Model"
description: Every way data of one organization could reach another on a shared deployment, the control that stops it, the test that proves it and the risk that remains.
---

# Next Platform: Isolation Threat Model

This page lists the threats to tenant isolation on a shared next-platform deployment, each with its control, the test that proves the control and the residual risk. The bar is the owner's: no data, metadata, names, counts, timing or errors of one organization reach another, and a shared deployment is at least as safe as one deployment per organization. Readers: the agents building each service and the reviewers of each phase in [07](07-editions-and-migration.md).

## 1. Attacker and assets

Attackers: a member or administrator of organization B, a client of B (App, pipeline, MCP connector, AI assistant prompt), an anonymous caller, a compromised App or pipeline step of B, an operator of the shared deployment acting outside a support case. Assets of organization A: context data and history, configuration and its history, names of projects, spaces, Endpoints and people, counts and sizes, usage, logs, AI conversations and knowledge chunks, App data and blobs, keys.

The test harness every row below uses: two organizations `org-a` and `org-b` seeded with the same names, the same entity ids and the same model, one person and one client in each, on a test deployment. A test passes when every call made as B about A answers exactly what the same call answers about an id that never existed (status, body, headers, and time within the noise bound of §3).

## 2. Threats, controls, tests

| # | Threat | Control | Test that proves it | Residual risk |
|---|---|---|---|---|
| T1 | A query of B returns A's rows | `org_id` on every tenant row, RLS forced, application roles without `BYPASSRLS` or superuser; `SET LOCAL jc.org` only in the store layer | `isolation_rows`: for each tenant table, a query run in B's transaction over A's ids returns 0; a startup check refuses to boot when a role bypasses RLS (today it only warns, [01 §7](01-analysis.md#7-isolation-that-depends-on-configuration)) | a superuser session opened by an operator; held by T14 |
| T2 | A tenant query forgets the context | one store function opens tenant transactions; the type `OrgId` has no default | `isolation_no_ctx`: cg query lists every sqlx call outside the store module, CI fails on a new one; a pg test runs each query with `jc.org` unset and expects 0 rows | a raw SQL string added outside the module and missed by review; the cg check catches the call |
| T3 | Same URN or name in A and B collides | identity is (org, space, URN); names unique within an organization only | `isolation_same_ids`: A and B create the same entity id and the same Endpoint name, each reads only its own | none known |
| T4 | Existence oracle through status codes | an object of another organization answers exactly as a missing one (404, same body) | `isolation_oracle`: every route with an id parameter, called by B with A's id and with a random id, compares status, body and headers | none known |
| T5 | Timing oracle | lookups by (org, id) on indexes keyed by `org_id` first; no shared per-name cache hit path | `isolation_timing`: 1000 interleaved calls with A's id and a random id, the two latency distributions compared (Kolmogorov-Smirnov, p > 0.01) | small timing differences under load; documented bound |
| T6 | Shared cache serves A's data to B | every cache key built by one type that requires `OrgId` and the subject's grant digest; process-wide statics refused in services | `isolation_cache`: A warms each cache, B asks the same question, compares with a cold answer; cg check lists `static` and `OnceLock` holding data in service crates (the class of KNOWLEDGE T-6414) | a new cache added through a crate the check does not scan |
| T7 | Search or vector index returns A's chunks | `org_id` column in every index row and as the first filter; vector search runs per organization partition; in the shared edition a large organization gets its own index | `isolation_search`: A indexes a unique term, B searches for it through every search surface (catalogue, assistant, MCP `search`) and gets nothing | approximate-nearest-neighbour libraries that filter after retrieval can return fewer results; correctness holds, recall drops |
| T8 | AI assistant mixes context across organizations | a conversation belongs to one `RequestCtx`; retrieval and tools go through the same `Check`; prompt caches keyed by organization; model provider called with no cross-organization batch | `isolation_ai`: B's prompt asks for A's unique term, A's Endpoint slug and A's people; the transcript and tool calls hold none; replay with a cached prompt prefix | the model provider's own retention, covered by the provider contract; an organization can turn AI off |
| T9 | Logs or traces show A's names or data to B or to support | logs carry `org` id and no payload values; an organization reads its own logs only through the API, filtered by `org` | `isolation_logs`: B's log query over every service returns no record with A's id; a log scanner in CI refuses a log line holding a request body field | an operator reading raw logs; held by T14 |
| T10 | Metrics leak counts or names | no per-organization Prometheus label; per-organization usage only in the usage table, read through the API | `isolation_metrics`: the metrics endpoint holds no `org` label and no project or space name; B's usage read holds only B | aggregate metrics show the deployment's total load |
| T11 | A job runs with the wrong context | the job row carries the enqueuer's signed `RequestCtx`; the worker runs only inside it | `isolation_jobs`: a job enqueued by A with B's id in its arguments reads only A; a job row with a tampered context is refused | none known |
| T12 | A WASM App or pipeline step escapes | wasmtime sandbox with fuel, memory and time limits (today's `joinedcontext-platform/crates/wasm-host/src/limits.rs`), no WASI filesystem, outbound HTTP only through the host to allow-listed hosts, data only through the App's Endpoint; one module instance per request | `isolation_wasm`: a hostile module tries host files, other Apps' schemas, metadata services and A's Endpoint; each refused; fuzz the host calls | a wasmtime sandbox escape (a CVE); held by patch cadence and by running `jc-work` without credentials beyond the `RequestCtx` |
| T13 | Container Apps (today's `service` and `fullstack`) share a node | container Apps stay in their own namespace with NetworkPolicies, offered only on the dedicated tier and self-hosted | `isolation_container_apps`: the shared edition refuses a container App manifest | kernel-level escape on the dedicated tier, as today |
| T14 | Operator or support reads A's data | no standing operator access to tenant data; a support case is a time-limited grant A's administrator approves, recorded in A's audit log; break-glass needs two operators and is shown to A | `isolation_support`: an operator token without a case answers 403 on every tenant route; the audit row exists after a case | database superuser on the host; held by encrypted blobs and sensitive columns (T16) and by host access logging |
| T15 | Backup of all organizations restored into one | logical per-organization export as the restore unit; physical backups restored only whole, by operators | `isolation_restore`: restore A's export into a fresh deployment, B's rows absent; restore drill monthly | a physical backup holds every organization until its retention ends |
| T16 | A deleted organization's data persists | deletion removes rows by `org_id` in batches, deletes the object prefix and destroys A's data key (crypto-shredding of blobs and encrypted columns) | `isolation_delete`: after deletion, every table and prefix holds no A row; a decrypt with A's key id fails | unencrypted columns in physical backups until their retention ends (state the window in the plan, GDPR Art. 17 with documented retention) |
| T17 | Tokens of B accepted for A | `org` claim checked against the route's organization by `jc-edge` and again by each service against `RequestCtx` | `isolation_tokens`: B's token, a token with a forged `org`, a token for another audience, each on A's routes | none known |
| T18 | Forged internal context | `RequestCtx` signed by `jc-edge` only; services refuse an unsigned or expired context; mTLS between services | `isolation_ctx`: a service called directly with a hand-made context refuses | compromise of `jc-edge`'s key; rotation and short lifetimes |
| T19 | Noisy neighbour (availability) | per-organization rate limits, fair queues, pool shares, statement timeouts, storage quotas ([02 §6](02-architecture.md#6-quotas-and-fair-share)) | `isolation_fairness`: B floods every route class at 10x its quota, A's p99 latency stays within 20 % of its baseline | a flood larger than the edge's capacity needs an upstream DDoS service |
| T20 | Cross-organization sharing widens by mistake | sharing only by a tuple the owner's administrator writes, red lane; the shared view is the Endpoint's narrowed grant | `isolation_sharing`: a share from A to B grants exactly the Endpoint's rows; revocation takes effect at the next request | an administrator sharing too much; shown on the Access page |
| T21 | Error messages carry another organization's text | problem documents built from the caller's own request and grants; inner errors replaced by a request id | `isolation_errors`: fuzz B's requests and scan every error body for A's seeded names | none known |
| T22 | Federated self-hosted instance pulls more than offered | a self-hosted instance reads the online service only through Endpoints and their grants, as any client | `isolation_federation`: a federated client of A reads B's Endpoint without a grant and is refused | as for any client |

## 3. Noise bound and timing

T5 and T19 compare distributions, not single calls. The bound is set per route class in the test, from 20 runs on an idle deployment, and written next to the test so a regression is a change of the bound, made in review.

## 4. Properties today's platform holds and this design keeps

- RLS forced on broker tables with application roles that do not bypass it (measured in [01 §3](01-analysis.md#3-measured-on-dev)); kept and made a boot refusal.
- Every data read decided by the Endpoint's view in the broker (ADR-N-050); kept.
- mTLS between workloads (Linkerd today); kept, by `jc-identity`'s internal CA.
- Default-deny NetworkPolicies; kept for the dedicated tier and self-hosted Kubernetes; in the shared edition fewer services make the policy list shorter, never absent.
- Per-App origin and egress allow-list (ADR-N-037); kept.
- No person's name in configuration (ADR-N-061); kept.

One property changes: today Apps of different projects run in separate Kubernetes namespaces. In the shared edition server Apps run as WASM in shared `jc-work` processes, isolated by the WASM sandbox rather than by the kernel and namespace (T12). Container Apps keep namespace isolation but leave the shared edition (T13). The owner decides this in [09](09-open-questions.md).

## Related

- [02-architecture.md](02-architecture.md) — the tenancy key carriers the controls rely on.
- [03-identity-and-authz.md](03-identity-and-authz.md) — `Check`, tokens and the internal context.
- [08-management-api-and-testing.md](08-management-api-and-testing.md) — where these tests run and how often.
- [Architecture/13](../../Architecture/13-security.md) — today's trust zones and controls.
