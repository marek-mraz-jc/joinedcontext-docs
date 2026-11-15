---
sidebar_position: 72
title: "ADR-N-071: A Managed Webhook DataSource on the Shared Ingest Listener"
---

# ADR-N-071: A Managed Webhook DataSource on the Shared Ingest Listener

Date: 2026-11-15  
Status: Proposed  
Amends: [PL-50](../Requirements/pipelines.md) (the refusal of `http_server` stays for author-written inputs)  
Decision Makers: product owner (2026-11-15 supervisor session, "more input sources"); drafted by worker-t7088 (T-7088, split of T-7058 G-12), owner may override

This record adds one managed DataSource type, `webhook`, that receives pushed events on the runner's shared ingest listener. An author still cannot write an `http_server` input: only the reconciler renders one, from the typed `spec.webhook` block, with authentication always on.

## 1. Context

- **Feeds that push.** The Things Network, ChirpStack, bike-share operators, 311 and complaint apps and form tools deliver events as signed HTTP POSTs. Today such a feed has to write through an Endpoint, which needs a Keycloak client and an OAuth2 token the sender cannot obtain; a provider signs its body with a shared secret or sends a fixed bearer token, and that is all it can do.
- **PL-50 refuses listeners.** `http_server` and `socket_server` are refused as `spec.type` because a listener in the runner's pod would be an unmanaged door: any address, no authentication, no limit.
- **ekiben already has the managed door.** In `streams` mode ekiben serves every `http_server` input on one shared ingest listener at `/{org}/{stream}{path}`. It refuses `address`, `cert_file`, `key_file` and `ws_path` there and requires `auth`: a bearer token or a SHA-256 HMAC of the body, each compared in constant time, a missing and a wrong credential answering the same `401`. It also enforces `max_body_bytes` (`413`), `max_in_flight` (`503`) and `rate_limit` (`429`), and removes the route when the stream is deleted (ekiben-io-http `http_server.rs`, `ingest.rs`).

## 2. Decision

1. **A typed `webhook` DataSource.** `spec.type: webhook` with a `spec.webhook` block and nothing else:
   - `auth` (required) holds exactly one of `hmac: { header, secretRef }` (a hex SHA-256 HMAC of the raw body in the provider's header, with or without a `sha256=` prefix) and `bearer: { tokenRef }` (`Authorization: Bearer <token>`). Each credential is a `secretRef` (MF-35); there is no `public` option.
   - `maxBodyBytes` is 1 to 16777216 and defaults to 1048576 (1 MiB). `maxInFlight` is 1 to 1024 and defaults to 64.
2. **The reconciler renders it, the author never does.** The input is `http_server` with `path: /{dataSource}`, `allowed_verbs: [POST]`, the `auth` above with each secret as a `${VAR}` of the source's injected environment (PL-15), `max_body_bytes`, `max_in_flight` and `sync_response.status: "202"`. It never carries `address`, `cert_file`, `key_file`, `ws_path` or `public: true`. `http_server` stays refused as an author-written `spec.type` and inside any wrapper input (PL-50).
3. **One public address per reading pipeline.** The stream of pipeline `{pipeline}` in project `{project}` is `{project}.{pipeline}`, so the sender posts to `{ingest base}/{project}.{pipeline}/{dataSource}`. In a jc installation the ingest base is `https://portal.{domain}/ingest/default` (`[[mounts.ekiben]]` entry `path_prefix = "/ingest"`). That entry serves only the ingest router, never ekiben's `/streams` API. A webhook source never terminates, so its pipeline is `resident` (PL-04).
4. **The Portal shows the address and can send a test event.** The DataSource page lists each reading pipeline's URL and the header the sender sets. "Send test event" posts a JSON body the person types through the same ingest handler, signed or authorised by the Portal with the referenced secret, and shows the status the runner answered. The secret never reaches the browser.

## 3. Alternatives considered

- **Lift the PL-50 refusal of `http_server`.** Rejected: an author could name `public: true` or omit the caps, and the refusal is what keeps a manifest from opening an unauthenticated door.
- **Push through an Endpoint.** Rejected: the sender would need an OAuth2 client of its own, which none of the providers above supports.
- **A separate webhook gateway.** Rejected: a second listener, a second rate limiter and a second route table, when ekiben's ingest listener already enforces all three.

## 4. Security

- Authentication is mandatory and typed; the credential comes only from a `secretRef` and is never written into the rendered stream, a log or a status.
- An unknown project, pipeline or source answers `404`; a missing or wrong credential on a known route answers `401` with the same body whether the credential is absent or wrong.
- The body is capped before any step runs (`413`), concurrent requests are capped (`503`), and the edge's per-address rate limit applies in front.
- Deleting the pipeline or the DataSource removes the route; a later POST answers `404`.
- The test-event action requires the DataSource's update permission, since it writes through the pipeline like a real event.

## 5. Consequences

- PL-50 names `webhook` as the one managed listener; [PL-118](../Requirements/pipelines.md) holds the rules above.
- The Portal's DataSource form gains the `webhook` type; the reconciler, `jcctl validate` and the Portal Check share the jc-core validation.
- A provider that signs another way (a timestamped signature, a JWT) needs its own `auth` variant and a new record.

## Related

- [PL-50](../Requirements/pipelines.md): any input the runner ships, and the inputs it refuses.
- [Architecture/08 §6](../Architecture/08-pipelines.md#6-external-feeds-the-datasource-kind-mf-35-pl-39): the DataSource kind.
- [ADR-N-012](adr-n-012-secrets-sops-openbao.md): where `secretRef` values come from.
