---
sidebar_position: 19
title: "Model Projections (MP)"
---

# Model Projections

Family **MP** (MP-01…MP-03). Owning chapter: [Architecture/04-context-spaces-and-endpoints.md](../Architecture/04-context-spaces-and-endpoints.md#3b-the-named-projection-of-a-model). Verified by: [Testing/01-backend-tests.md](../Testing/01-backend-tests.md).

One LinkML model per Context Space is the truth (DM-01). An Endpoint exposes a subset of its classes and attributes, and that subset is a named, reusable manifest rather than a rule retyped inside every Endpoint. This family defines the manifest, how Endpoints and Policies use it, and what the schema surface renders from it. Read it with [endpoints.md](endpoints.md) section 19, which says what an Endpoint reads and writes.

## 1. The manifest

- **MP-01** [P][S] — `kind: ModelProjection` MUST be a manifest under configuration as code (CC family) that names one space's DataModel and version (`spec.dataModelRef`), lists the exposed classes (`spec.classes[]`, each with `name` and `slots[]`) and MAY carry a residual filter (`spec.filter` with `q`, `scopeQ`, `geoQ`, `temporalQ` in NGSI-LD query syntax); CI and `jcctl plan` MUST refuse a projection naming a class or slot the referenced model version does not have, listing every offending name.

## 2. Endpoints and policies reference it

- **MP-02** [S] — An Endpoint's policy set MAY name a `ModelProjection` (`spec.projectionRef`) instead of restating types and attribute names, several Endpoints MAY share one, and the gateway MUST intersect the projection with the caller's grants exactly as it intersects an inline rule (GW10, GW11, R9), so a projection narrows and never widens and is not an authorization by itself.

## 3. The schema surface renders from it

- **MP-03** [P][A] — The `model.linkml.yaml`, JSON Schema, `@context`, SHACL, OWL and Markdown an Endpoint serves MUST be generated from the projection's classes and slots intersected with the caller's grants (EP-47, EP-48), never from a second hand-maintained LinkML source.

## Traceability

| Requirement Range | Architecture Section | Test Family |
|---|---|---|
| MP-01…MP-03 | [Architecture/04-context-spaces-and-endpoints.md#3b-the-named-projection-of-a-model](../Architecture/04-context-spaces-and-endpoints.md#3b-the-named-projection-of-a-model) | [Testing/01-backend-tests.md#1-property-based-testing-in-context-gateway](../Testing/01-backend-tests.md#1-property-based-testing-in-context-gateway) |

## Related

- [endpoints.md](endpoints.md) — EP-73…EP-75: the read set, the write set and the minted slug of an Endpoint.
- [data-models.md](data-models.md) — DM-01: the one LinkML source a projection is a subset of.
- [gateway-firewall.md](gateway-firewall.md) — GW10, GW11: the intersection a projection goes through on every read.
- [Architecture/04-context-spaces-and-endpoints.md](../Architecture/04-context-spaces-and-endpoints.md#3b-the-named-projection-of-a-model) — the worked example, Vehicle and User through one projection.
