---
sidebar_position: 11
title: "ADR-N-010: Canonical Data Modeling with LinkML"
---

# ADR-N-010: Canonical Data Modeling with LinkML

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

## 1. Context

CIVITAS/CORE v2 selected raw JSON Schema, JSON, and JSONata as the technology basis for model-centric data flows (ADR 045), rejecting heavyweight modeling environments such as EMF/Ecore (ADR 018).

However, authoring complex organisational domain models directly in raw JSON Schema 2020-12 and JSONata proved suboptimal:

1. **JSON-LD `@context` Disconnect**: JSON Schema describes structural validation (types, required fields, patterns) but cannot declare semantic RDF vocabulary bindings (`@context`, ontology IRIs). As a result, JSON Schema models frequently drifted from the NGSI-LD `@context`.
2. **Multi-Target Compilation**: The platform requires data models to compile into multiple runtime formats: JSON Schema **draft-07** for form generation (stack verdict S4), JSON-LD `@context` for NGSI-LD, and documentation schemas. Hand-maintaining these targets caused constant drift.
3. **No Native Inheritance / Enum Support**: Expressing class inheritance and shared organisational enums in raw JSON Schema leads to convoluted, unreadable `allOf`/`anyOf` structures.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Model-driven data flow | **Full** | LinkML serves as single authoritative source of truth for all data models. |
| Distributed architecture with unified UX | **Full** | Generates human-readable data dictionary documentation and UI forms. |
| Modular design | **Full** | Compiles to independent runtime artifacts without coupling to runtime services. |
| Integrability via defined interfaces | **Full** | Emits standard JSON Schema draft-07 and W3C JSON-LD 1.1 `@context`. |
| Open source as default | **Full** | LinkML is open source under Apache 2.0. |
| Cloud-native architecture | **Full** | Compiles at build/commit time in CI; zero runtime dependencies. |
| Standard solutions before custom code | **Full** | Standard modeling language widely adopted in biological and open data domains. |
| Self-contained deployment | **Full** | Output files (JSON Schema, `@context`) committed directly into Git repository. |
| Technological consistency | **Full** | Standardizes semantic modeling across all context spaces. |
| Multi-tenancy | **Full** | Models scoped per context space or shared via common platform repositories. |
| Security by design | **Full** | Strict schema validation prevents malformed attribute injection at gateway PEP. |

## 3. Decision

1. **LinkML as Canonical Modeling Truth**:
   - Data models in Context Spaces MUST be authored as LinkML YAML files (`projects/{project}/spaces/{space}/datamodels/{model}.linkml.yaml`).
   - Replaces raw JSON Schema authoring (superseding CIVITAS ADR 045).
2. **Build-Time Compilation in CI**:
   - The CI pipeline executes the official LinkML generators during commit validation:
     - `gen-json-schema --target-dialect draft-07` → Emits runtime JSON Schema for form generation and payload validation.
     - `gen-jsonld-context` → Emits the authoritative JSON-LD `@context` file served under `schema/context.jsonld`.
     - `gen-doc` → Emits human-readable Markdown documentation for the Portal data dictionary.
3. **Committed Compiled Artifacts**:
   - In accordance with the rendered-manifests pattern (CC-25), the generated `json-schema/` and `context.jsonld` files are committed alongside the source LinkML file, ensuring audit portability without requiring LinkML tooling at apply time.
4. **Smart Data Models Import**:
   - Pre-existing Smart Data Models (FIWARE/OASC) are imported by translating their schemas into LinkML definitions via automated tooling.

## 4. Consequences

### Positive

- **Single Semantic Truth**: Structural validation rules and RDF `@context` URI mappings are defined in one place and guaranteed never to drift.
- **Draft-07 Compatibility**: Solves the RJSF form generation compatibility challenge (S4) by compiling directly to tested draft-07 schemas.
- **Readable Domain Modeling**: LinkML's YAML syntax (classes, slots, enums, inheritance) is significantly easier for organisational data stewards to author and review than raw JSON Schema.

### Negative / Trade-offs

- Developers and data architects must learn LinkML syntax.
- CI pipeline requires Python LinkML generator tooling during the pre-merge validation stage.

## 5. See Also

- Supersedes: CIVITAS ADR 018, ADR 045.
- Requirements: [PF-08 (DataModels)](../Requirements/platform.md), [UI-01 (Forms)](../Requirements/portal-and-ui.md), [SP-13 (Schema URLs)](../Requirements/space-surface.md).
- Editor and import workflow: [Architecture/11-data-models §6](../Architecture/11-data-models.md); requirements `DM-01…DM-32` in [data-models.md](../Requirements/data-models.md). LinkML tooling runs as the Python **Model Tools** image, the single documented exception to the Rust/TypeScript rule (a stateless generator, not a service with authority).

## 6. Addendum, mapping language

Model-to-model transformations use **LinkML-Map** (`kind: Mapping`, schema-aware on both ends, validated against source and target LinkML schemas, compiled by Model Tools to Bloblang); last-mile technical transformations stay in **Bloblang** inside Bento. JSONata (legacy CIVITAS ADR 045), jq, JMESPath and JOLT are not introduced. SSSOM records vocabulary alignments and is never executed. Rationale and limits: [Architecture/11 §7](../Architecture/11-data-models.md#7-mappings-with-linkml-map), requirements DM-33…DM-42. Known risk: LinkML-Map is young and Python-only; the compile-to-Bloblang step confines that risk to authoring time (OPEN-QUESTIONS 11).

## Related

- [PF-08 (DataModels)](../Requirements/platform.md) — referenced above.
- [UI-01 (Forms)](../Requirements/portal-and-ui.md) — referenced above.
- [SP-13 (Schema URLs)](../Requirements/space-surface.md) — referenced above.
- [Architecture/11-data-models §6](../Architecture/11-data-models.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
