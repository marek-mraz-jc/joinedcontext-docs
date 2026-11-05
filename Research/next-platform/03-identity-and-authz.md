---
sidebar_position: 3
title: "Next Platform: Identity and Authorization"
description: A Rust OIDC and OAuth 2.1 provider and one authorization service for the many-organization platform, and how today's access kinds map onto them.
---

# Next Platform: Identity and Authorization

This page specifies `jc-identity`, the one service of the next platform that says who a caller is and what it may do. It replaces Keycloak and the access checks spread today over the Portal, the gateway PDP and the broker's grant lookup, and keeps the broker's per-row narrowing. Readers: the agents building identity and the reviewers of its threat model in [04](04-isolation-threat-model.md).

## 1. Why one service, and why in Rust

Today identity is Keycloak, one realm per installation (PF-01), and access is decided in three places: `Effective::may` in `joinedcontext-portal/src/permissions.rs` for configuration, the gateway PDP for MCP tools and discovery, and the Antares view engine for data (ADR-N-050). The board shows the cost of three copies: org-admins refused by a literal verb match (KNOWLEDGE T-6266), a hub cache that served one member's reach to another (T-6414), bare group names matched across organizations (T-6408), a realm-level scope linked to every client (T-6301).

The provider and the authorization service go in one service because every authorization question needs the membership the provider owns, and a network hop between them would be on every request. Rust because the owner asked for it and because the protocol surface the platform uses is small enough to own (§2). The risk of owning security-critical protocol code is named in §6.

## 2. Provider scope

`jc-identity` implements exactly these, and refuses everything else:

| Function | Standard | Today |
|---|---|---|
| Sign-in for people | OpenID Connect Core 1.0, authorization code with PKCE (S256 only), OAuth 2.1 draft rules (no implicit, no password grant) | Keycloak realm |
| Workload tokens | `client_credentials` with private-key JWT (RFC 7523) or a workload's platform token by token exchange | Keycloak clients, secrets, PF-47 |
| Delegation | Token Exchange (RFC 8693), audience per target service | Keycloak standard token exchange V2 (KNOWLEDGE T-6063) |
| MCP clients | Client ID Metadata Documents and Dynamic Client Registration (RFC 7591), resource indicators (RFC 8707) | Keycloak CIMD clients (KNOWLEDGE T-5954) |
| Second factor | WebAuthn passkeys, TOTP (RFC 6238) as fallback | Keycloak TOTP, PF-128 |
| Federation | an organization's own IdP as an upstream OIDC provider; SAML 2.0 and LDAP through a federation adapter (§6) | Keycloak brokering and LDAP federation, PF-127 |
| Logout and revocation | RP-initiated and back-channel logout, RFC 7009 revocation | Keycloak, gateway revocations poll |
| Keys | per-deployment signing keys, rotated, JWKS published | Keycloak realm keys |

Every token carries `org` (the `OrgId`), `sub`, `azp`, `aud` (one service) and `acr` (whether a second factor was proven). One issuer serves every organization; the organization is a claim, never a realm. An organization's branding, password rules, MFA requirement and upstream IdP are rows of that organization.

## 3. Authorization model

Decided (worker-t6588, owner may override): relationship-based access control in the style of Google Zanzibar for who holds which role where, plus attribute conditions for what a data grant narrows, because the platform's questions are of both kinds: "is this person a steward of project P" is a relationship, "may this caller read attribute A of type T within this polygon" is an attribute condition the broker evaluates per row. Options: pure ReBAC (cannot express per-row geo and time narrowing without one tuple per row), pure ABAC with policies over attributes (membership and inheritance become policy code that every service evaluates differently, today's failure), hybrid (chosen).

Zanzibar is a public source: Pang et al., "Zanzibar: Google's Consistent, Global Authorization System", USENIX ATC 2019, describing one service answering `Check` for every Google product over relation tuples, with a consistency token ("zookie") so a check is not answered from data older than the change it follows.

### Tuples

`(org, object_type:object_id, relation, subject_type:subject_id[#relation])`, stored in `authz_tuples` with `org_id` leading the key. Object types: `organization`, `project`, `space`, `endpoint`, `app`, `connector`, `group`. Relations: `admin`, `steward`, `editor`, `viewer`, `member`, `parent`. Inheritance (organization covers project covers space, PF-60) is a rewrite rule of the schema, not a stored tuple per child.

### Questions the service answers

| Call | Answer | Used by |
|---|---|---|
| `Check(ctx, subject, permission, object, at_least)` | allow or deny, with the reason id | every service, every request |
| `ListObjects(ctx, subject, permission, type)` | ids the subject reaches, paged | lists, catalogue, MCP `list_endpoints` |
| `Grant(ctx, endpoint, subject)` | the compiled data grant: types, attributes, operations, q, geo and time conditions | `jc-data`, which compiles it into the view's query (ADR-N-050 kept) |
| `Expand(ctx, object, relation)` | the subject tree | the Access page, audits |

A call names the organization of its `RequestCtx`; a tuple, object or subject of another organization is invisible to it. Cross-organization sharing is a tuple whose subject is an organization or Endpoint audience of another organization, written only by an administrator of the owning organization (§4, row SharedSpaceReference).

## 4. Today's kinds on the new model

| Today (jc-core) | Becomes | Notes |
|---|---|---|
| `Organization` (`kinds/organization.rs`) | an organization row in `jc-identity` and its settings row in `jc-control` | `spec.installation` retires: no organization owns the deployment ([05](05-requirements.md), PF-121 retired) |
| `Group` (`users/groups/`, PF-62) | tuples `group:G#member@user:U`, or a provider group synced from the upstream IdP (PF-64) | no person's name in configuration (keeps ADR-N-061) |
| `Role` | a permission set in the authorization schema; custom roles are rows of the organization | the seeded roles (`viewer`, `publisher`, steward) become schema roles |
| `RoleBinding` with `RoleScope` (`kinds/service_account.rs`) | tuples `project:P#steward@group:G`; scope `contextSpace`, `project`, `organization` maps to the object type | the red-lane approval of a binding stays (PF-70) |
| `ServiceAccount` | a client row with key material in `jc-identity`; its bindings are tuples | `pl-{pipeline}` accounts (PL-19) become rows made by the pipeline's creation |
| `Policy` (`kinds/policy.rs`, assignees `User`, `Group`, `Role`, `ServiceAccount`, `Did`, organization) | the attribute part of a data grant: rules (types, attributes, operations, q, geo, time) attached to an Endpoint; assignees become tuple subjects | a Policy with no `policyRef` binding every Endpoint of its space (KNOWLEDGE T-6455) becomes an explicit `endpoint:*` subject the editor has to write |
| `Endpoint` | an object with `audience` relations (`public`, `organization`, named subjects) and its compiled grant | the opaque slug stays the public address |
| `DelegationPolicy` (`kinds/delegation_policy.rs`, AG-150) | a ceiling relation on `connector` objects: `Check` for a connector call is the intersection of the person's permission, the connector's scope and the ceiling | keeps "a policy only narrows" |
| `SharedSpaceReference`, `allowedProjects` | a tuple granting a project or another organization's audience read on an Endpoint | across organizations only by the owner's administrator, red lane |
| App roles (ADR-N-027, ADR-N-030) | relations on the `app` object; one client row per App | no Keycloak client per App |

## 5. Tokens on the wire inside

`jc-edge` verifies the client's token and mints the signed `RequestCtx` ([02 §3](02-architecture.md#3-the-tenancy-key)). Services do not see the client's token; a service calling another service passes the same `RequestCtx`, so a downstream service decides for the original caller (keeps PF-46's intent: the acting service verifies what it acts on). Service-to-service transport identity is mutual TLS with certificates from `jc-identity`'s internal CA, rotated every 24 hours, replacing Linkerd's identity.

## 6. Risks and how they are held

| Risk | Control |
|---|---|
| Protocol bugs in a new provider | the OpenID Foundation conformance suite (public source: openid.net certification) in CI for every profile served; fuzzing of every parser (JWT, form posts, redirect URIs); an external review before the shared edition takes outside organizations |
| SAML and LDAP are large and old | not in the core: a separate federation adapter process maps them onto upstream OIDC; self-hosted organizations that need SAML run it, the shared edition offers OIDC federation first |
| A bug in `Check` exposes every organization at once | `Check` has a model checker over the schema (every rewrite rule terminates; no rule crosses `org`), property tests that generate random tuple sets and compare against a reference evaluator, and a deny-default that answers deny on any internal error |
| Key compromise | signing keys in the deployment's secret store, never in a row; rotation with overlap; per-organization data keys separate from token keys |
| Migration from Keycloak | phase 4 of [07](07-editions-and-migration.md): `jc-identity` first federates Keycloak as an upstream, then takes over users with password hashes imported (Keycloak's PBKDF2 format verified on first sign-in) |

## Related

- [02-architecture.md](02-architecture.md) — where `jc-identity` sits and the `RequestCtx` it signs for.
- [04-isolation-threat-model.md](04-isolation-threat-model.md) — the identity and admin-access threats.
- [Architecture/12](../../Architecture/12-identity-and-access.md) — today's identity and access model.
- [ADR-N-050](../../Decisions/adr-n-050-broker-views-decide-context-data.md) — the per-row decision kept in the broker.
- [ADR-N-064](../../Decisions/adr-n-064-scoped-connectors.md) — connectors and the delegation ceiling.
