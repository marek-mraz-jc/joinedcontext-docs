---
sidebar_position: 19
title: "ADR-N-018: Bearer tokens are verified in the PEPs, not at the edge"
---

# ADR-N-018: Bearer tokens are verified in the PEPs, not at the edge

Date: 2026-09-06  
Status: Accepted  
Decision Makers: Architecture Board

§3.4's "runs no `openid-connect` plugin on any route" is superseded by [ADR-N-019](adr-n-019-login-at-the-edge-apisix-openid-connect.md): the edge logs a browser in with `openid-connect` in session mode on `portal-ui`, `portal-api`, `apps-surface` and every `app-{name}` route, and forwards the person's access token. Verifying bearer tokens stays in the PEPs, as decided here.

## 1. Context

Two decisions this platform had already made contradict each other, and the edge fails closed
between them.

The realm signs access tokens with **ES256**. `defaultSignatureAlgorithm: ES256` is set in the
Keycloak values and the auto-generated RS256 key is disabled, because BSI TR-03187 AR-11 asks
for Ed25519 or ECDSA P-256 signing keys ([Architecture/13 §2](../Architecture/13-security.md#2-bsi-tr-03187-conformance-matrix)).
The live realm publishes exactly that: an ES256 key in the JWKS, and every issued token carries
`"alg": "ES256"` in its header.

**APISIX cannot verify an EC signature.** Its `openid-connect` plugin delegates to
lua-resty-openidc, which decides up front which algorithms it handles:

```lua
local function is_algorithm_supported(jwt_header)
  return jwt_header and jwt_header.alg and (jwt_header.alg == "none"
      or string.sub(jwt_header.alg, 1, 2) == "RS"
      or string.sub(jwt_header.alg, 1, 2) == "HS")
end
```

No key is ever fetched for an EC token, so every bearer call is refused with
`jwt signature verification failed: No trusted certs loaded` and `HTTP 401`. This is not a
version to upgrade past: the same function on lua-resty-openidc `master` is byte-identical, so
no APISIX image fixes it. The deployment smoke suite records the symptom as
`FAIL portal API answers a bearer call (expected 200, got 401)` next to
`ok portal API rejects an unauthenticated call (401)`: the edge is safe, and unusable.

Four ways out were on the table, three of them costing a control the platform had deliberately
chosen: verify in our own PEPs; go back to HTTP introspection; sign RS256; or APISIX `jwt-auth`
with a public key pasted into a consumer.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Security by design | **Full** | Keeps ES256 (AR-11) and keeps every surface authenticated; no static key, no per-request dependency on Keycloak. |
| Standard solutions before custom code | **Partial** | The stock edge plugin would have been less code, but it cannot verify the algorithm the realm signs with. The verifier itself is a library, not hand-rolled crypto. |
| Technological consistency | **Full** | Both PEPs are Rust and already parse the token to make a policy decision; one verifier in `jc-core` serves both. |
| Modular design | **Full** | The edge keeps routing, rate limiting and header hygiene; authorization stays with the component that owns the resource. |
| Multi-tenancy | **Full** | Audience binding is checked by the service the audience names, which is the only place that knows what it is called. |
| Open source as default | **Full** | No proprietary component enters the path. |

## 3. Decision

1. **The PEP that serves a request verifies its token.** The Portal verifies for `/api/v1/*`;
   the Context Gateway verifies for `/cs/{space}/*` and `/api/endpoint/{slug}/*` (PF-46).
2. **What is checked, and nothing else about who is calling:** `iss` equals the configured realm
   issuer, the signature over the token, `exp`, `nbf`, and `aud` containing the resource being
   called. `azp` is then mapped to a `ServiceAccount` manifest to learn the roles the PDP
   evaluates ([Architecture/12 §3](../Architecture/12-identity-and-access.md#3-service-identities)).
3. **JWKS is cached in process** and refreshed in the background. An unknown `kid` triggers at
   most one refresh per minute whatever the request rate, so invented `kid` values cannot turn a
   PEP into a load generator against Keycloak; a request arriving while that window is closed is
   rejected.
4. **The edge keeps everything else** and verifies no bearer token itself:
   `request-id`, inbound header stripping, rate limiting, CORS, `proxy-rewrite` and the response
   security headers. (As decided on 2026-09-06 it ran no `openid-connect` plugin at all; since
   [ADR-N-019](adr-n-019-login-at-the-edge-apisix-openid-connect.md) it runs one in session mode
   on the browser routes, to log a person in, and the PEP behind still verifies the token it
   forwards) ([Deployment/10 §4](../Deployment/10-edge-routing-apisix.md#4-plugin-chain-architecture-by-route-class)).
5. **A route whose upstream does not verify stays out of `apisix.yaml`.** Routing a path to a
   service that does not check the token would publish that path anonymously.
6. **One verifier, used twice.** It lives in `jc-core` and is used by both the Context Gateway
   and the Portal, so a rule fixed once is fixed everywhere.

Rejected, with the reason each one costs more than it saves:

- **HTTP introspection at the edge** (`use_jwks: false`) works with any algorithm, because
  Keycloak verifies its own signature. It puts a Keycloak round trip in front of every API call
  and makes the identity provider a per-request dependency of the whole platform, which is what
  moving to JWKS removed in the first place.
- **Signing RS256** is one realm setting and everything works today. It reverses AR-11, a control
  chosen on purpose, and Keycloak's generated RSA key is 2048 bits.
- **APISIX `jwt-auth`** does support ES256, but only against a public key pasted into a consumer:
  a static key that does not rotate with Keycloak. Static keys between cluster services are
  forbidden (PF-45).

## 4. Consequences

- Anonymous traffic on the endpoint surface is unchanged. It always passed the edge untouched and
  the Context Gateway decided what an anonymous caller may see; now the same component also
  decides whether a token that did arrive is real.
- Until the Context Gateway runs on a cluster, the Portal is the only verifying upstream there,
  so only routes pointing at the Portal may be published on it.
- A `401` now comes from the upstream rather than from APISIX. An access-log line with upstream
  status `401` is the signal to read the Portal or gateway log, not the APISIX error log
  ([Deployment/10 §8](../Deployment/10-edge-routing-apisix.md#8-failure-modes-and-operational-troubleshooting)).
- The edge no longer needs the `apisix-gateway` Keycloak client for verification.
- Key rotation is visible: a token signed with a `kid` the cached key set does not carry yet is
  refused until the next refresh window, at most a minute later.

## Related

- [ADR-N-007](adr-n-007-apisix-standalone-no-etcd.md) — the standalone edge this decision leaves in place.
- [ADR-N-003](adr-n-003-context-gateway-in-rust.md) — the PEP that now verifies.
- [12-identity-and-access](../Architecture/12-identity-and-access.md) — what a PEP checks in a token.
- [10-edge-routing-apisix](../Deployment/10-edge-routing-apisix.md) — the plugin chain without a verifier.
