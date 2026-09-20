---
sidebar_position: 2
title: "Stack Research: City-as-Code"
---

# City-as-Code, Concrete Stack Verdicts (per seam)

Status: Draft, research output
Date: 2026-08-18
Question: for each technology seam of the plane specified in
`../requirements/city-as-code.md` (CC-01…CC-70) and shaped by
`city-as-code-prior-art.md` (P1–P6), which concrete 2026 technology is
the right choice, and where is the current assumption wrong?
Method: targeted web research against primary sources (official docs,
release notes, licenses, repository activity, issue threads). Every
verdict carries a confidence level. Claims marked *reasoned* are
engineering conclusions from the cited facts, not sourced claims.
Related: `../requirements/city-as-code.md`, `city-as-code-prior-art.md`,
`configuration-plane-approaches.md`.

Seam IDs S1–S10. Architecture is not revisited: approach A stands.

---

## 1. Summary table

| Seam | Verdict | Runner-up | Assumption status |
|---|---|---|---|
| S1 JSON-LD core + language | **Go + `piprate/json-gold`** | Rust + `json-ld` + `rdf-canon` | refined |
| S2 Forge | **Gitea, but the CODEOWNERS rule is unreleased** | Forgejo | ⚠️ **GitLab CE disqualified** |
| S3 Template engine | **CUE (internal), JSON Schema (contract)** | Go `text/template` | confirmed, and it pins S1 |
| S4 Form generation | **react-jsonschema-form on draft-07** | JSON Forms | ⚠️ **2020-12 is untested** |
| S5 Pipeline engine | **`warpstreamlabs/bento` (MIT fork)** | Vector | ⚠️ **name the fork, not Bento** |
| S6 Secrets | **SOPS+age (city), OpenBao (region)** | Infisical | ⚠️ **"Vault-class" must become OpenBao** |
| S7 Gateway | **APISIX standalone file mode** | Kong DB-less | confirmed, 2 traps |
| S8 Existing NGSI-LD tooling | **none found: build stands** | n/a | confirmed (absence of evidence) |
| S9 Portal + MCP | **MCP as OAuth 2.1 resource server, Streamable HTTP** | n/a | refined |
| S10 Auto-merge + CI gates | **Gitea native auto-merge + Conftest** | `gitea-mq` | ⚠️ **Mergify/Kodiak unusable** |

Three seams change a committed document. S2 removes an option the docs
treat as equal. S5 and S6 replace a product name with a specific fork.

---

## 2. S1, Reconciler language and JSON-LD core

**Verdict: Go, with `piprate/json-gold`. Confidence: medium-high.**

Both candidate ecosystems are alive, contrary to the assumption that
this is a one-sided comparison:

| | Go `piprate/json-gold` | Rust `json-ld` (timothee-haudebourg) |
|---|---|---|
| Spec | JSON-LD 1.1, plus Framing 1.1 | expansion, compaction, flattening |
| Canonicalization | **URDNA2015 and URGNA2012 built in** | separate crate (`rdf-canon`) |
| Test suite | aims at the official W3C suite | wires the W3C suite in via `json-ld-testing` |
| Activity | v0.8.0 published Feb 2026; commits through Feb 2026 | ~450 commits, SpruceID-sponsored, used by `ssi` |
| Remote `@context` | yes | yes (`reqwest-loader`, `FsLoader`, `NoLoader`) |

An earlier reading that `json-gold` was abandoned since 2022 was wrong:
the GitHub releases page reports inconsistent dates, while pkg.go.dev
and the commit history both show Feb 2026 activity including
performance work. Anyone re-checking this should trust pkg.go.dev.

Go wins on three couplings rather than on library quality:

1. **CUE embeds as a Go library** (S3). CUE's comprehensive API is a Go
   API. A Rust reconciler would shell out to the `cue` binary, which
   costs the determinism guarantee CC-25 depends on (subprocess version
   skew becomes a correctness bug).
2. **Canonicalization ships in the same library** as expansion, instead
   of composing two crates whose spec versions can drift.
3. **A Terraform provider is a Go plugin.** The adapter route in
   prior-art §6 is native, not an FFI exercise.

Rust remains the runner-up and is the right answer if sharing code with
the Antares broker or a wasm build (in-browser plan preview) later
outweighs the CUE coupling. Note that `json-ld` documents itself as
early development with only part of the algorithm set implemented,
though expansion plus compaction is in fact all this plane needs.

### The diffing question (CC-17)

**Canonicalization is the wrong primary tool. Use JSON-LD expansion plus
a structural diff over the expanded form. Reasoned.**

RDFC-1.0 / URDNA2015 produce a canonical N-Quads serialization whose
purpose is a stable hash, answering "are these two documents
identical?". CC-15 requires the opposite: which attribute changed, so
`plan` can print a field-level diff. Canonicalization collapses exactly
the structure the operator needs to see.

The correct shape: expand both sides against the manifest `@context`,
then diff the expanded trees with NGSI-LD-aware rules (member ordering
insignificant, `datasetId` maps keyed rather than positional,
server-managed members stripped per CC-17). Keep canonicalization as an
optional fast-path equality check to skip the structural diff when two
documents hash identically. Attribute-level ownership (CC-69) then
filters the diff, it does not need canonical form at all.

## 3. S2, Forge: the CC-41 problem

**Verdict: Gitea, and CC-41 is not fully satisfiable today.
Confidence: high.**

`CC-41` and `CC-42` require domain ownership through directory-scoped
code owners and change approval through protected-branch required
approvals. Enforced code-owner approval does not exist in any free
self-hostable forge as of 2026-08-18:

- **GitLab CE: disqualified.** Required approvals are Premium/Ultimate;
  code-owner lists for specific files are Premium/Ultimate. GitLab Free
  lets any Developer approve, and those approvals do not block a merge.
  `city-as-code-prior-art.md` §3 lists "Gitea or GitLab CE" as
  equivalent options. They are not equivalent, and the CE half fails
  the EU-funding, no-paid-license posture.
- **Gitea 1.27.2 (latest stable, 2026-08-13): partial.** No "require
  review from code owners" toggle. Issue #32602 states the defect
  plainly: a non-owner with write access who approves "still counts as
  a valid approval". Closest available mechanism is *Block merge on
  official review requests*, which blocks merging while review requests
  are outstanding, including those CODEOWNERS generated.
- **Gitea 28.0.0 (unreleased): solves it.** PR #34995 merged
  2026-07-31 adds a branch-protection rule that blocks merging while
  reviews from code owners are pending, evaluating each CODEOWNERS rule
  individually. Not present in any released version.
- **Forgejo: no.** Issue #5179 open since 2024-08-30, implementation
  started July 2026 by porting the Gitea work.

Gitea does satisfy CC-58: *Disable force push* "completely forbids
rewriting history on the branch", alongside required-approval counts,
stale-approval dismissal or exclusion, push allowlists, merge
allowlists, status checks, signed-commit requirements and protected
file patterns.

**Interim mechanism (until 28.0.0 ships):** *Block merge on official
review requests* + required approvals + CI re-validation of ownership.
CC-59 already mandates that CI re-check `allowedRoles` and `riskClass`
on every merge request, so in the interim CI carries the enforcement
and the forge carries the review routing. Document this as the
enforcement path rather than implying the forge does it.

**A maintainer objection worth absorbing into CC-42.** Forgejo's
Andreas Ahlenstorf: if the CODEOWNERS file is not itself protected,
"CODEOWNERS can easily be circumvented and it becomes security
theatre". CC-42 claims the forge independently enforces the same
boundary as the portal, but that claim is circular while a domain
editor can edit the file that defines their own ownership. Add: the
`CODEOWNERS` file and the platform settings file are owned by *city
admin* only, via protected file patterns, and changes to them are
red-lane (CC-70 already says this for lane policy).

## 4. S3, Blueprint template engine

**Verdict: CUE internally, JSON Schema as the user-facing contract.
Confidence: medium.**

CUE has first-class JSON Schema support in both directions through both
the `cue` command and the Go API, and the Go `encoding/jsonschema`
package gained a `Generate()` function for CUE-to-JSON-Schema published
2026-07-16. That validates the optional suggestion in prior-art §1.11
and satisfies CC-12 plus CC-24 from one source: author the parameter
schema in CUE, emit JSON Schema for the portal's form generator, keep
the repository surface free of any DSL per CC-09.

Caveat: the generation direction is new (July 2026), so treat
CUE-to-JSON-Schema output as needing a golden-file test in CI rather
than as settled infrastructure. KCL is the credible alternative with
SDKs across more languages; it loses on the JSON Schema round-trip
being less central to its design. This seam pins S1 to Go, per above.

## 5. S4, Form generation from JSON Schema

**Verdict: react-jsonschema-form, pinned to draft-07. Confidence: high
on the constraint, medium on the library choice.**

The flag: `@rjsf/validator-ajv8` defaults to draft-07, and the project
documents that "`draft-2020-12` has breaking changes and hasn't been
fully tested with `@rjsf`". AJV 8 itself supports 2020-12; RJSF's own
schema-resolution layer on top of AJV is what is untested, because RJSF
uses AJV to resolve `anyOf`/`oneOf` selection, dependencies,
`if/then/else` and `$ref` through `retrieveSchema()`.

Consequence for CC-12 and CC-24: **specify draft-07 as the blueprint
parameter-schema dialect**, not "JSON Schema" unqualified. Conditionals
are supported (RJSF merges the `then`/`else` branch into the schema
before rendering), so the guardrail patterns in CC-60 are expressible.

Unverified in this pass: WCAG 2.1 AA conformance of generated forms,
Slovak i18n path, and the async entity-picker widget (CC-31 needs a
picker fed by a live gateway query under the user's own token, which is
a custom widget in every candidate library). Treat the entity picker as
bespoke work in all cases.

## 6. S5, Pipeline engine

**Verdict: `warpstreamlabs/bento` (MIT). Confidence: high.**

The history matters for procurement: Redpanda acquired Benthos,
rebranded it Redpanda Connect, redirected the community, and relicensed
away from MIT to a mix of Apache 2.0 and the Redpanda Community
License, moving several important connectors, including
contributor-written ones, under commercial terms. WarpStream forked the
pre-acquisition code as **Bento**, MIT, and maintains it as the
continuation. The repository shows ~5.7k commits, ~2.1k stars, and
both MQTT and HTTP (server and client) sources and sinks, which is
exactly the CC-11 ingestion job.

Action: CC-11 and prior-art §3 say "Bento", which is now ambiguous.
Write `warpstreamlabs/bento` explicitly, and record that
`redpanda-data/connect` is disqualified on licensing for a
decade-horizon municipal commitment. Vector is the runner-up and would
force a rewrite of the existing hfp-bento recipes.

## 7. S6, Secrets

**Verdict: SOPS+age for a city, OpenBao for a region. Confidence:
high on licensing, medium on the split.**

HashiCorp moved Vault from MPL 2.0 to BSL 1.1 in August 2023; each
release converts to MPL 2.0 four years after its date. **OpenBao** is
the community fork of Vault 1.14.0, the last MPL 2.0 version, hosted
under the Linux Foundation, MPL 2.0, initiated by IBM engineers but not
an IBM product, and API-compatible with Vault (auth methods, secrets
engines, policies work unchanged). Recent work added namespaces and
horizontal read scalability.

Action: prior-art §9.2 says "Vault-class". For an EU-funded municipal
procurement that phrase is a liability, since BSL is not open source by
OSI terms. Name OpenBao. The external-secrets *pattern* in §9.2
(references in Git, values in the store, reconciler resolves at apply,
plan/export redact) is unaffected and remains correct.

## 8. S7, Gateway declarative mode

**Verdict: APISIX standalone file mode. Confidence: high.**

Configured with `deployment.role: data_plane` and
`deployment.role_data_plane.config_provider: yaml`, APISIX drops etcd,
loads `conf/apisix.yaml` into memory at startup, and re-checks the file
on a 1-second interval, hot-reloading rules in memory with no worker
replacement. Critically for D4b and R1: **the Admin API cannot be
enabled in this mode**, because the Admin API is built on the etcd
solution. The zero-mutable-admin-surface property the design wants is
structural, not a configuration choice.

Two operational traps to record:

1. **`#END` marker required.** APISIX will not load rules from
   `conf/apisix.yaml` if the file does not end with `#END`. A rendered
   ConfigMap that loses this marker silently serves no routes.
2. **1-second poll, not an event.** Reload latency is bounded by the
   file-poll interval, which matters for the CC-65 green-lane latency
   budget.

Open item: APISIX 3.15 has a "standalone api-driven" mode (issue 12989
concerns it still contacting etcd in that mode). Whether that
mode reintroduces a mutable write surface was not established here and
should be checked before any version bump, since D4b's security
argument depends on the answer.

## 9. S8, Existing NGSI-LD tooling (anti-duplication)

**Verdict: no declarative NGSI-LD reconciler found. The build stands.
Confidence: medium (absence of evidence, not evidence of absence).**

Three targeted searches across FIWARE tooling, Kubernetes operators,
Terraform providers and Ansible collections returned no project that
reconciles NGSI-LD entities, subscriptions, context source
registrations or tenants from declarative files. What exists in the
FIWARE ecosystem for this job is tutorial-grade: curl sequences and
Postman collections for creating subscriptions and registrations.

This supports prior-art §3's "nothing speaks NGSI-LD" premise and its
conclusion that the reconciler is the one irreducible build. Stated
honestly: repeated failure to find a tool is weaker evidence than
finding one, and this should be re-checked before implementation
starts, particularly inside the FIWARE GitHub organisation and among
Stellio and Orion-LD deployment repositories.

## 10. S9, Portal and MCP surface

**Verdict: MCP server as an OAuth 2.1 resource server over Streamable
HTTP. Confidence: medium (sources are largely secondary).**

The 2026 shape of a self-hosted MCP server:

- The MCP server is a **resource server only**. It validates tokens
  issued by an external authorization server (Keycloak, I1) and
  enforces permissions internally. It never handles logins or issues
  tokens. This matches CC-40 exactly: every component is an ordinary
  OIDC client.
- **Streamable HTTP replaced HTTP+SSE**, giving a single endpoint that
  survives load balancers and proxies.
- A **July 2026 spec revision removed long-lived streams**: transport
  is stateless, authorization errors return per request, and a server
  may only make requests to a client while processing that client's
  request. Do not design the plane's MCP server around a persistent
  stream.
- Discovery and audience binding: publish
  `/.well-known/oauth-protected-resource` per RFC 9728, validate bearer
  tokens, and enforce RFC 8707 resource indicators so a token minted
  for another service cannot be replayed at the MCP server. Reported
  SDK support: TypeScript `@modelcontextprotocol/sdk` 1.29.0
  `StreamableHTTPServerTransport`, Python SDK 1.23+ with built-in
  OAuth 2.1 resource-server support.

CC-47's grounding requirement (revision and timestamp on every
live-state answer) is unaffected and remains a local design choice.
Portal framework and the Keycloak PKCE library were not settled in this
pass.

## 11. S10, Green-lane auto-merge and CI gates

**Verdict: Gitea native auto-merge plus Conftest in CI. Confidence:
medium.**

- **Mergify, Kodiak and the auto-merge GitHub Actions are unusable
  here.** They are GitHub Apps or GitHub-Actions-bound. The green lane
  (CC-63…CC-66) cannot be bought; it is a small Gitea/Forgejo Actions
  job plus the forge's own auto-merge.
- **Gitea has "Merge when checks succeed"**, and `gitea-mq` exists as a
  self-hosted merge-queue that drives it by setting a commit status.
  This is the mechanism for "policy bot auto-approves", inverted: CI
  validates, sets the status, and the forge merges. That is a better
  fit for CC-64 than a bot with merge rights, because the audit trail
  stays in the status checks.
- **Forgejo reportedly lacks auto-merge**, achievable only by wiring
  webhooks plus Actions, described as not reliably automatable. A
  second reason S2 lands on Gitea.
- **Conftest** (OPA project, single binary, self-hosted) evaluates Rego
  against YAML/JSON in CI and is the natural gate for CC-59 and CC-60
  metadata: `allowedRoles`, `riskClass`, quotas, allowed entity types,
  scope confinement. Evaluation is in-memory and effectively instant at
  configuration-tree sizes; deep recursion and large bundles are the
  documented slow paths, so keep policies modular.

CUE `vet` is the alternative and would consolidate S3 and S10 into one
language. Not compared head-to-head with Rego here; that comparison is
worth running before committing, since one language for both schema and
policy is a real simplification.

Latency: with a webhook-triggered apply (CC-65) the credible floor is
CI duration plus the S7 1-second config poll. Seconds is achievable;
the poll interval and CI cold-start dominate, not the merge.

---

## 12. Cross-cutting: one core, four wrappers

**Write `cityctl-core` in Go. Do not build an FFI layer. Confidence:
medium.**

The FFI question in prior-art §6 dissolves once each host's actual
integration contract is examined:

| Wrapper | Real contract | Binding needed |
|---|---|---|
| `cityctl` CLI/daemon | the binary itself | none |
| Terraform provider | separate binary, gRPC to Terraform | none: link the Go core directly |
| Ansible module | process invocation, JSON on stdin/stdout | none: subprocess |
| Backstage plugin | HTTP to `cityctl serve` | none: REST |

Three of the four are process boundaries, not library boundaries. The
deliverable that makes wrappers cheap is therefore a **stable JSON
contract on the CLI and `serve` API**, plus semver and golden-file
tests on `plan` output (prior-art §9.4 already requires the latter).
An FFI layer would be built for no consumer.

Go carries the two library couplings that are real: CUE's Go API (S3)
and Terraform's Go plugin model. `CGO_ENABLED=0` gives the static
binary CC-57 and the edge posture require.

Choose Rust instead only if a wasm build of the core (in-browser plan
preview against the wasm broker) or code sharing with Antares becomes a
requirement. In that case CUE must be replaced by a Rust-native
deterministic templater, since shelling out to `cue` forfeits CC-25.

## 13. Document changes this implies

**All seven edits below were applied to the target documents on
2026-08-23** (docs restructure). Kept here as the record of what this
research changed upstream; the canonical text now lives in the edited
files.

1. `city-as-code-prior-art.md` §3: replace "Gitea or GitLab CE" with
   Gitea, and record GitLab CE's paywall as the reason (S2).
2. `../requirements/city-as-code.md` CC-11 and prior-art §3: write
   `warpstreamlabs/bento`, and note `redpanda-data/connect` is
   licence-disqualified (S5).
3. prior-art §9.2: replace "Vault-class" with OpenBao (S6).
4. `../requirements/city-as-code.md` CC-12/CC-24: state draft-07 as the parameter
   schema dialect (S4).
5. `../requirements/city-as-code.md` CC-42: add that `CODEOWNERS` and the platform
   settings file are city-admin-owned and red-lane, closing the
   circularity (S2).
6. `../requirements/city-as-code.md` CC-41: add the interim enforcement note, that CI
   re-validation carries ownership enforcement until Gitea 28.0.0
   ships (S2).
7. `../requirements/city-as-code.md` CC-17: state that diffing is expansion plus
   structural diff, with canonicalization as an equality fast path only
   (S1).

## 14. Open questions

1. Does the APISIX 3.15 "standalone api-driven" mode reintroduce a
   mutable write surface, and does D4b's argument survive it?
2. CUE `vet` versus Conftest/Rego for CC-59/CC-60 validation: does one
   language for schema and policy win?
3. WCAG 2.1 AA and Slovak i18n status of RJSF-generated forms
   (CC-37 is a hard requirement, and this pass did not settle it).
4. Gitea 28.0.0 release date, which sets when CC-41 becomes fully
   forge-enforced.
5. Is there NGSI-LD reconciliation tooling inside the FIWARE GitHub
   organisation that three searches missed (S8)?

## Related

- [01-overview](../Architecture/01-overview.md) — what the platform took from this study.
