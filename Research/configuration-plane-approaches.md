---
sidebar_position: 3
title: "Configuration Plane Approaches"
---

# Configuration-Plane Approaches, Design-Space Survey

Status: Draft for autonomous evaluation
Date: 2026-08-18
Scope: All viable ways to configure a future-proof NGSI-LD platform
(Antares broker, APISIX, Bento/NiFi pipelines, FIWARE Data Space
Connector / DSP) so that it is simultaneously **code-driven**
(Helm/helmfile, Terraform, versioned manifests) and **UI-usable**
(forms, import/export, project duplication).
Related: `../requirements/city-as-code.md` (CC-01…CC-70, the
currently committed approach), `architecture.md`, `../registers/decision-register.md`
ADR 001–011.

This document enumerates the decision dimensions, the coherent
combinations, and the criteria to judge them, then defines the goal for
a later autonomous pass that evaluates every combination in depth.

---

## 1. The two-layer split (fixed baseline)

Every approach below respects one invariant already decided in CC-05:

| Layer | Contents | Tooling candidates |
|---|---|---|
| **Infrastructure** | cluster, broker/gateway/pipeline *deployment*, DNS, TLS, secrets stores | Terraform, Helm, helmfile, Kustomize, operators |
| **Configuration** | tenants/context spaces, CSRs, subscriptions, pipeline configs, data models, seed entities, policies, routes | the subject of this survey |

Infrastructure tooling never templates NGSI-LD payloads; configuration
manifests never encode deployment topology. Approaches differ in **who
owns the configuration layer and how the UI and the code view stay in
sync**.

---

## 2. Decision dimensions

### D1, Source of truth for configuration

| Option | Description | Precedent |
|---|---|---|
| **D1a Git repository** | Manifests in Git; live state is a projection; anything else is drift | CC-02, GitOps, Flux/Argo |
| **D1b Platform database** | UI writes to its own DB; export produces YAML/JSON snapshots | NiFi, Grafana pre-provisioning era, most SaaS |
| **D1c The broker itself** | Configuration stored as NGSI-LD entities (`Policy`, `ScopeDefinition` already are, per ADR 002/005); backup = entity export | extends ADR 002 |
| **D1d Hybrid bidirectional** | UI writes live, a sync job continuously exports to Git; Git and live state are peers | Crossplane import, `terraform import` workflows |

### D2, Reconciliation mechanism (desired → live)

| Option | Description | Precedent |
|---|---|---|
| **D2a Custom reconciler (`cityctl`)** | plan/apply/export CLI speaking only standard NGSI-LD + pipeline APIs | CC-15…CC-22 |
| **D2b Kubernetes operator + CRDs** | `Subscription`, `Registration`, `Pipeline` as CRDs; controller converges | apisix-ingress-controller pattern |
| **D2c Terraform provider** | NGSI-LD resources as a TF provider; state file is the diff engine | terraform-provider-keycloak analogy |
| **D2d Imperative scripts** | idempotent seed scripts run by CI/hand; no diffing | portal-API-as-code recipe (CIVITAS bb geoserver) |
| **D2e None (UI is authoritative)** | changes made live in UI; export is the only code artifact | NiFi flow registry |

### D3, Infrastructure packaging

| Option | Description | Precedent |
|---|---|---|
| **D3a Helmfile + component modules** | one `charts.yaml`/`values`/`helmfile.yaml.gotmpl` per component, one `global.yaml` per environment | civitas-core-deployment, minimal-production |
| **D3b Terraform-everything** | TF for cloud + helm_release/kubectl providers for workloads | azure infrastructure-modules v2.0.0 + infrastructure-live |
| **D3c Terraform for cloud, helmfile for workloads** | clean split at the kubeconfig boundary | current CIVITAS Hetzner/AKS practice |
| **D3d Operator/umbrella chart** | one meta-chart deploys the whole platform | fiware/data-space-connector umbrella chart |

### D4, APISIX configuration mode

| Option | Description | Trade-off |
|---|---|---|
| **D4a etcd + Admin API** | routes created at runtime by a control component | dynamic, but Admin API is a mutable-state surface to secure |
| **D4b Standalone declarative** | `apisix.yaml` from ConfigMap, `etcd.enabled: false`, no Admin API at all | pure GitOps; reload-on-change; Admin API attack surface gone |
| **D4c Ingress controller + ApisixRoute CRDs** | routes are Kubernetes resources | K8s-native GitOps; couples gateway config to K8s API |
| **D4d Hybrid** | static platform routes declarative; per-flow routes via a narrow, policy-guarded Admin API client | manual apisix OWS route incident argues for D4b/D4c defaults |

### D5, Pipeline engine

| Option | Description | Fit |
|---|---|---|
| **D5a Bento** | single YAML per pipeline, stateless, lints in CI, native GitOps citizen | CC-11; hfp-bento demo proved broker-ingest recipes |
| **D5b NiFi** | visual flow programming, flow registry for versioning, UI-first | strong for [H] users; JSON flow exports diff poorly |
| **D5c Bento default + NiFi optional** | Bento for production flows; NiFi as an authoring/exploration tool whose flows are ported to Bento before productionizing | keeps Git diffs meaningful |
| **D5d NiFi + Registry as its own plane** | accept a second, NiFi-native versioning plane beside Git | two sources of truth |

### D6, Data-space integration

| Option | Description | Precedent |
|---|---|---|
| **D6a FIWARE Data Space Connector (umbrella Helm)** | TMForum + contract-management + VCVerifier; NGSI-LD-native; separate CB for the exposed data service in production | data-space-connector docs |
| **D6b FDSC-EDC enabled** | D6a plus the Eclipse EDC bridge for IDSA Dataspace Protocol interoperability | data-space-connector roles doc |
| **D6c Eclipse EDC standalone** | pure DSP connector; NGSI-LD exposure is custom work | drops the TMForum/ODRL→Policy mapper synergy (ADR 003) |
| **D6d Deferred** | design the seams (ADR 003 mapper, receiverInfo slots), ship without a connector | smallest v1 |

### D7, User-facing configuration UX

| Option | Description | Precedent |
|---|---|---|
| **D7a Blueprint/flow gallery** | parameterized templates → expanded manifests → merge request; Git invisible to [H] | CC-23…CC-39 |
| **D7b Direct CRUD UI + export/import** | UI edits live objects; export YAML/JSON; import replays | classic admin console |
| **D7c In-app YAML editor** | expert mode edits manifests with schema validation | gated by role in CC-30 |
| **D7d MCP/agent surface** | agents propose changes through the same repository path | CC-45…CC-48; additive to any of the above |

### D8, Project duplication and portability

| Option | Description |
|---|---|
| **D8a Repository template** | new city/project = clone template repo + set parameters; `apply` recreates everything (CC-50) |
| **D8b Export archive** | one-click download of the repo (or DB dump) at a revision; import bootstraps a new instance (CC-49) |
| **D8c Copier/scaffold components** | copier templates generate component skeletons (civitas-component-builder pattern) |
| **D8d Helm values-per-instance** | duplication = new values file against the same umbrella chart (infrastructure layer only) |

---

## 3. Coherent combinations (the approaches to evaluate)

Free combination of D1–D8 yields thousands of cells; most are
incoherent (a Terraform provider reconciling against a UI-owned
database fights itself). These seven are the internally consistent
stacks worth deep evaluation. Each gets a letter used by the goal
below.

### Approach A, Pure city-as-code (the committed baseline)

D1a + D2a + D3c + D4b + D5a + D6a/b + D7a+c+d + D8a+b

Git is the only truth; `cityctl` is the only writer; the UI is a
blueprint gallery that writes commits; APISIX runs declarative;
Bento pipelines are opaque versioned YAML. This is exactly
CC-01…CC-70.

- **For**: perfect audit (CC-44), trivial export/duplicate (CC-49/50),
  broker replaceable (CC-01), blue/green upgrades (CC-51), no Admin
  API surface.
- **Against**: `cityctl` and the blueprint app are bespoke builds; the
  merge-request loop adds minutes of latency (CC-56); a forge outage
  freezes config changes (accepted by CC-55).
- **Open risks to verify**: normalization diffing (CC-17) against
  JSON-LD expansion is genuinely hard; form-from-JSON-Schema UX
  quality; whether [H] users accept approval latency.

### Approach B, Kubernetes-native operator

D1a + D2b + D3a + D4c + D5a + D6a + D7a + D8d

Everything is a CRD: `ContextSpace`, `CityCSR`, `CitySubscription`,
`BentoPipeline`; Flux/Argo syncs the repo; an operator converges CRDs
to broker state; APISIX config rides ApisixRoute CRDs.

- **For**: reuses battle-tested GitOps machinery (Argo UI gives status,
  diff, drift for free); one reconciliation idiom for infra and
  config.
- **Against**: couples the configuration plane to Kubernetes (violates
  the spirit of CC-57 portability to non-K8s edge sites; Antares
  targets 35 MiB edge boxes where there is no cluster); writing a
  correct operator is more work than a CLI; CRD schema evolution is
  painful; the broker gains a K8s dependency in practice even if not
  in code.

### Approach C, Terraform-everything

D1a + D2c + D3b + D4a-via-provider + D5a + D6a + D7b + D8d

One language for cloud, cluster, workloads, and configuration: a
custom `terraform-provider-ngsild` plus the existing APISIX provider.

- **For**: one tool, one state, one plan/apply UX; import command
  covers adoption.
- **Against**: TF state becomes a second truth beside Git (state-file
  drift, locking, secrets-in-state); providers for NGSI-LD don't
  exist (bespoke build, HCL wrapping of JSON-LD is exactly the
  proprietary-DSL smell CC-09 bans); [H] users never touch it, so a
  full UI must still be built; apply latency and blast radius are
  worse than a scoped reconciler.

### Approach D, UI-first with export (the classic console)

D1b + D2e + D3a + D4a + D5b + D6a + D7b + D8b

The platform UI owns configuration in its own database; NiFi owns
flows; APISIX is driven through the Admin API; users export/import
YAML/JSON archives and duplicate projects from snapshots.

- **For**: shortest path to a demo; zero Git friction; NiFi's canvas
  is genuinely good for exploratory pipeline authoring; import/export
  and duplicate are natural first-class buttons.
- **Against**: snapshots are backups, not truth (no review, no diff,
  no CI validation, no CC-44 audit chain); drift is undefined because
  everything is drift; broker replacement and blue/green (CC-50/51)
  degrade into migration projects; Admin API + NiFi canvas are two
  large mutable attack surfaces; fails CC-02/03 outright.

### Approach E, Hybrid bidirectional sync

D1d + D2a + D3c + D4d + D5c + D6a + D7b + D8a+b

UI writes live for instant feedback; a continuous exporter commits the
resulting state to Git ("adopt by default"); `cityctl apply` is used
for restore, duplicate, and promotion between environments.

- **For**: UI latency of Approach D with the portability of A;
  duplication and DR still work from Git.
- **Against**: two writers → merge conflicts between live edits and
  Git edits are structural, not accidental; approval becomes advisory
  (change is already live when reviewed), gutting CC-34/CC-44;
  history records what happened, not what was intended. Every team
  that ships this converges back to one-way flow eventually.

### Approach F, Broker-as-config-store

D1c + D2a-thin + D3c + D4b + D5a + D6a + D7b + D8b

Push ADR 002/005 to its conclusion: subscriptions, CSRs, pipeline
descriptors, even blueprints live as NGSI-LD entities in a dedicated
config tenant. The UI does plain NGSI-LD CRUD; export = entity dump;
temporal API gives change history for free.

- **For**: no new storage, no forge dependency; NGSI-LD temporal
  history is a built-in audit log; MCP/agents use the same API as
  everything else; maximally spec-native.
- **Against**: the broker becomes self-hosting (bootstrap problem:
  who configures the config tenant?); Git-grade review/approval must
  be reinvented on top of entity operations; CC-01 is stressed, the
  broker is now availability-critical for its own configuration;
  pipeline YAML wrapped in entities is awkward.

### Approach G, Minimal ops-only (no user plane yet)

D1a + D2d + D3c + D4b + D5a + D6d + D7 none + D8a

Manifests in Git, applied by idempotent CI scripts; no reconciler
diffing, no UI. What the CIVITAS bb deployments do today, formalized.

- **For**: exists now; smallest bespoke surface; every later approach
  can grow out of it.
- **Against**: no [H] surface at all (fails the "user can use UI"
  requirement); no drift detection; deletes are manual; scripts
  accumulate broker-specific hacks without CC-16 discipline.

---

## 4. Evaluation criteria

Score each approach 1–5 per criterion, with written evidence (cite
workspace docs, requirement IDs, or a runnable probe).

| # | Criterion | Anchored in |
|---|---|---|
| C1 | Future-proofness: broker/gateway/pipeline each replaceable without config rewrite | CC-01, CC-50–52 |
| C2 | Ease of configuration for [H] users (forms, no Git/YAML exposure) | CC-29–39 |
| C3 | Code-first power for [P]/[A] (CI, CLI, MCP parity) | CC-45–48 |
| C4 | Import/export and project duplication as first-class, low-friction operations | CC-49–50, user requirement |
| C5 | Audit and EU-funding accountability (who/what/when/approved-by) | CC-44, CC-58 |
| C6 | Security surface (mutable admin APIs, write paths, bypass routes) | R1–R43, GW rules, architecture invariant |
| C7 | Drift handling (detect, revert, adopt) | CC-21–22, CC-38 |
| C8 | Bespoke-build cost (what must be written and maintained by us) | ponytail: laziest stack that holds |
| C9 | Data-space readiness (DSP/ODRL contract → local policy provisioning) | ADR 003, D6, architecture invariant |
| C10 | Edge/non-K8s deployability of the configuration plane | Antares edge posture, CC-57 |

Disqualifiers (automatic fail regardless of score): a second
enforcement path around the PEP; configuration writes that bypass the
declared source of truth; plaintext secrets in exports (CC-06).

## 5. Initial scoring (hypothesis, the autonomous pass must verify)

| | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 | Σ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** city-as-code | 5 | 4 | 5 | 5 | 5 | 5 | 5 | 2 | 5 | 4 | **45** |
| **B** K8s operator | 4 | 4 | 4 | 4 | 5 | 4 | 5 | 2 | 4 | 1 | 37 |
| **C** Terraform | 3 | 1 | 4 | 3 | 4 | 3 | 4 | 2 | 3 | 3 | 30 |
| **D** UI-first | 2 | 5 | 2 | 4 | 2 | 2 | 1 | 3 | 3 | 3 | 27 |
| **E** hybrid sync | 3 | 5 | 4 | 4 | 2 | 3 | 2 | 1 | 4 | 3 | 31 |
| **F** broker-store | 4 | 3 | 4 | 4 | 3 | 3 | 3 | 3 | 4 | 4 | 35 |
| **G** ops-only | 4 | 0 | 3 | 3 | 3 | 4 | 1 | 5 | 2 | 4 | 29 |

Working recommendation: **A** as the target, **G** as the migration
starting point (G → A is additive: add `cityctl` diffing, then
blueprints, then the app), with **F**'s idea kept where it is already
decided (policies and scopes as entities per ADR 002/005) and **D5c**
(NiFi as optional authoring tool, never as truth) if [H] pipeline
authoring demand materializes. This matches what
`../requirements/city-as-code.md` already commits to; the evaluation pass
exists to stress-test that commitment against B–F rather than assume
it.

---

## 6. Goal for the autonomous evaluation pass

Paste as the `/goal` completion condition (or run manually) in a
session rooted at `/workspace`:

```text
/goal For each approach A–G in docs/research/configuration-plane-approaches.md,
produce docs/evaluations/approach-<letter>.md containing: (1) a score
1–5 for every criterion C1–C10 with at least one cited piece of
evidence per score — a workspace file+section, a requirement ID
(CC/R/GW/ADR), or an executed probe (e.g. rendering the APISIX
standalone ConfigMap, dry-running a helmfile template, drafting one
CRD or one Terraform resource schema and noting where it breaks); (2)
an explicit check against the three disqualifiers; (3) the two
strongest arguments AGAINST the approach, steelmanned; (4) a
migration-path note: what G→<letter> would require. Scores must not be
copied from the hypothesis table in section 5 — recompute them and
flag every cell where your score differs by ≥2 with a one-paragraph
justification. Then rewrite section 5 of
docs/research/configuration-plane-approaches.md with the verified matrix and a
final ranked recommendation, and update registers/decision-register.md with
a one-line "Configuration plane" decision row (status Proposed). The
goal is met when all seven evaluation files exist with all four parts,
every C-score cell in section 5 carries verified numbers, and the
decision-register row exists.
```

Sizing note: one evaluation ≈ one focused agent; the probes in (1) are
what makes this verification rather than opinion re-statement.

## Related

- [01-overview](../Architecture/01-overview.md) — what the platform took from this study.
