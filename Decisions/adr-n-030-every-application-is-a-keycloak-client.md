---
sidebar_position: 31
title: "ADR-N-030: Every Application Is a Keycloak Client of Its Own, with Its Roles as Client Roles"
---

# ADR-N-030: Every Application Is a Keycloak Client of Its Own, with Its Roles as Client Roles

Date: 2026-09-24  
Status: Accepted  
Decision Makers: product owner (decision of 2026-09-24, T-2676)

## 1. Context

The owner's direction of 2026-09-24: "there should be create proper oidc/oauth2 login for applications, with keycloak client app, with roles etc.. and portal should manage the logins", and "portal should manage so two applications cannot cross with namespaces, like name or ID is unique, groups are unique, and also the context spaces are unique".

What runs on `dev` on that date:

- Every app route and the shared `/apps/*` surface log people in with the one confidential client `edge` (AP-27, ADR-N-019). One session cookie, `jc_edge_apps` on `/apps/`, serves every static app, although AP-29 scopes the cookie to `/apps/{name}/`.
- No `app-{name}` route reaches APISIX. The file is rendered by helm, and an App published at runtime has no way into it, so `fullstack` apps answer `404` and a `public` app still asks for a login (T-2668).
- Application roles are computed by the Portal and the gateway per request from `spec.access` (ADR-N-027, AP-92, AP-97). Keycloak knows nothing about them, and its admin console cannot show who holds a role.
- App names are unique in the organization (AP-14a) and Context Space names are unique in it (PF-44). Keycloak group names and the names derived from an App (client, forge repository, pod) are not checked together, and every project's app pods share one namespace.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | Login, client roles, group role mappings and the audience are Keycloak's own; the edge keeps APISIX `openid-connect`. |
| Technological consistency | **Full** | One reconciler writes the client as it already writes groups (PF-62, PF-63); the manifest stays the one source. |
| Security by design | **Full** | A session is scoped to one application, a client redirects only to its own path, secrets never reach a ConfigMap or Git, and a role still counts only on the application's own Endpoint. |
| Modular design | **Full** | The App declares, the Portal writes Keycloak and the edge file, Keycloak asserts, the gateway enforces. |
| Multi-tenancy | **Full** | Names are unique in the organization at every write door, and each project's app pods run in a namespace of their own. |

## 3. Decision

1. **Each App is a client.** When an App is published, the Portal's reconciler creates the confidential client `app-{name}` in the organization's realm. The client uses the standard flow with PKCE and has no direct grants and no service account. Its redirect and post-logout URIs are `https://{host}/apps/{name}/*` only, and its web origin is `https://{host}`. It carries the attribute `managed-by: joinedcontext` and the owning `{project}/{name}`. The reconciler is its only writer: it overwrites and reports a change made in the console (as PF-63 does for groups), and it deletes the client when the App is retired or removed. Keycloak generates the secret. The Portal reads it and never logs it, stores it in Git or writes it to a ConfigMap.
2. **The Portal composes the edge file.** Helm renders the shared routes into the ConfigMap `apisix-standalone-base`. The reconciler reads that base and adds, per published App, the route `app-{name}` (`/apps/{name}/*`, priority 30) and the route `app-{name}-endpoint` (`/apps/{name}/api/endpoint/*`, priority 35, the `/apps/{name}` prefix stripped before the gateway). Both routes use the `openid-connect` session of client `app-{name}`. The cookie `jc_app_{name}` sits on `/apps/{name}/` (AP-29), the callback is `/apps/{name}/callback` and the logout `/apps/{name}/logout`. A `public` App uses `unauth_action: pass`. The upstream is `app-{name}` in the project's apps namespace for `service` and `fullstack` Apps, and the Portal's static host for `static` ones. The reconciler writes the result, `#END` included, as the Kubernetes Secret `apisix-standalone-config`, which APISIX mounts and reloads without a restart. The client secrets therefore live only in Keycloak and in that Secret. The shared `apps-surface` route stays as the fallback, which answers an App that is not published.
3. **Roles are client roles.** Every `spec.roles[]` entry is a client role of `app-{name}`. Every `spec.access[]` subject is a role mapping the reconciler writes: a `group` subject maps the Keycloak group and a `user` subject maps the user. The reconciler is the only writer of those mappings, and the manifest stays the membership, reviewed as a Change (AP-99). A token of client `app-{name}` carries the person's roles in `resource_access.app-{name}.roles`. An audience mapper adds `app-{name}` and the slug of every Endpoint the App reads, so the gateway admits the token there.
4. **A role still counts only on the App's own Endpoint.** The gateway grants `endpoint:{project}/{endpoint}/{role}` on the App's generated Endpoint only, and only from `resource_access.app-{name}.roles` of a token whose `azp` is `app-{name}`. A role in any other client's `resource_access`, a realm role, or a role starting with `endpoint:` grants nothing on that Endpoint. So ADR-N-027's rule survives: an application's grant is never held on another surface. The static host and `GET …/apps/{name}/me` (AP-109) read the roles from the verified token and no longer compute them.
5. **Unique names, at every write door.** Propose, import, generation and `jcctl validate` refuse a clash, naming both owners:
   - an App name another project's App has (AP-14a), together with every name derived from it (client `app-{name}`, forge repository `{project}_{name}`, pod and Service `app-{name}`, Endpoint `app-{name}`), when a Keycloak client of that id exists that is not managed for this App;
   - a `Group` name another project's `Group` has, or a Keycloak group the reconciler does not manage;
   - a Context Space name another project's space has (PF-44).
6. **A namespace per project for app pods.** A project's `service` and `fullstack` Apps run in `{release}-{project}-apps`. The reconciler creates the namespace when the project's first pod-backed App is published, with the labels `joinedcontext.com/project` and `joinedcontext.com/managed-by`. It enforces Pod Security `restricted`, applies a default-deny NetworkPolicy that admits the APISIX pods only, adds the pull Secret, and gives the Portal a RoleBinding. It deletes the namespace when the project's last pod-backed App is retired. The Portal's ServiceAccount may create and delete only namespaces that carry that label and prefix; a Kyverno policy refuses any other. The shared apps namespace is emptied when every App has moved.

## 4. Alternatives Considered

- **Keep the one `edge` client and compute roles in the Portal** (ADR-N-027). It works, but it is the model the owner replaced: Keycloak cannot show or audit app roles, and one session serves every app.
- **A login in the app pod.** Each `fullstack` app would carry its own OIDC code flow. It puts login code into generated applications (AP-23, AP-26) and leaves static apps unchanged. Rejected.
- **Client secrets through APISIX environment variables.** The `${{VAR}}` substitution reads the process environment, fixed at start, so every new App would restart the edge. Rejected in favour of the Secret-mounted file.
- **Keep the edge file in a ConfigMap.** It would put client secrets into a ConfigMap. Rejected.
- **Roles as realm roles or Keycloak groups per role.** A realm role would be held on every surface, and a group per role multiplies groups. Client roles are scoped to the client by construction.

## 5. Consequences

- Supersedes ADR-N-027 §3.2 and §3.4 (where a person's roles come from) and §3.7 (client roles out of scope), and amends ADR-N-019 and AP-27: the `edge` client keeps the Portal and the shared surfaces, and each App logs in with its own client. ADR-N-027's rule that a role counts only on the App's own Endpoint stands.
- A membership change reaches a person at their next token refresh, within the realm's access-token lifespan, rather than on the next request. Accepted.
- The Portal gains Keycloak client administration for clients carrying its own attribute, write on the Secret `apisix-standalone-config`, read on the ConfigMap `apisix-standalone-base`, and namespace creation guarded by Kyverno.
- Requirements AP-27, AP-29, AP-92, AP-97 and AP-109 change and AP-111…AP-117 are new. Deployment/10 §2 and §3 and Architecture/16 §5 and §12 follow.
- Work: T-2668 (the composed edge file), T-2677 (the client), T-2678 (client roles and the gateway), T-2679 (uniqueness at every door), T-2680 (namespace per project).

## Related

- [ADR-N-019](adr-n-019-login-at-the-edge-apisix-openid-connect.md) — the edge login this amends.
- [ADR-N-027](adr-n-027-application-roles.md) — application roles, partly superseded here.
- [Requirements/apps §7 and §18](../Requirements/apps.md#18-application-roles) — AP-26…AP-29, AP-90…AP-99, AP-111…AP-117.
- [Deployment/10-edge-routing](../Deployment/10-edge-routing-apisix.md) — the routing table and the standalone file.
