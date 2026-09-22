---
sidebar_position: 27
title: "ADR-N-026: The Build Lane Runs in the Cluster, and a Static Application May Have No Build Step"
---

# ADR-N-026: The Build Lane Runs in the Cluster, and a Static Application May Have No Build Step

Date: 2026-09-22  
Status: Superseded  
Superseded by: ADR-N-028, for decisions 1, 2, 4 and 8 (where the build runs, where the bundle is stored, the Job's walls and where the catalog reads the state); decisions 3, 5, 6 and 7 stand  
Decision Makers: product owner

## 1. Context

The owner's words (2026-09-22): "the applications does not work, there is no source code for applications", "each applications should have separate git repository", "there are different types just frontend with react ... html, frontend and serverless backend like deno serverless functions with frontend", "create these sample applications in demo dev cluster", "i cannot open any applications".

What the reference installation does today, measured on `dev` on 2026-09-22 after an edge login as `demo.steward@hel.fi`:

- `/apps/bbsk-ukazovatele/` answers `200`. It is the one bundle that exists, and it is baked into the Portal image: `joinedcontext-portal/Dockerfile` builds `apps/bbsk-ukazovatele/ui` in its `apps` stage into `/srv/apps` and sets `JC_PORTAL_APPS_DIR=/srv/apps`.
- `/apps/allerts/` and `/apps/citiy-bike-station/` answer `404 app '…' not found`, although their manifests in the configuration repository say `lifecycle: published`. Neither has `status.build`.
- Nothing in the cluster builds an application. There is no CI runner (no `act_runner`, Gitea Actions unused). The reconciler skips every `static` App (`src/apps/converge.rs`: "a static app is served by the Portal, not by a pod"). The artifact store has no uploader, so the interim of AP-74 is still in force.
- The static host has no functions route: `src/apps/static_host.rs` serves `GET /apps/{name}/` and `GET /apps/{name}/{*path}` and nothing else, so the published half of SDK-23 does not exist.
- The application repository `helsinki_map-alerts` holds only `README.md` on `main`. The whole application sits on its run branch `agent/app-map-alerts/…`, which nobody merged and nothing built.

The requirements already say what a build produces and who writes it down (AP-11, AP-12, AP-13a, AP-72, AP-73). They say "CI" without saying whose CI. On an installation whose forge is Gitea and whose application repositories are private there (AP-75, T-2468), GitHub CI cannot clone them, and no other CI exists. The missing piece is where the build runs.

## 2. Decision

**The build lane is a Kubernetes `Job` the Portal reconciler starts in the apps namespace. It clones the application's repository at the approved commit, builds it offline with a builder image of the Portal's own version, uploads the bundle to the artifact store and writes `App.status.build` through the Portal API. A `static` application comes in three shapes, told apart by `spec.build`.**

1. **When a build runs.** The reconciler starts a build when a `published` `static` App's `spec.source.git.ref` names a commit the artifact store holds no build of, and when a person asks for a rebuild. At most one build Job runs per App. A newer `ref` waits for the running Job and then builds, and the running one is not cancelled halfway through an upload.
2. **What the Job does.** The builder image `joinedcontext-app-builder`, tagged and signed with the Portal release and pinned by digest like every image (CC-35), clones `spec.source.git.url` at `ref` with a read-only forge token scoped to that one repository. It installs, runs the interface and function tests, builds, computes `integrity.json` (AP-12), uploads the bundle under `apps/{org}/{project}/{app}/{digest}/` (Architecture/17 §2), and proposes `status.build {digest, commit, sdkVersion, builtAt}` as the lane's `ServiceAccount` (AP-73). A failing step ends the Job with its log tail on the App's `Ready` condition, and the previous build keeps serving (AP-72).
3. **The SDK reaches the build offline.** The builder image bakes the SDK tarball and the template's pnpm store of the same Portal version, so `pnpm install --offline --frozen-lockfile` needs no registry. SDK-12 already forbids every package beyond the template's, so nothing else can be asked for. This answers the question T-0682 asked ("where CI installs the SDK").
4. **Untrusted code, contained.** An application's code is untrusted (T-1707), so the Job runs it with no Kubernetes token mounted, under the restricted Pod Security Standard, with egress to the forge and the artifact store only, a wall clock and a memory limit, and no platform credential beyond the clone token and the store's write key for its own prefix.
5. **Three shapes of a `static` application**, all `spec.kind: static`:
   - `build: { node: "22" }` is a Vite project: React on the SDK, the generator's output. The lane runs `pnpm build`.
   - `build: {}`, no toolchain named, is **no build step**: the repository tree is the bundle, `index.html` at its root, served as it is. The lane computes its `integrity.json`. The page reads its data with `fetch` on the same origin from the endpoint slug in `#jc-config`.
   - Either shape may hold `functions/*.ts`. The lane bundles them into `functions.js` (SDK-24), and the static host hands that bundle to `jc-functions` on `POST /apps/{name}/api/functions/{fn}` with the person's `X-Access-Token` (SDK-23, published half).
6. **Functions stay on `jc-functions`.** The runtime stays QuickJS (ADR-N-022). A function is plain TypeScript `(request, ctx) => response` with no Node or Deno API, so the same file runs in vitest, in Deno and in the platform. That is what the owner's "serverless backend like deno serverless functions" gets, without a second runtime to secure and operate.
7. **Publication merges, then builds.** Approving the Change that publishes a run merges the run's branch into the application repository's default branch (AP-77), and the lane then builds that default branch at the merge commit. A repository whose default branch holds only `README.md` is an application that was never published, and the catalog says so instead of offering to open it.
8. **The catalog shows the build.** An App reads `building`, `build failed` with the log tail, or `served <commit>`. **Open** appears only while a build is served (AP-70, AP-72).

## 3. Alternatives Considered

| Option | Why not |
|---|---|
| GitHub Actions in the application repository | The repositories are private on the installation's Gitea (AP-75). A GitHub mirror (AP-79) is optional and a copy, not the record, and an installation without GitHub would have no lane at all. |
| Gitea Actions with an `act_runner` in the cluster | A runner is a long-lived privileged daemon with its own registration secret, runs every repository's workflow file (the application's own code decides what runs), and adds a component to operate. A `Job` the reconciler starts runs one fixed command and nothing the repository wrote. |
| Build inside the Portal pod | The Portal holds the platform's credentials. Untrusted `pnpm build` beside them is the risk T-1707 names. |
| Keep baking bundles into the Portal image | One release per application change, and a generated application never reaches the image at all. That is the defect this ADR answers. |
| A Deno runtime for functions | A second sandbox to harden and a second set of limits. The owner's requirement is the programming model, which plain TypeScript on QuickJS already offers. |

## 4. What Changes

- **jc-core** (T-2590): `spec.build: {}` becomes valid for a `static` App, meaning no build step. It stays refused for `service` and `fullstack`, which always need a toolchain.
- **Deployment** (T-2592): the builder image, the apps namespace's build `ServiceAccount` and Role (create and watch Jobs only), the Job's NetworkPolicy (forge and artifact store), and the store's write key for the `apps/` prefix.
- **Portal** (T-2593, T-2594): the reconciler starts and watches the Job and surfaces its state on the App. The static host serves from the store and gains `POST /apps/{name}/api/functions/{fn}`. The catalog shows the build state.
- **Samples** (T-2596…T-2599): one application per shape, each in its own repository, seeded on `dev`.

## 5. Security Analysis

- The lane's `ServiceAccount` holds `propose` on `App`, constrained to `status.build`, and nothing else (AP-73). A digest the lane did not upload is not served (AP-72).
- The Job holds a clone token for one repository, read-only, and the store's write key for its own prefix. It has no Kubernetes API token, no platform database, no Keycloak client secret and no egress beyond the forge and the store.
- A functions call carries the person's access token to `jc-functions`, which reads only the application's endpoint with it (GW10). A published application's functions can never read more than the person calling them may.
- The functions route runs the functions of the build the host is serving, never a file of the repository that was not built.

## 6. Out of Scope

- `fullstack` Rust applications (`hsl-transport`, `air-quality`) keep their image build in the Portal repository's CI (§6 of Architecture/16).
- The App pod's NetworkPolicy admits APISIX from namespace `apisix` while `dev` runs it in `dev` (`reconciler.rs`). That defect has its own line in the defect log and its own fix.
- Application roles and who may open an application are T-2589's decision.

## 7. Requirements

The decision lands as AP-80…AP-86 in [Requirements/apps.md](../Requirements/apps.md), with AP-11, AP-74, SDK-17, SDK-23 and SDK-24 amended to name the lane.

## Related

- [ADR-N-022](adr-n-022-generated-applications-are-code-on-the-app-sdk.md) — why an application is code on the SDK, and why functions run in QuickJS.
- [Architecture/20-app-sdk.md §6](../Architecture/20-app-sdk.md#6-publication) — publication, the build lane and the functions route.
- [Architecture/17-artifact-store.md §2](../Architecture/17-artifact-store.md#2-layout-and-ownership) — the `apps/` prefix the lane writes.
- [Requirements/apps.md](../Requirements/apps.md) — AP-11, AP-13a, AP-72…AP-86.
