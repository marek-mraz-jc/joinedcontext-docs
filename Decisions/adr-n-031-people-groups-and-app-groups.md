---
sidebar_position: 32
title: "ADR-N-031: People, Groups and the Default Groups of an Application, Managed in the Portal"
---

# ADR-N-031: People, Groups and the Default Groups of an Application, Managed in the Portal

Date: 2026-09-24  
Status: Accepted  
Decision Makers: product owner (decisions of 2026-09-24, T-2682, T-2689, T-2690)

## 1. Context

The owner's directions of 2026-09-24:

- "add option to create users, the whole lifecycle of the user.. create group add roles, add roles to the group from the app, by default create for every app groups with roles ready to assign".
- "by default do not open the app in a new window, it should be open in platform", with an option to open it in a new window.
- "log in by default … it cannot be public". Asked, the owner chose to keep public as an explicit choice.
- Organization management belongs on the left, both as a section and in a profile block.

What the Portal can do on that date:

- **People:** none of it. A person exists only if someone creates them in the Keycloak console.
- **Groups:** creating a group and listing its members (PF-62) works, but a group's page shows no roles.
- **Application roles:** the App page adds a person or a group to a role (AP-99). An App has no group of its own.
- **Opening an App:** "Open app" opens a new tab, and every App route refuses to be framed.
- **Visibility:** an App with no `spec.visibility` counts as `public`.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | Keycloak keeps people, credentials, required actions and e-mails; the Portal calls its admin API. |
| Technological consistency | **Full** | Membership and roles stay as code (`Group`, `RoleBinding`, `spec.access`) through the one propose function. |
| Security by design | **Full** | No personal data in Git; no password stored or logged; a login by default; only the Portal's host may frame an App. |
| Modular design | **Full** | People (Keycloak), membership (manifests), roles (bindings and client roles) and the frame are separate parts. |
| Multi-tenancy | **Full** | Default group names are unique in the organization (AP-115). |

## 3. Decision

1. **People live in Keycloak, not in Git.** A person's name and e-mail are personal data, so there is no `User` manifest. The Portal manages people through the Keycloak admin API, and every action lands in the activity log as who, what and when, never a credential. Membership stays as code.
2. **Who may.** The taxonomy seeds `people-admin`, whose verbs `create`, `update`, `disable` and `delete` on the kind `Person` apply at organization scope; `org-admin` holds it. Anyone else sees the controls disabled with the reason (UI-44).
3. **The lifecycle of a person.**
   - Create (e-mail, name, language). Keycloak sends the execute-actions e-mail (`VERIFY_EMAIL`, `UPDATE_PASSWORD`). A realm without SMTP instead gets a temporary password with `UPDATE_PASSWORD` required. The Portal shows that password once and never stores or logs it.
   - Edit the name. A changed e-mail must be verified again.
   - Disable (which also ends every session) and enable.
   - Send a password reset.
   - Remove the second factor.
   - Sign out everywhere.
   - Delete: the Portal proposes one Change that removes the person from every `Group` and `RoleBinding` naming them, and deletes the Keycloak user once that Change merges.
   - A person's page lists their groups, their platform roles by scope and their application roles.
4. **A group has roles.** A group's page edits its members, its platform `RoleBinding`s (a role at organization, project or space scope) and its application roles (the `spec.access` entries naming it), each edit through the one propose function. Deleting a group is one Change that also removes every binding and access entry naming it.
5. **Every application role has a default group.** Any door that adds a role to an App (propose, generation, import) commits, in the same Change, the `Group` `{app}-{role}` annotated `joinedcontext.com/app: {project}/{app}`, and the `spec.access` entry giving that role to that group. Removing a role removes its group, with a warning when the group still has members. Retiring the App proposes removing all of its default groups. On the App page, "Roles and members" adds a person to a role by adding them to its default group, and gives the role to other groups too.
6. **A login by default.** An App without `spec.visibility` is `project`, and every door defaults to `project`. `public` is an explicit choice that the form spells out ("Anyone on the internet can open this app without signing in"). A Change that sets `public` or moves an App to it takes the red lane and needs `approve` from a publisher (PF-71, PF-72).
7. **An App opens inside the Portal.** "Open app" goes to `/projects/{project}/apps/{name}/open`, where the App runs in a sandboxed frame under the Portal's header and sidebar. The sandbox allows scripts, same origin, forms, popups and downloads, but no top navigation. An "Open in new window" button opens the App's own URL. App routes send `Content-Security-Policy: frame-ancestors https://portal.{host}` in place of `X-Frame-Options: SAMEORIGIN` and `frame-ancestors 'none'`, and Keycloak's pages stay unframeable. The Keycloak session makes the App client's login two redirects inside the frame. When that session has expired, the page offers "Sign in again", which takes the whole window through the login.
8. **Organization on the left.** The sidebar gets an Organization section listing its tabs, People among them, and a profile block at its bottom: the person, Profile, Organization and Sign out.

## 4. Alternatives Considered

- **A `User` manifest in the organization repository.** It would give every person a review and a history, but it puts names and e-mails into Git history, which a deletion cannot remove. Rejected.
- **Assign application roles to people only.** One entry per person per App does not scale past a demo. Groups are what an organization administers.
- **Frame the App without a CSP change.** Browsers refuse, because `X-Frame-Options` blocks the Portal's host. A proxy of the App through the Portal would instead mix the two origins' cookies.
- **Forbid public Apps.** Offered to the owner, who kept public as an opt-in.

## 5. Consequences

- New requirements: PF-90…PF-95 (people and group roles), AP-118…AP-122 (default groups, login by default, the in-Portal page) and UI-82…UI-83 (sidebar).
- Work: T-2683 and T-2684 (people), T-2685 (group roles), T-2686 and T-2687 (default groups), T-2688 (journey), T-2689 (open in the Portal), T-2690 (login by default), T-2681 (sidebar).
- The Portal's realm role gains user administration. It still has no client administration beyond the `app-*` clients carrying its attribute (ADR-N-030).

## Related

- [ADR-N-030](adr-n-030-every-application-is-a-keycloak-client.md) — the App's own client and its client roles.
- [ADR-N-027](adr-n-027-application-roles.md) — application roles.
- [Requirements/platform](../Requirements/platform.md#people-and-group-roles) — PF-90…PF-95.
- [Requirements/apps §21](../Requirements/apps.md#21-default-groups-a-login-by-default-and-opening-inside-the-portal) — AP-118…AP-122.
