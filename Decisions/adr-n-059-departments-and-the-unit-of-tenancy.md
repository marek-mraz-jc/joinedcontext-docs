---
sidebar_position: 60
title: "ADR-N-059: Departments and the Unit of Tenancy"
---

# ADR-N-059: Departments and the Unit of Tenancy

Date: 2026-10-24  
Status: Proposed  
Decision Makers: product owner (2026-10-24: "find if there is an even better approach than these projects"); drafted by worker-t5543 (T-5543), owner may override

This record asks whether Organization > Project > Context Space fits a municipality of about 100 employees in departments, measures five ways to model the departments on one reference municipality, and proposes one with a migration path. It changes no kind; the code each step needs is listed in § 7 for the owner to admit.

## 1. Context

A Project is the expensive unit. Each one costs a forge repository ([ADR-N-029](adr-n-029-one-repository-per-project.md)), the Keycloak groups and forge teams `{slug}-readers` and `{slug}-writers` (PF-87, Portal `src/reconciler/groups.rs` `converge_with`), an apps namespace ([ADR-N-030](adr-n-030-every-application-is-a-keycloak-client.md); `dev-helsinki-apps` on dev), a quota block (PF-73) and, when it ingests, a static Keycloak client `{project}-pipelines` with its secret (`components/pipeline-runner/keycloak-clients.yaml`).

The kinds already allow a department without a project. `RoleScope` takes `contextSpace`, `project` or `organization` (jc-core `kinds/service_account.rs`), the Portal resolves a space-scoped binding (`src/permissions.rs`), a Policy's assignee may be a `group` (jc-core `kinds/policy.rs` `PrincipalKind::Group`), a Policy holds several `rules` and an Endpoint several `policyRefs` ([ADR-N-057](adr-n-057-policy-rules-policy-refs-authzen.md)), and a `RoleBinding` subject may name a group the identity provider owns (`source: provider`, PF-64). No page says how a department maps onto these: in `Decisions/`, `Architecture/` and `Requirements/` only [ADR-N-039](adr-n-039-organization-and-project-data-models.md) mentions departments, and it says the legacy platform has "no level below the tenant".

The seeds use one project per publishing body. Deployment `531cc78c`, `components/context-gateway/seed`: 10 Projects, 71 ContextSpaces, 243 Policies, 163 Endpoints, 5 Groups (all default groups of Apps), 14 RoleBindings (10 organization-scoped, 4 project-scoped, none space-scoped), 11 ServiceAccounts, 3 Organizations; 12 `components/*/keycloak-clients.yaml` files; one realm for every Organization. A city is one project with several spaces (banskabystrica 5, bbsk 5, zilina 5, slovensko 49), and the city and its region (projects `banskabystrica` and `bbsk`) share data through a `SharedSpaceReference`. [ADR-N-058](adr-n-058-several-organizations-per-installation.md) put several Organizations in one installation.

## 2. The reference municipality and how it was measured

One municipality, the same in every model: 100 people in 8 departments (20, 15, 15, 12, 12, 10, 8, 8), 12 Context Spaces (four departments hold two, four hold one), 40 Endpoints of one entity type each, 2 public datasets and 3 datasets one department reads from another. The first two people of a department edit its spaces; the rest read them. Each Endpoint's data is read by its department, written by the project's `pipelines` ServiceAccount, read by `public` when it is public and by the consuming department when it is shared.

`Decisions/assets/adr-n-059/models.py` renders each model as a configuration repository at the jc-core paths and counts it; `test_models.py` beside it asserts that the table below is the script's output and that every model, before and after each request, passes `jcctl validate --repo-dir` (98 to 146 manifests valid per model at platform `2281f692`; the only warning is the missing data model of each space, the same in every model, so models are left out of the count). Reproduce it with:

```sh
python3 Decisions/assets/adr-n-059/models.py --table
JC_JCCTL=/path/to/jcctl python3 Decisions/assets/adr-n-059/test_models.py
```

How the derived rows count: Keycloak groups are the `Group` manifests, two per project (PF-87), one subtree per Organization ([ADR-N-058 § 2.5](adr-n-058-several-organizations-per-installation.md#25-keycloak)) and, in model E, the 8 department groups Keycloak owns. Keycloak clients are the one `{project}-pipelines` client per project. A Change is one merge request in one repository, so a request that touches the organization repository and two project repositories is three Changes. "Keycloak edit" is a change made in Keycloak outside Git.

The five models:

- **A: Project per department.** 8 projects; each space lives in its department's project; a shared dataset is an `allowedProjects` entry and a Policy rule in the owner's project plus a `SharedSpaceReference` in the reader's.
- **B: Departments as Groups in one project.** One project; a `Group` per department; one Policy per Endpoint names the department's Group; bindings at project scope.
- **C: Spaces as the unit, shared Policies.** One project; a `Group` per department; one Policy per space (rules for the department and the pipelines) that every Endpoint of the space binds, plus one Policy per public or shared dataset; bindings at `contextSpace` scope.
- **D: Organization per department.** The nearest shape jc-core accepts to a hierarchy: 8 sibling Organizations under the installation Organization ([ADR-N-058](adr-n-058-several-organizations-per-installation.md)), each with one project. jc-core has no parent Organization; a true hierarchy would add one and change nothing counted here.
- **E: Department attribute from Keycloak.** C, with membership owned by Keycloak: the department groups are provider groups (`source: provider`, PF-64), filled from a `department` user attribute, so Git holds no `Group` and no person.

## 3. Comparison

<!-- begin table: python3 Decisions/assets/adr-n-059/models.py --table -->
| Measure | A: Project per department | B: Departments as Groups in one project | C: Spaces as the unit, shared Policies | D: Organization per department | E: Department attribute from Keycloak |
|---|---:|---:|---:|---:|---:|
| Manifests | 138 | 121 | 106 | 146 | 98 |
| Organization | 1 | 1 | 1 | 9 | 1 |
| Project | 8 | 1 | 1 | 8 | 1 |
| ContextSpace | 12 | 12 | 12 | 12 | 12 |
| Endpoint | 40 | 40 | 40 | 40 | 40 |
| Policy | 40 | 40 | 17 | 40 | 17 |
| Policy rules | 85 | 85 | 29 | 85 | 29 |
| Rules naming a department | 43 | 43 | 15 | 43 | 15 |
| Group manifests | 8 | 8 | 8 | 8 | 0 |
| RoleBinding | 16 | 16 | 24 | 16 | 24 |
| SharedSpaceReference | 3 | 0 | 0 | 3 | 0 |
| ServiceAccount | 8 | 1 | 1 | 8 | 1 |
| Keycloak groups | 25 | 11 | 11 | 33 | 11 |
| Keycloak clients | 8 | 1 | 1 | 8 | 1 |
| Forge repositories | 9 | 2 | 2 | 9 | 2 |
| Forge teams | 16 | 2 | 2 | 16 | 2 |
| App namespaces | 8 | 1 | 1 | 8 | 1 |
| Quota blocks | 8 | 1 | 1 | 8 | 1 |
| CKAN organisations | 1 | 1 | 1 | 9 | 1 |
| (a) Add a person to a department | 1 Change, 1 file | 1 Change, 1 file | 1 Change, 1 file | 1 Change, 1 file | 0 Changes, 0 files, 1 Keycloak edit |
| (b) Give one department read on another's dataset | 2 Changes, 3 files | 1 Change, 1 file | 1 Change, 2 files | 2 Changes, 3 files | 1 Change, 2 files |
| (c) Merge two departments into one | 3 Changes, 22 files | 2 Changes, 8 files | 2 Changes, 6 files | 3 Changes, 23 files | 2 Changes, 4 files, 8 Keycloak edits |
<!-- end table -->

What the numbers say:

- One project instead of eight removes 7 forge repositories, 14 forge teams, 14 derived Keycloak groups, 7 Keycloak clients with their secrets, 7 apps namespaces and 7 quota blocks (A against C).
- A Policy per space instead of per Endpoint takes the Policies from 40 to 17 and the rules from 85 to 29 (C against B). The data door stays the Endpoint: each one still names its Policies.
- Adding a person costs one Change in every model that keeps people in Git; only E makes it a Keycloak edit.
- Sharing a dataset across departments costs two Changes when departments are projects (the owner's Policy and the reader's `SharedSpaceReference`) and one when they share a project.
- Merging two departments moves spaces between repositories in A and D (22 and 23 files over 3 Changes, with a project deleted under PF-77); in B, C and E it edits Groups, bindings and Policies in two repositories.

## 4. What each model breaks

| Concern | A: project per department | B: Groups, one project | C: spaces as the unit | D: Organization per department | E: Keycloak attribute |
|---|---|---|---|---|---|
| URN space segment (PF-44, PF-84, [ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md)) | Default segment is `{department}-{space}`: a reorganization that moves a space changes its tenant and every id unless `spec.urnSegment` is pinned first | Stable: no space moves | Stable | As A | Stable |
| Quotas (PF-73) | One per department: a department cannot use up another's | One for the city | One for the city; `entitiesPerSpace` and the per-Endpoint `requestsPerMinute` still bound each space | As A, and an Organization default per department | As C |
| Apps namespace ([ADR-N-030](adr-n-030-every-application-is-a-keycloak-client.md)) | One per department | Shared by every department's Apps | Shared | One per department | Shared |
| CKAN organisation ([ADR-N-058 § 2.6](adr-n-058-several-organizations-per-installation.md#26-ckan)) | One for the city; the department is the dataset's `catalog.publisher` | As A | As A | One per department | As A |
| Forge membership (PF-87) | A department's repository and teams are its own | Every project member sees every department's manifests in one repository | As B, and a space-scoped binding places nobody in a forge team, so space editors change their spaces through the Portal only | As A | As C |
| Who may grant another department's data | The owner project's editors | Any project-scoped editor: the `editor` role proposes **and approves** `Policy`, so one department's lead can grant their own department another's dataset with nobody else involved | Only the owner space's editors | The owner Organization's editors | As C |
| Membership record | Git (`Group`), reviewed | Git | Git | Git | Keycloak admin events; the attribute must be writable by administrators only, or a person assigns themselves a department |

### 4.1 Security properties

Every model keeps the three properties this record must not weaken:

1. **No right from a URN segment** ([ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md)). Rights come from a Policy's assignee and a binding's scope in all five; none reads a department, project or space from an id.
2. **One data door per Endpoint and its Policies.** In C and E an Endpoint names two Policies through `policyRefs`; the broker's view still decides every read and write of that Endpoint ([ADR-N-050](adr-n-050-broker-views-decide-context-data.md)).
3. **No department reads another's data without a Policy naming it.** `test_no_department_reads_another_without_a_policy_naming_it` walks every Policy rule of every model: a department group appears only in its own spaces' Policies or in a rule limited to the one shared entity type.

B keeps the third property for data and loses it for changes: the editor who can approve a Policy anywhere in the project can write the Policy that names their own department. C and E keep it because the binding that lets a lead edit a Policy is scoped to the lead's own spaces. E adds one condition: Keycloak's user profile must make `department` an administrator-only attribute, and the provider group must be filled by a mapper or an HR sync that people cannot drive.

### 4.2 Attribute-based access

A `department` claim would let a Policy rule match an attribute of the token instead of a group: an assignee of a new principal kind, for example `{kind: claim, id: department=doprava}`, in the rules of [ADR-N-057](adr-n-057-policy-rules-policy-refs-authzen.md). Measured on the reference municipality, it would replace the 15 rules that name a department group in C with 15 rules that name a claim value: a Policy belongs to one Context Space (`spec.contextSpaceRef`), so the rule count stays one per space and one per shared dataset. A template rule such as "the subject's department equals the space's owner" would need an owner attribute on the space and a rule language with variables, which neither the gateway PDP nor the broker's `joinedcontext` engine has; the broker receives today a subject with groups, not arbitrary claims ([ADR-N-050](adr-n-050-broker-views-decide-context-data.md)). What ABAC changes is where membership lives, and model E gets that today through provider groups without a new principal kind.

## 5. Decision

Decided (worker-t5543, owner may override): **model C**. A municipality is one Project; a department is a `Group`; a department's rights are `RoleBinding`s scoped to its Context Spaces; each space has one shared Policy for its department and its pipelines, and each public or cross-department dataset adds a Policy of its own naming exactly who reads it. A department whose people Keycloak already holds through an HR attribute uses provider groups (model E) instead of `Group` manifests, with the attribute administrator-only.

A Project stays the unit for what needs its own budget, repository and apps namespace: a separate publishing body (a city company, a region), a supplier's work, or a department that must not see the others' configuration. An Organization ([ADR-N-058](adr-n-058-several-organizations-per-installation.md)) stays the unit for a separate legal body with its own administrators and CKAN organisation.

Because: C costs one repository, one client and one namespace where A costs eight, cuts the Policies from 40 to 17, makes a cross-department share one Change instead of two, keeps the separation of data and of grants that B loses, and leaves every URN where it is. Options: A, B, C, D, E of § 2.

## 6. Migration path

The seeds need no space moved: each city is already one project. The steps add departments to a project, and the same steps fold an installation that took model A back into one project. No space is renamed and no URN changes.

1. **Pin the segments** (`ContextSpace`). For every space that will move between projects, set `spec.urnSegment` to the segment it renders today, `{project}-{name}` unless already pinned (PF-84). The tenant and every entity id stay as they are. Today's seeds need this step for no space.
2. **Name the departments** (`Group`, or provider groups). One `Group` per department with its people, or one provider group per department filled from the Keycloak `department` attribute.
3. **Bind them to their spaces** (`RoleBinding`). For each space, a `viewer` binding for its department's group and an `editor` binding for its leads, `scope: {contextSpace: ...}`. Organization-scoped bindings (the 10 in the seeds) stay.
4. **Share each space's access** (`Policy`, `Endpoint`). Write one Policy per space with a rule for the department group and one for the pipelines ServiceAccount, and add its URN to `policyRefs` of every Endpoint of the space. Each public or cross-department dataset keeps a Policy of its own. A per-Endpoint Policy the shared one replaces is removed in the same Change.
5. **Move spaces into the one project** (only when coming from model A; `ContextSpace`, `Endpoint`, `Policy`, `DataModel`, `Mapping`, `Pipeline`, `DataSource`, `ServiceAccount`, `App`). Move each space's files to `projects/{city}/spaces/{space}/` with `metadata.namespace` set to the city project; slugs, names and the pinned segments stay. Replace each `allowedProjects` entry naming a department project with the city project, and each `SharedSpaceReference` between departments with a rule in the owner space's Policy naming the reader's group. The `pipelines` client becomes `{city}-pipelines`: a new Keycloak client and secret, and the runner's `JC_CLIENT_SECRET_{CITY}`.
6. **Retire the empty department projects** (`Project`). Only after `jcctl validate` shows the project holds no space: PF-77 drops the broker tenant of every space a deleted project still holds. The forge repository is archived, its teams and apps namespace removed.
7. **Check nothing moved.** For each space, the entity count and a sample of ids through its public or project Endpoint (`entities?type=T&count=true&limit=0`) before and after; each Endpoint slug answers as before.

## 7. Consequences and follow-ups

Accepting this record changes no kind. The owner admits each follow-up separately:

1. A space moved between projects in one Change keeps its broker tenant: the reconciler must treat the delete and the create of the same pinned segment as a move, never as a drop and a new tenant (prerequisite of step 5; PF-77, PF-84).
2. A test that a Policy rule naming a provider group matches a token carrying that group at the gateway PDP and in the broker's `joinedcontext` engine (model E).
3. The Portal's space list and Access page filter by the department groups bound to a space, so a department sees "its" spaces first.
4. A quota per space or per group, for a city that wants departmental budgets inside one project (PF-73).
5. The Keycloak realm import makes `department` an administrator-only user-profile attribute when a deployment turns E on.
6. A `claim` principal kind for Policy rules only if a customer needs attributes that are not groups (§ 4.2); not needed for departments.

## Related

- [ADR-N-029](adr-n-029-one-repository-per-project.md): why a project costs a repository and forge teams.
- [ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md): identity is (space, URN), the property the migration keeps.
- [ADR-N-057](adr-n-057-policy-rules-policy-refs-authzen.md): `rules[]` and `policyRefs[]`, which model C uses.
- [ADR-N-058](adr-n-058-several-organizations-per-installation.md): several Organizations, model D's basis.
- [Requirements/platform.md](../Requirements/platform.md): PF-44, PF-64, PF-73, PF-77, PF-84, PF-87.
