---
sidebar_position: 68
title: "ADR-N-067: Organization Members Read Internal Datasets"
---

# ADR-N-067: Organization Members Read Internal Datasets

Date: 2026-11-01  
Status: Proposed  
Decision Makers: product owner (2026-11-01, supervisor session: "all the users have to sign in to the platform, but they don't have to have access to projects ... they just need to have access to these private endpoints inside of our organization"; "few datasets can be shared internally for all users, few of them only for certain groups ... usually assign that to groups"; "when the user has a phone and logs in to the MCP connector, he should only have access to the datasets that he is allowed"); drafted by the supervisor (T-6378), owner may override

This record decides how a person who belongs to an Organization but works in none of its projects signs in and reads the datasets meant for them: every public dataset, every dataset shared with the whole Organization, and every dataset shared with a group they are in. The same answer holds in the Portal catalogue, the dataset grid, the MCP hub and a personal MCP connector on a phone. It narrows what `audience: organization` means in [ADR-N-002](adr-n-002-context-space-and-endpoint-model.md) and builds on [ADR-N-031](adr-n-031-people-groups-and-app-groups.md), [ADR-N-057](adr-n-057-policy-rules-policy-refs-authzen.md), [ADR-N-058](adr-n-058-several-organizations-per-installation.md), [ADR-N-059](adr-n-059-departments-and-the-unit-of-tenancy.md), [ADR-N-061](adr-n-061-group-members-without-personal-data.md) and [ADR-N-064](adr-n-064-scoped-connectors.md).

## 1. Context

The parts exist; the way through them does not.

- **Audience.** An Endpoint's `audience` is `public`, `organization` or `project-list` (jc-core `kinds/endpoint.rs`, EP-14..EP-16). [Architecture/04](../Architecture/04-context-spaces-and-endpoints.md) says `organization` means "any authenticated user or service account belonging to the parent Organization". The gateway enforces something narrower: the caller's token `groups` must name a **project** of that Organization (`context-gateway/src/auth/subject.rs`). A person whose only groups are `platform-readers` or a department group gets 404 (test `attack_organization_audience_tests.rs`, F-SEC1-009).
- **Membership in the token.** The realm's group mapper writes plain names (`full.path: false`). The token cannot say which Organization a person belongs to, and two Organizations can both have a group `analysts` ([ADR-N-058 §2.4](adr-n-058-several-organizations-per-installation.md) keeps rights inside an Organization).
- **Assignees.** A Policy grant names a `user`, `group`, `role`, `serviceAccount` or `did`. Nothing names "every member of this Organization".
- **Catalogues.** The Portal catalogue reads CKAN anonymously and shows public datasets only, signed in or not. CKAN marks non-public datasets private, and nothing gives a signed-in person CKAN membership. The hub's `catalog` Endpoint holds public datasets only.
- **Portal shell.** Sign-in works today only because every realm user is in `platform-readers`, which a seeded RoleBinding makes `viewer` of every project. Without that binding the person lands on the "no project" state.
- **Connectors.** A `/c/{id}` connector is scoped to projects; a person with no project can build none.

## 2. Decision

### 2.1 Three kinds of people, one sign-in

| Person | What they hold | What they see |
|---|---|---|
| Visitor | no account | public datasets in the open data portal (CKAN), the public catalogue and the anonymous MCP hub |
| **Member** | an account in the Organization, no RoleBinding | everything a visitor sees, plus the datasets the Organization or their groups may read; their own settings and connectors; no project, Context Space or Pipeline page |
| Project person | an account plus RoleBindings (viewer, editor, steward, ...) | as today |

A member is the default: a person created in the Organization is a member until someone binds a role. The seeded "every realm user is viewer of every project" binding (PF-61) ends; `viewer` becomes a binding someone grants.

### 2.2 Membership is explicit and in the token

- Each Organization has its Keycloak group subtree `/{organization}` ([ADR-N-058 §2.5](adr-n-058-several-organizations-per-installation.md)). Every person of the Organization is a direct member of `/{organization}/members`; groups for data access live beside it as `/{organization}/{group}`.
- The token gains two claims from verified group membership, written by Keycloak mappers: `jc_org` (the Organization names, from the subtree roots) and `jc_groups` (full paths, `/{organization}/{group}`). The plain `groups` claim stays for the current project checks until every reader moves to `jc_groups`.
- The gateway, the Portal and Antares read membership only from a verified token (jc-core `Verifier::identify`), never from a header a client sent and never from a URN segment ([ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md)).

### 2.3 `audience: organization` means members; the Policy says which members

- The gateway admits a caller to an `organization` Endpoint when `jc_org` names the Endpoint's Organization. Membership in a project is no longer required. A caller from another Organization still gets 404.
- Admission is only the door. What a member reads is decided by the Endpoint's Policies (`policyRefs`, ADR-N-057), in Antares for reads ([ADR-N-050](adr-n-050-broker-views-decide-context-data.md)) as today. An `organization` Endpoint with no grant to a member reads nothing for them.
- **Shared with everyone in the Organization:** a grant whose assignee is the new kind `{kind: organization}`. It matches any caller whose `jc_org` names the Policy's Organization. It cannot name another Organization.
- **Shared with a group:** a grant whose assignee is `{kind: group, id: <group>}`. The PDP matches it against `jc_groups` as `/{policy organization}/{group}`, so a same-named group of another Organization never matches.
- No new audience level. `public`, `organization`, `project-list` keep their names; only `organization` admission changes.

```yaml excerpt
apiVersion: joinedcontext.com/v1alpha1
kind: Policy
metadata: { name: staff-traffic, namespace: helsinki }
spec:
  contextSpaceRef: { name: mobility }
  rules:
    - assignee: { kind: organization }          # every member of helsinki
      information: [{ type: TrafficFlowObserved, operations: [retrieveOps] }]
    - assignee: { kind: group, id: traffic-analysts }   # /helsinki/traffic-analysts
      information: [{ type: Vehicle, operations: [retrieveOps, retrieveTemporal, queryTemporal] }]
```

### 2.4 One rule for every list of datasets

The question "which datasets may this person read" has one answer, computed by the same per-Endpoint evaluation (AuthZEN `access/v1/evaluation`, ADR-N-057) wherever datasets are listed:

- **Portal catalogue** (`/catalogue`): anonymous, it lists public datasets; signed in, it lists public datasets plus every Endpoint the person may read, each marked `public`, `organization` or with the group that grants it. Internal datasets are read live from their Endpoint, never copied (owner 2026-10-22, no CKAN data copies).
- **Dataset page and grid:** the one SDK grid (T-6376) reads with the person's own session through the Endpoint and its Policy. Anonymous on a non-public dataset: a "sign in" state; signed in without a grant: a "no access" state; never an empty grid and never a cached public copy.
- **CKAN stays the public open data portal.** Non-public datasets are not listed there. Decided (supervisor, owner may override): no CKAN membership sync, because a second copy of who-may-read-what in CKAN can drift from the Policies; options were (a) sync Keycloak groups into CKAN organisation membership, (b) CKAN public only and the Portal catalogue for members.
- **MCP hub** (`/api/mcp`): `search`, `list_endpoints` and the `catalog` Endpoint return public Endpoints to an anonymous caller and public plus readable Endpoints to a signed-in member. A member's token is offered `endpoint:*` for reading at consent (EP-88).
- **Personal connector** (`/c/{id}`, ADR-N-064): a member may create one with the scope "organization data, read". Its ceiling is read-only on the Endpoints the person may read; the default DelegationPolicy for members grants no write. A phone client (claude.ai, ChatGPT) signs in once and sees only those datasets.

### 2.5 Managing it: the Organization's "Data access" page

People and groups are already managed under `/organization` (people, groups, members). This record adds:

- **Organization → Data access**: a matrix of the Organization's non-public Endpoints against `Everyone in the organization` and each group, each cell naming the Policy rule that grants it, with a link to propose a change. Read for `org-admin` and `people-admin`; changes go through the usual proposal and approval.
- **Group page**: "Datasets this group reads" (the reverse of the matrix) beside its members.
- **Endpoint page**: "Who can read this" (audience plus each grant's assignee) in plain words.
- **Person page**: "What this person can read" (the catalogue as that person would see it), for support.
- **People**: `people-admin` invites a person as a member without choosing a project.

### 2.6 Roles

A new taxonomy role `member` is implied by membership and grants: sign in, read the catalogue, manage own settings and connectors. It grants no read of any Endpoint by itself; data comes only from Policies. `org-admin` and `people-admin` keep their meaning; the matrix page needs one of them to read and the usual approval to change.

### 2.7 Demo people and groups

- **Dev (realm `dev`)**: Organization `helsinki` gets `/helsinki/members` and `/helsinki/traffic-analysts`. Persons `demo.member` (member only) and `demo.analyst` (member plus `traffic-analysts`), no RoleBinding. One Endpoint shared with the whole Organization and one shared with `traffic-analysts`, seeded with their Policies, so the walk "visitor, member, analyst" shows three different catalogues.
- **Prod (realm `smartcity`)**: the same groups, created empty, and the same two Endpoints' Policies. Test persons on prod only with credentials in SOPS and MFA required, and only over datasets that hold no personal data.

## 3. Consequences

- **Wider door, same gate.** Members of an Organization reach every `organization` Endpoint's door. Before the switch, list every `organization` Endpoint with its Policy assignees (dev and prod); a grant to `role: viewer` or a project group keeps working for project people and gives members nothing. A grant that meant "everyone signed in" is rewritten as `{kind: organization}`.
- **Two claims to keep right.** `jc_org` and `jc_groups` come only from Keycloak group membership; the realm test asserts both mappers on every client that reaches the gateway, Portal-made `app-*` and `mcp-*` clients included.
- **Isolation tests.** A member of Organization A with a group named like one of B's reads nothing of B; an anonymous read of an internal Endpoint returns no entity body; a member without a grant gets 404 on the Endpoint and no row in any catalogue; a connector of a member cannot write.
- **PF-61 ends.** Existing demo persons that relied on `platform-readers` being `viewer` get explicit bindings in the seed.
- **CKAN unchanged** for visitors; Architecture/04's sentence about CKAN membership from a realm role is removed.

## 4. Implementation order

1. Keycloak: `/{org}/members`, `jc_org` and `jc_groups` mappers, realm tests; demo people and groups on dev (deployment).
2. jc-core: assignee kind `organization`; group assignees matched by full path; taxonomy role `member` (platform).
3. Gateway and Antares: `organization` admission by `jc_org`; isolation tests above (platform, Antares).
4. Portal: member shell (no project needed), signed-in catalogue, Data access matrix, group/endpoint/person panels, member connector scope (portal).
5. MCP hub catalogue and search for signed-in members; consent offers `endpoint:*` read (platform).
6. Prod: groups and Policies, test persons in SOPS (prod-deployer, after a green release gate).

Each step is a task with its own Tests and Security lines; requirement ids go into [Requirements/endpoints.md](../Requirements/endpoints.md) with the first step.

## Related

- [ADR-N-002](adr-n-002-context-space-and-endpoint-model.md), [ADR-N-031](adr-n-031-people-groups-and-app-groups.md), [ADR-N-050](adr-n-050-broker-views-decide-context-data.md), [ADR-N-057](adr-n-057-policy-rules-policy-refs-authzen.md), [ADR-N-058](adr-n-058-several-organizations-per-installation.md), [ADR-N-059](adr-n-059-departments-and-the-unit-of-tenancy.md), [ADR-N-061](adr-n-061-group-members-without-personal-data.md), [ADR-N-064](adr-n-064-scoped-connectors.md)
- [Architecture/04 Context Spaces and Endpoints](../Architecture/04-context-spaces-and-endpoints.md)
