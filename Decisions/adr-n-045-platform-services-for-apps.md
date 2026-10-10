---
sidebar_position: 46
title: "ADR-N-045: Platform Services for Apps, One List, Three Layers, One Client per Service"
---

# ADR-N-045: Platform Services for Apps, One List, Three Layers, One Client per Service

Date: 2026-10-10  
Status: Accepted  
Decision Makers: product owner (request of 2026-10-10, T-3582: "an SDK like Base44 or Lovable, so an AI agent only glues the platform's services together"; addition of the same day: every service is switched on and off in settings); the shape below was decided by worker-1, owner may override

## 1. Context

The owner wants an App to be glue: the platform runs and secures e-mail, authorization, data, files, jobs and AI, the App declares what it uses and calls one typed client per service. Today each of these pieces has its own shape, and two are missing:

| Service | What exists on 2026-10-10 | Where |
|---|---|---|
| identity | `me()` and `useMe()` read the served configuration's `user`; `can()` answers from the Endpoint's grant document; every App is the Keycloak client `app-{name}`; a function gets `request.user` | portal `sdk/src/sdk/client.ts:587`, `sdk/src/sdk/access.ts:50`, `src/reconciler/app_clients.rs:148`, `src/apps/functions.rs:96`; ADR-N-030 |
| data | `jc()` over the App's Endpoint `/api/endpoint/{slug}/ngsi-ld/v1`; `jc-app-sdk::gateway` reads `http://gateway/…`, GET only | portal `sdk/src/sdk/client.ts:595`, `sdk/src/grid/source.ts:229`; platform `crates/app-sdk/src/gateway.rs:88`, `crates/wasm-host/src/host.rs:83` |
| files | `jc:app/blob` and `jc-app-sdk::blob` for `wasm` Apps; `spec.storage` refused on every other kind; nothing in the TypeScript SDK | platform `crates/wasm-host/wit/jc-app.wit:45`, `crates/app-sdk/src/lib.rs:123`, `crates/jc-core/src/kinds/app.rs:1157` |
| email | none: the Portal refuses an alert's `delivery: email` because it has no relay; only Keycloak's realm SMTP sends password resets | portal `src/alerts.rs:263`; task T-3309 (blocked on the relay) |
| jobs | `spec.server.jobs[]` on `wasm` Apps, run by the host's scheduler as the App's own principal; no helper in `jc-app-sdk`, nothing in the TypeScript SDK | platform `crates/jc-core/src/kinds/app.rs:712`, `crates/wasm-host/src/jobs.rs`; portal `src/reconciler/wasm_shards.rs:124`; AP-154, AP-159 |
| ai | none for an App: the model proxy answers agent runs with a run ticket only, and the assistant is a Portal API | platform `crates/agent-proxy/src/auth.rs:67`; portal `src/api/assistant.rs:1011` |

The graph queries behind the table are recorded in T-3582.

## 2. Decision

### 2.1 One closed list in the App's manifest

`spec.services` lists what the App uses, each name once, from `identity`, `data`, `files`, `email`, `jobs` and `ai`; any other name is refused like an unknown field (AP-160). `identity` and `data` are every App's whether listed or not, because an App without a Keycloak client or an Endpoint does not exist on this platform (AP-161). The other four are off until listed: each sends something out (`email`), stores something (`files`), runs without a person (`jobs`) or costs money per call (`ai`). `jobs` is the existing `spec.server.jobs[]` and stays a `wasm` App's; declaring jobs lists the service, so no manifest written before this decision changes (AP-162).

An App's own SQL schema (`spec.storage.sql`, AP-148) is not a service in this list: it is part of the `wasm` shape, provisioned per App and reached only by its component.

### 2.2 Three layers, each narrowing the one above

| Layer | Says | Field |
|---|---|---|
| Organization | which services the organization's Apps may use at all, and the per-App ceilings | `spec.policies.apps.services`, `spec.limits.apps` |
| Project | which of those this project's Apps may use, and lower ceilings | `spec.apps.services`, `spec.apps.limits` |
| App | which it uses, and its own quotas | `spec.services`, `spec.limits` |

A lower layer may only narrow: a project naming a service its organization does not allow is refused, and so is an App naming a service its project does not (AP-163). Every layer is a manifest, so every switch is a Change with its approval (AP-166). The Portal checks all three on every call, so switching a layer off stops published Apps at their next call, and the refusal names the layer (AP-164). The builder offers only what is on (AP-22). The screens that write these fields are the follow-up task T-3586.

### 2.3 The platform holds every credential

The SMTP account, the model key and the object store's keys are `secretRef`s the Portal resolves; no App, function or component ever holds one (AP-167). A browser calls `/api/services/{service}/…` on its own App host with the person's session, as it already calls its Endpoint (AP-133); a function calls the same routes with its caller's token; a component calls host interfaces of `jc:app@0.2.0`, and the host asks the Portal the same three questions.

- **email** sends only to people of the App's organization, named by id, or to the person signed in, never to an address typed into the App, so a public form cannot make the platform a relay (AP-168). The relay is the one T-3309 configures for alerts; one mailer serves both.
- **ai** calls a model the organization's agents may use, with the organization's model key, counted against the App's daily tokens; prompts and answers are not logged (AP-169).
- **files** extends the `wasm` App's storage prefix to every App: the same `apps/<shard>/<id>/` prefix, through the host interface for a component and through `/api/services/files/` for everything else (AP-170).

### 2.4 One client per service, in both SDKs

`jc()` offers `identity`, `data`, `files`, `email`, `jobs` and `ai`; the first two are the calls `jc()` already has, under their service names, not a second implementation (SDK-41). `jc-app-sdk` offers the same six modules over the host's interfaces, keeping `gateway` and `blob` as re-exports while a published component imports `jc:app@0.1.0` (SDK-42). A refused call throws or returns one error type that names the service and the layer or the quota (SDK-43). The signatures are in [API/06](../API/06-app-services.md).

## 3. Security Analysis

| Threat | What stops it |
|---|---|
| An App leaks or misuses a service credential | it never holds one; the Portal or the host makes the outgoing call (AP-167) |
| A public App becomes a spam relay | recipients are people of the organization by id, or the signed-in person; per-App daily quota (AP-165, AP-168) |
| An App runs up a model bill | `ai` is off until listed at three layers; daily tokens per App, ceilings from the organization (AP-165, AP-169) |
| A project turns on what its organization refused | the lower layer is refused at the Change and checked again at every call (AP-163, AP-164) |
| An App's files reach another App's | one prefix per App, refused outside it by the Portal or the host and by the store's own key policy (AP-145, AP-170) |
| A prompt with personal data is kept | prompts and answers are not logged; the log has the App, the model and the token count (AP-169) |

## 4. Alternatives Considered

| Alternative | Why not |
|---|---|
| Each App brings its own keys (SMTP, model, S3) as `secretRef`s | every App would hold a credential, quotas would be the vendor's and invisible to the organization, and a generated App would need a person to create accounts before it runs |
| Services always on, quotas only | a public form with e-mail on by default is a relay; an organization that wants no model spend has to set every quota to zero |
| One generic `call(service, op, body)` client | the model writes untyped calls and learns of a typo at run time; one module per service type-checks |
| Settings in a database table instead of manifests | a switch would bypass the Change and its approval, and Configuration as Code would no longer say what an organization allows |

## 5. Consequences

- `AppSpec` gains `services`, `OrganizationSpec` gains `policies.apps.services` and `limits.apps`, `ProjectSpec` gains `apps`; the schema refuses an unknown service name.
- The Portal gains a service API under `/api/services/`, routed on every App host, and one mailer (with T-3309).
- `jc:app` moves to `0.2.0` with `email`, `ai` and an identity value per request; `jc-app-sdk` follows.
- Implementation tasks: T-3583 (e-mail), T-3584 (the SDK modules for identity, files, jobs and ai), T-3585 (the builder's pack and catalogue of services), T-3586 (the settings screens of the three layers).

## 6. Requirements

- AP-160…AP-170: the list, the layers, the quotas, the credentials and each service's limits.
- SDK-41…SDK-45: the clients, the refusal and the test stubs.

## Related

- [Requirements/apps.md §29](../Requirements/apps.md#29-platform-services-for-apps) — the normative rules this decision is written down as.
- [API/06](../API/06-app-services.md) — the routes, the client signatures and the refusals.
- [ADR-N-044](adr-n-044-server-wasm-apps-on-a-shared-host.md) — the shared host whose interfaces the Rust client wraps.
- [ADR-N-030](adr-n-030-every-application-is-a-keycloak-client.md) — the Keycloak client that is every App's identity.
- [ADR-N-035](adr-n-035-organization-policies-and-limits.md) — organization policies and limits as manifest fields, which the layers extend.
