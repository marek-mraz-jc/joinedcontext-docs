---
sidebar_position: 19
title: "Connecting a Municipality's Directory"
description: "How a municipality keeps its people and department groups in Active Directory, OpenLDAP, Entra ID or ADFS, how Keycloak federates them, how a department gets a role with source: provider, and how manifests name people by Keycloak user id."
---

# Connecting a Municipality's Directory

A municipality that already keeps its staff in a directory keeps them there. Keycloak federates the directory, the directory stays the source of who works in which department, and the configuration repository holds only which department holds which role (PF-127). No manifest names a person by name or e-mail: where one has to name a person, it holds the person's Keycloak user id (PF-126, [ADR-N-061](../Decisions/adr-n-061-group-members-without-personal-data.md)).

## 1. What lives where

| Thing | Kept in | Changed by |
|---|---|---|
| A person, their password or sign-in, their e-mail | the directory | the municipality's IT, as today |
| A department and who is in it | the directory, synced into Keycloak as a group under `/directory` | the municipality's IT, as today |
| Which department holds which role, in which scope | a `RoleBinding` in the organization repository, subject `{ group: <department>, source: provider }` | a Change in the red lane (PF-52, PF-64) |
| A grant to one person (a `Group` member, a `user` subject, a `Policy` assignee of kind `user`) | the repository, by the person's Keycloak user id | a Change in the red lane |

The reconciler never creates, edits or prunes a directory group (PF-63): the group carries no `managed-by: joinedcontext` mark, so it is somebody else's. A person who leaves a department or the municipality loses the role at Keycloak's next sync or login, with no Change, because the binding names the department and not the person.

## 2. Active Directory or OpenLDAP: LDAP user federation

Keycloak reads the directory over LDAP (LDAPS in production). Configure it in the realm import of `components/keycloak` (keycloak-config-cli) or in the Keycloak admin console under User federation. Three settings matter more than the rest:

- **Import users on.** Keycloak then keeps a local copy of each person with an ordinary Keycloak user id (a UUID), the `sub` of their token and the form a manifest names them by. With import off, Keycloak answers ids of the form `f:<provider>:<ldap id>`, which manifest validation refuses (PF-126).
- **Edit mode `READ_ONLY`.** Nothing in the platform writes back to the directory.
- **A group mapper with groups path `/directory`.** The departments arrive as Keycloak groups under one parent, so their names cannot collide with a project group or a `Group` manifest of the same name.

```yaml
# components/keycloak realm import (keycloak-config-cli), one LDAP provider and its group mapper
components:
  org.keycloak.storage.UserStorageProvider:
    - name: directory
      providerId: ldap
      subComponents:
        org.keycloak.storage.ldap.mappers.LDAPStorageMapper:
          - name: departments
            providerId: group-ldap-mapper
            config:
              groups.dn: ["OU=Departments,DC=city,DC=example"]
              group.name.ldap.attribute: [cn]
              group.object.classes: [group]          # groupOfNames on OpenLDAP
              membership.ldap.attribute: [member]
              membership.attribute.type: [DN]
              membership.user.ldap.attribute: [sAMAccountName]   # uid on OpenLDAP
              mode: [READ_ONLY]
              user.roles.retrieve.strategy: [LOAD_GROUPS_BY_MEMBER_ATTRIBUTE]
              groups.path: [/directory]
              drop.non.existing.groups.during.sync: ["true"]
      config:
        enabled: ["true"]
        vendor: [ad]                                 # other on OpenLDAP
        connectionUrl: ["ldaps://dc1.city.example:636"]
        authType: [simple]
        bindDn: ["CN=svc-keycloak,OU=Service,DC=city,DC=example"]
        bindCredential: ["$(env:LDAP_BIND_PASSWORD)"]
        usersDn: ["OU=Staff,DC=city,DC=example"]
        usernameLDAPAttribute: [sAMAccountName]      # uid on OpenLDAP
        rdnLDAPAttribute: [cn]                       # uid on OpenLDAP
        uuidLDAPAttribute: [objectGUID]              # entryUUID on OpenLDAP
        userObjectClasses: ["person, organizationalPerson, user"]   # inetOrgPerson on OpenLDAP
        editMode: [READ_ONLY]
        importEnabled: ["true"]
        syncRegistrations: ["false"]
        fullSyncPeriod: ["86400"]
        changedSyncPeriod: ["900"]
```

The bind password is a Secret in the Keycloak namespace that keycloak-config-cli reads through its environment (`$(env:LDAP_BIND_PASSWORD)`), the way the demo people's passwords reach it; it is never written into Git or into the values files. Give the bind account read access to the people and department OUs and nothing else.

Active Directory marks a disabled account in `userAccountControl`, and Keycloak's `ad` vendor refuses a disabled person at sign-in. A person deleted from the directory can no longer sign in. In `READ_ONLY` mode with `LOAD_GROUPS_BY_MEMBER_ATTRIBUTE`, Keycloak reads a department's members from the directory when it is asked, so a person moved out of a department in the directory is out of the Keycloak group at once; the syncs above refresh the imported names and e-mails.

## 3. Entra ID or ADFS: identity brokering

A municipality on Entra ID (or ADFS) keeps the sign-in at Microsoft: Keycloak brokers it over OpenID Connect (SAML for an ADFS that offers only SAML). The person is created in Keycloak at their first sign-in and gets a Keycloak user id, as with LDAP import.

1. Register an application in Entra ID with the redirect URI `https://idm.<domain>/realms/<realm>/broker/entra/endpoint`, and let its token carry the `groups` claim (security groups, as group object ids).
2. Add an OpenID Connect identity provider `entra` to the realm: discovery URL `https://login.microsoftonline.com/<tenant id>/v2.0/.well-known/openid-configuration`, the application's client id, its secret from a Secret as in section 2, and sync mode `FORCE`, so each sign-in brings the person's groups again.
3. For each department, add an identity provider mapper of type *Advanced Claim to Group*: claim `groups` equal to the Entra group's object id, group `/directory/<department>`. Create the `/directory/<department>` groups in the realm import; they carry no `managed-by` mark.

Brokering sees the person only when they sign in. A person removed from an Entra group keeps the Keycloak group until their next sign-in, and their session ends at its normal expiry; disable the person in Entra ID and their next sign-in fails. A municipality that needs the change to reach Keycloak sooner shortens the realm's SSO session lifetime.

## 4. Giving a department a role

A department gets a role through a `RoleBinding` subject marked `source: provider`, reviewed in the red lane like any other binding (PF-52, PF-64). The group is the path below `/directory`:

```yaml
# users/rolebindings/transport-editors.yaml
apiVersion: joinedcontext.com/v1alpha1
kind: RoleBinding
metadata:
  name: transport-editors
  namespace: org
spec:
  subjects:
    - group: odbor-dopravy
      source: provider
  role: editor
  scope: { project: doprava }
```

Validation accepts a marked group without a `Group` manifest, refuses the mark on a `user` subject and on any subject other than a `RoleBinding`'s, and refuses a marked group that a `Group` manifest also declares (PF-64).

## 5. Naming one person

A grant to one person names their Keycloak user id, never their name or e-mail, because Git keeps every past version of a file for good (PF-126):

```yaml
spec:
  subjects:
    - user: 3f2a9c1e-7b4d-4e8a-9c61-0d5e2b7f8a14
```

The Portal's people page shows each person's id, and its person picker writes the id when a reviewer chooses a person by name. A reviewer holding `update` on `Person` or `approve` on `Group` sees the name beside the id in a Change; anyone else sees the id alone. On the development profile the demo people have fixed ids (`components/keycloak/demo-users.yaml`), which the seeds use; a production realm's first owner gets `global.initialUserId`.

## 6. How it is tested

`tests/test_keycloak_ldap_federation.py` in `joinedcontext-deployment` runs the pinned Keycloak and an OpenLDAP server in containers and configures the realm as section 2 does, with the OpenLDAP values. It checks that a directory person signs in under a Keycloak user id, that their department arrives as `/directory/<department>`, that removing them from the department in the directory removes the Keycloak membership, and that a person deleted from the directory can no longer sign in. `tests/test_keycloak_people.py` checks the fixed ids of the demo people.

## Related

- [ADR-N-061: Group members without personal data](../Decisions/adr-n-061-group-members-without-personal-data.md)
- [Architecture: Identity and Access](../Architecture/12-identity-and-access.md)
- [Requirements: Platform (PF-52, PF-62, PF-63, PF-64, PF-126, PF-127)](../Requirements/platform.md)
- [Security Hardening](08-security-hardening.md)
