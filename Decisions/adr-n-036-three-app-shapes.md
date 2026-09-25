---
sidebar_position: 37
title: "ADR-N-036: Three App Shapes, Each with a UI and a Complete Template"
---

# ADR-N-036: Three App Shapes, Each with a UI and a Complete Template

Date: 2026-09-25  
Status: Accepted  
Decision Makers: product owner (direction of 2026-09-24)

## 1. Context

The owner's direction of 2026-09-24: "have just UI, or UI + Node.js, or UI + Rust, and everything needs to be set up with all libraries, so the development is really fast for these applications … there is no application without a UI". The same day the owner added: "write these apps primarily with React and Rust, so they will not take RAM", "by default JavaScript serverless React", and "Node backends only when the owner asks for one".

Today `spec.class` is `static`, `service` or `fullstack` (AP-01):

- `static` is a React build on the App SDK, served by the Portal's static host, with optional functions in the QuickJS runtime (SDK-21).
- `fullstack` is the same UI with an axum server in a pod of its own (AP-105…AP-108).
- `service` is a pod with no UI. Nothing generates one, and no reference application is one.

The `static` template pins its libraries with ranges (`^9.4.0`), and the Rust server of a `fullstack` app is copied from the reference applications instead of a template. A generated app therefore starts from less than a person needs, and every build resolves ranges again.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | Each shape is an ordinary Vite project, plus an ordinary Node or Cargo project for its server. The template is the scaffold a developer would write by hand, completed once. |
| Technological consistency | **Full** | React on the App SDK is the one UI. Rust is the backend the platform itself is written in. Node is admitted as a shape only because the owner asked for it, and the generator never picks it on its own. |
| Security by design | **Full** | Every shape keeps its walls: the static host and the edge login for the UI (AP-26), and the forge lane, the Portal as the only image writer and the restricted pod for a server (AP-105…AP-108). No shape adds a credential. |
| Modular design | **Full** | A shape is a template, a runner image and a lane job. The reconciler differs only in the command it runs. |
| Resource economy | **Full** | The default shape has no pod and no idle memory. A server is Rust unless a person asks for Node. |

## 3. Decision

1. **Three shapes, each with a UI.** `spec.class` is one of:
   - `ui`: React on the App SDK, built by the lane and served by the static host, with optional serverless functions (SDK-21). This is today's `static` and the default.
   - `ui-rust`: the same UI plus an axum server in its own pod. This is today's `fullstack`.
   - `ui-node`: the same UI plus a Node.js 22 server in its own pod, built and walled like `ui-rust`.

   `service` is removed: validation refuses an App without a UI. For one release, `static` and `fullstack` are read as aliases of `ui` and `ui-rust`, and the Portal proposes one Change per project that rewrites them. The release after that refuses them.
2. **The shape follows the need, and says why.** The generator picks `ui` unless the request needs something only a server gives:
   - a database of the app's own;
   - scheduled or long-running work;
   - a write workflow of several steps;
   - computation too heavy for a function.

   It then picks `ui-rust`, and picks `ui-node` only when the person asks for Node. The run states the shape and the reason before its first build. The person may switch shapes until then.

   `ui-node` is declared and not built yet (owner, 2026-09-25, T-2723): no App on the installation asks for Node, and its runner instance would take up to 3 Gi on a node that is full. Until a person asks for one, validation refuses `ui-node` with a message naming `ui` and `ui-rust` (AP-124), and the generator offers `ui-rust` instead (AP-125).
3. **One complete template per shape, in the Portal release.** Every template carries, pinned to an exact version with its lockfile committed:
   - the SDK and its grid, map (maplibre), charts (echarts), forms (`EntityForm`), i18n and the typed endpoint client;
   - routing between pages;
   - an example of each.

   It carries its tests (vitest with testing-library; `cargo test` or `node --test` for the server) and a `README` with `pnpm dev`, `pnpm test` and `pnpm build`. A server template adds the `/me` call (AP-109), the endpoint client with the person's token, structured logs and a health route.
4. **Fast by construction.** Each shape's runner image holds the complete dependency cache of its template's lockfiles: the pnpm store for every shape, plus the Cargo registry for `ui-rust`. A build reaches no registry (AP-82). CI scaffolds a fresh app of each shape from its template and fails the job when:
   - the first offline build takes longer than 2 minutes;
   - a one-file rebuild takes longer than 30 seconds;
   - an entry of a template's lockfile is missing from its runner image's cache.
5. **Memory is part of done.** A `ui` app has no pod: "0, static". A `ui-rust` server is a static binary on an empty base and targets a memory limit of 64 Mi or less. The measured figure of each reference app is recorded with its task.

## 4. Alternatives Considered

- **Keep `service`.** An App is something a person opens. A backend with no UI is a Pipeline, a function or a platform component, and each of those already has its walls.
- **One template with optional server folders.** The build, the runner image and the reconciler differ per server language. One template per shape keeps each lockfile and each cache exact.
- **Node as the default server.** It costs more memory per pod than a Rust binary, and the owner asked for Rust first. Node stays a shape a person picks.

## 5. Consequences

- AP-01 names the three shapes. AP-124…AP-129 are new. AP-105…AP-108 speak of `ui-rust` and extend to `ui-node`. SDK-13 picks and states the shape. AP-08 and the `service` clauses of AP-94 and AP-116 are withdrawn.
- jc-core renames `AppClass` and reads the aliases. The Portal, jcctl and the reference manifests follow. Work: T-2723 (`ui-node`) and T-2724 (complete templates and the scaffold jobs).

## Related

- [Requirements/apps](../Requirements/apps.md) — AP-01, AP-105…AP-108 and AP-124…AP-129.
- [Requirements/app-sdk](../Requirements/app-sdk.md) — SDK-13, SDK-21.
- [ADR-N-028](adr-n-028-applications-build-on-the-forge.md) — the forge lane every shape builds on.
