---
sidebar_position: 20
title: "ADR-N-019: Login at the edge: APISIX openid-connect for the Portal and every app, Portal on portal.{domain}"
---

# ADR-N-019: Login at the edge: APISIX openid-connect for the Portal and every app, Portal on portal.{domain}

Date: 2026-09-07  
Status: Accepted  
Decision Makers: product owner

## 1. Context

This decision supersedes ADR-N-017 §3.2 (the oauth2-proxy sidecar) and its rejection of the `openid-connect` plugin; the rest of ADR-N-017 (full-stack kind, builder agent) stands.

ADR-N-017 put an oauth2-proxy sidecar into every `service`/`fullstack` app pod and left `static` apps and the Portal to do their own login. The owner decided otherwise on 2026-09-07: one login front for everything a person opens in a browser, the `openid-connect` plugin APISIX already runs, and no authentication code in any app, whether a person wrote it or the builder agent generated it. The Portal moves from the apex host to `portal.{domain}`; the apex keeps the shared surfaces (`/apps/*`, `/git/*`, `/cs/*`, `/api/endpoint/*`) and redirects `/` to the Portal.

One constraint shapes the details: lua-resty-openidc, which the plugin delegates to, verifies RS and HS signatures only, and the realm signs ES256 (TR-03187 AR-11, T-0252). Keycloak overrides the signature algorithm per client, so the edge client gets RS256 tokens while the realm default stays ES256 for every other client.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | The plugin APISIX ships does the code flow, the session and the logout; no sidecar, no per-app login code. |
| Technological consistency | **Full** | One login mechanism for the Portal, static apps and full-stack apps. |
| Security by design | **Full** | Identity headers are stripped from every client request and set only by the edge; the app pod is reachable from APISIX alone; no secrets per app. |
| Modular design | **Partial** | An app image no longer runs behind its own login outside the platform; it needs any OIDC-aware proxy in front. Accepted by the owner. |
| Multi-tenancy | **Full** | One confidential client per realm; cookie scoped per host and per app path. |

## 3. Decision

1. **Hosts.** The Portal (UI and `/api/v1`) is served on `https://portal.{domain}`. The apex `https://{domain}` keeps `/apps/*`, `/git/*`, `/cs/*`, `/api/endpoint/*`, `/.well-known/*` and answers `/` with a redirect to the Portal.
2. **Edge login.** APISIX runs `openid-connect` in session mode (`bearer_only: false`) on `portal-ui`, `portal-api`, `apps-surface` and every `app-{name}` route, with one confidential client `edge` of the organization's realm (redirect URIs `https://portal.{domain}/*` and `https://{domain}/apps/*`). The client's tokens are signed RS256 by per-client override; the realm default stays ES256. The client secret and the session secret reach APISIX as environment variables from Kubernetes Secrets (`${EDGE_CLIENT_SECRET}`, `${OIDC_SESSION_SECRET}`), never through Git.
3. **What the upstream receives.** `X-Userinfo` (base64 JSON of the userinfo) and `X-Access-Token` (the user's access token). Every route strips both from the client request first, so only the edge can set them. `portal-ui`, `apps-surface` and non-public app routes use `unauth_action: auth`; `portal-api` and public app routes use `unauth_action: pass`, and the upstream decides what an anonymous caller may see.
4. **Portal.** The Portal accepts `X-Access-Token` from the edge as it accepts `Authorization: Bearer` when `JC_TRUST_EDGE_TOKEN: "true"` is set (the deployment sets it; a Portal without APISIX in front never trusts the header). Bearer callers (CLIs, service accounts) are unchanged. The Portal's own OIDC code flow stays as the fallback for installations without an edge.
5. **Apps.** No sidecar, no per-app OIDC client, no reconciler-owned secrets. The app container listens on port 8080 of its pod, reachable only from APISIX (NetworkPolicy). A `static` app is served by the Portal's static host behind the same plugin. The session cookie of an app route is scoped to `/apps/{name}/`; `logout_path` is `/apps/{name}/logout` and ends the Keycloak session (front-channel); the cookie lifetime is bounded by the realm's SSO idle time.
6. **Generated apps.** The builder prompt of `app-from-prompt` states the contract: the app reads the user from `X-Userinfo` and calls its endpoint with `X-Access-Token`; it contains no login, session or token code. CI (AP-11) fails an app that ships an OIDC library or a login route.

## 4. Consequences

### Positive

- One login front, one session model, one place to audit; a person logs in once for the Portal and every app.
- The generated code is only application logic, as ADR-N-017 wanted, without the extra container per pod.
- Static apps get a login for the first time.

### Negative / Trade-offs

- Every app depends on the platform edge (or another OIDC proxy) to run; the compose-file portability of ADR-N-017 is gone.
- The `edge` client's tokens are RS256, an exception to the ES256-only realm, documented in the realm configuration.
- Back-channel logout (AP-29 as written under ADR-N-017) is not available in the plugin; the SSO idle bound and the front-channel logout replace it.
- Every app change of visibility rewrites the shared `apisix.yaml`, which jcctl renders deterministically anyway.

## 5. See Also

- Architecture: [16-apps-on-demand §5](../Architecture/16-apps-on-demand.md#5-login-in-front-of-the-portal-and-every-app-apisix-openid-connect), [12-identity-and-access](../Architecture/12-identity-and-access.md).
- Requirements: [AP-23, AP-26…AP-29](../Requirements/apps.md), [PF-45](../Requirements/platform.md).
- Deployment: [10-edge-routing-apisix](../Deployment/10-edge-routing-apisix.md).
- Decisions: [ADR-N-017](adr-n-017-fullstack-apps-oauth2-proxy-builder-agent.md) (superseded in part), [ADR-N-007](adr-n-007-apisix-standalone-no-etcd.md).

## Related

- [16-apps-on-demand](../Architecture/16-apps-on-demand.md) — the app lifecycle this login front sits in front of.
- [10-edge-routing-apisix](../Deployment/10-edge-routing-apisix.md) — the route table and plugin configuration that implement it.
- [ADR-N-017](adr-n-017-fullstack-apps-oauth2-proxy-builder-agent.md) — the sidecar decision this one replaces.
