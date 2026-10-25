---
sidebar_position: 62
title: "ADR-N-061: Group Members Without Personal Data in Git"
---

# ADR-N-061: Group Members Without Personal Data in Git

Date: 2026-10-24  
Status: Accepted  
Decision Makers: product owner (2026-09-15: membership belongs in the repository, T-0852; 2026-09-24: no personal data in Git, ADR-N-031); recorded by worker-t5544 (T-5544), owner may override

This record amends decision 1 of [ADR-N-031](adr-n-031-people-groups-and-app-groups.md) ("Membership stays as code") and PF-49, PF-62, PF-63 and PF-64 ([Requirements/platform.md](../Requirements/platform.md#roles-as-code)).

## 1. Context

[ADR-N-031](adr-n-031-people-groups-and-app-groups.md) keeps people in Keycloak and rejects a `User` manifest because "it puts names and e-mails into Git history, which a deletion cannot remove". The same record keeps membership as code, and a member is named by e-mail:

- `GroupSpec.members[].user` is "The person's e-mail address, the name Keycloak carries them under" (`joinedcontext-platform` `crates/jc-core/src/kinds/group.rs`, origin/main 2281f692).
- A `RoleBinding` subject `user` is "The user's identifier in the identity provider (username or e-mail)" (`crates/jc-core/src/kinds/role.rs`), and the seeds fill it with e-mails.
- A data `Policy` assignee `{kind: user, id: …}` holds an e-mail in the project repositories' seeds too.
- The reconciler matches members to Keycloak users by e-mail (`joinedcontext-portal` `src/reconciler/groups.rs`).

Deleting a person (PF-93) proposes a Change that removes their line, but every earlier commit still holds the address. Measured on 2026-10-24 over the seed that fills the organization repositories (`joinedcontext-deployment` `components/context-gateway/seed`, read-only `git log -p`, counts only):

| Measure | Count |
|---|---|
| Seed files naming a person by e-mail (`Group` members, `RoleBinding` subjects, `Policy` assignees) | 23 |
| Distinct e-mails at HEAD | 12 |
| Distinct e-mails in `Group` members at HEAD | 3 |
| Distinct e-mails in the seed's whole history | 13 |
| E-mails gone from HEAD and still in history | 1 |

The dev forge's own history was not counted: it is not readable without the cluster's credentials, which a worker does not hold. The integrator runs `git log -p -- users/groups users/assignments | grep -cE '(user): .+@'` on a read-only clone of each organization repository and adds the numbers to T-5544.

A municipality of 100 employees in 8 departments adds 100 or more addresses to that history, one per person, and every move between departments adds a commit naming them again. The Portal creates people one at a time (`POST /api/v1/people`, `src/api/people.rs`); there is no bulk path and no SCIM endpoint. PF-64 already lets a `RoleBinding` name a group the identity provider owns (`source: provider`), but no page names LDAP, Active Directory or Entra ID as that provider.

## 2. Options

| | (a) Today: e-mail in Git | (b) Keycloak user id in Git | (c) Directory groups, `source: provider` | (d) CSV import, later SCIM |
|---|---|---|---|---|
| What Git holds | name of the group, e-mail of each member | name of the group, the Keycloak user id (UUID) of each member | name of the directory group in a `RoleBinding`; no member at all | as (a) or (b): the import only creates people and proposes members |
| Personal data in history | yes, for good | a pseudonymous id; once the Keycloak user is deleted it points at nobody | none | as the storage it feeds |
| Offboarding | Portal deletes the person, a Change removes the line; the e-mail stays in history | Portal deletes the person, a Change removes the id; history keeps an id that resolves to nobody | the directory disables the account; Keycloak's next sync drops the membership and the login; nothing in Git changes | as (a) or (b) |
| Audit | commit: who added which e-mail when; activity log | commit: who added which id when; the Portal resolves an id to a name while the person exists; activity log | Keycloak admin events and the directory's own log; the binding's commit says which directory group holds which role | the import is one Change and one activity entry per person |
| Fresh environment | recreated from Git; a member logs in later | recreated from Git when the realm keeps its user ids (realm export and import keep them); a new realm needs the one-off id rewrite of §3.4 | recreated by configuring the same federation; memberships come back with the first sync | recreated from the CSV again |
| Review of a change | readable diff | the diff shows ids; the Portal's change page shows the names to a reviewer who may read people | the binding is reviewed (red lane, PF-52); membership is the directory's process | one large Change to review |
| Cost | none | jc-core field rule, reconciler lookup by id, PDP matches `sub`, Portal resolves names, one migration Change | Keycloak user-federation or identity-brokering config per installation, documented; the code exists (PF-64) | CSV page and parser; SCIM needs an endpoint of our own, Keycloak has none |
| Risk | GDPR erasure cannot be honoured | a Keycloak id is still personal data while the person exists | a directory group grants a role only through a reviewed binding; a directory compromise moves people between groups, as it already moves logins | a wrong CSV adds 100 people at once |

## 3. Decision

1. **No e-mail, name or username in Git.** A `Group` member, a `RoleBinding` subject `user` and a `Policy` assignee of kind `user` name a person by their Keycloak user id, the `sub` claim of their token. Validation refuses any other form, an e-mail first. The id carries no name; after the person is deleted from Keycloak it resolves to nobody, so history keeps nothing an erasure has to remove. This is option (b).
2. **A municipality with a directory federates it, and binds its groups.** Keycloak reads the directory: user federation over LDAP for Active Directory or OpenLDAP (users imported, a group mapper), or identity brokering over OIDC or SAML for Entra ID or ADFS (a group-claim mapper). The department groups are realm groups the reconciler never manages, and the organization repository binds them with `source: provider` (PF-64). Nothing personal is in Git, offboarding is the directory's, and a fresh environment gets its members back with the first sync. This is option (c), the recommended setup for 100 employees.
3. **Roles stay reviewed code.** A directory group gets a role only through a `RoleBinding` in the organization repository, red lane, approved by someone other than its author (PF-52, PF-58). A directory administrator who moves a person between groups changes who holds a role, never what a role grants or which group holds it.
4. **Migration without rewriting history.** Since force-push is forbidden and history is the audit, the existing commits stay. The Portal proposes one Change per organization repository that replaces every e-mail member, `user` subject and `user` assignee by the Keycloak id the realm holds for it; an address no Keycloak user carries is listed in the Change for its author to remove. The seeds name their demo people by the ids the dev realm import fixes. The e-mails already in history remain, in demo data only.
5. **Bulk import later, SCIM not now.** A CSV import on the Portal's people page (option d) is a later convenience for organizations without a directory: it creates the people in Keycloak and proposes the group members by id in one Change. SCIM 2.0 waits for an organization whose identity provider can push only SCIM; Keycloak ships no SCIM server, and LDAP or OIDC federation covers Active Directory and Entra ID without it.

A `Group` member after this decision (an excerpt until the jc-core half ships, since `jcctl validate` still asks for an e-mail), and a directory department bound to a role:

```yaml excerpt
apiVersion: joinedcontext.com/v1alpha1
kind: Group
metadata:
  name: transport-editors
  namespace: org
spec:
  description: The transport department's editors, kept in the Portal.
  members:
    - user: 3f2a9c1e-7b4d-4e8a-9c61-0d5e2b7f8a14
```

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: Role
metadata:
  name: transport-reader
  namespace: org
spec:
  rules:
    - kinds: [ContextSpace, Endpoint]
      verbs: [read]
---
apiVersion: joinedcontext.com/v1alpha1
kind: RoleBinding
metadata:
  name: transport-department-readers
  namespace: org
spec:
  subjects:
    - group: odbor-dopravy
      source: provider
  role: transport-reader
  scope: { project: transport }
```

## 4. Consequences

- PF-126 (no personal data in a member or subject) and PF-127 (directory federation) are new and open. PF-49, PF-62 and PF-63 keep their e-mail wording, which the code and its tests hold today, and PF-62 points at PF-126; PF-126 supersedes that wording once the follow-up work below ships, and that work rewrites PF-49, PF-62 and PF-63 in the same docs change. PF-64 names directory groups as provider groups now, since `source: provider` binds them without new code.
- The approval page shows a member's name next to their id to a reviewer who holds `update` on `Person` or `approve` on `Group`; anyone else sees the id.
- A member must exist in Keycloak before a Change names them, so "the binding takes effect on that person's first login" (PF-62) ends: the Portal creates the person first (PF-92), and a directory user exists once Keycloak has synced it.
- Follow-up work, each a task for the owner to admit: jc-core `Member.user`, `Subject.user` and the `Policy` user assignee take a Keycloak id and refuse an e-mail; the reconciler (`src/reconciler/groups.rs`) adds and prunes members by id; the gateway and the Portal PDP match a `user` subject or assignee against `sub`; the Portal names ids on the change and group pages and proposes the migration Change; the seeds move to ids; Deployment documents LDAP federation and Entra brokering for a municipality; a CSV import on the people page.

## 5. Options considered

- **(a) Keep e-mails.** Rejected: it contradicts ADR-N-031's own reason for having no `User` manifest, and an erasure request cannot be met without a history rewrite.
- **A pseudonymous handle minted by the Portal** in place of the Keycloak id. It would survive a new realm, but adds a user attribute, a lookup by attribute and a minting rule for no gain while realm export keeps ids.
- **(c) alone, no members in Git.** Rejected as the only path: an organization without a directory still needs groups, and the owner keeps membership as reviewed code (T-0852).
- **(d) SCIM now.** Deferred: it needs an endpoint of our own beside Keycloak, and no organization on the board asks for it.

## Related

- [ADR-N-031](adr-n-031-people-groups-and-app-groups.md) — people in Keycloak; decision 1 amended here.
- [ADR-N-059](adr-n-059-departments-and-the-unit-of-tenancy.md) — departments as the unit of tenancy; its option E keeps department groups in Keycloak too.
- [ADR-N-054](adr-n-054-history-versions-provenance-gdpr.md) — history and erasure.
- [ADR-N-058](adr-n-058-several-organizations-per-installation.md) — one Keycloak group subtree per Organization.
- [Requirements/platform](../Requirements/platform.md#roles-as-code) — PF-49, PF-62…PF-64, PF-126, PF-127.
- [Architecture/12](../Architecture/12-identity-and-access.md) — identity and access.
