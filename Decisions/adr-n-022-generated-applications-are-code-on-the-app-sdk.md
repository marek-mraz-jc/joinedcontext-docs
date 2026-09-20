---
sidebar_position: 23
title: "ADR-N-022: Generated Applications Are Code on the App SDK, Not a Specification for a Renderer"
---

# ADR-N-022: Generated Applications Are Code on the App SDK, Not a Specification for a Renderer

Date: 2026-09-14  
Status: Accepted  
Decision Makers: product owner

## 1. Context

The kit pass (AP-56…AP-60, Architecture/19 §1.2) builds a `static` application from one model call: the model writes `spec.json`, a prebuilt React bundle renders it with six views (stats, map, table, chart, detail, form). It reaches a preview in 9 seconds on the demo server, and every application it builds looks the same, because the model can only choose among those six views. The `index.html` escape hatch lets the model write a page of its own, but that page gets no data client, no form, no permission check and no platform component, so the model rewrites them from scratch with CDN libraries.

AP-23 already required generated code to use "the typed client produced from the endpoint's OpenAPI documents and the platform UI kit". That client and that kit were never built as a library. The kit pass skipped them: the model got a configuration format because there was nothing to write code against.

The owner's direction (2026-09-14): generated applications should work like Base44, where the agent builds as much of the application as possible on the first run and later instructions change real React files, not only a JSON configuration. The SDK comes first, with a ready, tested application (the main page, forms, filters, charts and chart libraries, and a backend of serverless JavaScript functions) so the agent only adds a few files and does it fast; the one-shot pack holds every file the model needs; TypeScript types come from the LinkML model with LinkML's own generator; the first run is a one-shot generation of the whole application, and after it an AI agent edits the files. Base44 and similar builders get their speed and quality from exactly that: the model writes free-form components against a fixed SDK for entities, identity and integrations, and never writes the plumbing.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | React 19, TypeScript, ES modules and import maps as browsers ship them; the SDK wraps the NGSI-LD API the endpoint already serves. |
| Technological consistency | **Full** | TypeScript and React in the SDK (ADR-N-001); the transpile step runs in the Portal's Rust process. |
| Security by design | **Full** | The SDK is the only data path and it knows one endpoint; the preview stays one sandboxed document with no session, and every read and write leaves through the host page (AP-50, AP-63). |
| Modular design | **Full** | One package, one API reference; a new capability is a new export, not a new view kind in a schema. |
| Multi-tenancy | **Full** | The endpoint and its Policy stay the grant (AP-04); the SDK carries no address and no credential of its own. |

## 3. Decision

1. **The App SDK.** The platform ships `@joinedcontext/sdk`, a TypeScript package built from `joinedcontext-portal/sdk/` with the Portal and at its version. It holds the data client of the application's endpoint (entities, temporal, schema, effective access), identity, React hooks, design tokens and chart themes, formatters, the schema's form fields, the basemap and map worker, and exports. A compact `API.md` beside the package is the reference the model reads. The components a context-data application needs (application shell, stat tiles, table, MapLibre map on the basemap route, charts, entity detail, the schema-grounded `EntityForm`, filters, export buttons) are not package internals: the owner amended this decision so they are source files of the template, copied into every application like shadcn components, which the model changes as freely as a page.
2. **Generated applications are code, starting from a complete template.** A `static` application is a Vite project that starts as `sdk/template/`: an application shell with an overview and one page per entity type (filter bar, table, map, chart, detail, edit form where writes are granted) that runs for any endpoint from its schema alone and is previewed the moment the run starts. `src/jc-types.ts` is rendered by Model Tools with LinkML's `gen-typescript` from the endpoint's projected LinkML. The template's chart cards use Apache ECharts and Recharts is bundled beside it (owner's choice: both); maps are MapLibre with deck.gl (ADR-N-011). The look lives in one `design-tokens.json` the SDK turns into CSS variables, chart themes and map colours, so changing that file re-themes the application. The template carries vitest tests for its pages and functions. Imports are limited to relative files, React, the chart and map libraries and the SDK entry points.
3. **Serverless functions.** An application's backend is `functions/{name}.ts` files with a plain request, context and response signature. They run in `jc-functions`, a Rust service embedding QuickJS: a fresh context per invocation, 64 MiB and 5 seconds, no network, file system, environment or secrets, and one host capability, the endpoint client, which calls the application's endpoint with the caller's token. The runtime holds no credential and no code; the Portal sends the functions with each call.
4. **First run: one shot with every file. After it: an editing agent.** The first run is one model call whose pack holds every template file, the SDK's API reference and type declarations, the types, data needs, access, samples and prompt, and which writes the whole application over the template: pages, functions and their tests. The reference profile runs it on `google/gemini-3.8-flash` with medium reasoning (AgentProfile `model.reasoningEffort`, AG-72). Every later instruction is handled by an agent loop in the Portal process with file tools (`list_files`, `read_file`, `edit_file`, `write_file`, `delete_file`, `check`, `call_function`, `preview_errors`, `finish`), bounded by the profile's step limit.
5. **The Portal previews code without a build service.** Each pass is transpiled in the Portal process (TypeScript and JSX to JavaScript), and the preview is one HTML document: an inline import map, the SDK runtime embedded in the Portal, the transpiled files as `data:` modules. The frame stays `sandbox="allow-scripts"` with no session; the SDK sends every read and every write to the host page, which performs it with the reviewer's session against the sandbox endpoint.
6. **Errors go back to the model.** In the first run a transpile error, a refused import or the first runtime error the preview reports is handed back once with file, line and message; the editing agent sees the same errors as results of its `check` and `preview_errors` tools. The last working preview stays.
7. **The spec pass retires.** `spec.json`, the kit renderer and the `index.html` escape hatch are deleted once the code pass reaches a preview on dev. Until then they keep serving runs.
8. **Publication builds and tests the same files.** CI runs the application's tests and builds the committed project with the SDK version the Portal pinned in its `package.json` (AP-11); the preview transpiler is a fast path, not a second source of truth.

## 4. Alternatives Considered

- **Keep `spec.json` and grow the view catalogue.** Every new screen shape is a schema change, a renderer change and a model instruction, and applications still look alike. Rejected by the owner.
- **An agent loop from the first message.** Slower to a first application than one call with the whole pack, because the agent reads before it writes; kept for the instructions after the first run, where small edits to known files are what it is good at.
- **Let the model write whole applications without an SDK** (the `index.html` escape hatch, or the OpenHands workspace for every app). The model rewrites data access, forms and maps each time: more output tokens per app, more places to get a security rule wrong, minutes instead of seconds. Kept only for `fullstack` applications that need a backend.
- **A build service with `pnpm install` and Vite per pass.** Correct but slow (tens of seconds per pass) and it needs a workspace with package-registry egress for a preview. Rejected for the preview; CI still runs the real build at publication.
- **A Node.js container, Deno or workerd per application for functions.** A container per application costs memory on a single node and minutes to start; Deno and workerd are strong sandboxes but add a runtime component with its own configuration and upgrade path. QuickJS embedded in one Rust service gives a per-call isolate with hard memory and time limits and nothing to deploy per application; the plain handler signature keeps a later move to workerd open without rewriting functions.
- **Transpile in the browser** (esbuild-wasm or sucrase inside the frame). Adds megabytes to every preview and moves error reporting into the untrusted frame. Rejected in favour of the Portal process.

## 5. Consequences

- AP-56, AP-58, AP-61, AP-63, AP-64 and AP-65 are amended to name the SDK and the code pass; AP-60 hands later instructions to the editing agent; the SDK family (SDK-01…SDK-26) holds the new contract. Architecture/20 is the owning chapter.
- The bridge of AP-63 carries reads as well as writes, and the writes it accepts are the operations of the run's confirmed data needs, not only the form's two.
- The preview no longer inlines rows: filters, paging and forms work live against the sandbox endpoint with the reviewer's grants.
- The Portal image gains a TypeScript transpiler crate and the SDK runtime with React, ECharts, Recharts, MapLibre and deck.gl; `kit/` becomes `sdk/`.
- A new platform component, `jc-functions` (Rust, QuickJS), reachable from the Portal only; an application's functions reach data only through its endpoint with the caller's grants, so the server side adds compute, not authority. 16 §11's "no server-side code for static apps" is amended accordingly.
- Model Tools gains a `typescript` artifact; the Portal asks it for `jc-types.ts` at the start of every run.
- The first preview is the template, within seconds; the model's first run replaces it within the 60-second target.
- Where CI resolves `@joinedcontext/sdk` for a published build (a public registry or the organization forge's package registry) is open and needs the owner.

## Related

- [Architecture/20-app-sdk](../Architecture/20-app-sdk.md) — the SDK, the generated project, the code pass and the preview.
- [Requirements/app-sdk](../Requirements/app-sdk.md) — SDK-01…SDK-26.
- [Architecture/19-agent-runner §1.2](../Architecture/19-agent-runner.md#12-the-kit-pass-a-static-application-in-one-model-call) — the spec pass this decision retires.
- [Architecture/16-apps-on-demand](../Architecture/16-apps-on-demand.md) — what an application is and how it is published.
- [ADR-N-020](adr-n-020-agent-runner-and-credential-proxy.md) — the credential-free proxy the model call still goes through.
