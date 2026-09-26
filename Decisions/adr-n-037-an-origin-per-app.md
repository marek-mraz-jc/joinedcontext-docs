---
sidebar_position: 38
title: "ADR-N-037: An Origin per App and an Egress Allow-List per App"
---

# ADR-N-037: An Origin per App and an Egress Allow-List per App

Date: 2026-09-25  
Status: Accepted  
Decision Makers: product owner (decision of 2026-09-24, T-2477; amendment §6 of 2026-09-26, T-3013)

## 1. Context

Every published App lives at `https://{domain}/apps/{name}/` (ADR-N-019), on the same origin as every other App, the forge (`/git/*`) and the endpoints (`/api/endpoint/*`). The survey of T-1706 found what that costs (T-2477):

- A page of App A reads App B's `localStorage` and IndexedDB, and scripts B in a frame or a window it opened, which defeats B's own CSP.
- A page of App A sends requests to `/apps/B/api/endpoint/…`. The browser attaches B's session cookie because the path matches, so A acts as the person through B's grants. The same holds for `/git/*` with the apex session.
- The per-app CSP `connect-src 'self'` names that shared origin, so it separates nothing between Apps.
- A server pod may reach `0.0.0.0/0` on 443. It calls its own endpoint through the public host, which kube-proxy DNATs to the ingress controller, so the NetworkPolicy cannot name a pod there. A generated server can send whatever it reads anywhere.

On 2026-09-24 the owner chose a host per App and an egress allow-list per App. The same day the domain moved to `dev.joinedcontext.com` (T-2806). The record `*.dev` A answers every deeper name, `{app}.apps.dev…` included, because no `apps.dev` node exists (RFC 4592). The zone has no DNS API, so there is no wildcard certificate. Each host gets its own certificate by HTTP-01, and Let's Encrypt allows 50 per registered domain per week.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | The browser's same-origin policy is the wall between Apps. The per-host certificate is an ordinary cert-manager HTTP-01 Certificate, and the egress rule is an ordinary NetworkPolicy. |
| Security by design | **Full** | Storage, cookies, frames and fetches separate by origin with no code of ours. A pod that can reach only the gateway and its declared destinations cannot send data anywhere else. |
| Least privilege | **Full** | An App's host routes only that App and its own endpoints. Its pod reaches only its endpoint, plus what its manifest declares and a publisher approved. |
| Operability | **Partial** | Every published App costs one certificate. Publishing waits for its certificate, and a burst of more than about 50 new Apps a week hits the rate limit. |

## 3. Decision

1. **A host per App.** A published App is served on `https://{name}.apps.{domain}/`, and on no path of another host (AP-133). Its routes `app-{name}` and `app-{name}-endpoint` match that host only:
   - `/*` is the App;
   - `/api/endpoint/{slug}/*` goes to the gateway, for the slugs of the endpoints the App reads and no other;
   - everything else on the host is a 404 at the edge.

   The App's session cookie is host-only on its own host, and the Keycloak client `app-{name}` accepts that host alone as its redirect and web origin. The build's base path is `/`.
2. **A certificate per App, by HTTP-01.** The reconciler creates the edge Ingress for the host, with a TLS secret of its own issued by `letsencrypt-prod`, once when the App is published. It deletes both when the App is retired. It never requests a certificate for an App that is not published, and never requests one again on a reconcile. An App reads `published` only once its certificate is `Ready`.
3. **The old path redirects, then goes.** `/apps/{name}/*` on the apex answers `308` to the App's host and carries no session. The apex routes `apps-surface` and `context-endpoint-apps` are removed.
4. **Egress to the gateway and declared destinations only.** A server pod calls its endpoint in the cluster, `JC_ENDPOINT_URL` pointing at the context gateway's Service with the person's token (the mesh carries it as mTLS). Its NetworkPolicy therefore admits DNS, the Linkerd control plane, the gateway pods and the destinations `spec.egress[]` declares, and nothing else (AP-134). A destination is a CIDR with its ports, rendered as an `ipBlock` with the private ranges excepted. Declaring one takes the red lane, like a `public` App.

## 4. Alternatives Considered

- **A CSP `sandbox` on the shared origin (option b of T-2477).** Each App would get an opaque origin, with no storage, no cookies and a token held by the SDK. It keeps one certificate. But it breaks every App that keeps state in storage, and it puts a bearer token in page JavaScript, which AP-23 forbids.
- **Accept the risk for the MVP (option c).** The owner declined it. The attack is one line of script in a generated App.
- **A wildcard certificate by DNS-01.** It needs a DNS API the zone does not have (T-2806). Taken on 2026-09-26 with a delegated zone, see §6.
- **Egress by host name.** A NetworkPolicy matches addresses, not names. An App that must reach a name-addressed service behind a CDN waits for a platform egress proxy that enforces a per-App list of names. That is a known limit of this decision: until the proxy exists, `spec.egress` takes addresses only.

## 5. Consequences

- AP-133…AP-135 are new. AP-12, AP-26, AP-29 and AP-112 now name the App's host instead of its path. ADR-N-019 keeps the edge login and loses the `/apps/{name}/` layout.
- **Work, one task per repository** (T-2837 platform, T-2838 Portal, T-2839 deployment and conformance):
  - the Portal: its reconciler composes the host-bound routes and the redirect (AP-112), creates the Ingress and certificate per App, the NetworkPolicy of AP-134, the in-cluster `JC_ENDPOINT_URL` and base path `/`, and points "Open app" at the host;
  - jcctl renders the same routes where it renders app routes;
  - the deployment removes the apex app routes, admits the apps namespace to the gateway and adds the security suite.
- Publishing an App now waits for one HTTP-01 challenge, usually well under a minute.

## 6. Amendment 2026-09-26: a Wildcard Certificate by DNS-01

The owner ordered on 2026-09-26 that every App answer on its host the moment it is published, with no certificate to wait for (T-3013). A new host waited for one HTTP-01 challenge, and a host whose challenge failed served the ingress controller's default certificate. The parent zone still has no DNS API, so the App zone moves to a provider that has one.

1. **The App zone is delegated.** The parent zone gets `NS` records for `apps.{domain}` that name the new provider's servers, and the delegated zone holds `*` `A` to the ingress address. Every App host keeps resolving, now from the delegated zone. A lone `_acme-challenge.apps.{domain}` record at the parent is never an option: any record under `apps.{domain}` creates that node, and `*.{domain}` then stops answering the App hosts (RFC 4592).
2. **On dev the provider is Hetzner DNS**, through the Hetzner Cloud API. Hetzner scopes an API token to a project, not to a zone, so the zone lives in a Hetzner project that holds that zone and nothing else. Its token can change that zone alone.
3. **One certificate `*.apps.{domain}`.** The namespaced Issuer `letsencrypt-dns01` in the APISIX namespace solves DNS-01 through Hetzner's cert-manager webhook (group `acme.hetzner.com`, solver `hetzner`). The token is a Secret supplied by `secretRef`, and it never appears in values, Git or a log. The Certificate `apisix-apps-wildcard` writes its key to the Secret `apisix-apps-wildcard-tls`, and the edge Ingress carries a rule and a TLS entry for `*.apps.{domain}`.
4. **The reconciler reads the certificate.** When `apisix-apps-wildcard` is `Ready` and names `*.apps.{domain}`, an App's host is ready with no Ingress or certificate of its own. Without it, the reconciler keeps the per-host HTTP-01 path of §3.2. The per-host certificates issued earlier stay until the wildcard is proven on dev; one later change removes them.
5. **Off by default.** `global.ingress.appsWildcard.enabled` turns it on. An installation without a DNS API keeps §3.2 unchanged.

The wildcard's key serves every App host. It lives only in the APISIX namespace, where the ingress controller already reads the edge certificate's key. The separation between Apps does not change: the browser separates origins by host name, whichever certificate serves the host.

## Related

- [Requirements/apps](../Requirements/apps.md) — AP-133…AP-135, AP-12, AP-26, AP-29, AP-112.
- [ADR-N-019](adr-n-019-login-at-the-edge-apisix-openid-connect.md) — the edge login this keeps.
- [ADR-N-030](adr-n-030-every-application-is-a-keycloak-client.md) — the per-App client whose redirect URIs move to the host.
- [Deployment/10-edge-routing-apisix](../Deployment/10-edge-routing-apisix.md) — the route table.
