---
sidebar_position: 9
title: "App Builder Gap: Base44, Lovable and joinedcontext"
description: What a person gets from one prompt in Base44, in Lovable and in the joinedcontext app builder, the gaps worth closing, the Rust WASM shape and what the switch to Antares views changes for the SDK; read 2026-10-10.
---

# App builder gap: Base44, Lovable and joinedcontext

The owner asked for an SDK and app builder "like Base44 or Lovable", with an option for Rust WASM (2026-10-10, T-3574). This report puts the three side by side as a person sees them, decides the Rust shape, records what the switch of Endpoints to Antares views means for the SDK, and names the tasks that close the gaps. Base44 and Lovable cells come from their public documentation read on 2026-10-10; joinedcontext cells cite a requirement, a file or a task. "unknown" means the documentation did not say.

## 1. Feature table

| Capability | Base44 | Lovable | joinedcontext |
|---|---|---|---|
| Data model from the prompt | yes: "The AI sets up your tables" ([data](https://docs.base44.com/Building-your-app/Managing-your-app-data.md)); schemas as JSON files in `base44/entities/` ([entities](https://docs.base44.com/developers/backend/resources/entities/overview.md)) | yes: describing what to track creates the tables ([Cloud](https://docs.lovable.dev/features/cloud.md)) | no: the builder derives `dataNeeds` from the published models of existing spaces and asks the person to confirm (AP-22); a new type is a DataModel Change by a person. Gap 4.1 |
| Auth and roles | sign-in plus two roles, Admin and User, and per-entity read, write and delete rules ([access](https://docs.base44.com/Setting-up-your-app/Managing-access.md)) | e-mail, phone, Google, Apple, Microsoft, SAML, guests ([auth](https://docs.lovable.dev/features/authentication.md)); roles unknown | every App is a Keycloak client (AP-111), its own roles held by groups (AP-90…AP-99, AP-118), each write decided by the gateway's Policies (AP-139) |
| Server functions | Deno TypeScript functions, `functions.invoke()` or their own HTTP address, secrets by `secrets.get()` ([functions](https://docs.base44.com/developers/backend/resources/backend-functions/overview.md)) | edge functions on Lovable Cloud ([Cloud](https://docs.lovable.dev/features/cloud.md)) | `functions/{name}.ts` in QuickJS with the caller's token (SDK-21); a Rust server part on the shared host for `kind: wasm` (AP-143, AP-148), written by hand today. Gap 4.2 |
| File storage | `UploadFile` built in, public storage ([built-in](https://docs.base44.com/Integrations/built-in-integrations.md)) | storage in Cloud ([Cloud](https://docs.lovable.dev/features/cloud.md)) | `jc:app/blob` under one prefix per App, `wasm` Apps only (AP-145); every App once AP-170 lands (T-3584) |
| Scheduled jobs | cron (five fields), intervals, once, and entity-triggered ([automations](https://docs.base44.com/developers/backend/resources/backend-functions/automations.md)) | described in chat, listed under Cloud → Jobs ([jobs](https://docs.lovable.dev/features/jobs.md)); syntax unknown | `spec.server.jobs[]` on `wasm` Apps, five-field cron in UTC, at most 10, at least 5 minutes apart (AP-154, platform `crates/jc-core/src/kinds/app.rs`); no trigger on an entity change |
| Integrations | built-ins without keys (`InvokeLLM`, `SendEmail`, `UploadFile`, image, video, speech) and custom ones from an OpenAPI file set up by an admin ([built-in](https://docs.base44.com/Integrations/built-in-integrations.md), [using](https://docs.base44.com/Integrations/Using-integrations.md)) | a connector catalogue, custom REST or MCP connectors ([integrations](https://docs.lovable.dev/integrations/introduction.md)); AI without a key, on workspace credits ([AI](https://docs.lovable.dev/features/ai.md)); transactional e-mail from a verified domain ([emails](https://docs.lovable.dev/features/custom-emails.md)) | no network from App code (AP-49); a server pod's egress by address only (AP-134). E-mail and AI as declared services (ADR-N-045, T-3583, T-3584); no third-party connector |
| Visual edit | Edit mode: select an element, set colour, type, spacing, Tailwind classes ([design](https://docs.base44.com/Building-your-app/Design.md)) | preview toolbar: select, edit text, annotate, comment ([toolbar](https://docs.lovable.dev/features/preview-toolbar.md)) | by prompt only, the editing agent over the run's files ([Architecture/20 §4.2](../Architecture/20-app-sdk.md#42-after-the-first-run-the-editing-agent)). Gap 4.3 |
| Code export, git sync | two-way GitHub sync on `main` ([GitHub](https://docs.base44.com/developers/app-code/local-development/github.md)) | two-way GitHub sync on one branch, export only ([GitHub](https://docs.lovable.dev/integrations/github.md)) | one forge repository per App, every pass a commit on the run's branch, a merge request to publish (AP-75…AP-77), and a private GitHub copy where the installation names an owner (AP-79) |
| Preview | the editor's preview URL with unpublished changes ([preview](https://docs.base44.com/api-reference/get-preview-url.md)) | the editor's preview ([toolbar](https://docs.lovable.dev/features/preview-toolbar.md)) | one sandboxed document in a frame, requests answered by the host page for the run's Endpoints only (SDK-16, SDK-18), its tests run before publication is offered (SDK-38) |
| Publish, custom domain | custom domain from the Starter plan ([domain](https://docs.base44.com/Setting-up-your-app/Setting-up-your-custom-domain.md)) | `xxx.lovable.app` or an own domain on a paid plan ([domain](https://docs.lovable.dev/features/custom-domain.md)) | `https://{name}.apps.{domain}/` only (AP-133); a generated App is never public (AP-42). Gap 4.4 |
| Versions, rollback | restore a checkpoint: code, function deployments and entity schemas ([checkpoint](https://docs.base44.com/api-reference/restore-checkpoint.md)) | every change a version; revert restores code and edge functions, not data ([history](https://docs.lovable.dev/features/projects/history.md)) | every build kept by digest and served by `status.build.digest` (AP-72, AP-74), every pass a commit (AP-76); no restore action. Gap 4.5 |

Where joinedcontext differs on purpose: an App never holds a key (AP-147, AP-167), never writes outside its Endpoint's Policies, and is never public when generated (AP-42). Base44 and Lovable hand an App its own secrets and a public URL.

## 2. Rust WASM: what the builder offers for server logic in Rust

Today the builder writes React and QuickJS functions and never a `kind: wasm` App (portal `src/agents/` holds no `wasm` shape). The platform under it is complete: the shared host, one schema and one prefix per App (ADR-N-044), the build lane's `wasm32-wasip2` step (AP-151) and `jc-app-sdk`.

Decided (worker-1, owner may override): the builder generates a `kind: wasm` App when the person asks for server-side state, a schedule or Rust, and stays on `ui` with functions otherwise. The shape is T-3575's default: a `template-wasm` beside `sdk/template-fullstack`, a React interface plus `server/`, a crate on `jc-app-sdk` with one route, one `jc:app/sql` table in `migrations/` and one test, and the builder edits both halves in the same run. It compiles in the build lane as AP-151 already says (`cargo test`, then `cargo build --release --target wasm32-wasip2`, offline and locked). Before publication, the run's test sandbox runs `cargo test` of `server/` beside the interface tests, on the `rust` runner image of AP-106, so a red Rust test holds publication like a red vitest (SDK-38). The preview answers the interface's `/api/*` from the SDK's stub and the run's fixtures; the component itself first runs on the host after publication, as a `project` App. The options were: a preview placement on the shared host with a throwaway schema per run (a schema, a role and a prefix created and dropped per run, for a preview the tests already cover), or JS functions only (no Rust). The first can follow when a person needs to try the server live before publishing.

## 3. The switch of Endpoints to Antares views

The SDK's data client reaches one address, `/api/endpoint/{slug}/ngsi-ld/v1`, on the App's own host (portal `sdk/src/grid/source.ts`, the allow-list in `sdk/src/sdk/client.ts`), and a component reaches the same Endpoint through `http://gateway/…`, which the host rewrites to the App's own slug (platform `crates/wasm-host/src/host.rs`, AP-147). When an Endpoint becomes an Antares view (`/x/views/{view}/ngsi-ld/v1`, T-3525), the slug path should stay the App's address and only what answers behind it change: the gateway or the edge maps the slug to its view. The SDK and `jc-app-sdk` then change nothing, every App published before the switch keeps working, and there is no dual path in the client. The task that follows the SDK (T-3576) should test that mapping rather than rewrite the client; recorded there.

## 4. Gaps worth closing

| Gap | Task |
|---|---|
| 4.1 A type the prompt needs and no space has: the builder proposes a DataModel and a space as a Change for a person to approve, then builds on it | T-3608 |
| 4.2 Server logic in Rust from the prompt | T-3575 (exists) |
| 4.3 Point at an element in the preview and say what to change; the edit is scoped to that element's source | T-3609 |
| 4.4 An App on a domain of the organization's own, with its certificate | T-3610 |
| 4.5 Restore an earlier build of an App in one action | T-3611 |
| E-mail, files, jobs and AI as declared services | T-3583, T-3584, T-3585, T-3586 (exist) |
| The SDK on Antares views | T-3576 (exists) |

Not filed: third-party connectors (a catalogue of REST or MCP integrations an App calls). An App reaches no network but its Endpoint (AP-49), and a connector is a Pipeline's job on this platform, so the data arrives in a space first. Revisit when a city asks for a write to an outside system from an App.

## Related

- [ADR-N-045](../Decisions/adr-n-045-platform-services-for-apps.md) — the services list that closes the e-mail, files, jobs and AI rows.
- [ADR-N-044](../Decisions/adr-n-044-server-wasm-apps-on-a-shared-host.md) — the shared host a generated Rust App runs on.
- [Architecture/20](../Architecture/20-app-sdk.md) — the SDK, the first run, the editing agent and the preview.
- [Requirements/apps.md](../Requirements/apps.md) — AP-42, AP-49 and AP-133, the rules that keep this platform different on purpose.
