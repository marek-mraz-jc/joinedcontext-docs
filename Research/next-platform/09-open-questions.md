---
sidebar_position: 9
title: "Next Platform: Open Questions"
description: The owner's decisions the next platform waits on, each with the recommended answer.
---

# Next Platform: Open Questions

This page lists what only the owner can decide before or during the migration of [07](07-editions-and-migration.md), each with a recommended answer that the work follows until the owner says otherwise. Readers: the owner and the supervisor.

## 1. Product and scope

| # | Question | Recommended answer | Why |
|---|---|---|---|
| Q1 | Who is the shared edition for first: Slovak and Czech municipalities, or anyone who signs up? | invited public bodies only until phase 7's external review | the isolation tests prove the design; an outside review proves the build |
| Q2 | Are container Apps (today's `service` and `fullstack`) offered in the shared edition? | no; WASM server Apps only, container Apps on a dedicated tier and self-hosted ([04 §4](04-isolation-threat-model.md#4-properties-todays-platform-holds-and-this-design-keeps)) | kernel isolation per namespace cannot be kept at zero idle cost |
| Q3 | Is GraphQL needed for a named consumer? | no; OData for reads, REST and bound actions for writes ([08 §1](08-management-api-and-testing.md#1-one-management-language)) | the OData parts exist and keep reads cacheable and bounded |
| Q4 | Does the Portal UI stay TypeScript? | yes | the goal is Rust services; the UI is 178 110 lines of working React |
| Q5 | Is CKAN's Action API needed by an outside harvester? | assume no; add a read-only `package_search`/`package_show` subset only when a harvester is named | dropping CKAN removes Solr, Redis and about 840 MiB at rest (CKAN 311, Solr 514, Redis 15) |

## 2. Identity

| # | Question | Recommended answer | Why |
|---|---|---|---|
| Q6 | Rust OIDC provider or keep Keycloak? | build `jc-identity` in phase 4, with Keycloak as an upstream during the move, and an external review before outside organizations use it | the owner's Rust goal; the protocol surface is small ([03 §2](03-identity-and-authz.md#2-provider-scope)) |
| Q7 | Must SAML be in the core? | no; a federation adapter for organizations that need it | SAML is large and old; most public bodies offer OIDC (Entra ID, Google Workspace) |
| Q8 | May operators ever read tenant data without the organization's approval? | only by break-glass with two operators, shown to the organization afterwards ([04](04-isolation-threat-model.md) T14) | the owner's isolation bar |

## 3. Operations and money

| # | Question | Recommended answer | Why |
|---|---|---|---|
| Q9 | Off-node backups for prod: which S3 and whose account? | the owner provides an S3 bucket and keys now (NP1-13) | prod has only a nightly local dump today |
| Q10 | Accepted write pause per migration phase? | up to 15 minutes, announced, reads never down | the broker key migration needs a short write pause |
| Q11 | History retention default? | 30 days by default, longer per space only within the plan | T-6581 filled the disk with weeks of history |
| Q12 | Separate data disk for PostgreSQL on dev and prod? | yes, a Hetzner volume per node | the database shares the node disk today; one more volume costs a few euros a month |
| Q13 | Where does the shared edition run? | one Hetzner region on two nodes plus a managed S3 bucket until the load needs more | cost; the design scales out by adding service replicas |

## 4. Repositories

| # | Question | Recommended answer | Why |
|---|---|---|---|
| Q14 | One repository for the six services? | yes: platform, Portal and Antares merge into one Rust workspace, docs and deployment stay apart | removes the pin chain behind [01 §6.4](01-analysis.md#64-merge-latency-across-repositories) |
| Q15 | Does Antares stay publishable as a standalone broker? | yes, as crates and a binary built from the same workspace | the broker is a product of its own and the views keep working without `jc-identity` |

## Related

- [07-editions-and-migration.md](07-editions-and-migration.md) — the phases these answers unblock.
- [06-rust-components.md](06-rust-components.md) — the component decisions behind Q4 to Q7.
- [OPEN-QUESTIONS.md](../../OPEN-QUESTIONS.md) — today's open architecture questions.
