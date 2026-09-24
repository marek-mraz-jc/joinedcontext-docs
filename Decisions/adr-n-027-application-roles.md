---
sidebar_position: 28
title: "ADR-N-027: Application Roles, Declared in the App and Held on Its Endpoint Only"
---

# ADR-N-027: Application Roles, Declared in the App and Held on Its Endpoint Only

Date: 2026-09-22  
Status: Accepted  
Decision Makers: product owner (direction of 2026-09-22, T-2589)

> §3.2, §3.4 and §3.7 are superseded by [ADR-N-030](adr-n-030-every-application-is-a-keycloak-client.md): roles are client roles of `app-{name}`, and the rule that a role counts only on the App's own Endpoint stands.

## 1. Context

The owner's direction of 2026-09-22: "i need to add oidc/oauth2 login to applications via keycloak with roles, etc.. and assign roles to applications, etc... so i can create complex applications". The login is there: every `/apps/{name}/*` route carries the APISIX `openid-connect` session against the Keycloak client `edge` (ADR-N-019, AP-26, AP-29). What an application cannot do is tell one signed-in person from another:

- The static host decides who may open an app with `visibility == public || authenticated` (portal `src/apps/static_host.rs`, `may_read`), so `private`, `project` and `organization` all mean "signed in".
- `#jc-config` carries no person. The SDK's `JcUser.roles` (`sdk/src/sdk/config.ts`) is a field nothing fills.
- A write in `dataNeeds` is granted to everyone the endpoint admits, so an application cannot keep an editor's button from a viewer except by hiding it.
- The grant itself matches nobody on a `project` or `organization` app. The reconciler assigns each data need's `Policy` to the role `app-{name}` (portal `src/apps/reconciler.rs`, `assignee`), and the Context Gateway fills a human's roles from `realm_access.roles` alone (`context-gateway/src/app.rs`, `roles_on`). No token carries `app-{name}`, so every read through such an app's endpoint is refused.

Two facts fix the shape of the answer. A `Policy` names a context space and a principal and nothing else (`jc-core` `PolicySpec`): a grant made to `user jana@…` holds on every surface of that space, not only through the application. And tokens carry no permissions (I4): Keycloak asserts `preferred_username` (the e-mail, since the realm sets `registrationEmailAsUsername`) and `groups` (short names, `full.path` false), and the platform decides the rest.

Roles as code (`Role`, `RoleBinding`, `Group`, Architecture/12 §2a) govern who may change configuration. They say nothing about what a person may do inside an application.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | Keycloak keeps login and group membership; the roles compile to the existing `Endpoint` and `Policy` kinds, no permission language of their own (16 §11). |
| Technological consistency | **Full** | One manifest, one reconciler, the gateway's own PDP; the SDK reads the served configuration it already reads. |
| Security by design | **Full** | A role is held only on the app's endpoint, computed per request from verified claims, never from a token claim of its own, a cookie or the bundle; a role narrows who receives a grant and never widens the grant (AP-06). |
| Modular design | **Full** | The App declares, the reconciler renders, the gateway enforces, the host and the SDK tell the person; each part is testable alone. |
| Multi-tenancy | **Full** | Role names are namespaced by the project and the endpoint, so two applications' `editor` roles are two roles. |

## 3. Decision

1. **An App declares its roles and their members.** `spec.roles: [{name, title, description}]`, `name` matching `[a-z][a-z0-9-]{0,31}`, at most 16, `title` a language map. `spec.access: [{role, subjects: [{user: e-mail} | {group: name}]}]`, where `group` names a `Group` manifest of `users/groups/` as a `RoleBinding` subject does (PF-62, PF-64). Both are configuration in the App manifest, reviewed in the lane the change's writes put it in (AP-09, AP-10). A subject is never a wildcard.
2. **Roles are held on the app's endpoint and nowhere else.** The reconciler writes into the Endpoint it generates for the app `callerRole: true` and the app's roles with their subjects. The gateway gives a caller it admits on that Endpoint, for that request only, the role `endpoint:{project}/{endpoint}` and one role `endpoint:{project}/{endpoint}/{role}` for each role whose subjects match the caller: `user` against `preferred_username`, `group` against the `groups` claim. A token that asserts a role starting with `endpoint:` has that role dropped. Every `Policy` the reconciler renders names one of these roles, so no grant of an application reaches another surface of the space.
3. **Who may open.** `spec.visibility` gains `roles`: only a signed-in person holding at least one role of the application opens it. Anyone else gets a `403` page that names the application, lists its roles with their titles and says who to ask (the project's stewards), never a blank page and never a member's address. `visibility: roles` needs at least one role and is refused on `service` and `fullstack` apps, whose requests never pass the static host that enforces it. The four existing visibilities keep their meaning, and a person's roles are computed under them too.
4. **What the application learns.** The static host computes the person's roles on every request from the identity the Portal already verifies, the edge's `X-Access-Token` (`sub`, `email`, `name`, `groups`), against `spec.access` of the published manifest. It writes `user: {id, name, email, roles}` into `#jc-config`, or `user: null` for an anonymous visitor, and never a token (AP-23). An index that carries a person is served `Cache-Control: private, no-store`. The SDK's `me()` and `useMe()` return that object; `useAccess().can()` stays the endpoint's answer, and when it says no to a person with roles the reason names them: "your role viewer does not permit updateAttrs on Alert" (SDK-07). A function receives the same object as `request.user`, set by the host (SDK-21).
5. **Data needs gated by role.** `dataNeeds[].roles: [editor]` is optional. An item without it compiles as today, to the endpoint's caller role. An item with it compiles to one `Policy` per role, assigned to that role's endpoint role, so the gateway refuses a viewer's write (GW10, AP-04) and the UI only reflects the refusal. A write on an item without `roles` stays red lane, and the review says "everyone who can open {app} can {operations} {types}".
6. **The Portal page.** The App page gets a "Roles and members" section: the roles with their descriptions, the members of each role (users and groups), and "Add member" and "Remove", which propose the manifest change through the one propose function. A person without `propose` on `App` sees them disabled with the reason (PF-50, UI-44).
7. **Out of scope.** Keycloak client roles per application, a login sidecar per app (ADR-N-019), and roles inside `service` and `fullstack` pods, which read the identity the edge hands them and decide for themselves.

## 4. Alternatives Considered

- **Assign each role's `Policy` straight to its subjects** (`user`, `group` principals the gateway already matches). The first draft of this decision. Rejected: a `Policy` is space-wide, so a person made `editor` of one application could write through any other endpoint of the space that admits them. The endpoint role keeps the grant inside the application.
- **A Keycloak client role, or a Keycloak group, per application role.** Puts application permissions into the token (I4), makes a membership change wait for the next token refresh, and lets the token grow with every application. Rejected.
- **Read the edge's `X-Userinfo` header in the Portal.** It is the same identity as `X-Access-Token`, but a base64 document without a signature and a second parser on a trust boundary. The Portal already verifies `X-Access-Token` for every edge request (ADR-N-018, ADR-N-019), so the host reads the verified identity.
- **Accept any Keycloak group as a subject.** A group with no manifest matches nobody silently, which PF-64 already refuses for `RoleBinding`; an application role follows the same rule.
- **Keep `private | project | organization | public` and hide controls by role in the UI.** A hidden button is not a refusal; the gateway has to say no.

## 5. Consequences

- New requirements AP-90…AP-99 and SDK-35…SDK-37; Architecture/16 §12 is the owning section, and Architecture/04, 12 and 20 point to it.
- `jc-core`: `AppSpec.roles`, `AppSpec.access`, `AppVisibility::Roles`, `DataNeed.roles`, and `EndpointSpec.callerRole` and `EndpointSpec.roles` with their validation (T-2591). The Context Gateway adds the endpoint roles to a caller's subject and drops a token role starting with `endpoint:` (T-2591).
- Portal: role resolution and the `403` page in the static host, `#jc-config.user`, `request.user` for functions, the reconciler's Endpoint and per-role Policies, the SDK's `me()` and the reason sentence, and the App page section (T-2595).
- The reconciler's base grant moves from the role `app-{name}`, which no caller holds, to the endpoint's caller role. That is what makes a `project` or `organization` application read at all.
- An application with roles changes only by a reviewed commit. Adding a member is a Change like any other, which is slower than a Keycloak console click and is what makes it auditable.

## Related

- [Architecture/16-apps-on-demand §12](../Architecture/16-apps-on-demand.md#12-roles-of-an-application) — how roles are declared, rendered and enforced.
- [Requirements/apps §18](../Requirements/apps.md#18-application-roles) — AP-90…AP-99.
- [Requirements/app-sdk §6](../Requirements/app-sdk.md#6-the-person-and-their-roles) — SDK-35…SDK-37.
- [ADR-N-019](adr-n-019-login-at-the-edge-apisix-openid-connect.md) — the edge login the roles build on.
- [Architecture/12-identity-and-access](../Architecture/12-identity-and-access.md) — roles as code, which govern configuration and not applications.
