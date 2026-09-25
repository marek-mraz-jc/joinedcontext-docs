---
sidebar_position: 16
title: "Configuration as Code (CC)"
---

# Configuration as Code, Configuration Plane for Federated Digital Twins

Status: Draft
Date: 2026-08-16
Scope: The declarative configuration plane of a federated digital twin: the
versioned city repository, the reconciler, blueprints, the end-user
application, roles, and the MCP/automation surface. This layer configures
the platform that R1–R43 (access control), GW1–GW34 (gateway rules) and
I1–I4 (identity) secure; it does not redefine any of them.
Related: `access-control.md` (Part I R1–R43, Part II MIM0–MIM10),
`gateway-firewall.md`, `policy-firewall.md`,
ADR 001 (URN), ADR 004 (Scopes).

Family **CC** (CC-01…CC-84). Owning chapter: [Architecture/06-configuration-as-code.md](../Architecture/06-configuration-as-code.md). Verified by: [Testing/04-configuration-and-pipeline-tests.md](../Testing/04-configuration-and-pipeline-tests.md).

Keywords MUST / SHOULD / MAY per RFC 2119.

Consumer classes as in `access-control.md` Part II: **[H]** human through the
user application, **[P]** program through APIs/CLI/CI, **[A]** AI agent
through MCP. Every capability of this plane is tagged.

Vocabulary: *manifest*, one YAML file declaring one desired resource;
*city repository*, the Git repository holding all manifests of one city;
*reconciler* (`jcctl`), the component that converges live platform state
to the repository; *blueprint*, a parameterized template that expands to
one or more manifests; *flow*, a blueprint instance as shown to [H] users.

## 1. Architecture and source of truth

- **CC-01** — The context broker MUST remain a vanilla ETSI GS CIM 009
  NGSI-LD implementation. It MUST NOT read configuration files of this
  plane (no YAML/Git awareness), MUST NOT require vendor extensions for
  any capability of this document, and MUST remain independently
  upgradable and replaceable by any other compliant broker.
- **CC-02** — The city repository MUST be the single source of truth for
  all declarative platform configuration: context spaces/tenants,
  Context Source Registrations, subscriptions, pipeline configurations,
  data models (`@context`, JSON Schema), seed entities, and platform
  runtime settings. A configuration that is not in the repository is
  drift, never an alternative truth.
- **CC-03** — The reconciler MUST be the only component that writes
  configuration to the broker and pipeline runtime. The user application,
  MCP server, and CI MUST effect changes exclusively by writing to the
  repository (commit or merge request), never by calling the broker
  directly.
- **CC-04** — All reconciler traffic MUST pass through the gateway (R1)
  under its own service identity (I1–I4); the reconciler receives write
  grants through ordinary `Policy` entities, not gateway bypasses. Fail
  closed per R5 applies to it like any other client.
- **CC-05** — The infrastructure layer (cluster, broker/pipeline
  deployment, Helm/Terraform) and this configuration layer MUST stay
  separate: infrastructure tooling MUST NOT template NGSI-LD payloads,
  and manifests MUST NOT encode deployment topology.
- **CC-06** — Secrets (credentials, tokens, endpoint keys) MUST NOT be
  stored in the repository in plaintext. Manifests reference secrets by
  name; values live in a secret store or SOPS-encrypted files.
- **CC-07** — Live sensor observations and temporal history MUST NOT be
  stored in the repository. The repository declares structure (including
  seed entities); state flows through the broker. Consequently temporal
  data is NOT reproducible from Git and MUST be covered by ordinary
  database backup, explicitly out of scope of CC-49–CC-53 replay.

## 2. Repository and manifest model

- **CC-08** — The city repository MUST follow a fixed top-level layout,
  one directory per resource family: `spaces/`, `registrations/`,
  `subscriptions/`, `pipelines/`, `datamodels/`, `entities/seed/`,
  `blueprints/`, plus one platform settings file. Domain subdirectories
  (e.g. `subscriptions/parking/`) carry ownership (CC-41). Superseded by
  CC-85, layout 2: the organization repository and one repository per
  project (PF-85).
- **CC-09** — Every NGSI-LD manifest MUST use a thin envelope
  (`kind`, `metadata`, `spec`) where `spec` is the literal NGSI-LD
  payload rendered as YAML, no proprietary DSL, no renamed members. A
  manifest stripped of its envelope MUST be a valid CIM 009 payload.
- **CC-10** — Resource identifiers MUST be deterministic, derived from
  the manifest path and city namespace per the ADR 001 URN scheme
  (`urn:ngsi-ld:{Typ}:{Razidlo}:{Evidencia}:…`), so that re-applying a
  manifest updates the same resource. Random identifiers are banned in
  manifests (they break both idempotency and R34 prefix routing).
- **CC-11** — Pipeline configurations (Bento, specifically the MIT fork
  `warpstreamlabs/bento`; `redpanda-data/connect` is disqualified on
  licensing, see stack verdict S5) MUST be stored in their
  native format, unwrapped. The plane treats them as opaque versioned
  artifacts validated by the pipeline engine's own linter in CI.
- **CC-12** — Every manifest family MUST have a published JSON Schema
  (derived from the CIM 009 OpenAPI for NGSI-LD kinds; Smart Data Models
  for entity payloads). The schema dialect is **draft-07** (the dialect
  the form-generation layer is tested against, stack verdict S4). CI
  MUST reject manifests that fail schema validation before any merge.
- **CC-13** — Federation topology MUST be reviewable in Git: each city's
  `registrations/` declares what it exposes and which peers it registers;
  cross-city edges live in a dedicated federation repository or
  directory. CI MUST validate the declared topology: anchored
  `idPattern` per R24, loop detection, no dangling peer endpoints, and
  the reachability invariant that every declared source is covered by at
  least one registration path to its hub.
- **CC-14** — A city joining or leaving a federation MUST be expressible
  as a merge request touching only registration manifests (plus peer
  identity material per I3), no code, no broker-specific steps.

## 3. Reconciler (`jcctl`)

- **CC-15** [P] — The reconciler MUST implement `plan` (diff desired
  state against live state, read-only) and `apply` (converge live state).
  `plan` output MUST be human-readable per resource: create / update
  (with field-level diff) / delete / unchanged.
- **CC-16** — The reconciler MUST use only standard NGSI-LD API
  operations (entities, subscriptions, CSRs, `NGSILD-Tenant`) and the
  pipeline engine's public API. Any broker-specific call is a defect
  (violates CC-01).
- **CC-17** — Diffing MUST be JSON-LD expansion of both sides against
  the manifest's `@context` followed by a structural diff over the
  expanded trees (member ordering insignificant, `datasetId` maps keyed
  rather than positional, server-managed members stripped: `createdAt`,
  `modifiedAt`, `status`, server-assigned system attributes).
  RDF canonicalization MAY serve only as an equality fast path to skip
  the structural diff, never as the primary mechanism (stack verdict
  S1). A no-op `apply` immediately after `apply` MUST produce an empty
  plan.
- **CC-18** — `apply` MUST be idempotent and convergent: repeated runs
  from the same commit produce no further changes. Partial failure MUST
  leave a re-runnable state and report per-resource results; it MUST
  NOT abort remaining independent resources.
- **CC-19** — Deletion MUST be explicit: resources removed from the
  repository are reported by `plan` and deleted by `apply` only with a
  dedicated flag or per-resource confirmation policy. Default `apply`
  never deletes.
- **CC-20** — CI MUST run `plan` on every merge request and publish the
  diff as review material; `apply` MUST run only from the protected main
  branch after merge. The applied commit hash MUST be recorded
  (annotation or report) so live state is traceable to a revision.
- **CC-21** — Drift detection MUST run continuously or on schedule:
  `plan` against live state, with non-empty results surfaced to
  operators (UI status + notification). For each drifted resource the
  operator MUST be offered exactly two resolutions: *revert* (re-apply
  Git) or *adopt* (export live state as a manifest change → merge
  request, CC-38).
- **CC-22** — The reconciler MUST support `export`: serializing live
  state of any resource family into valid manifests (envelope + spec),
  used by adoption (CC-21), initial onboarding of an existing platform,
  and portability (CC-50).

## 4. Blueprints (the abstraction for regular users)

- **CC-23** — The plane MUST support blueprints: parameterized templates,
  authored by platform engineers, that expand to one or more manifests
  (subscription + pipeline + seed entities …). Blueprints are the ONLY
  authoring surface exposed to [H] users; raw manifests remain available
  to [P]/[A].
- **CC-24** — Each blueprint MUST declare a parameter schema (JSON
  Schema **draft-07**, per CC-12) with human-readable titles,
  descriptions, defaults, and
  enumerated choices resolvable from live data (e.g. "select a sensor" →
  entity query by type). Parameters MUST be the complete user-facing
  surface: a valid parameter set MUST always render valid manifests.
- **CC-25** — Blueprint expansion MUST be deterministic and pure:
  same blueprint version + same parameters → byte-identical manifests.
  Expanded manifests are committed to the repository (not expanded at
  apply time), so review, diff, and audit always see concrete resources.
- **CC-26** — Blueprints MUST be versioned in the repository. A blueprint
  upgrade MUST NOT silently rewrite existing instances; re-rendering
  instances against a new blueprint version is an explicit, reviewable
  operation with a per-instance diff.
- **CC-27** — Every blueprint instance MUST record its provenance in
  manifest metadata (blueprint name, version, parameter values) so the
  UI can re-open any flow as the form that created it (CC-32).
- **CC-28** — The blueprint library MUST ship with the platform's common
  flows at minimum: threshold alert (subscription → notification
  channel), data-source onboarding (data source + pipeline +
  registration; the pipeline's first run seeds the space, because seed
  entities are not manifests, CC-72), dataset publication
  (registration + open-data view), and cross-city sharing (CSR pair per
  CC-14). The platform publishes the library and an instance follows it
  through a `SyncSource`, so a new version arrives as a reviewable change
  (CC-26).

## 5. User application

- **CC-29** [H] — Regular users MUST be able to perform every routine
  configuration task through forms and lists alone. Git, YAML, merge
  requests, branch names, and reconciler mechanics MUST NOT be visible
  in the default user experience, they are plumbing, surfaced only in
  an expert/advanced view.
- **CC-30** [H] — The application's primary model is the *flow gallery*:
  users browse blueprints (CC-28), instantiate them by filling a form
  generated from the parameter schema (CC-24), and manage their
  instances. Free-form manifest editing is a separate expert mode gated
  by role.
- **CC-31** [H] — Forms MUST be generated from JSON Schema (CC-12,
  CC-24), never hand-built per resource; entity/sensor pickers MUST be
  populated from live broker queries through the gateway (so R9/R11
  narrowing automatically limits what a user can select to what they may
  see).
- **CC-32** [H] — Saving a form MUST transparently produce the
  repository change (expanded manifests, commit, merge request) with a
  generated human-readable description. Re-opening a flow MUST
  reconstruct the filled form from provenance metadata (CC-27).
- **CC-33** [H] — Every flow MUST display a lifecycle status derived
  from repository + reconciler state, with at minimum: *draft* (unsaved),
  *pending approval* (open merge request), *deploying* (merged, apply in
  progress), *live* (applied, no drift), *error* (apply failed or
  runtime failing), *drifted* (CC-21). Status transitions MUST NOT
  require the user to understand the underlying mechanism.
- **CC-34** [H] — Approvals MUST happen in-app: an approver sees the
  pending change as a summary ("adds an alert on sensor X notifying Y")
  plus the CI `plan` diff (CC-20), and approve/reject buttons drive the
  underlying merge-request approval. Approvers MUST NOT need the Git
  forge UI for routine approvals.
- **CC-35** [H] — Each flow MUST show run evidence: recent notification
  deliveries, pipeline throughput/errors, and last-change history
  (from Git log, rendered as plain sentences with author and time).
  A disabled/enabled toggle per flow MUST be available and MUST itself
  be a repository change (e.g. `isActive` on the subscription).
- **CC-36** [H] — The application MUST answer the live federation and
  data topology (spaces, registrations, pipeline routes) read-only for
  every role that may read the project, from the manifests and the
  health each object reported, as the federation graph of the API
  (UI-27); the Portal draws no page of it (UI-28).
- **CC-37** [H] — The application MUST be localized (Slovak first,
  English second), meet WCAG 2.1 AA basics, and use human names and
  descriptions from manifest metadata, never raw URNs, in default
  views.
- **CC-38** [H] — Drift resolution (CC-21) MUST be a two-button choice
  in-app (*revert* / *adopt*), with adopt producing an ordinary pending
  approval like any other change.
- **CC-39** [H][A] — Destructive operations (flow deletion, space
  removal) MUST require a distinct confirmation step and MUST follow the
  explicit-deletion path (CC-19); nothing in the default UI can delete
  live resources directly.

## 6. Roles and identity

- **CC-40** — Authentication MUST be OIDC against the platform identity
  provider (Keycloak, I1); the application, forge, MCP server, and
  reconciler are all ordinary OIDC clients. No component maintains its
  own user database.
- **CC-41** — Authorization MUST be mapped onto Git primitives, not
  reimplemented: domain ownership via directory-scoped code owners,
  change approval via protected-branch required approvals, and admin via
  merge rights on the main branch. The role model MUST include at
  minimum: *viewer* (read live state), *domain editor* (propose changes
  in owned directories), *approver* (approve owned directories),
  *city admin* (merge anywhere, manage blueprints).
  *Interim enforcement note (stack verdict S2):* released Gitea cannot
  yet require code-owner approval (lands in Gitea 28.0.0); until then
  CI re-validation of ownership (CC-59) carries the enforcement and the
  forge carries review routing via *Block merge on official review
  requests* + required approvals.
- **CC-42** — The identity-provider role MUST govern what the
  application renders and permits (which forms, which buttons); the
  forge configuration MUST independently enforce the same boundaries on
  the repository, so a bypassed UI cannot exceed a user's Git rights
  (defense in depth, same posture as GW-layer RLS). To keep this
  non-circular, the `CODEOWNERS` file and the platform settings file
  MUST themselves be owned by *city admin* only (protected file
  patterns) and changes to them are always red-lane (CC-70; stack
  verdict S2).
- **CC-43** — What a user can *read* (entity pickers, live views,
  topology detail) is governed by the R1–R43 policy layer through the
  gateway, with the user's own token, the application MUST NOT hold a
  privileged read identity for user-facing queries.
- **CC-44** — Every configuration change MUST be attributable end to
  end: the commit records the human author (not a shared bot identity),
  the merge records the approver, and the apply report records the
  revision (CC-20). This chain is the audit trail; no parallel audit
  store is required for configuration changes.

## 7. MCP and automation surface

- **CC-45** [A] — The Portal's MCP server (AG-60) MUST expose the plane
  to agents with at minimum: a plan, a dry run, the live state, the
  topology, the blueprints and their instantiation, and a proposal
  (writes a manifest change and opens a merge request); every one an
  operation of the registry (AG-59), none private to the MCP.
- **CC-46** [A] — MCP writes MUST follow the same path as the UI:
  repository proposal → approval → reconcile. An agent MUST NOT be able
  to reach the broker's write surface directly regardless of its token
  (CC-03 + gateway policy).
- **CC-47** [A] — MCP tool results MUST be structured and grounded:
  live-state answers carry the queried revision/timestamp; plan results
  distinguish desired, live, and drifted per resource, so an agent can
  reason about state without screen-scraping.
- **CC-48** [P][A] — Everything the UI can do MUST be achievable through
  the [P]/[A] surfaces (CLI/API/MCP), the UI is a client of the plane,
  never a privileged component with private endpoints.

## 8. Export, portability and upgrade

- **CC-49** [H][P] — Full export MUST be trivially available: the
  repository at any revision IS the complete configuration export. The
  application MUST offer it as a one-click archive download (current or
  historical revision) without Git knowledge.
- **CC-50** — Restoring a city onto a fresh, empty, compliant platform
  MUST require only: deploy infrastructure, point the reconciler at the
  repository, `apply`. This is simultaneously the disaster-recovery and
  the broker-replacement procedure (CC-01); temporal history restores
  separately per CC-07.
- **CC-51** — Broker upgrades MUST be executable blue/green: deploy the
  new version empty, replay via CC-50, verify with `plan` (empty diff)
  plus smoke queries, switch traffic. No in-place migration of
  configuration is ever required.
- **CC-52** — The plane MUST remain broker-agnostic in practice, not
  just in principle: CI SHOULD periodically run `apply` + `plan` against
  a second compliant broker implementation to detect accidental
  dependence on implementation-specific behaviour.
- **CC-53** — Blueprint and manifest formats MUST be forward-versioned
  (schema version in the envelope) with documented migration for
  breaking changes; the reconciler MUST refuse manifests newer than it
  understands rather than misapply them.

## 9. Non-functional

- **CC-54** — Reconciliation MUST scale to a realistic city: thousands
  of manifests, hundreds of subscriptions/registrations, tens of
  pipelines; a full `plan` SHOULD complete in under a minute, and
  `apply` MUST batch and rate-limit so it never destabilizes a serving
  broker (fan-out budget spirit of R37).
- **CC-55** — Availability MUST be decoupled: broker/pipeline serving
  MUST NOT depend on the forge, reconciler, or application being up —
  their outage freezes configuration changes only. The application's
  live views degrade gracefully when the broker is unreachable.
- **CC-56** — The proposal→approval→live loop for a routine flow SHOULD
  complete within minutes of approval (bounded apply trigger latency),
  and the user MUST see status progress (CC-33) without polling
  manually.
- **CC-57** — All plane components (forge, reconciler, MCP server,
  application) MUST be self-hostable open-source software, deployable
  within the same infrastructure as the platform, with no mandatory SaaS
  dependency, required for municipal data-sovereignty and EU-funding
  procurement postures (MIM alignment in `access-control.md` Part II).
- **CC-58** — The repository history MUST be retained per the funding
  body's audit horizon; protected branches MUST prevent history rewrite
  on main. Configuration audit answers (who changed what, when, approved
  by whom) MUST be derivable from Git alone (CC-44).

## 10. Blueprint authorization and resource ownership

- **CC-59** — Every blueprint MUST declare `allowedRoles` and a
  `riskClass` (*green* / *yellow* / *red*) in its metadata. The flow
  gallery MUST filter by the user's role (CC-30), and CI MUST
  re-validate both on every merge request regardless of how it was
  authored, a hand-crafted MR bypassing the portal gains nothing
  (defense in depth per CC-42).
- **CC-60** — Authorization guardrails MUST be encoded structurally in
  the blueprint parameter schema, quotas (e.g. subscriptions per
  team), allowed entity types, scope confined to the requester's own
  `/admin` subtree (ADR 004), and enforced by CI validation. Guardrails
  MUST NOT depend on reviewer vigilance.
- **CC-61** — A creation blueprint MUST expand to include the ADR 002
  `Policy` entities granting the requesting principal (and their
  declared team) rights over the new resource's scope, in the same
  commit as the resource itself. No resource of this plane may reach
  live state without an owner policy.
- **CC-62** — Deletion rights MUST be separable from creation rights:
  destructive flows MAY be restricted to *approver* or above regardless
  of who created the resource, and always follow the explicit-deletion
  path (CC-19, CC-39).

## 11. Interaction lanes and sandboxes

- **CC-63** — The plane MUST implement risk-classed lanes bound to
  `riskClass` (CC-59): *green*, merge request merged by the Portal
  as it is proposed (API/01 §13); *yellow*, one domain approver (CC-34); *red*
  (cross-domain, public exposure, federation edges, a standing egress
  of context data to an address the manifest names, any deletion) —
  the full approval chain. Lane assignment MUST be enforced in CI and
  the forge, not only rendered in the portal.
- **CC-64** — The green lane MUST remain a full repository path:
  committed, attributed, drift-managed, revertible. Auto-approved is
  never bypassed, CC-02/CC-03 hold unchanged in every lane.
- **CC-65** — Green-lane end-to-end latency (form save → resource live)
  MUST be seconds, not minutes: apply MUST be webhook-triggered (no
  polling) and MUST reconcile only the wave subset affected by the
  change (refines CC-56 for the green lane).
- **CC-66** — The portal MUST open green-lane resources optimistically
  in *deploying* state and stream status transitions to *live* or
  *error* (extends CC-33), the user starts working without watching
  the machinery.
- **CC-67** — The plane MUST support *unmanaged sandbox spaces*:
  ephemeral, TTL-tagged tenants created instantly through the green
  lane, marked unmanaged in ownership metadata so drift detection
  (CC-21) ignores them, and auto-reaped at TTL expiry. Sandbox data
  never counts as drift and is never backed by Git.
- **CC-68** — Promotion from a sandbox to managed configuration MUST
  use the export/adopt path (CC-22), producing an ordinary merge
  request. No sandbox object becomes durable configuration any other
  way.
- **CC-69** — Manifests MUST declare which attributes of a resource the
  plane manages (default: exactly those present in the manifest); diff,
  drift detection, and `apply` MUST consider managed attributes only,
  so live telemetry on seed entities is never drift (sharpens CC-17;
  the field-ownership pattern of Kubernetes Server-Side Apply
  transplanted to NGSI-LD attributes). Ownership metadata lives in the
  manifest envelope, never in the broker (CC-01).
- **CC-70** — Lane policy itself (which resource families and risk
  classes require which approvals) MUST be versioned in the platform
  settings file of the repository; changes to lane policy are always
  red-lane.
- **CC-71** — A manifest an assistant or an inference drafts from a
  person's input (a DataModel inferred from a dropped file, DM-54; an
  Endpoint drafted from a request to share, EP-72; a Pipeline drafted
  from a sample, PL-44) is a draft in the person's editor and nothing
  else until the person proposes it: it enters the plane as the same
  Change a hand-written manifest would, in the lane its content earns
  (CC-63), with the person as author and the drafting tool named in
  the change description. No assistant and no tool MUST write to the
  repository on the person's behalf.
- **CC-72** [P] — Every configuration kind MUST be read directly from the
- **CC-73** — Environment-specific values MUST live in the Organization repository as `kind: Environment` at `environments/{name}.yaml` (namespace `org`: the `orgDomain` of that environment, hosts, image digests, the secret backend, feature flags, `deny_unknown_fields`), and every loader (`jcctl`, the Portal's sync, the gateway's store) MUST merge the overlay named by `JC_ENVIRONMENT` over the manifests before validation, so one repository renders every environment (CC-08, CC-50).
- **CC-74** — A manifest MUST NOT carry a host, a domain or an image digest as a literal: a URN in a manifest is written with `{orgDomain}` and rendered at load from the overlay, an Endpoint slug is minted per environment, and an exported bundle carries the placeholders, so import and export are environment-neutral by construction (MF-17, PF-44, EP-27).
- **CC-75** [S] — A change to an `Environment` overlay MUST take the red lane, because it changes hosts and digests, and an overlay MUST name a secret backend and never a secret value (CC-06, CC-70).
  Git repository by the component that serves it; there is no live
  configuration API to write manifests to. `jcctl apply --gateway-url <url>`
  MUST have one live mutation responsibility: replaying seed entities from
  `projects/{p}/spaces/{s}/entities/seed/*.json` (NGSI-LD normalized entities,
  one file per entity or an array) through
  `POST /cs/{space}/ngsi-ld/v1/entityOperations/upsert` with the ServiceAccount's
  audience-bound token; `jcctl plan` MUST compare declared seed entities in Git
  against the live entities returned by the broker for those identifiers, and a
  second apply over an unchanged repository MUST send no write.

---

## 12. Standardization statement

- **Spec-native, no invention**: all live-state reads/writes are plain
  CIM 009 operations (CC-16); URN discipline and prefix routing per
  ADR 001 / R33–R34; scopes per ADR 004.
- **Standards adopted at the edges**: RFC 2119 keywords; OIDC for every
  component (CC-40); JSON Schema for manifests, blueprint parameters and
  generated forms (CC-12, CC-24, CC-31); Git semantics (protected
  branches, code owners, merge-request approvals) as the authorization
  substrate (CC-41).
- **Profiled extensions (documented, additive)**: the manifest envelope
  (CC-09) including attribute-ownership metadata (CC-69), blueprint
  format + provenance + `allowedRoles`/`riskClass` metadata (CC-23–27,
  CC-59), the lane model (CC-63, CC-70), the `jcctl`
  plan/apply/export contract (CC-15, CC-22), and the MCP tool surface
  (CC-45).
- **Deliberately non-standard, tracked**: none, this plane sits entirely
  outside the NGSI-LD API and requires no ETSI change requests.

## 13. Workspaces and previews

Several related edits are held together, tried somewhere safe and brought back as one reviewed Change ([ADR-N-024](../Decisions/adr-n-024-workspaces-branch-and-preview.md)).

- **CC-76** [H][P][A] — The plane MUST offer a *workspace*: a named branch of the Organization repository with a recorded owner, base revision, scope (a project, a space subtree or a list of resources) and TTL, into which every proposing operation can commit instead of opening a Change of its own; the registry of workspaces MUST be a database table beside the drafts, not a manifest on `main`. Amended by CC-87: a project workspace is a branch of the project repository.
- **CC-77** [P] — A manifest in a workspace MUST keep the name it has in the main project; a workspace MUST NOT rename anything at rest.
- **CC-78** [P] — A workspace MUST be rendered as a *preview* by the same loader, with a render prefix applied to every organization-unique identity (project namespace, Context Space name, the `{space}` segment of URNs) and slugs minted for the preview; a preview render that contains an unprefixed organization-unique name MUST fail. At most one preview runs per workspace and two on a node, with every pipeline paused until a person starts it.
- **CC-79** [H][A] — Bringing a workspace back MUST be one Change: the pull request of its branch, classified by the riskiest file, approved as any Change (CC-34, PF-50, PF-58, AG-11).
- **CC-80** [P] — A conflict with the main project MUST be resolved inside the workspace by a person, per field, and the result MUST be checked again before it is proposed; no side wins by default.
- **CC-81** [P] — An expired workspace MUST lose its preview namespaces and its branch; nothing of it remains in the main branch.

## 14. Identity: local names, rendered prefixes

- **CC-82** [P] — A manifest MUST name itself and refer to other resources of its project by local name only; the project, the organization and the environment MUST NOT appear in a name, a reference or a mapping as a literal. What must be unique beyond the project MUST be rendered by the loader from where the manifest lives, the way `{orgDomain}` and slugs already are (CC-73, CC-74).
- **CC-83** [P] — The loader MUST refuse (strict) or report (lax) a manifest or a mapping file that carries its own project name, its space's rendered segment or the organization's domain as a literal where a rendered value exists, naming the file, the path and the replacement. Extended by CC-88 to a literal where a project parameter exists.
- **CC-84** [H][A] — A copy (Save as, a workspace, an import, a whole project or organization) MUST end with a report of what cannot be copied and must be provided where it lands: secret values behind each `secretRef`, people named in RoleBindings and Policies, hosts and certificates of the Environment, credentials of feeds; each item links to where it is set.

## 15. Repositories per project

- **CC-85** — Repository layout 2 MUST hold: in the organization repository `org.yaml`, `environments/`, `users/`, `blueprints/`, `agentprofiles/`, `portal/`, `policies/` and `projects/{slug}.yaml` (PF-86); in a project repository, at its root, what `projects/{slug}/` holds in layout 1 (`project.yaml`, `spaces/`, `pipelines/`, `datasources/`, `dashboards/`, `apps/`, `access/`, `shared/`, `ckan/`). Both MUST carry `.jc/layout`, one integer; an organization repository without the file is read as layout 1, the layout that predates it. The loader MUST refuse a layout it does not know, and `jcctl migrate` MUST be the only writer of a layout change (CC-53 covers the envelope, this rule the tree; supersedes CC-08).
- **CC-86** — The reconciler, the gateway and the Portal MUST assemble one render from the organization checkout plus every registered project checkout at its `spec.ref`, into the virtual tree `projects/{slug}/…` the kinds address in layout 1. Uniqueness across the organization (PF-44, endpoint slugs) MUST be checked at assembly. A project whose ref cannot be fetched MUST render at its last fetched ref and report that ref and the error on its registry entry's `status`.
- **CC-87** — A `Change` MUST target exactly one repository. A project workspace MUST be a branch of the project repository, and an organization workspace a branch of the organization repository (amends CC-76). An operation that has to touch both MUST produce two linked Changes, the organization one in the red lane, and the project one MUST NOT be applied before the organization one.
- **CC-88** — `project.yaml` MUST carry `spec.version` (semver) and `spec.parameters`, one declaration per deployment knob in a subset of JSON Schema (`type` of `string`, `integer`, `number`, `boolean` or `secret`, with optional `default`, `description` and `enum`); a parameter of type `secret` MUST be a `secretRef` name whose value the deployment sets. A manifest MUST reference a parameter as `{param:name}` and a mapping as `env("JC_PARAM_<NAME>")`, beside `{orgDomain}` and `env("JC_ORG_DOMAIN")`. Values MUST come from the registry entry over the defaults, and the loader MUST refuse a project file carrying a literal where a parameter exists (extends CC-83). A release is the tag `v{version}` on the project repository; the registry entry pins one.
- **CC-89** [S] — A registry entry MAY name an external git repository: the platform MUST mirror it read-only at the pinned ref and MUST refuse every edit through the Portal with "this project is authored at {url}". This replaces a `SyncSource` for a whole project; a `SyncSource` stays for subtrees (model libraries, blueprint sets).
- **CC-90** — Every project repository MUST run the same CI on every merge request: schema validation, Conftest and `jcctl validate --project`. The organization render (CC-86) MUST be the gate before an apply and MUST run when a pinned ref moves or a tracked branch receives a push (webhook).

## Traceability

| Requirement Range | Architecture Section | Test Family |
|---|---|---|
| CC-01–CC-07 | [Architecture/02-principles.md#12-configuration-as-code-first](../Architecture/02-principles.md#12-configuration-as-code-first) | [Testing/04-configuration-and-pipeline-tests.md#4-plan-and-idempotency](../Testing/04-configuration-and-pipeline-tests.md#4-plan-and-idempotency) |
| CC-08–CC-14 | [Architecture/06-configuration-as-code.md#2-manifest-envelope--kinds-catalogue-cc-09-cc-12](../Architecture/06-configuration-as-code.md#2-manifest-envelope--kinds-catalogue-cc-09-cc-12) | [Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation](../Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation) |
| CC-15–CC-22 | [Architecture/06-configuration-as-code.md#3-the-reconciler-engine](../Architecture/06-configuration-as-code.md#3-the-reconciler-engine) | [Testing/01-backend-tests.md#3-jcctl](../Testing/01-backend-tests.md#3-jcctl) |
| CC-23–CC-28 | [Architecture/06-configuration-as-code.md#2-manifest-envelope--kinds-catalogue-cc-09-cc-12](../Architecture/06-configuration-as-code.md#2-manifest-envelope--kinds-catalogue-cc-09-cc-12) | [Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation](../Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation) |
| CC-29–CC-39 | [Architecture/09-portal.md#2-portal-ui-architecture](../Architecture/09-portal.md#2-portal-ui-architecture) | [Testing/03-frontend-and-e2e-tests.md#2-playwright-twice](../Testing/03-frontend-and-e2e-tests.md#2-playwright-twice) |
| CC-40–CC-44 | [Architecture/12-identity-and-access.md#2-organization-group--role-model](../Architecture/12-identity-and-access.md#2-organization-group--role-model) | [Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation](../Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation) |
| CC-45–CC-48 | [Architecture/07-agents-and-mcp.md#1-dual-mcp-surfaces](../Architecture/07-agents-and-mcp.md#1-dual-mcp-surfaces) | [Testing/02-conformance-tests.md#4-model-context-protocol](../Testing/02-conformance-tests.md#4-model-context-protocol) |
| CC-49–CC-53 | [Architecture/06-configuration-as-code.md#6-download-import-and-sync-defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34](../Architecture/06-configuration-as-code.md#6-download-import-and-sync-defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34) | [Testing/04-configuration-and-pipeline-tests.md#4-plan-and-idempotency](../Testing/04-configuration-and-pipeline-tests.md#4-plan-and-idempotency) |
| CC-54–CC-58 | [Architecture/13-security.md#4-end-to-end-audit-trail-cc-44-cc-58](../Architecture/13-security.md#4-end-to-end-audit-trail-cc-44-cc-58) | [Testing/05-deployment-and-performance-tests.md#2-the-k3d-variant-matrix](../Testing/05-deployment-and-performance-tests.md#2-the-k3d-variant-matrix) |
| CC-59–CC-62 | [Architecture/06-configuration-as-code.md#4-risk-classified-interaction-lanes-cc-63cc-66](../Architecture/06-configuration-as-code.md#4-risk-classified-interaction-lanes-cc-63cc-66) | [Testing/04-configuration-and-pipeline-tests.md#2-the-gate-on-an-organization-repository](../Testing/04-configuration-and-pipeline-tests.md#2-the-gate-on-an-organization-repository) |
| CC-63–CC-70 | [Architecture/06-configuration-as-code.md#4-risk-classified-interaction-lanes-cc-63cc-66](../Architecture/06-configuration-as-code.md#4-risk-classified-interaction-lanes-cc-63cc-66) | [Testing/04-configuration-and-pipeline-tests.md#4-plan-and-idempotency](../Testing/04-configuration-and-pipeline-tests.md#4-plan-and-idempotency) |
| CC-71 | [Architecture/11-data-models.md#67-a-model-from-a-sample-dm-54-dm-55](../Architecture/11-data-models.md#67-a-model-from-a-sample-dm-54-dm-55) | [Testing/03-frontend-and-e2e-tests.md#2-playwright-twice](../Testing/03-frontend-and-e2e-tests.md#2-playwright-twice) |
| CC-72 | [Architecture/06-configuration-as-code.md#3-the-reconciler-engine](../Architecture/06-configuration-as-code.md#3-the-reconciler-engine) | [Testing/01-backend-tests.md#3-jcctl](../Testing/01-backend-tests.md#3-jcctl) |
| CC-73…CC-75 | [Architecture/06-configuration-as-code.md#1-repository-layout-cc-08-cc-85](../Architecture/06-configuration-as-code.md#1-repository-layout-cc-08-cc-85) | [Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation](../Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation) |
| CC-76…CC-81 | [Architecture/06-configuration-as-code.md#7-workspaces-and-previews-cc-76cc-81](../Architecture/06-configuration-as-code.md#7-workspaces-and-previews-cc-76cc-81) | [Testing/04-configuration-and-pipeline-tests.md#4-plan-and-idempotency](../Testing/04-configuration-and-pipeline-tests.md#4-plan-and-idempotency) |
| CC-85…CC-90 | [Architecture/06-configuration-as-code.md#1-repository-layout-cc-08-cc-85](../Architecture/06-configuration-as-code.md#1-repository-layout-cc-08-cc-85) | [Testing/04-configuration-and-pipeline-tests.md#2-the-gate-on-an-organization-repository](../Testing/04-configuration-and-pipeline-tests.md#2-the-gate-on-an-organization-repository) |
| CC-82…CC-84 | [Architecture/06-configuration-as-code.md#8-identity-local-names-and-rendered-prefixes](../Architecture/06-configuration-as-code.md#8-identity-local-names-and-rendered-prefixes) | [Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation](../Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation) |

## Related

- [00-index](00-index.md) — all requirement families.
- [traceability](traceability.md) — requirement to chapter and test mapping.
