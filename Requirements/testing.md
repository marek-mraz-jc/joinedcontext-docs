---
sidebar_position: 8
title: "Testing & Quality Assurance"
---

# Testing & Quality Assurance

Family **TS** (TS-01…TS-25). Owning chapter: [01-overview.md](../Architecture/01-overview.md). Verified by: [00-strategy.md](../Testing/00-strategy.md).

This chapter specifies the normative verification pyramid, automated quality gates, and conformance suites required across all platform components.

## 1. Rust Core and Property-Based Testing

- **TS-01** — All Rust crates (Context Gateway, Portal API, `jcctl`, `antares-ql`) MUST maintain unit test coverage verified in CI.
- **TS-02** — Query Rewriting Soundness (R57): The Context Gateway MUST be tested using property-based testing (`proptest`) generating arbitrary permutations of user queries, entity schemas, and policy grant combinations, asserting:
  - **Read Soundness**: No returned entity or attribute falls outside the mathematical union of applicable grants.
  - **Write Soundness**: No accepted create or update payload violates any constraint in the governing policy.
  - **Privilege Bleed Invariance**: Cross-product leakage between distinct policy constraints is mathematically impossible (ADR 006).
- **TS-03** — Representation Translators: Automated property tests MUST verify bidirectional transformation invariants (NGSI-LD ↔ CSV/XLSX/GeoJSON/OGC/STA) ensuring that type semantics and nullability constraints are strictly preserved.
- **TS-04** — Code quality gates in CI MUST enforce `cargo clippy --all-targets -- -D warnings` and `cargo deny check` (licenses, advisories, bans) with zero warnings permitted.

## 2. Specification Conformance Testing

- **TS-05** — Context Broker Conformance: The context broker (Antares, Scorpio, or Stellio) MUST pass the official ETSI NGSI-LD Testing Task Force (TTF) Robot test suite for all supported API features.
- **TS-06** — Gateway Transparency: The ETSI NGSI-LD conformance test suite MUST also be executed against the Context Gateway running in front of the broker under an unrestricted administrative policy, verifying that the gateway introduces zero spec divergence (R15).
- **TS-07** — OGC API Conformance: The `ogc/features/` endpoint representation MUST pass the OGC API – Features Part 1: Core Abstract Test Suite (ATS).
- **TS-08** — SensorThings Conformance: The `sta/v1.1/` read-only representation MUST pass the OGC SensorThings API Sensing Profile conformance tests for all supported core collections.

## 3. Contract and Client Integrity Testing

- **TS-09** — The Portal API and Context Gateway management endpoints MUST be fuzzed in CI against their published OpenAPI specifications using `schemathesis`. Any unhandled panic, 500 Internal Server Error, or schema divergence MUST fail the pipeline.
- **TS-10** — The Portal UI build pipeline MUST recompile the TypeScript API client from the fresh OpenAPI specification and verify zero TypeScript compiler errors (`tsc --noEmit`).

## 4. Frontend, E2E, and Accessibility Testing

- **TS-11** [H] — Component Unit Tests: React UI components, custom hooks, and utility mappers MUST be tested using Vitest and Testing Library.
- **TS-12** [H] — End-to-End (E2E) Workflows: Automated browser tests using Playwright MUST execute against a live deployment environment in CI, validating:
  - User onboarding and initial password setup.
  - Blueprint instantiation and form submission.
  - In-app review and approval workflows.
  - Map dashboard interaction and layer filtering.
  - Playwright tests MUST interact exclusively with user-visible DOM elements (labels, buttons, roles), avoiding direct URL-manipulation shortcuts.
- **TS-13** [H] — Accessibility Audits: Automated accessibility scans using `@axe-core/playwright` MUST run against all core portal views during E2E test runs, enforcing zero WCAG 2.1 AA violations.
- **TS-14** [H] — Localization Integrity: CI MUST execute an automated translation check verifying that all ICU translation keys defined in `en.json` exist across `sk.json`, `de.json`, and `cs.json`.

## 5. Pipeline and Blueprint Verification

- **TS-15** — Pipeline Linting: CI pipelines MUST execute `bento lint` over every pipeline manifest in the repository.
- **TS-16** — Pipeline Golden Testing: Every data transformation pipeline MUST maintain a corresponding `test_definition.yaml` containing mock input events and expected outputs. CI MUST execute `bento test` and verify exact payload matches.
- **TS-17** — Blueprint Determinism: CI MUST re-render all committed blueprint instances against their declared templates and parameters, asserting that the output is byte-identical to the committed manifests (CC-25).

## 6. Manifest CI Gates and Reconciler Verification

- **TS-18** — Manifest Schema Validation: CI MUST validate every YAML manifest in the repository against its published JSON Schema draft-07 specification (CC-12).
- **TS-19** — Policy Guardrails: Conftest (OPA/Rego) gates in CI MUST assert that all proposed manifests adhere to organization quotas, permitted entity types, assigned roles, and scope boundaries (CC-59, CC-60).
- **TS-20** — Reconciler Plan Gate: CI MUST execute `jcctl plan` for every merge request and automatically post the human-readable plan diff as an MR comment (CC-20).
- **TS-21** — Reconciler Idempotency: Integration test suites MUST execute `jcctl apply` twice consecutively against a test instance and assert that the second run generates a completely empty diff (CC-18).

## 7. Performance and Latency Budgets

- **TS-22** — Automated load testing using `k6` MUST run against the Context Gateway in CI on dedicated hardware, asserting:
  - P99 gateway overhead latency ≤ 5.0 ms for cached policy evaluations.
  - Minimum throughput of 5,000 requests/second per replica on commodity hardware.
  - Zero memory leaks during a sustained 30-minute stress test.
  - Application generator budgets, measured on the reference installation in `ci-full` and reported beside the gateway numbers:
    - First preview of a kit application reachable within 60 seconds of the request, from one model call (AP-57).
    - A generation of the reference size complete within 10 minutes from confirmed data needs to a reachable preview (AP-55).

## 8. Security, Supply Chain, and Red-Teaming

- **TS-23** — Container Image Security: All built container images MUST be scanned using Trivy; any unpatched vulnerability with severity `CRITICAL` or `HIGH` MUST block image release.
- **TS-24** — Dependency Scanning: CI MUST run `cargo audit` (Rust) and `npm audit` (JavaScript), blocking dependencies with published security advisories.
- **TS-25** — Agent Red-Teaming: The test suite MUST include an adversarial prompt-injection corpus passed through mock sensor observations and entity attributes, asserting that the Agent Runner never escalates privileges, escapes sandboxes, or triggers unapproved destructive tool calls.

## Traceability

| Requirements | Section | Architecture | Tests |
|---|---|---|---|
| TS-01…TS-04 | Rust Core and Property-Based Testing | [01-overview.md](../Architecture/01-overview.md) | [00-strategy.md](../Testing/00-strategy.md) |
| TS-05…TS-08 | Specification Conformance Testing | [01-overview.md](../Architecture/01-overview.md) | [00-strategy.md](../Testing/00-strategy.md) |
| TS-09…TS-10 | Contract and Client Integrity Testing | [01-overview.md](../Architecture/01-overview.md) | [00-strategy.md](../Testing/00-strategy.md) |
| TS-11…TS-14 | Frontend, E2E, and Accessibility Testing | [01-overview.md](../Architecture/01-overview.md) | [00-strategy.md](../Testing/00-strategy.md) |
| TS-15…TS-17 | Pipeline and Blueprint Verification | [01-overview.md](../Architecture/01-overview.md) | [00-strategy.md](../Testing/00-strategy.md) |
| TS-18…TS-21 | Manifest CI Gates and Reconciler Verification | [01-overview.md](../Architecture/01-overview.md) | [00-strategy.md](../Testing/00-strategy.md) |
| TS-22 | Performance and Latency Budgets | [01-overview.md](../Architecture/01-overview.md) | [00-strategy.md](../Testing/00-strategy.md) |
| TS-23…TS-25 | Security, Supply Chain, and Red-Teaming | [01-overview.md](../Architecture/01-overview.md) | [00-strategy.md](../Testing/00-strategy.md) |
