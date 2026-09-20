---
sidebar_position: 6
title: "ADR-N-005: Reconciler `jcctl` in Rust with Minijinja Templating"
---

# ADR-N-005: Reconciler `jcctl` in Rust with Minijinja Templating

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

## 1. Context

The Configuration-as-Code architecture (ADR-N-004) requires a reconciler CLI and daemon (`jcctl`) that computes diffs between desired Git state and live platform state, executing converged apply operations.

Early research (stack verdicts S1 and S3) proposed Go using `piprate/json-gold` and CUE for template expansion. However, during concrete architectural evaluation, several drawbacks emerged:

1. CUE requires embedding large Go runtimes and its CUE-to-JSON-Schema generator (`encoding/jsonschema`) is newly released and unstable.
2. The context broker's AST parsing engine (`antares-ql`) is implemented in Rust. Building `jcctl` in Go would require either compiling CGO FFI bindings or maintaining a duplicate NGSI-LD parser.
3. We require single static binaries for lightweight edge deployment (sub-35 MB).

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Model-driven data flow | **Full** | `jcctl` compiles LinkML and blueprint manifests into live NGSI-LD entities. |
| Distributed architecture with unified UX | **Full** | Provides both CLI for DevOps/CI and `serve` mode for Portal API integration. |
| Modular design | **Full** | Decoupled core library (`jcctl-core`) with CLI and daemon entry points. |
| Integrability via defined interfaces | **Full** | Uses strictly standard CIM 009 REST operations against the broker. |
| Open source as default | **Full** | Built with Rust community crates (Minijinja, Reqwest, Tokio). |
| Cloud-native architecture | **Full** | Single static binary (`CGO_ENABLED=0`), zero external runtime dependencies. |
| Standard solutions before custom code | **Full** | Uses Jinja2 specification standards implemented via Minijinja. |
| Self-contained deployment | **Full** | Operates standalone without external daemon requirements. |
| Technological consistency | **Full** | Unifies platform core backend components on Rust. |
| Multi-tenancy | **Full** | Reconciles organization spaces deterministically across wave hierarchies. |
| Security by design | **Full** | Sandboxed template execution; no arbitrary host filesystem access. |

## 3. Decision

1. **Build `jcctl` in Rust**:
   - Replaces the previously hypothesized Go + CUE stack (superseding stack verdicts S1 and S3).
   - Implemented as a modular library (`jcctl-core`) and a single static CLI/daemon binary (`jcctl`).
2. **Minijinja for Blueprint Expansion**:
   - Blueprints expand parameter schemas into concrete manifests using `minijinja` (sandboxed Jinja2 implementation in Rust).
   - Enforces strict determinism (CC-25): filesystem access disabled, environment variables disabled, map iteration order sorted stably.
3. **JSON-LD Structural Diffing**:
   - Live diffing expands both manifest and broker JSON-LD payloads using `@context`, stripping server-assigned system attributes (`createdAt`, `modifiedAt`, `status`), and diffing the normalized AST trees (CC-17).
   - Evaluates attribute-level ownership (CC-69), diffing only attributes declared as managed.
4. **Wave-Based Ordering**:
   - Executes apply operations in strict dependency waves:
     `Wave 1: ContextSpaces → Wave 2: DataModels → Wave 3: Policies/Scopes → Wave 4: Seed Entities → Wave 5: Subscriptions & CSRs → Wave 6: Pipelines & Endpoints`.

## 4. Consequences

### Positive

- **Native AST Sharing**: Directly links `antares-ql` to validate and normalize NGSI-LD queries without FFI overhead or grammar duplication.
- **Sub-30 MB Single Binary**: Fits the organisational edge deployment profile; runs in CI containers with zero setup latency.
- **Deterministic Blueprint Output**: Sandboxed Jinja templating guarantees byte-identical manifest generation.

### Negative / Trade-offs

- JSON-LD expansion and RDF canonicalization routines in Rust (`json-ld` crate) must be carefully monitored for specification compliance.
- Jinja templating is less structurally typed than CUE, requiring CI schema validation (draft-07) to catch invalid outputs.

## 5. See Also

- Supersedes: Research stack verdicts S1 (Go) and S3 (CUE).
- Requirements: [CC-15…CC-22 (Reconciler)](../Requirements/city-as-code.md), [TS-20, TS-21 (Reconciler Gates)](../Requirements/testing.md).

## Related

- [CC-15…CC-22 (Reconciler)](../Requirements/city-as-code.md) — referenced above.
- [TS-20, TS-21 (Reconciler Gates)](../Requirements/testing.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
