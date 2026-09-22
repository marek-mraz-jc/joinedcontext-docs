---
sidebar_position: 12
title: "Apps on Demand"
---

# Apps on Demand

Family **AP** (AP-01…AP-86). Owning chapters: [16-apps-on-demand.md](../Architecture/16-apps-on-demand.md) and [19-agent-runner.md](../Architecture/19-agent-runner.md). Verified by: [03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md).

Requirement family **AP-01…AP-86** for AI-generated, purpose-built applications that consume context data through a dedicated, least-privilege Endpoint. Architecture in [Architecture/16-apps-on-demand](../Architecture/16-apps-on-demand.md) and [Architecture/19-agent-runner](../Architecture/19-agent-runner.md).

## 1. Manifest and source

- **AP-01** — An app MUST be declared as `kind: App` at `projects/{p}/apps/{name}/app.yaml` with `spec.kind` ∈ {`static`, `service`, `fullstack`}, `spec.source`, `spec.build`, `spec.visibility`, `spec.dataNeeds[]`, `spec.limits`, and a language-map `metadata.title`.
- **AP-02** — App source code MUST live in the org repository (beside the manifest) or in a repository of the same forge referenced by `spec.source.git`; sources outside the organization's forge MUST NOT be deployable.
- **AP-03** — Generated apps MUST carry `joinedcontext.com/generated-by` (agent identity, AG-17) and `joinedcontext.com/prompt-digest`; the prompt MUST be stored as `apps/{name}/PROMPT.md` in the same commit.

## 2. Least-privilege data access

- **AP-04** — An app MUST access context data exclusively through one Endpoint rendered by the reconciler from `spec.dataNeeds`; the app manifest MUST NOT reference an existing endpoint of another owner, the broker, the database or Portal API management routes.
- **AP-05** — `dataNeeds[]` items MUST declare `contextSpaceRef`, `types`, `attrs`, `operations` (CIM 009 operation names, R8) and MAY declare `q`, `scopeQ`, `geoQ`, `temporalQ` constraints and `representations`; the reconciler MUST render one `Policy` per item and one `Endpoint` (`app-{name}`) whose `enabledRepresentations` is the union of the items' representations.
- **AP-06** — CI MUST verify `dataNeeds ⊆ grants of the requesting user` (CC-60) and MUST fail the change otherwise; an app can never hold more than the person who published it.
- **AP-07** — Static apps MUST act with the end user's own token (OIDC public client with PKCE, audience bound to the app endpoint, RFC 8707); the effective grant is the intersection of the user's grants and the endpoint's grants (GW10).
- **AP-08** — Service apps MUST use a dedicated Keycloak service account whose token audience is the app endpoint only; the account MUST have no other grants.
- **AP-09** — Any `dataNeeds` item with a write operation MUST be red lane, MUST target types owned by the same project, and MUST be shown in the review as "this app can change X".
- **AP-10** — Widening `dataNeeds` after publication MUST be at least yellow lane; going `public` or adding writes MUST be red lane; narrowing MAY be green.

## 3. Build and supply chain

- **AP-11** — The build lane (AP-80) MUST build apps from source (no prebuilt bundles or images accepted), produce an SBOM, run dependency and secret scanning, and fail on any referenced network host other than the app's own endpoint and the OIDC issuer.
- **AP-12** — Static builds MUST be served with Subresource Integrity and a CSP whose `connect-src` is limited to `'self'` (the platform host) and whose `frame-ancestors` defaults to `'none'`; the Portal MAY relax `frame-ancestors` for embedding when `spec.embeddable: true`.
- **AP-13** — Service app images MUST be signed and pinned by digest in the rendered Deployment; `latest` tags MUST be rejected in CI.
- **AP-13a** — The digest the reconciler deploys MUST be `App.status.build` (`digest`, `commit`, `sdkVersion`, `builtAt`), written back by the build lane in the commit that publishes the artifact; an App without it MUST render no pod, and the `joinedcontext.com/image` and `joinedcontext.com/module` annotations MUST be refused with `400` on every write door and on import, so a hand-typed digest never reaches the host (AP-13, AP-18, AP-72, AP-73).

## 4. Runtime and isolation

- **AP-14** — Static apps MUST be served under `https://{host}/apps/{name}/` by the Portal static host through APISIX; no separate hostname is required.
- **AP-14a** [S] — An App name MUST be unique across the organization, not only inside its project: `/apps/{name}/` and the pod `app-{name}` are one address each. `jcctl validate` and every write door (propose, import) MUST refuse a second project's App of a name another project already declares, naming both projects, so the edge never has to choose whose route or visibility wins (AP-14, AP-26, PF-50).
- **AP-15** — Service apps MUST run in the instance namespace with default-deny NetworkPolicies allowing egress only to APISIX and the OIDC issuer, with resource requests/limits from `spec.limits` and the platform's restricted Pod Security Standard.
- **AP-16** — Apps MUST NOT receive long-lived secrets; `secretRef` is not permitted in `kind: App`. Apps needing external data MUST declare a Pipeline that brings it into a space.
- **AP-17** — The gateway MUST label app traffic with the app name; per-app rate limits (`spec.limits.requestsPerMinute`, `maxFileRows`) MUST be enforced on the app endpoint independently of the user's other endpoints.

## 5. Lifecycle and preview

- **AP-18** — Lifecycle states MUST be `draft → preview → published → retired`; only `published` apps are reachable by their `visibility` audience.
- **AP-19** — `preview` MUST bind the app to a sandbox space (CC-67) seeded per the blueprint (synthetic data by default; copying real data into a sandbox MUST require the space owner's approval) and MUST be reachable only by the author and reviewers through a sandboxed iframe in the Portal.
- **AP-20** — Publishing MUST be a merge request that flips the state and binds the endpoint to the real space; the lane follows AP-09/AP-10 and `visibility`.
- **AP-21** — `retired` MUST remove the route and the endpoint through the explicit-deletion path (CC-19); the source remains in the repository.

## 6. Generation by agents

- **AP-22** [A] — The `app-from-prompt` blueprint MUST derive `dataNeeds` from `describe_schema` results and present them to the requesting user for confirmation before any code is generated; the confirmed list is the grant, not the prompt.
- **AP-23** [A] — Generated code MUST use the typed client produced from the endpoint's OpenAPI documents and the platform UI kit (theme tokens, map components, i18n bundles); hand-written fetch calls to other hosts MUST fail AP-11. Generated code MUST contain no login, session or token-handling code: the user arrives in `X-Userinfo` and the endpoint is called with `X-Access-Token`, both set by the edge (AP-26, AP-28); an OIDC library or a login route in the app MUST fail AP-11.
- **AP-24** [A][H] — Every iteration between user and agent on a preview MUST be a commit on the app's branch; publishing squashes nothing and the review shows the full history and the final `dataNeeds` diff.

## 7. Full-stack apps and login front

- **AP-25** — `spec.kind: fullstack` MUST denote one OCI image containing a Rust (`axum`) backend that serves the React build and the app's server-side logic; it MUST be the default kind produced by the `app-from-prompt` blueprint.
- **AP-26** [S] — Every app route `/apps/{name}/*` (`static`, `service` and `fullstack` alike) and the shared `/apps/*` surface MUST carry the APISIX `openid-connect` plugin in session mode as the only login front (ADR-N-019); no app pod carries a login sidecar. A `service`/`fullstack` app container MUST listen on port 8080 of its pod and MUST be reachable from APISIX only (NetworkPolicy).
- **AP-27** [S] — The login client MUST be the one confidential OIDC client `edge` of the organization's Keycloak realm, shared by the Portal routes and every app route; its tokens MUST be signed RS256 by per-client override (the realm default stays ES256, T-0252) and its secret MUST reach APISIX only as an environment variable from a Kubernetes Secret. The reconciler MUST NOT create per-app clients or secrets.
- **AP-28** — The edge MUST forward the user's access token as `X-Access-Token` and the userinfo as `X-Userinfo` to the app, and MUST strip both from every client request first; the app MUST call its endpoint with that token so the effective grant is the intersection of user and endpoint grants (GW10). For `visibility: public` the route MUST use `unauth_action: pass`, anonymous requests reach the app without the headers, and the app MUST call the endpoint anonymously.
- **AP-29** [S] — The session cookie of an app route MUST be scoped to `/apps/{name}/` with `Secure`, `HttpOnly`, `SameSite=Lax`; `/apps/{name}/logout` MUST end the edge session and the Keycloak session (front-channel), and the cookie lifetime MUST NOT exceed the realm's SSO idle time.

## 8. Autonomous build

- **AP-30** [A] — The Agent Runner `builder` profile MUST carry out the whole build loop (scaffold, implement, build, test, commit, CI, preview deployment, smoke test, repair) without human action other than the `dataNeeds` confirmation (AP-22) and the lane approvals of AP-20.
- **AP-31** [A][S] — The builder MUST work in an ephemeral workspace bound to the app's sandbox space only; its internet access MUST pass through the platform egress proxy with an allow-list of package registries and documentation hosts, logged per agent identity (AG-26).
- **AP-32** [A] — The builder MUST commit only under `apps/{name}/` on the app's branch; CI (AP-11…AP-13) MUST gate every preview deployment; the builder MUST stop at the step limit of AG-25 and hand the last failing log to the user.
- **AP-33** [A] — Green-lane publications (non-public, read-only, own project) MAY be merged by the builder after CI passes; yellow and red lanes MUST wait for the human approval of AP-20.

## 9. Reference apps

- **AP-34** — The platform MUST ship two reference apps, `hsl-transport` and `air-quality`, declared as `spec.kind: fullstack` with their manifest and source under `apps/{name}/` in the `joinedcontext-portal` repository (AP-01).
- **AP-35** — A reference app MUST carry neither `joinedcontext.com/generated-by` nor `joinedcontext.com/prompt-digest`, because its source is written by hand and not by an agent (AP-03).
- **AP-36** — Each reference app crate MUST be a member of the Portal repository's cargo workspace, so the existing format, lint and test lanes cover it without a new CI job.
- **AP-37** — A reference app MUST NOT depend on the Portal library or on any platform-internal address, reaching context data only through the endpoint URL it is given at runtime (AP-04).
- **AP-38** — `hsl-transport` MUST declare `visibility: public` and read-only `dataNeeds` over the `transport` space, so its sidecar passes anonymous requests through (AP-28).
- **AP-39** — `air-quality` MUST declare `visibility: project` and exactly one write operation, `updateAttrs` on the `stewardNote` attribute, which places its publication in the red lane (AP-09, AP-20).
- **AP-40** [S] — A reference app MUST answer HTTP 401 to a write request that carries no `X-Access-Token` and never retry that request anonymously (AP-28, GW10).
- **AP-41** — Live updates in a reference app MUST be produced by the app backend polling its own endpoint and re-emitting Server-Sent Events at `{JC_BASE_PATH}api/stream`, because an Endpoint offers no streaming surface (EP-01).

## 10. Applications on Demand Security and Deployment Invariants

- **AP-42** — An application generated by an agent MUST have `spec.visibility` of `project` or `organization`; `public` MUST be refused for a generated application.
- **AP-43** — A generated application MUST be reachable only at `https://{host}/apps/{name}/` behind the platform edge, and the edge route MUST use `unauth_action: auth` so an anonymous browser is sent to Keycloak before the application answers.
- **AP-44** — The generation request MUST be validated on the server: an application MAY read one to five endpoints of the project (`endpointNames`, the first one the run's primary endpoint), each data need MUST belong to the first listed endpoint whose `contextSpaceRef` is the need's context space (the primary endpoint when none is), the confirmed data needs MUST be a subset of what their endpoints publish and of the requesting user's own grants (AP-06), and the request MUST be rejected with every violation named at once.
- **AP-45** — A generated application MUST declare only `queryEntity`, `retrieveEntity`, and `queryTemporal` operations unless the user explicitly asks for a write, which MUST make the change red lane (AP-09).

## 11. Agent-Generated Source, Edge Routing, and Preview Isolation

- **AP-46** — The run MUST write only under `projects/{p}/apps/{name}/` on its own branch, and the prompt MUST be committed as `PROMPT.md` in the same tree (AP-03).
- **AP-47** — A generated `fullstack` application MUST be a Rust `axum` backend serving an embedded React build, modelled on the reference applications, and MUST contain no login, session, or token-handling code (ADR-N-019, AP-23).
- **AP-48** — A generated `static` application MUST be a React build served by the Portal static host under the same edge login, and MUST call only its own endpoint.
- **AP-49** — The generated code MUST reach data only through `/api/endpoint/{slug}/…` with the user's forwarded token, and CI MUST fail any other network host (AP-11).
- **AP-50** — The preview MUST be reachable by the initiating user and reviewers only, and MUST be framed with `sandbox="allow-scripts"` without `allow-same-origin`.

## 12. Application Run Lifecycle, Conversation, and Governance

- **AP-51** — The Applications section MUST show the run's live conversation, its questions, its commits, its build and test results, and its preview link.
- **AP-52** — A run that produced commits MUST leave them in the forge whatever its outcome, so a failed generation is inspectable and resumable.
- **AP-53** — Publication MUST follow the existing lane rules (AP-10, AP-20); the builder MUST NOT approve its own merge request.
- **AP-54** — An installation without a builder `AgentProfile` or without model credentials MUST hide the generator and say what is missing, never offer a control that cannot work.
- **AP-55** [P] — From the confirmed data needs to a reachable preview, a generation of the reference size MUST complete within 10 minutes on the reference installation, and the Portal MUST show progress within 5 seconds of the request.

## 13. The Code Pass

- **AP-56** — A `static` application requested from the generator MUST be code the model writes against the App SDK (`@joinedcontext/sdk`, SDK-01) in a Vite project the Portal transpiles and previews (ADR-N-022); the `spec.json` kit pass MAY keep serving runs only until the code pass reaches a preview on the reference installation, and MUST then be removed (AP-48, AP-49).
- **AP-57** [P] — The first preview of a kit application MUST be a generated version, never the template, reachable within 40 seconds of the request on the reference installation from one model call, and the Portal MUST show the run's progress within 5 seconds (AP-55).
- **AP-58** [A] — The first run MUST hand the model the SDK's `API.md`, the template application, the confirmed data needs, the endpoint's `jc-types.ts`, schema and effective access and five served entities per type (SDK-13), and the Portal MUST apply model output only to the files SDK-11 allows; output naming any other path MUST be refused and reported as a run event (AG-39, AP-46).
- **AP-59** [A] — An application the Portal cannot transpile or the preview cannot run MUST be handed back to the model once with the errors; a second failure MUST end the pass with the errors on the run's conversation and in the frame's building state, never with a blank preview, the template or the version that failed (SDK-14).
- **AP-60** [H] — Every instruction a person sends on a `static` run after its first run MUST be handled by the editing agent of SDK-20 over the current files and the preview MUST reload with the result; the conversation MUST carry the agent's final message as an assistant turn and its tool calls as activity lines (AG-45, AP-51).

## 14. Forms that write

- **AP-61** [A] — The SDK's `EntityForm` MUST be grounded in the LinkML DataModel of the space its endpoint serves: one input per named attribute, typed by the slot's `range` (a number input for `integer`/`float` with the slot's `minimum_value` and `maximum_value` as bounds, a select over the enum's `permissible_values`, `pattern` as the input's pattern, a required slot required), so the form never asks for what the model does not define and never sends what it would refuse; the SDK MUST ship this as one `<EntityForm>` bound to the endpoint's JSON Schema, and the pass MUST hand the model that schema with the pack (AP-58) so generated code names only attributes the schema declares (SDK-08, SDK-10).
- **AP-62** — A save in `EntityForm` MUST be one write through the app's own Endpoint and nothing else: `PATCH /api/endpoint/{slug}/ngsi-ld/v1/entities/{id}/attrs` for a picked entity, `POST /api/endpoint/{slug}/ngsi-ld/v1/entities` for a new one, carrying the person's own identity (the platform session of the origin a published `static` app is served from, or the `X-Access-Token` the edge sets for a `fullstack` app, AP-28) and evaluated by the gateway's write rules in full (GW16); a write the Policy does not grant MUST come back as `403` with an RFC 7807 problem the form shows beside its inputs, and neither a refusal nor a success MUST reload the page. An application MUST NOT reach a broker, a database or any route but its endpoint's to write (AP-07, AP-42).
- **AP-63** — In the sandboxed preview (AP-50) the frame holds no session and no token; every read and write of the SDK MUST leave the frame as a message to the page that framed it, and only that page MUST perform it, with the reviewer's session, against the endpoints of the app's sandbox (AP-19) and post the answer back. The bridge MUST accept only the slugs of the endpoints the preview was built for, only reads and the write operations of the run's confirmed data needs, only from the frame it created, and MUST refuse everything else without forwarding it; a token or a cookie MUST never be inlined into the preview document (SDK-18).

## 15. Applications vs Dashboards, SDK Capabilities, Artifacts and Basemaps

- **AP-64** [H][P] — An Application MUST be generated code (on the App SDK for `static`, in the workspace for `fullstack`) served by the Portal behind the edge login for one purpose over one Endpoint; a Dashboard MUST be a declarative manifest of layers over Endpoint data rendered by the Portal (Architecture/10), optionally routed to an addon (Grafana). The Applications section MUST NOT generate Dashboard manifests and the Dashboard surface MUST NOT generate an application; both MAY exist for the same Endpoint.
- **AP-65** [A][S] — The SDK MUST declare what it offers (components, hooks, options, export formats, basemap) in `API.md`, and the pass MUST supply that file to the model in the pack (AP-58) so generated code uses only what the SDK exports; a generated application MUST NOT use a CDN, a remote module, or a package manager at runtime, and the SDK runtime MUST be served from the platform origin or embedded in the preview document (AP-49, SDK-12, SDK-16).
- **AP-66** [H] — A generated application MAY produce in-browser client-side artifacts (PDF, CSV, GeoJSON, PNG of a chart) constructed exclusively from rows and entities already rendered in the view without contacting a new network host or uploading data; every artifact MUST be stamped with the Endpoint name, filter state, and UTC timestamp of export, and a PDF MUST carry the basemap attribution.
- **AP-67** [S] — Basemap tiles and styles for application map views MUST be served exclusively through the Portal routes `GET /api/v1/projects/{project}/basemap/{style}/{z}/{x}/{y}.{ext}` and `GET /api/v1/projects/{project}/basemap/{style}/style.json`, which need no session because a basemap carries none of the platform's data and the sandboxed preview holds no session (AP-63), and which answer any origin (`Access-Control-Allow-Origin: *`) but serve only the configured style, with a per-client rate cap, so they are not a general proxy; the SDK's map MUST take the style URL from the document the Portal serves and never name a tile host of its own; tile coordinates MUST be validated before forwarding upstream, upstream basemap URLs and API keys MUST be configured at the platform level (keys referenced via `secretRef` and never sent to the browser), responses MUST be cached to disk with a bounded size and TTL, attribution MUST be mandatory, and an unconfigured basemap MUST return HTTP 404 problem details while the map view renders data points over a plain background with a notice.

## 16. Application Record Durability, Resumption and Draft Governance

- **AP-68** [P][S] — Calling `POST /api/v1/projects/{project}/agent-runs` MUST create the draft application and the run that builds it as one record in the Portal's database (a single insert, so neither exists without the other), recording the initiating user, the time, the prompt, the endpoint and the confirmed data needs; the `App` manifest reaches Git only through publish (AP-20). While a run for the same application name is live, a second request MUST be refused with `409 Conflict`; once that run has ended, a new run MUST continue the application as its next version.
- **AP-69** [H][S] — The Portal route `/projects/{project}/apps/{name}` MUST display the application along with its active agent run; opening the route MUST replay the conversation history from sequence 0 and resume live Server-Sent Events via `Last-Event-ID` (AG-45) without disclosing or delivering any run ticket or platform credential to the browser.
- **AP-70** [H][S] — Draft applications MUST be visible in the project application catalog annotated with their active run state (`building`, `needs you`, `failed`, `ready to publish`), but MUST NOT be served at `/apps/{name}/` or embedded externally until transitioned to `published` (AP-18); previewing a draft application MUST be permitted strictly within the sandboxed run preview frame (AP-50, AP-63).
- **AP-71** [H] — An application's run page MUST link the application's source in Git: `sourceUrl` on the run is the forge's public web address of the run's `pathPrefix` on its branch (`JC_GITEA_PUBLIC_URL`, never a cluster-internal name), and the published application's own `status.sourceUrl` once its Change is merged. After Publish the run carries `changeId`, and the page shows the Change with Approve in place for a person the approval rules allow (CC-34, PF-50, PF-58), so an administrator publishes an application without leaving it; a red-lane Change links to its approval page for the typed confirmation (CC-39).
- **AP-72** [S] — The static host MUST serve the artifact named by `App.status.build.digest` and nothing else; a digest the artifact store does not hold MUST set a red `Ready` condition on the App while the previous build keeps serving, never a pod or a bundle from a source other than CI (AP-11, AP-13a).
- **AP-73** [S] — The build lane MUST run as a `ServiceAccount` whose only configuration right is `propose` on `App` constrained to `status.build`, the one writer of that field; a change by any other principal that sets or alters `status.build`, through any door, MUST be refused as the platform-computed `status` is (MF-25, PF-49).
- **AP-74** — Until the artifact-store uploader exists (Architecture/17 §2 `apps/` prefix), the build lane MUST publish into the static host's build directory keyed by the commit and MUST write the same `status.build` shape, so the manifest contract does not change when the store arrives (AP-13a).
  > Note: The in-cluster build lane of AP-80 closes this interim: the lane uploads to the store's `apps/` prefix. Until T-2592 and T-2593 land, no lane exists on the reference installation at all, and a `static` App without a bundle baked into the Portal image answers `404` (ADR-N-026 §1).
- **AP-75** [S] — A `static` application the Portal generates MUST have its own repository on the organization's forge, named `{project}_{app}` in the organization of the configuration repository (the `_` no project or application name can hold, so two projects never share one), private, created by the Portal with its forge token on the application's first commit and never recreated, renamed or overwritten when it already exists; the repository MUST hold the whole application at its root (every file of the template the run started from, every file the run wrote, and a `README.md` saying how to install, test and run it).
- **AP-76** — Every pass of a `static` run MUST be one commit on the run's branch `agent/app-{app}/{runId}` of the application's repository, branched from its default branch, and the run's first commit MUST make the branch hold exactly the run's files and its `README.md`, deleting a file of an earlier version the run no longer holds, so every run branch is the whole application at that pass.
- **AP-77** [S] — Publishing a `static` run MUST open, or reuse when one is open, a merge request from the run's branch into the default branch of the application's repository, and MUST propose the `App` manifest with `spec.source.git` `{url, ref}`: `url` the repository's `https` clone address on the forge's public URL, `ref` the commit the run's branch points at, so the Change a reviewer approves names one commit (AP-02, AP-10). Approving that Change MUST merge the application's merge request with a merge commit, only while its head is still that commit, and MUST then mark the run `published`; a merge the forge refuses MUST leave the approved Change merged and MUST be said on the run.
- **AP-78** [H] — A `static` run's `sourceUrl` MUST be the forge's public web address of the application's repository at the run's branch (AP-71), and a person the forge's team mapping lets read the organization MAY clone that repository with their own forge credentials (PF-79); the Portal's forge token MUST be the only credential that creates or writes it.
- **AP-79** [S] — When the installation names a GitHub owner for application repositories, every repository of AP-75 MUST also exist as a regular private repository `{owner}/{project}_{app}` on GitHub, created by the Portal on the application's first commit and never recreated or overwritten when it exists, and kept current by the forge's push mirror on every commit, so the GitHub copy holds the whole application and every branch the forge holds. The forge stays the repository the runs commit to, the merge request of AP-77 is opened and merged, and the `App` manifest names; GitHub is a copy. The GitHub credential MUST reach the Portal by `secretRef` only, and MUST NOT be written into a manifest, a log, a run event or the repository. A copy the Portal could not set up MUST be said on the run and MUST NOT fail the pass, and the run MUST link the GitHub copy beside the forge's (`mirrorUrl`, AP-71).

## 17. The Build Lane in the Cluster and the Three Shapes of a Static Application

Decided in [ADR-N-026](../Decisions/adr-n-026-the-build-lane-runs-in-the-cluster.md).

- **AP-80** [S] — The build lane of a `static` App MUST be a Kubernetes `Job` the Portal reconciler starts in the apps namespace whenever a `published` App's `spec.source.git.ref` names a commit the artifact store holds no build of, or a person asks for a rebuild; at most one build Job MUST run per App, and a newer `ref` MUST wait for the running one rather than cancel it. The Job MUST clone `spec.source.git.url` at `ref`, run the interface and function tests, build, compute `integrity.json` (AP-12), upload the bundle under `apps/{org}/{project}/{app}/{digest}/` and propose `status.build` as the lane's `ServiceAccount` (AP-73); a failing step MUST put its log tail on the App's `Ready` condition while the previous build keeps serving (AP-72).
- **AP-81** [S] — The build Job MUST run with no Kubernetes service-account token mounted, under the restricted Pod Security Standard, with egress to the forge and the artifact store only, a wall-clock and a memory limit, and no credential other than a read-only clone token scoped to the one repository and the store's write key for its own prefix.
- **AP-82** — The builder image MUST be tagged, signed and pinned by digest with the Portal release it belongs to, and MUST bake that release's SDK tarball and the template's pnpm store, so the lane installs with `pnpm install --offline --frozen-lockfile` and reaches no package registry.
- **AP-83** — A `static` App whose `spec.build` names no toolchain (`build: {}`) MUST be built by no build step: the repository tree at `ref` is the bundle, with `index.html` at its root, and the lane MUST compute its `integrity.json` and upload it as it is. `service` and `fullstack` Apps MUST still name at least one toolchain.
- **AP-84** [S] — The static host MUST serve `POST /apps/{name}/api/functions/{fn}` for a published App whose served build holds `functions.js`, invoking `jc-functions` with the functions of that build, the request and the person's `X-Access-Token` from the edge (SDK-23); a function the served build does not hold MUST answer `404`, and no file of the repository that was not built MUST ever run.
- **AP-85** — Approving the Change that publishes a `static` run MUST merge the run's branch into the application repository's default branch before the lane builds, and the lane MUST build that default branch at the merge commit (AP-77); an App whose repository's default branch holds only `README.md` MUST be shown as never published.
- **AP-86** [H] — The application catalog and the App page MUST show the build state: `building`, `build failed` with the log tail, or `served <commit>`; **Open** MUST be offered only while a build is served (AP-70, AP-72).

## Traceability

| Requirements | Section | Architecture | Tests |
|---|---|---|---|
| AP-01…AP-03 | Manifest and source | [16-apps-on-demand.md](../Architecture/16-apps-on-demand.md) | [03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| AP-04…AP-10 | Least-privilege data access | [16-apps-on-demand.md](../Architecture/16-apps-on-demand.md) | [03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| AP-11…AP-13 | Build and supply chain | [16-apps-on-demand.md](../Architecture/16-apps-on-demand.md) | [03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| AP-14…AP-17 | Runtime and isolation | [16-apps-on-demand.md](../Architecture/16-apps-on-demand.md) | [03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| AP-18…AP-21 | Lifecycle and preview | [16-apps-on-demand.md](../Architecture/16-apps-on-demand.md) | [03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| AP-22…AP-24 | Generation by agents | [16-apps-on-demand.md](../Architecture/16-apps-on-demand.md) | [03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| AP-25…AP-29 | Full-stack apps and login front | [16-apps-on-demand.md §5](../Architecture/16-apps-on-demand.md#5-login-in-front-of-the-portal-and-every-app-apisix-openid-connect) | [06-security-tests.md](../Testing/06-security-tests.md) |
| AP-30…AP-33 | Autonomous build | [16-apps-on-demand.md §4](../Architecture/16-apps-on-demand.md#4-autonomous-build-the-builder-agent) | [03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| AP-34…AP-41 | Reference apps | [16-apps-on-demand.md §6](../Architecture/16-apps-on-demand.md#6-the-two-reference-apps) | [06-security-tests.md](../Testing/06-security-tests.md) |
| AP-42…AP-45 | Applications Security Invariants | [16-apps-on-demand.md](../Architecture/16-apps-on-demand.md) | [06-security-tests.md](../Testing/06-security-tests.md) |
| AP-46…AP-50 | Generated Source and Preview Isolation | [19-agent-runner.md](../Architecture/19-agent-runner.md) | [06-security-tests.md](../Testing/06-security-tests.md) |
| AP-51…AP-55 | Run Lifecycle and Governance | [19-agent-runner.md](../Architecture/19-agent-runner.md) | [03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| AP-56…AP-60 | The Code Pass | [19-agent-runner.md §1.2](../Architecture/19-agent-runner.md#12-the-kit-pass-a-static-application-in-one-model-call) | [03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| AP-61…AP-63 | Forms that write | [16-apps-on-demand.md §8](../Architecture/16-apps-on-demand.md#8-forms-that-write-through-the-endpoint) | [03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| AP-64…AP-67 | Applications, SDK, Artifacts & Basemaps | [16-apps-on-demand.md](../Architecture/16-apps-on-demand.md) | [03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| AP-68…AP-71 | Durability, Resumption & Draft Governance | [16-apps-on-demand.md](../Architecture/16-apps-on-demand.md) | [03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| AP-72…AP-79 | Source in git, one build by digest, one repository per application and its GitHub copy | [20-app-sdk.md#6-publication](../Architecture/20-app-sdk.md#6-publication) | [Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation](../Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation) |
| AP-80…AP-86 | The build lane in the cluster and the three shapes of a static application | [20-app-sdk.md#6-publication](../Architecture/20-app-sdk.md#6-publication), [ADR-N-026](../Decisions/adr-n-026-the-build-lane-runs-in-the-cluster.md) | [06-security-tests.md](../Testing/06-security-tests.md) |

## Related

- [app-sdk.md](app-sdk.md) — the package, the template and the runtime a generated application is built on.
- [agents.md](agents.md) — the run that generates an application and the proxy it works through.
- [Architecture/16-apps-on-demand.md](../Architecture/16-apps-on-demand.md) — how the platform builds, hosts and secures an application.
- [Architecture/19-agent-runner.md](../Architecture/19-agent-runner.md) — the runner, the workspace and the credential proxy behind a build.
- [Testing/03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) — the suites that prove these requirements.
