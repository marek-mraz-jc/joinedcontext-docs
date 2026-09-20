---
sidebar_position: 16
title: "ADR-N-015: S3-compatible Artifact Store with RustFS as Default"
---

# ADR-N-015: S3-compatible Artifact Store with RustFS as Default

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

## 1. Context

Endpoints must publish what their data contains in every mainstream schema formalism (LinkML, JSON Schema, `@context`, SHACL, OWL, RDF, documentation), narrowed to each endpoint's grant, and the same artifacts must be reachable through MCP. Rendering them per request would put Python generators on the gateway's hot path and make byte-stability of versioned URLs a convention rather than a guarantee. The platform also accumulates other rendered outputs (compiled Bloblang mappings, RDF dumps, export bundles, app builds, cached file downloads) that were each heading for their own PersistentVolumeClaim.

## 2. Decision

1. Rendered, derivative, immutable objects live in one **S3-compatible artifact store**; Git keeps authored state, PostgreSQL and the broker keep runtime state.
2. Model Tools renders the full artifact set at publish time; `jcctl` uploads it; the Context Gateway streams it under `/cs/{space}/schema/` and `/api/endpoint/{slug}/schema/` with sha256 `ETag`s and exposes it as MCP tools and resources.
3. Default implementation: **RustFS** (Apache-2.0, Rust, S3 API) as a core component. The platform uses only the core S3 subset (put/get/head/list/delete, multipart, versioning, object lock) so Garage, SeaweedFS, Ceph RGW or a cloud bucket are interchangeable through the `artifactStore` values block.
4. Published prefixes are object-locked; `filecache/` is a purgeable, lifecycle-managed cache; only `jcctl` and CI write, gateway and Portal read, nobody else reaches the store.

## 3. Alternatives considered

- **MinIO**: mature, but community builds ended in 2025 and the licence is AGPL; rejected as default, still usable through the S3 values block.
- **Garage / SeaweedFS**: solid (Garage is Rust, AGPL); kept as documented fallbacks, not default, because RustFS' Apache-2.0 licence and MinIO-compatible operator model fit the stack rule better.
- **PVC + gateway file serving**: no immutability guarantee, per-component backup and quota stories, no multi-replica sharing; rejected.
- **Commit every rendered artifact to Git**: SHACL/OWL/RDF for every model version and every endpoint projection would bloat the org repository and mix authored with derived content; only the DM-02 set stays committed.
- **Render on request**: rejected for latency, CPU and stability reasons above.

## 4. Consequences

- One more core component with a PVC; small footprint (one Rust binary).
- Everything in the store is rebuildable (`jcctl artifacts rebuild`), so backup priority is low and loss is an inconvenience, not an incident.
- RustFS maturity is a known risk; the S3-subset rule confines it (OPEN-QUESTIONS 12).

Requirements: PF-29…PF-33, DM-43…DM-47, EP-46…EP-52. Architecture: [17-artifact-store](../Architecture/17-artifact-store.md).

## Related

- [17-artifact-store](../Architecture/17-artifact-store.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
