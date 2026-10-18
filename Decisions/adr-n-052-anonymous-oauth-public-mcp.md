---
sidebar_position: 53
title: "ADR-N-052: Public Data on Its Own Host, and OAuth for Public MCP Without Users"
---

# ADR-N-052: Public Data on Its Own Host, and OAuth for Public MCP Without Users

Date: 2026-10-18  
Status: Accepted  
Decision Makers: product owner (order of 2026-10-18 via the supervisor: the domain "should always be api.data.joinedcontext.com/api/mcp, api.data.joinedcontext.com/api/endpoint/&lt;id&gt;", corrected by the owner at 14:50Z to `api.dev.joinedcontext.com` on `dev` and `api.joinedcontext.com` in production, and for a Gemini connector "i dont want to store users... at all"); recorded by worker-2 (T-4629), owner may override

This record moves the public data surfaces of the Context Gateway to a host of their own and gives the public MCP servers an OAuth 2.1 front that identifies nobody. [ADR-N-025](adr-n-025-one-mcp-connector-several-endpoints.md) (the hub) and [ADR-N-043](adr-n-043-named-mcp-servers.md) (named servers) keep their paths and their rules.

## 1. Context

Today the gateway answers on the Portal's host: `https://dev.joinedcontext.com/api/endpoint/{endpointSlug}/…` and `https://dev.joinedcontext.com/api/mcp`. The address a person copies into a GIS client or an assistant therefore names the management application, and moving either one moves both.

Consumer Gemini custom apps connect to a remote MCP server only through OAuth 2.1. They discover the server's authorization server through RFC 9728 protected-resource metadata and RFC 8414 server metadata, register a client with Dynamic Client Registration (RFC 7591), and run an authorization code flow with PKCE that returns through `https://oauth-redirect.googleusercontent.com/…` (Google help 17209137; reports in BasedHardware/omi#11263 and firecrawl-mcp-server#345). The public MCP servers accept anonymous calls and name Keycloak as their authorization server. Keycloak's DCR stores every registered client, and its authorization code flow needs a user who logs in. So Gemini cannot connect to data that anyone may read without an account.

## 2. Decision

### 2.1 One host for public data

1. **The host.** The gateway's public surfaces answer on `api.{domain}`: `api.joinedcontext.com` in production, `api.dev.joinedcontext.com` on `dev` (the `*.dev` record already resolves it). The paths stay: `/api/mcp` and everything under it (named servers, `me`, `org`), `/api/endpoint/{endpointSlug}/` and everything under it (`mcp`, `ws`, `ogc/…`, `schema/…`, file downloads, NGSI-LD, the DCAT-AP record), the canonical space surface `/cs/{space}/` and everything under it, and the harvesting feed `/catalog.jsonld`, `/catalog.ttl` and `/catalog/{project}.jsonld|.ttl` (owner, 15:05Z: every surface that serves data to the outside). `JC_GATEWAY_PUBLIC_URL` is `https://api.{domain}`, so RFC 8707 resource URIs and token audiences name the new host.
2. **What stays.** Pages a person reads in a browser keep their hosts: the Portal on `portal.{domain}` with its `/api/v1`, `/api/v1/mcp` and its public pages (`/v/`, `/f/`, `/d/`, `/catalogue`, `/connect`, `/docs`), the open-data catalogue on `data.{domain}` with CKAN's own `/api/3` and `/catalog.ttl` (harvesters register CKAN by its site URL, T-4586), and the assistant widget on `assistant.{domain}` with its chat API `/api/v1/d/*`, the widget's same-origin backend.
3. **The old addresses.** The four paths on the apex `{domain}` and on `portal.{domain}`, the addresses people copied, answer `308 Permanent Redirect` to the same path and query on `api.{domain}`, so an anonymous connector, a GIS layer or a harvester added before the move keeps working. One exception on `portal.{domain}`: a request that carries the Portal's edge session cookie (`__Host-jc_edge`) is still served there, because that cookie is host-only and a redirect to another host would drop it, which would break the Portal's own screens (Explore, the Endpoints view, the space browser). A client that follows a redirect drops its `Authorization` header across hosts (curl, reqwest, browsers), so a caller with a bearer changes its address; the redirect carries anonymous readers and tells the others where to go. The redirect ships in release `v0.1.0` of `joinedcontext-deployment` and is removed in `v0.2.0`; the release notes of `v0.2.0` say so.

### 2.2 A stateless authorization server for anonymous data

The gateway runs an OAuth 2.1 authorization server on `api.{domain}` that stores nothing and identifies nobody. It serves only the MCP servers an anonymous caller may already read: the hub, a named server or an Endpoint's own MCP whose answer without a token is not empty.

1. **Metadata.** `/.well-known/oauth-authorization-server` (RFC 8414) names the three endpoints below, `code_challenge_methods_supported: ["S256"]`, `grant_types_supported: ["authorization_code", "refresh_token"]`, `token_endpoint_auth_methods_supported: ["none"]` and `response_types_supported: ["code"]`. The protected-resource metadata (RFC 9728) of a public MCP server lists this server first and Keycloak second in `authorization_servers`. A server that is not anonymous-readable lists Keycloak alone, unchanged.
2. **Registration, `POST /oauth/register`** (RFC 7591). The request names `redirect_uris`: at most 5, each at most 2048 bytes; more is refused `400 invalid_client_metadata`. Every URI must match the redirect allowlist (2.3); one that does not is refused `400 invalid_redirect_uri` and nothing is issued. The answer's `client_id` is a token the gateway signs over the registered URIs, its issue time and an expiry 365 days later. No client is written anywhere: the next request proves its registration by carrying that `client_id`. `token_endpoint_auth_method` is `none` (a public client); no client secret exists.
3. **Authorize, `GET /oauth/authorize`.** No login page and no consent page: there is nobody to log in and nothing to consent to beyond what the open data already allows. The gateway verifies the `client_id` signature and expiry, requires `redirect_uri` to be one the `client_id` names, `response_type=code`, `code_challenge_method=S256` and a `code_challenge`. It answers `302` to that `redirect_uri` with a `code` it signs over the `client_id`, the `redirect_uri`, the challenge and the `resource` (RFC 8707), valid for 60 seconds, and the caller's `state` unchanged. Any failed check answers an error page on the gateway's own host and never redirects, so the step cannot become an open redirect.
4. **Token, `POST /oauth/token`.** For `authorization_code`, the gateway verifies the code's signature and expiry, that `client_id` and `redirect_uri` match it, and that the `code_verifier` hashes to its challenge. It answers an access token valid for one hour and a refresh token valid for 30 days. For `refresh_token`, it verifies the refresh token and answers a new pair. Both tokens are JWTs the gateway signs with `iss` = `https://api.{domain}`, `aud` = the requested resource, a random `jti`, and no `sub`, no name, no email and no group. A code or a refresh token used twice works twice: with nothing stored there is nothing to spend, and what it buys is what any anonymous caller already gets.
5. **What the token grants.** Exactly the rights of a caller without a token: the `public` Endpoints and the anonymous allowance of every quota. The rate limiter, and every place that asks whether a request carries a credential, class it with the callers that present no token, so minting tokens never buys a bucket of its own. The gateway accepts it only on the resource named in its `aud`. A call with no token at all keeps working as today, so `curl` and the clients that never ran OAuth are unaffected.
6. **The signing key.** One key, at least 32 bytes, used with HMAC-SHA-256 for the `client_id`, the code and both tokens. Each of the four carries its own `typ` claim (`jc-client`, `jc-code`, `jc-access`, `jc-refresh`), and each step accepts only its own: a `client_id` presented as a bearer, or a refresh token presented as an access token, is refused, although one key signs them all. It is referenced by `secretRef` and resolved by the reconciler, never in Git, an image or a log. Two verifiers stay apart: the Keycloak verifier accepts only Keycloak's asymmetric algorithms and keeps refusing `HS256`, and the anonymous verifier is chosen by `iss` = `https://api.{domain}`, accepts `HS256` with this key only and never Keycloak's keys. Rotating it invalidates every `client_id` and token at once. A client then registers again, which costs an anonymous reader one more redirect and nothing else.

### 2.3 The redirect allowlist

The gateway accepts a redirect URI only on these hosts, configured as `JC_GATEWAY_OAUTH_REDIRECT_HOSTS` with this default:

- `oauth-redirect.googleusercontent.com` (Gemini), over `https`;
- `claude.ai` and `claude.com` (Claude), over `https`;
- `chatgpt.com` (ChatGPT), over `https`;
- `localhost`, `127.0.0.1` and `[::1]` on any port, over `http` (command-line clients, RFC 8252 §7.3).

The host is compared exactly after parsing the URI; a userinfo part, a fragment or another scheme is refused. Adding an assistant is a configuration change reviewed like any other.

The deployment sets the variable to `oauth-redirect.googleusercontent.com` alone, on `dev` and in production, by owner order (2026-10-18T15:59Z, "oauth2 should be only for gemini"). The default above applies only where the variable is unset. Claude, ChatGPT and Grok read the public MCP servers without a token: a registration naming their hosts is refused `400 invalid_redirect_uri`, and an anonymous call never answers `401`, so no client is pushed into OAuth (T-4630).

### 2.4 What does not change

"Identity is Keycloak only" still holds. This token names no one, and every decision about a person or a workload still starts from a Keycloak token. An Endpoint that is not anonymous-readable, a project's named server and a person's connector (`/api/mcp/me/{name}`) take Keycloak tokens only, as before.

## 3. Alternatives

1. **Keycloak's DCR.** It stores every registered client in the realm, and its authorization code flow ends at a login page, which needs a user. Rejected: the owner wants no users and no stored clients.
2. **A shared guest user in Keycloak.** A static credential stored in the realm and handed to every assistant. Rejected: it is the static key the platform removed (T-4362), with a login page in front.
3. **Leave the public MCP anonymous.** Rejected: Gemini cannot connect without OAuth.
4. **Keep the Portal's host for data.** Rejected by the owner's order; it also ties the address people copy to the management application.

## 4. Consequences

- The deployment adds the route and the certificate for `api.{domain}`, sets `JC_GATEWAY_PUBLIC_URL`, and redirects the old paths (T-4630).
- The DCAT-AP catalogue IRIs (`https://api.{domain}/catalog/{project}`) and the resource URIs of the spaces name the new host; a national portal that harvested the old address follows the `308` and sees the catalogue under its new IRI once.
- The gateway gains `/oauth/register`, `/oauth/authorize`, `/oauth/token` and the server metadata, in Rust beside its token verification (T-4631).
- The Portal, the CKAN theme and the conformance suites change every address they print (T-4632). The MCP Registry entry names the new host (T-4633).
- A leaked access token is worth nothing a stranger could not get with `curl`. The risks left are the open redirect and the cost of minting, which the allowlist and the edge rate limit on `/oauth/*` cover.

## Related

- [ADR-N-025](adr-n-025-one-mcp-connector-several-endpoints.md) — the hub this host serves.
- [ADR-N-043](adr-n-043-named-mcp-servers.md) — named servers, which keep Keycloak unless anonymous-readable.
- [Requirements/endpoints.md](../Requirements/endpoints.md) — EP-128 and EP-129 state this decision as requirements.
- [API/02 §8](../API/02-endpoint-representations.md#8-model-context-protocol-mcp) — the MCP surface and its OAuth endpoints.
