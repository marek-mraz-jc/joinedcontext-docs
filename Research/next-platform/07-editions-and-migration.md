---
sidebar_position: 7
title: "Next Platform: Editions and Migration"
description: One artifact set for the shared and self-hosted editions, federation between them, and the phased migration from today's dev and prod with a phase-1 task list.
---

# Next Platform: Editions and Migration

This page describes how one set of artifacts runs as the shared online service and as a self-hosted installation, how the two federate without opening isolation, and how today's dev (one city) and prod (one city, real public users) move to the next platform without data loss. It ends with the phase-1 task list the supervisor can file. Readers: the owner, the supervisor filing tasks and the deployer.

## 1. Editions

| | Shared (online) | Self-hosted |
|---|---|---|
| Who runs it | the operator, for many organizations | one organization, in its own cloud or data centre |
| Model (public source) | ArcGIS Online: organizations with members, groups and content on shared infrastructure (Esri, "What is ArcGIS Online", ArcGIS Online documentation) | ArcGIS Enterprise: the installable counterpart with the same portal and item model (Esri, ArcGIS Enterprise documentation) |
| Organizations | any number | usually one; more allowed |
| Storage | managed PostgreSQL or CNPG; cloud S3 | CNPG or the organization's PostgreSQL; RustFS or any S3 |
| Container Apps | refused (NP-39) | allowed, one namespace each |
| Kyverno, Linkerd | not used | optional, if the cluster runs them |
| Installer | the chart with the `shared` profile | the chart on Kubernetes, or the single-host bundle (the six binaries, PostgreSQL, systemd units) |
| Billing | usage store feeds plans and invoices | usage store for the organization's own reporting |

Configuration differs, code does not: one profile file sets limits, the S3 endpoint, the federation peers and which optional parts run (NP-80).

## 2. One artifact set

- Six signed container images (`jc-edge`, `jc-identity`, `jc-control`, `jc-data`, `jc-work`, `jc-ai`), pinned by digest, each also published as a static Linux binary.
- One Helm chart with two profiles (`shared`, `self-hosted`) and a values schema; the single-host bundle uses the same binaries.
- One schema migration set per service, run by the service at start under an advisory lock, backwards compatible for one release (NP-82).
- Configuration as code stays: `jcctl` exports an organization's configuration as the same `projects/{p}/{plural}/{name}.yaml` tree, and imports one as a Change. Git becomes the exchange format; `jc-control` holds the versions.

## 3. Upgrades

An upgrade is a rolling restart: expand-only migrations in release N, readers of both shapes in N, contract migrations in N+1. A self-hosted installation may skip at most one release; the installer refuses a larger jump and names the release to install first. An organization moving from self-hosted to shared, or back, is an export and import of its logical archive (NP-83) with its `OrgId` kept, so ids and history survive.

## 4. Federation without opening isolation

A self-hosted organization shares data with the online service, or the other way round, only through Endpoints:

1. The owning side publishes an Endpoint with an audience naming the other side's organization (a tuple, [03 §3](03-identity-and-authz.md#3-authorization-model)).
2. The reading side registers the Endpoint as a federated source (today's `ContextSourceRegistration` with `sharedRef`, PF-125) and calls it with a token from its own issuer, exchanged at the owning side's `jc-identity` for an audience-bound token (RFC 8693).
3. The owning side decides each request with the Endpoint's grant, as for any client (T22 in [04](04-isolation-threat-model.md)).

No database, queue, cache or index spans the two sides.

## 5. Migration from today

Today: dev serves one city with three Organizations in the seed (ADR-N-059 §1), prod serves one city with real public users on its own node; both run the stack of [01 §2](01-analysis.md#2-components-today). Decided (worker-t6588, owner may override): migrate in place component by component behind the existing public URLs, because a parallel second stack does not fit the 16 GB nodes and the URLs (`/api/endpoint/{slug}/…`, `portal.{domain}`) are what public users hold. Options: big-bang cut-over to a new cluster (needs a second node per environment and a long freeze), side-by-side per organization (needs both stacks warm), in place (chosen).

Downtime target: no read downtime; writes paused at most 15 minutes per phase for the broker key migration; the owner confirms the window ([09](09-open-questions.md)).

| Phase | Content | Exit |
|---|---|---|
| 1 | Tenancy key and fair share in the broker; retention and storage quota; per-organization limits at the gateway; isolation test harness; idle-cost probe | `isolation_*` tests for rows, ids, oracle and fairness green on dev; dev disk and pool failures of [01 §6](01-analysis.md#6-recurring-operational-failures-and-root-causes) covered by limits |
| 2 | `jc-edge` behind Traefik, then in front; `RequestCtx`; APISIX removed | every public URL served by `jc-edge`; smoke and conformance green |
| 3 | `jc-identity` authorization behind Keycloak; Portal and broker ask `Check` | one decision path; authz property tests green |
| 4 | `jc-identity` provider; Keycloak as upstream, then retired; mTLS by the internal CA; Linkerd removed | sign-in, MFA, MCP clients on the new issuer |
| 5 | Configuration store in `jc-control`; Gitea read-only, then export-only; pipeline engine in `jc-work`; multi-tenant MQTT | no per-project repository, runner or MQTT pod |
| 6 | Drops: CKAN, QuickJS, OpenHands, oauth2-proxy | [01 §3](01-analysis.md#3-measured-on-dev) memory floor measured again |
| 7 | Shared edition opened to a second outside organization | external review of [04](04-isolation-threat-model.md) done |

Data safety in every phase: a logical dump before each migration step, off-node WAL from phase 1 on (NP-84; prod has only a nightly local dump today), a restore drill on a scratch database before the step runs on prod, and prod migrated only after the same step ran a week on dev.

## 6. Phase-1 task list

Each task is a few hours for one worker, in one repository unless named. The supervisor files them under group `next-platform`, phase `next`, in this order; later tasks depend on the ones named.

1. **NP1-01 ADR: the tenancy key.** Repo docs. Write the next free ADR number in Decisions, titled "The tenancy key": `OrgId` (128-bit, opaque, never reused) on every row, request, job, cache key and object key, with RLS forced on `org_id`. Done when: the ADR is on docs main with NP-01 to NP-03 quoted and ADR-N-058 §2.2 marked as superseded in part. Tests: docs ci checks and markdownlint 0.45.
2. **NP1-02 `OrgId` and `RequestCtx` types.** Repo platform, crate `jc-core` (later `jc-types`). Newtype `OrgId` without `Default` or `From<&str>`, a parser from a verified claim, `RequestCtx` with an HMAC signature over its fields. Depends on NP1-01. Done when: the types are public with docs. Tests: unit tests for parse, sign, verify, tamper refusal, expiry; a compile-fail test that `OrgId::default()` does not exist.
3. **NP1-03 Broker: refuse to boot on an RLS-bypassing role.** Repo Antares, crate antares-sql. Turn today's start-up warning into a refusal unless an explicit maintenance flag is set. Done when: a broker connected as a `BYPASSRLS` role exits with a message naming the role. Tests: pg test with a bypassing role (red before), one with the app role (green).
4. **NP1-04 Broker: `org_id` column, expand step.** Repo Antares, crate antares-sql. Migration adding a nullable `org_id` to every tenant table and a mapping table Tenant → organization, filled from the Portal's projects. Depends on NP1-02. Done when: the migration runs online on a copy of dev's database (`pg_dump` of a sample) within the lock budget. Tests: migration test, rollback entry, `pg_explain` of the hot reads unchanged.
5. **NP1-05 Broker: per-tenant pool share.** Repo Antares, crate antares-sql. A semaphore per tenant in front of the pool acquire, at most a configured share of the pool size. Done when: one tenant holding its share cannot take the last slots. Tests: pg test with pool size 4 and share 2: tenant A blocks two slots, tenant B still acquires.
6. **NP1-06 Broker: retention required on history.** Repo Antares plus deployment seed. A space that records history without a retention period gets the deployment default (30 days, configurable), and the maintenance job drops older partitions. Done when: dev's history has a retention and the oldest partition is dropped by the job. Tests: pg test of the drop; seed test that every space with history names retention.
7. **NP1-07 Broker: storage quota per tenant.** Repo Antares. Count bytes per tenant from inserts (sampled `pg_column_size` of written values, corrected nightly from `pg_class`) and refuse a write above the quota with `429` and a problem document. Depends on NP1-06. Done when: a write over quota answers 429 naming the limit. Tests: unit test of the counter, pg test of the refusal.
8. **NP1-08 Gateway: per-organization token bucket.** Repo platform, crate `context-gateway`. Rate limit keyed on the verified organization of the Endpoint, beside today's per-client limit, with `Retry-After`. Done when: dev's gateway applies a per-organization limit from settings. Tests: unit test of the bucket; integration test that organization B's flood leaves A's request admitted.
9. **NP1-09 Cache key audit.** Repo platform and Portal. List every process-wide cache (`static`, `OnceLock`, `LazyLock` holding data) with a cg query and record whether its key includes the organization and the grant digest; file one finding line per unsafe cache. Done when: the list and the Cypher are in the task body and a cg check fails on a new data-holding static in the gateway. Tests: the cg check run in cg-main.
10. **NP1-10 Isolation test harness.** Repo conformance. Seed two organizations with the same names and ids on a throwaway deployment (docker compose with the broker, gateway and Portal) and run `isolation_rows`, `isolation_same_ids` and `isolation_oracle` ([04 §2](04-isolation-threat-model.md#2-threats-controls-tests)). Done when: the three tests run in CI on dispatch and pass. Tests: the harness's selftest against a stub that leaks (red) and the real stack (green).
11. **NP1-11 Fairness load test.** Repo conformance. k6 scenario: organization B at 10x its limit, organization A at its baseline; assert A's p99 within 20 %. Depends on NP1-05, NP1-08. Done when: the scenario runs against a local stack and its result is in the task. Tests: the k6 thresholds.
12. **NP1-12 Idle-cost probe.** Repo deployment. Script that counts pods, PVCs, Keycloak clients, forge repositories and database connections before and after creating an empty Organization on a local render; today's numbers recorded as the baseline. Done when: the script prints the delta and the baseline is in [01](01-analysis.md). Tests: pytest of the script against a fake cluster answer.
13. **NP1-13 Off-node WAL for prod.** Repo deployment. CNPG `barmanObjectStore` to an S3 bucket with the owner's credentials (secretRef). Blocked on the owner's S3 keys (KNOWLEDGE: no off-site copy until the owner's S3 keys exist). Done when: WAL archives arrive and a restore drill restores yesterday into a scratch cluster. Tests: render test of the backup spec; the drill log.
14. **NP1-14 ADR: OData as the management read language.** Repo docs. Record [08 §1](08-management-api-and-testing.md#1-one-management-language)'s decision, superseding ADR-N-063 §3.2 in part. Done when: the ADR is on docs main. Tests: docs ci checks.

## Related

- [06-rust-components.md](06-rust-components.md) — the component order the phases follow.
- [04-isolation-threat-model.md](04-isolation-threat-model.md) — the tests phase 1 starts.
- [08-management-api-and-testing.md](08-management-api-and-testing.md) — the management API and test plan behind NP1-10 to NP1-14.
- [09-open-questions.md](09-open-questions.md) — the owner's calls the phases wait on.
