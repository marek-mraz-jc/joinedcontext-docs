---
sidebar_position: 5
title: "Next Platform: Requirements"
description: The proposed requirement family NP for the many-organization platform and how each one keeps, changes or retires today's requirement ids.
---

# Next Platform: Requirements

This page proposes the requirement family `NP` (ids NP-01 to NP-88) for the next platform, grouped by area, and a map of today's requirement ids each one keeps, changes or retires. It stays a research proposal until the owner admits it; admitted requirements move to a `Requirements/next-platform.md` family file with a traceability table. Tags as in [STYLE.md](../../STYLE.md): `[P]` performance, `[H]` human-facing, `[A]` agent-facing, `[S]` security. The architecture each one refers to is [02](02-architecture.md); the tests are in [04](04-isolation-threat-model.md) and [08](08-management-api-and-testing.md).

## 1. Tenancy

- **NP-01** [S] — One deployment MUST host any number of organizations, each identified by an `OrgId` minted at creation and never reused.
- **NP-02** [S] — Every row, request context, job, message, cache key, object key, log record and token that concerns tenant data MUST carry the `OrgId` of its organization.
- **NP-03** [S] — No service MUST derive an organization from a name, a domain, a host label or a URN segment; the `OrgId` comes from a verified token or a route table entry.
- **NP-04** — Names of projects, spaces, Endpoints, groups and Apps MUST be unique within their organization only.
- **NP-05** — No organization MUST own the deployment; deployment-wide settings MUST belong to the operator.
- **NP-06** [H] — An organization MUST be created through one management call that also makes its first administrator.
- **NP-07** [S] — Deleting an organization MUST remove every row and object of it and destroy its data keys within 30 days of the request.

## 2. Cost at rest

- **NP-10** [P] — An organization with no request in the last hour MUST hold no process, pod, database connection, listener or warm cache entry of its own.
- **NP-11** [P] — Creating an organization MUST add no process, pod, namespace, realm, repository or persistent volume.
- **NP-12** [P] — The shared edition's services SHOULD hold under 2 GiB of memory together at rest, PostgreSQL excluded.
- **NP-13** [P] — A WASM App or pipeline module MUST load on its first request and be evicted when unused.
- **NP-14** [P] — Each service MUST size its database pool by load and MUST NOT keep connections per organization.

## 3. Quotas and fair share

- **NP-20** [S] — Every resource a request or job spends (requests, concurrency, database time, storage bytes, history, job CPU and memory, AI tokens, egress) MUST have a per-organization limit set from the organization's plan.
- **NP-21** [S] — Each service MUST serve organizations with pending work by weighted fair queueing, so one organization's backlog delays no other organization's next request.
- **NP-22** [S] — A refusal for a limit MUST answer `429` with `Retry-After` and a problem document naming the limit and the current use.
- **NP-23** — Every Context Space recording history MUST declare a retention period no longer than its plan allows.
- **NP-24** [P] — A storage write that would pass the organization's byte quota MUST be refused before it is written.
- **NP-25** [H] — An organization's administrators MUST see each limit with its current use through the management API.

## 4. Isolation

- **NP-30** [S] — Every tenant table MUST have row-level security forced on `org_id`, and a service MUST refuse to start when its database role bypasses row-level security.
- **NP-31** [S] — A call about an object of another organization MUST answer exactly as for an object that does not exist.
- **NP-32** [S] — Every cache MUST key its entries by `OrgId` and the caller's grant digest.
- **NP-33** [S] — Search and vector queries MUST filter by `OrgId` before ranking.
- **NP-34** [S] — An AI conversation MUST read only through the asking subject's grants in its own organization, and prompt caches MUST be keyed by organization.
- **NP-35** [S] — Logs and traces MUST carry the `OrgId` and MUST NOT carry request or response payload values.
- **NP-36** [S] — Metrics MUST NOT carry an organization, project or space label; per-organization numbers MUST be served only from the usage store through the API.
- **NP-37** [S] — A job MUST run inside the signed request context of its enqueuer and no other.
- **NP-38** [S] — A WASM App or pipeline step MUST run with fuel, memory and wall-time limits, no host filesystem, and outbound calls only to its allow-listed hosts.
- **NP-39** [S] — The shared edition MUST refuse container Apps; they MAY run on a dedicated tier or self-hosted, each in its own namespace.
- **NP-40** [S] — Operator access to tenant data MUST require a support grant approved by an administrator of that organization, limited in time and recorded in its audit log.
- **NP-41** [S] — Blobs and columns marked sensitive MUST be encrypted with a per-organization data key held outside the database.
- **NP-42** [S] — Sharing data with another organization MUST be a grant on one Endpoint written by an administrator of the owning organization in the red lane.

## 5. Identity

- **NP-50** [S] — `jc-identity` MUST be the only token issuer, with one issuer for all organizations and the organization as the `org` claim.
- **NP-51** [S] — People MUST sign in by OIDC authorization code with PKCE S256; the implicit and password grants MUST NOT be served.
- **NP-52** [S] — Workloads MUST authenticate with private-key JWT or by token exchange of their platform token; shared client secrets MUST NOT be issued.
- **NP-53** [S] — Every token MUST name one audience service and MUST be verified by that service.
- **NP-54** [S] — Every decision door MUST refuse a session that proved no second factor when the organization or the role requires one.
- **NP-55** [S] — An organization MAY name an upstream OIDC provider; SAML and LDAP MUST go through a federation adapter outside the core.
- **NP-56** [A][S] — MCP clients MUST register by Client ID Metadata Document or Dynamic Client Registration and receive tokens bound to the resource they name.
- **NP-57** [S] — Service-to-service calls MUST use mutual TLS with certificates from the deployment's internal CA, rotated at least daily.

## 6. Authorization

- **NP-60** [S] — Every access decision MUST be answered by `jc-identity`'s `Check`, `ListObjects` or `Grant` call; no service MUST hold its own membership resolution.
- **NP-61** [S] — `Check` MUST answer deny on any internal error.
- **NP-62** [S] — A decision MUST NOT be answered from tuples older than the change the caller presents a consistency token for.
- **NP-63** [S] — The broker's view MUST compile the Endpoint's grant into the query and narrow the answer (ADR-N-050).
- **NP-64** [A][S] — A connector call MUST be allowed only within the intersection of the person's permission, the connector's scope and the delegation ceiling.

## 7. Data plane

- **NP-70** — `jc-data` MUST serve NGSI-LD (ETSI GS CIM 009) and the read representations of today's Endpoints from one view decision.
- **NP-71** [P] — Bulk reads and pipeline transfers between services MUST use Apache Arrow record batches over Arrow Flight.
- **NP-72** — Services MUST exchange typed messages generated from one Rust type crate, over gRPC with protobuf.
- **NP-73** [S] — Every write to context data MUST go through an Endpoint and its grant, pipelines included.

## 8. Pipelines, Apps, AI, catalogue

- **NP-74** — A pipeline MUST run as a job of the shared worker pool, triggered by schedule, source event or request.
- **NP-75** — A server App MUST be a WASM component on the shared worker pool with its data in its own schema under its organization (ADR-N-044).
- **NP-76** [A] — AI token use MUST be metered per organization, per conversation and per day, against the plan.
- **NP-77** — The catalogue MUST publish DCAT-AP per organization and render its HTML on request from `jc-control` rows.

## 9. Operations, editions, upgrades

- **NP-80** — The shared and self-hosted editions MUST be built from one set of artifacts and differ only in configuration.
- **NP-81** — A self-hosted deployment MUST install with one command onto Kubernetes or onto one Linux host.
- **NP-82** — An upgrade MUST run online, with database migrations that are backwards compatible for one release.
- **NP-83** — Each organization MUST be exportable and restorable as one logical archive.
- **NP-84** — Physical backups MUST be continuous to off-node object storage.
- **NP-85** [S] — Every release MUST pass the cross-organization tests of [04](04-isolation-threat-model.md) before it ships.

## 10. Compliance

- **NP-86** [S] — The platform MUST support GDPR rights (access, rectification, erasure) per organization and per person, and record the processing of attributes marked personal data.
- **NP-87** [S] — The platform MUST ship a software bill of materials and a vulnerability handling process per the EU Cyber Resilience Act, and incident reporting hooks that support an operator's NIS2 duties.
- **NP-88** — An organization MUST be able to export all its data in documented open formats, supporting the switching duties of the EU Data Act.

## 11. Today's requirements: keep, change, retire

| Today | Verdict | By |
|---|---|---|
| PF-01 (one Instance, single realm, one or more Organizations) | change: one deployment, one issuer, many organizations | NP-01, NP-50 |
| PF-02 (Organizations share one Git repository) | retire: configuration lives in `jc-control` per organization | NP-80, [07](07-editions-and-migration.md) |
| PF-03 (an Organization has an administrator) | keep | NP-06 |
| PF-04, PF-05, PF-06, PF-07, PF-08 (ownership chain) | keep | NP-04 |
| PF-09 (space id unique within an Instance) | change: unique within the organization | NP-04 |
| PF-10 (identity is space and URN) | keep, with the organization in front | NP-02 |
| PF-17, PF-73, PF-74, PF-75 (quotas) | change: every resource, enforced at run time | NP-20 to NP-25 |
| PF-18, TS-19 (quotas checked by Conftest in CI) | retire: limits are checked by the service at request time | NP-20 |
| PF-44 (minting over `JC_ORG_DOMAIN`) | change: minting over the organization's own domain | NP-03 |
| PF-45 (Keycloak is the only identity provider) | change: `jc-identity` | NP-50 |
| PF-46, PF-47 (PEPs verify tokens; workload tokens) | keep, in new form | NP-52, NP-53 |
| PF-60 (additive scope inheritance) | keep, as rewrite rules | NP-60 |
| PF-62, PF-63, PF-64 (groups in Git, reconciler writes Keycloak groups) | change: groups are tuples or provider groups | NP-55, NP-60 |
| PF-79, PF-87 (forge identity and teams per project) | retire: no forge as store | NP-11 |
| PF-121, PF-122, PF-123, PF-124 (ADR-N-058 files, installation Organization, Keycloak subtree, CKAN organisation) | retire PF-121 and PF-124, keep PF-122 and PF-123 in substance | NP-05, NP-42, NP-60 |
| PF-125 (cross-project CSR through SharedSpaceReference) | keep, widened to organizations | NP-42 |
| PF-126 (no personal names in repositories) | keep | NP-55 |
| PF-127 (directory federation through Keycloak) | change: federation adapter | NP-55 |
| PF-128 (second factor at decision doors) | keep | NP-54 |
| OPS-01, OPS-02, OPS-03 (Helmfile layout, namespaces) | change: one chart and one installer | NP-81 |
| OPS-06, OPS-07, OPS-08 (replicas, PDB, rolling) | keep for the shared edition | NP-82 |
| OPS-09 (WAL archiving to S3) | keep | NP-84 |
| PL-19 (a pipeline runs as its own principal) | keep | NP-37, NP-74 |
| AG-158 (no personal data in connector answers without grant) | keep | NP-34, NP-86 |
| MF-51, MF-52 (assistant sources and deployments) | keep, under the organization | NP-34, NP-76 |
| AP-01, AP-02 (App manifest, source in the organization forge) | change: source stored in `jc-control` | NP-75 |
| Part A §8 baseline (Linkerd mTLS, Kyverno, NetworkPolicies) | keep the properties, change the means | NP-57, NP-39 |

Ids not listed keep their meaning inside an organization; a later pass maps each family file line by line.

## Related

- [02-architecture.md](02-architecture.md) — the services these requirements bind.
- [04-isolation-threat-model.md](04-isolation-threat-model.md) — the tests for §4.
- [Requirements/platform.md](../../Requirements/platform.md) — today's PF family.
- [Requirements/operations.md](../../Requirements/operations.md) — today's OPS family.
