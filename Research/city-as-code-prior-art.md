---
sidebar_position: 1
title: "Prior Art: City-as-Code"
---

# City-as-Code, Prior Art and the Recommended Solution

Status: Draft
Date: 2026-08-18
Question: What is the best concrete solution for the plane specified in
`../requirements/city-as-code.md` (CC-01…CC-58)? Who has already solved "configuration
as code + usable UI + versioning + inter-resource dependencies", how,
and what do we reuse versus build? Existing technology is treated as a
pattern library, not a constraint, anything can be built.
Related: `../requirements/city-as-code.md`, `configuration-plane-approaches.md`
(approach A is the frame; this document fills in the *how*).

---

## 1. How others do it, the pattern catalog

Each entry: what the system is, the mechanism that matters, what we
steal, what we avoid.

### 1.1 Kubernetes, declarative API + Server-Side Apply

The reference implementation of desired-state reconciliation. The
under-appreciated part is **Server-Side Apply (SSA)**: every field of
an object records a *field manager*; two writers (a UI, a GitOps
controller, an autoscaler) co-own one object safely because conflicts
are detected per field, not per object.

- **Steal**: field-level ownership. This is the industry's only proven
  answer to "UI and code edit the same thing". Applied to NGSI-LD it
  becomes *attribute-level ownership*: a seed entity's structural
  attributes are Git-owned, its telemetry attributes are pipeline-owned,
  and the reconciler diffs only the attributes it manages. This
  directly solves the hardest open problem in CC-17 (normalization
  diffing) and CC-07 (state vs structure).
- **Avoid**: making the whole plane K8s-resident (approach B's flaw —
  ties configuration to a cluster the edge boxes don't have).

### 1.2 Argo CD / Flux, GitOps reconcilers with a status UI

Git is truth; a controller continuously diffs live vs desired; the UI
shows sync state, per-resource diff, history, and offers *actions*
(sync, rollback), but never authors configuration. Ordering is solved
with **sync waves** (numbered phases) and **health checks** (a resource
must be healthy before the next wave applies).

- **Steal**: continuous diff + status surface (CC-21, CC-33); sync
  waves as the dependency model, spaces → data models → seed entities
  → registrations → subscriptions → pipelines is a natural wave order,
  simpler and more debuggable than a full dependency graph.
- **Steal**: the **rendered-manifests pattern** the Argo community
  converged on, commit expanded output, not templates, so review and
  audit always see concrete resources. CC-25 already requires this;
  prior art confirms it.
- **Avoid**: read-only-UI-only. Argo's gap is exactly the [H] authoring
  surface CC-29 demands; it proves a status UI alone is not enough.

### 1.3 Grafana, the UI-first system that converged to Git

A decade of evolution in one product: JSON export (backup only) →
file provisioning (one-way, UI edits lost) → dashboards-as-code
(Jsonnet/Terraform, [H] users locked out) → **Git Sync: the UI edit
itself becomes a branch + pull request**. Each earlier stage failed for
a reason we would otherwise rediscover: exports drift, one-way
provisioning makes the UI read-only, code-only excludes normal users.

- **Steal**: the endpoint — *the UI is a Git client*. Saving a form
  produces a commit/MR transparently (CC-32 verbatim). Grafana is the
  strongest single validation of approach A's UX model.
- **Avoid**: shipping the intermediate stages (export-only = approach D;
  one-way provisioning = approach G with extra steps).

### 1.4 Backstage, scaffolder templates and catalog-in-Git

The internal-developer-portal pattern: entities live as YAML in Git;
the **scaffolder** presents a form generated from a parameter schema,
renders a template, and opens a pull request. Owners approve in the
forge; CI validates.

- **Steal**: blueprint = parameter JSON Schema + deterministic template
  - PR output (CC-23…CC-27 are precisely Backstage scaffolder
  semantics); forms generated from schema, never hand-built (CC-31).
- **Avoid**: Backstage's weight (a TypeScript monolith to fork). The
  pattern is portable without the product.

### 1.5 Crossplane, compositions as typed blueprints

CRDs define a *claim* ("I want a database, size M"); a composition
expands it into concrete resources. The claim is the durable,
user-owned artifact; expansion is versioned and upgradeable.

- **Steal**: keep the *instance* (blueprint name + parameters) as the
  first-class committed artifact alongside the expanded output, CC-27
  provenance, so re-rendering under a new blueprint version is a
  reviewable diff (CC-26).
- **Avoid**: runtime expansion (composition happens in-cluster at apply
  time; audits see abstractions, not resources, conflicts with CC-25).

### 1.6 Terraform / OpenTofu, plan/apply and the state-file lesson

The plan → review → apply loop with an explicit dependency DAG. Its
weakness after 10+ years of industry use: the **state file** is a
second source of truth that drifts from both Git and reality, holds
secrets, and needs locking.

- **Steal**: `plan` output as the review artifact posted on every MR
  (CC-20); explicit-deletion semantics (destroy is never implicit —
  CC-19).
- **Avoid**: any state file. The broker's live state is queryable; diff
  desired-vs-live directly (the Kubernetes model, not the Terraform
  model). Deterministic URNs (CC-10) are what make this possible, the
  identity mapping Terraform keeps in state, we derive from the
  manifest path.

### 1.7 GitHub/GitLab themselves, settings-as-code and web edits

The forges solved their own problem twice: web UI edits are ordinary
commits (everyone reviews the same way), and authorization is Git
primitives, protected branches, CODEOWNERS, required approvals.

- **Steal**: authorization mapped onto the forge, never reimplemented
  (CC-41–42); in-app approval driving the underlying MR approval
  (CC-34).

### 1.8 Home Assistant, the cautionary two-store tale

YAML config and UI-managed storage coexist as two truths per domain;
users permanently juggle "is this automation in YAML or in .storage?".
Comments and formatting are destroyed when the UI touches YAML.

- **Lesson**: never split ownership *by resource instance* between UI
  store and Git store (approach E's structural conflict). One store,
  one writer path; the UI joins the code path rather than owning a
  parallel one.

### 1.9 NiFi / Node-RED, canvas-first pipelines with registries

Visual flow authoring is genuinely superior for exploration; flow
exports (large position-laden JSON) diff and review poorly; the NiFi
Registry is a second, non-Git version-control plane.

- **Lesson**: canvases are authoring tools, not sources of truth. Bento
  YAML remains the committed artifact (CC-11); a canvas, if ever added,
  renders to Bento config the way blueprints render to manifests
  (D5c in the approaches survey).

### 1.10 Internal developer portals (Port, Cortex) and dbt Cloud

Self-service UI actions that trigger IaC pipelines; dbt Cloud's IDE is
a thin Git client (edit → branch → PR → CI). Both converge on the same
shape as Grafana Git Sync and Backstage: **UI in front, Git underneath,
CI as the gate**.

### 1.11 CUE / KCL / Jsonnet, configuration languages

Typed configuration languages unify schema, defaults, and templating;
CUE in particular validates and generates JSON Schema from one source.

- **Steal (optionally)**: author blueprint schemas + expansion in CUE
  internally, *emitting* plain YAML manifests and JSON Schema, the
  repository surface stays language-free (CC-09 bans a DSL in
  manifests, not in the blueprint engine's implementation).

## 2. The convergent industry pattern

Independently, Grafana, Backstage, dbt, the forges, and the GitOps
ecosystem arrived at one architecture. Nobody sustains bidirectional
sync; nobody survives on export-only; two-writer models survive only
with field-level ownership.

```text
[H] form UI ─┐
[P] CLI/CI ──┼──► Git repository ──► CI validate + plan ──► approval/merge
[A] MCP ─────┘        (truth)                                    │
                                                                 ▼
              status/diff/history UI ◄── reconciler ──► live platform
                                          (waves, live diff, no state file)
```

Six named patterns compose it:

| # | Pattern | Proven by | Lands in CC-* |
|---|---|---|---|
| P1 | UI as Git client (form → commit → MR) | Grafana Git Sync, dbt Cloud, forge web edits | CC-29–34 |
| P2 | Blueprint = schema + deterministic template + PR | Backstage scaffolder, Crossplane claims | CC-23–28 |
| P3 | Reconciler with live diff, no state file | Kubernetes, Argo/Flux | CC-15–22 |
| P4 | Ordering by waves + health, not free-form DAG | Argo sync waves | CC-18, CC-54 |
| P5 | Field/attribute-level ownership for co-writers | Kubernetes SSA | CC-07, CC-17 |
| P6 | AuthZ = forge primitives; audit = Git history | GitHub/GitLab | CC-40–44, CC-58 |

## 3. Buy vs build

| Component | Verdict | Basis |
|---|---|---|
| Forge (repo, MRs, protected branches, CODEOWNERS, CI) | **Buy/host: Gitea** | Self-hostable (CC-57); P6 gives roles + audit for free. GitLab CE is disqualified: required approvals and code-owner enforcement are Premium/Ultimate features (stack verdict S2) |
| Secrets | **Buy: SOPS + age, or the cluster secret store** | CC-06; solved problem |
| Pipeline engine | **Buy: Bento (`warpstreamlabs/bento`, MIT)** | CC-11; YAML-native GitOps citizen. `redpanda-data/connect` is licence-disqualified (stack verdict S5) |
| Blueprint engine | **Mostly buy**: JSON Schema + a deterministic template layer (CUE or plain Go templates), wrapped in ~small code | P2; determinism is the only hard requirement (CC-25) |
| Reconciler (`cityctl`) | **Build (small)** | Nothing speaks NGSI-LD; it is a diff loop over a standard API — plan/apply/export over entities, subscriptions, CSRs, tenants + Bento configs. The K8s-operator and Terraform-provider routes were evaluated and rejected (approaches B, C) |
| User application | **Build (thin)** | Flow gallery + schema-generated forms (react-jsonschema-form class of library) + forge API for MR/approve + `cityctl` server mode for status. Backstage could host it as a plugin, but the payload is small enough that the platform's own portal is the leaner home |
| MCP server | **Build (very small)** | Same verbs `cityctl` already has (CC-45); it is a façade |
| Status/drift dashboard | **Reuse the user app** | P3; do not adopt Argo just for its UI on a non-K8s target |

The bespoke surface is deliberately three thin components, reconciler,
blueprint expander, portal app, all speaking standard interfaces
(NGSI-LD API, Git, JSON Schema, OIDC). Everything else is hosted
commodity.

## 4. The recommended solution, concretely

Approach A from `configuration-plane-approaches.md`, instantiated with
the mechanisms above:

1. **Repository** per city (Gitea, self-hosted; see §3 on GitLab CE), layout per
   CC-08, rendered-manifests discipline: blueprints expand at commit
   time; both the instance file (parameters + blueprint version) and
   the expanded manifests are committed.
2. **`cityctl`**, single static binary (fits the 35 MiB edge posture):
   - `plan` / `apply` / `export` / `serve` (read-only status API for
     the portal and MCP).
   - Live diff against the broker through the gateway; identity from
     deterministic URNs; **no state file**.
   - **Waves**: spaces → datamodels → seed entities → registrations →
     subscriptions → pipelines; each wave gated on health probes.
   - **Attribute ownership** (the SSA transplant): manifests declare
     which attributes the plane manages (default: all in the manifest);
     diffing and drift detection consider only managed attributes, so
     live telemetry on seed entities is never "drift". Ownership
     metadata lives in the manifest envelope, not in the broker
     (CC-01 stays intact).
3. **Portal**, flow gallery per CC-30: JSON-Schema-generated forms,
   entity pickers via gateway queries under the user's own token
   (CC-43), save = branch + MR via forge API (P1), approve in-app
   (CC-34), status/drift from `cityctl serve` with the two-button
   revert/adopt (CC-38).
4. **CI**, schema validation, blueprint re-render check (committed
   expansion must equal recomputed expansion), `plan` posted to the MR,
   apply-on-merge from main only, applied commit recorded (CC-20).
5. **Duplication/portability**, a city template repository plus a
   parameter overlay (city name, Razidlo, domains); *duplicate project*
   in the UI = scaffold new repo from template + `apply` (CC-49–50).
   The same path is disaster recovery and broker replacement.
6. **MCP**, `plan`, `validate`, `get_live_state`, `list_blueprints`,
   `instantiate_blueprint`, `propose_change`, all through the Git path
   (CC-45–48).

### What is genuinely novel (must be designed, not copied)

- NGSI-LD-aware normalization for diffing (JSON-LD expansion, member
  ordering, server-managed member stripping), CC-17; no prior art
  does JSON-LD-aware diffs.
- Attribute-ownership semantics on NGSI-LD entities (P5 transplant).
- The blueprint library content itself (CC-28 flows).
- Broker-agnostic conformance check in CI (CC-52), run the same
  apply/plan against a second compliant broker.

Everything else in the design is an assembled, already-proven pattern.

## 5. Why not an existing product wholesale

- **Backstage + Argo + Crossplane** covers ~70 % *if* everything were a
  K8s CRD, but broker configuration is not, edge sites have no
  cluster, and wrapping NGSI-LD into CRDs re-creates approach B's
  coupling for no gain.
- **Terraform + a custom provider** re-introduces the state file and
  HCL as a proprietary manifest dialect (CC-09/CC-10 violations),
  and still builds no [H] surface.
- **Grafana/NiFi-style console with export** is the pattern the
  industry demonstrably abandoned (§1.3, §1.9).

The winning move is not a product but the convergent pattern P1–P6 with
three thin custom components on standard seams, which is also the
future-proof posture: each seam (Git, JSON Schema, OIDC, NGSI-LD API)
outlives any individual tool sitting on it.

## 6. The extension route, a new module inside an existing tool

Instead of standalone components, each piece could ship as a
plugin/module of a host that already has the lifecycle machinery.
Every mainstream host was checked for each of the three bespoke parts:

| Host + extension mechanism | Would carry | What you inherit | Why it fails / holds |
|---|---|---|---|
| **Terraform/OpenTofu provider** (`terraform-provider-ngsild`) | reconciler | plan/apply UX, DAG, huge mindshare | State file + HCL-as-manifest-dialect (CC-09/10 conflict); no continuous drift daemon; approach C's verdict stands |
| **Pulumi provider** | reconciler | typed SDKs | Same state problem, plus a general-purpose language as config surface |
| **Ansible collection** (`urbivita.ngsild` modules) | apply engine | idempotent module contract, familiar packaging, no state file, AWX gives a rudimentary UI | Viable for `apply`; weak `plan` (check-mode diffs are shallow), no JSON-LD normalization for free, no continuous drift watch, no serve API — half the reconciler still gets written, now inside Ansible's execution model |
| **Kubernetes operator / Crossplane provider** | reconciler | full reconcile loop, SSA, Argo/Flux + their UIs for free | Everything must become a CRD and every site needs a cluster — approach B's verdict; edge boxes lose |
| **Argo CD config-management plugin / Flux controller** | blueprint expansion | GitOps pipeline integration | Argo/Flux can only *apply to the K8s API*; a CMP renders manifests but cannot push them to an NGSI-LD endpoint — forces the operator route above |
| **Backstage plugin** | portal (gallery + forms + approvals) | scaffolder = CC-23 blueprints nearly verbatim, forge integration, catalog UI | **Holds.** Cost is adopting Backstage itself (TS monolith, its own ops burden). Right choice if the city already runs Backstage; oversized as a mandatory dependency |
| **Grafana app plugin** | portal | auth, nav, popularity in city IT | Dashboard-shaped UX fights form/approval flows; Git Sync is for dashboards, not arbitrary repos |
| **Gitea/GitLab CI components + forge webhooks** | CI gate + apply trigger | already in the stack | **Holds** — this is not even an extension, it is the intended use (P6) |
| **Bento plugin** | pipeline steps | already native | **Holds** — custom processors are ordinary Bento plugins |
| **kpt / KRM functions** | blueprint expansion | deterministic render contract | Apply side is K8s-only again |

Pattern in the table: hosts happily carry the **render** and **UI**
halves, but every host's *apply* machinery is welded to its own target
(K8s API, cloud APIs via state, SSH). Nothing existing applies to an
NGSI-LD endpoint, that gap is the one irreducible build, and it is
small.

**Recommended shape, core once, adapters everywhere.** Build the
irreducible part as a library (`cityctl-core`: normalization, diff,
waves, attribute ownership, NGSI-LD client) with the standalone binary
as its first consumer. Then extension modules become cheap
*distribution*, not architecture:

- `cityctl` CLI/daemon, the default, edge-capable deployment;
- an Ansible module and a Terraform provider *wrapping the core*, for
  cities whose ops teams live in those tools (state file used as cache
  only, never as truth, live diff stays authoritative);
- a Backstage plugin speaking to `cityctl serve`, for cities that
  already run a portal;
- the platform's own thin portal, for everyone else.

This inverts the risk: instead of betting the plane on one host tool's
lifetime (the opposite of future-proof), the core owns the NGSI-LD
logic and hosts are replaceable skins. If Backstage, Terraform, or
Ansible fall out of favor, the adapter is discarded, CC-01's
replaceability argument, applied to our own tooling.

## 7. Permissions, strict RBAC without a new RBAC engine

Who may create what is answered by composing four layers that all
already exist; the only glue is blueprint metadata.

1. **Identity**, Keycloak OIDC for every component (CC-40). Roles per
   CC-41: *viewer*, *domain editor(domain)*, *approver(domain)*,
   *city admin*, held as Keycloak groups.
2. **Configuration-write rights live in the forge, never in our code**
   (CC-41–42): directory-scoped CODEOWNERS say who approves
   `subscriptions/parking/` vs `registrations/`; branch protection says
   who merges and how many approvals each path needs. The portal
   renders only what the role allows, and the forge independently
   enforces the same boundary, a bypassed UI cannot exceed the user's
   Git rights.
3. **Blueprint-level RBAC**, each blueprint declares `allowedRoles`
   and a `riskClass` in its metadata. The gallery filters by role;
   CI re-validates on every MR (defense in depth: hand-crafting the MR
   without the portal changes nothing). Parameter schemas carry the
   guardrails, quotas (max subscriptions per team), allowed entity
   types, scope restricted to the requester's own `/admin` subtree —
   so "strict" is enforced structurally, at validation time, not by
   reviewer vigilance.
4. **Data-plane rights are born with the resource**: a creation
   blueprint expands not only into the resource but into the ADR 002
   `Policy` entities that grant the requesting user (and their team)
   rights over the new resource's scope. RBAC for the new tenant is
   therefore versioned, reviewable, and applied in the same commit —
   there is no separate "now go click permissions" step, and no
   resource ever exists without an owner policy.

Destructive rights stay separate: deletion follows the explicit lane
(CC-19/CC-39) and can be reserved to *approver*+ regardless of who
created the resource.

## 8. The fast interactive path, lanes and the two-plane split

The latency tension ("create a tenant, start working *now*" vs
commit → approval → reconcile) dissolves into two orthogonal moves.

**Move 1, split the planes.** Only *configuration* rides Git. Working
**inside** a tenant, creating and updating entities, querying,
exploring, wiring a dashboard, is the ordinary NGSI-LD data plane
through the gateway under the user's `Policy` entities: milliseconds,
fully interactive, no Git anywhere (CC-07 already draws this line).
Most of what feels like "working on it" after creating a tenant never
touches the slow plane at all.

**Move 2, risk-classed lanes for the configuration plane.** Strict
RBAC and speed coexist because approval requirements attach to the
blueprint's `riskClass` (§7.3), not to the plane as a whole:

| Lane | Criteria | Flow | Target latency |
|---|---|---|---|
| **Green — self-service** | resource entirely inside the requester's own scope, bounded blast radius (personal/team workspace tenant, private subscription within quota) | portal commits; policy bot auto-approves the MR; webhook-triggered reconcile of just the touched wave subset | seconds |
| **Yellow — one approver** | shared-domain resources (pipeline writing shared data, new data model) | normal MR, one domain approver in-app (CC-34) | minutes–hours, human-bound |
| **Red — full review** | cross-domain, public exposure, federation edges, any deletion | full approval chain | deliberate |

The green lane is still Git: committed, attributed, drift-managed,
revertible, auto-*approved*, never bypassed. Prior art: auto-merge
bots (Renovate class) and platform-engineering "paved roads", where
pre-approved templates earn pre-approved merges. Making it *feel*
instant is engineering, not architecture: webhook-triggered apply (no
polling), partial-wave reconcile, and cheap tenants, Antares'
shared-schema RLS design (10k-tenant target) makes tenant creation one
API call. The portal opens the workspace optimistically in *deploying*
state and streams it to *live* (CC-33/CC-56).

**Move 3 (for genuinely exploratory work), sandbox first, adopt
later.** Instant scratch spaces skip Git entirely: an ephemeral,
TTL-tagged tenant marked *unmanaged* in ownership metadata (so drift
detection ignores it, §4.2), or, for zero-cost experiments, the wasm
in-browser broker. When something built interactively should become
durable, `cityctl export` adopts the live objects into manifests and
opens the MR (the CC-21/CC-22 adopt path). This is ordinary dev→prod
promotion: interactivity lives where drift doesn't matter, Git guards
only what must survive.

The user never sees the machinery, the portal shows *created* (green),
or *pending approval* (yellow/red), and nothing else. The "complicated
backend" is complicated exactly once, in `cityctl-core`; every surface
above it is a form, a status chip, and two buttons.

## 9. Four hard problems

### 9.1 Repo access, "only their own part"

Git has no per-directory **read** control: cloning a repo means reading
all of it, forever (history included). Every system that offers
path-level read ACLs (Google's monorepo, Perforce, Gerrit per-ref
rules) built custom VCS infrastructure to get it, off the table.
Three honest options remain, and the answer layers two of them:

1. **Portal as the narrowed view (default).** [H] users don't read Git
   at all, they see flows and live state through the gateway under
   their own token (CC-43), so the R-layer policy narrowing already
   scopes what they see. "Access to their own part" is a portal
   property, not a Git property, for everyone but experts.
2. **Satellite repos where read isolation is real.** *Write* scoping
   inside one repo is solved (CODEOWNERS, protected branches); *read*
   isolation is not. Where a domain genuinely must not read another's
   configuration, that domain gets its own repository, and the
   reconciler aggregates repos through a declared **fleet manifest**
   (the Flux multi-repo / Argo ApplicationSet pattern). Repo
   membership = read access; the fleet manifest itself is red-lane.
3. **Transparent monorepo otherwise.** Configuration minus secrets is
   rarely confidential inside one city administration; a readable
   monorepo with CODEOWNERS write-scoping is the cheap default, and
   transparency is a feature for audit.

### 9.2 Secrets

CC-06 said "no plaintext, reference by name"; the working mechanism is
the External-Secrets pattern:

- Manifests carry **named references only** (`secretRef: parking-mqtt`).
- Values live in the platform secret store (OpenBao, MPL 2.0
  Vault fork, since Vault itself moved to BSL and fails the open-source
  procurement posture (stack verdict S6), or SOPS+age
  files for a small city; same reference discipline either way).
- The **portal writes secret values directly to the store** over its
  API; the merge request contains only the reference. Secrets never
  transit Git, MR diffs, or CI logs.
- The **reconciler resolves references at apply time** and injects the
  material where NGSI-LD expects it (`receiverInfo` /
  `contextSourceInfo`, ADR 009). `plan`, diff, drift, and `export`
  redact secret-bearing members, a rotated token is not drift.
- **Rotation** happens in the store without a configuration change;
  the reconciler re-materializes on the next apply or a rotation
  signal. Store audit log covers value access; Git covers reference
  changes.

### 9.3 Cross-references between on-the-fly resources

The trap is runtime-assigned identity: if resource A gets a random ID
at creation, resource B created in the same blueprint can't reference
it without an imperative lookup step. The plane dodges the trap
structurally:

- **Deterministic URNs (CC-10) make references computable.** The URN of
  any resource derives from its manifest path and city namespace, so a
  blueprint expands references to resources that don't exist yet —
  correctly. This is the Kubernetes name-coupling model (Service →
  Deployment by name), strengthened by ADR 001's derivation rule; no
  Terraform-style interpolation graph and no state needed.
- **CI validates referential integrity repo-wide**, dangling
  references, type mismatches, the same check CC-13 already runs for
  federation topology, generalized.
- **Waves order existence**: a referenced tenant applies in an earlier
  wave than the subscription referencing it (§4.2); within-wave
  references are legal because CI proved both sides exist in the same
  revision.
- **Runtime values stay out of manifests.** Endpoints derive from names
  by convention (the Kubernetes Service pattern: stable name, runtime
  discovery). The rare genuinely runtime-assigned value is resolved by
  the reconciler as an output of wave N fed into wave N+1, and every
  such resolution is listed in `plan` output.
- **Cross-domain references go through exported interfaces.** A domain
  declares which of its resources are exported (the Crossplane
  published-claim / Terraform remote-state-output pattern);
  referencing a non-exported foreign resource fails CI, and changes
  that cross ownership are yellow/red lane. On-the-fly creation stays
  green-lane only while its references stay inside the requester's own
  scope.

### 9.4 Version control and backward compatibility

- **History is self-contained by construction.** Because expanded
  manifests are committed (rendered-manifests pattern, CC-25), any
  historical revision replays without the blueprint-engine version
  that produced it. Blueprint engine compatibility only matters for
  *new* renders, this single property removes the classic
  template-tool upgrade trap.
- **Envelope schema version** (CC-53): the reconciler refuses manifests
  newer than it understands; migrations are documented and shipped as
  repo-wide, reviewable rewrites.
- **Blueprint upgrades are explicit** (CC-26): instances pin their
  blueprint version; re-rendering under a new version is a
  per-instance diff, never a silent rewrite.
- **Data models evolve additively**: `@context` + JSON Schema versions
  in `datamodels/`; a breaking change is a new versioned type plus a
  migration blueprint, never an in-place mutation (JSON-LD expansion
  per ADR 008 absorbs vocabulary drift between peers).
- **`cityctl` itself is semver'd with golden-file tests**: recorded
  plan outputs must stay stable across upgrades, and CC-52's
  second-broker CI run catches accidental implementation coupling.

## Related

- [01-overview](../Architecture/01-overview.md) — what the platform took from this study.
