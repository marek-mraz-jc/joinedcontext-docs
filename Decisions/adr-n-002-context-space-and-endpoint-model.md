---
sidebar_position: 3
title: "ADR-N-002: Context Space and Multi-Representation Endpoint Model"
---

# ADR-N-002: Context Space and Multi-Representation Endpoint Model

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

## 1. Context

CIVITAS/CORE v2 organized data through a hierarchy of DataPools, DataSets, DataSources, and Distributions, exposing datasets through separate subdomains (`portal-backend.<domain>`, `api.<domain>`) per ADR 040. External consumption of datasets required consumers to navigate different API endpoints depending on whether the payload was SensorThings (STA), WFS/WMS, or generic REST.

This model created several architectural challenges:

1. Subdomain sprawl required complex dynamic DNS, ingress routing, and multi-domain TLS certificate management.
2. The `NGSILD-Tenant` HTTP header leaked internal database multi-tenancy concepts into public consumer clients.
3. Access control policies had to be duplicated across gateway routes and disparate storage engines (FROST, GeoServer, PostgreSQL).

We need an explicit, stable abstraction separating internal multi-tenancy from external multi-representation consumption.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Model-driven data flow | **Full** | Manifests declare Context Spaces and Endpoints; URLs map deterministically to data models. |
| Distributed architecture with unified UX | **Full** | Path-based routing under a single domain simplifies federation and presentation. |
| Modular design | **Full** | Clear decoupling: Context Space handles storage; Endpoint handles presentation. |
| Integrability via defined interfaces | **Full** | Every Endpoint provides CIM 009 NGSI-LD, OGC API Features, and SensorThings simultaneously. |
| Open source as default | **Full** | Relies strictly on standard specifications. |
| Cloud-native architecture | **Full** | In-memory slug resolution table scales horizontally across stateless gateway pods. |
| Standard solutions before custom code | **Full** | Standardizes on ETSI GS CIM 009, OGC API Features Part 1, and DCAT-AP. |
| Self-contained deployment | **Full** | Operates cleanly under a single host domain without wildcard DNS requirements. |
| Technological consistency | **Full** | Pure translation layer over unified NGSI-LD broker queries. |
| Multi-tenancy | **Full** | Space maps 1:1 to broker tenant; Endpoints provide scoped authorization views. |
| Security by design | **Full** | High-entropy opaque slugs prevent endpoint enumeration; RLS prevents broker bleed. |

## 3. Decision

1. **Context Space as Data Tenant**:
   - The internal unit of data isolation is the **Context Space** (`kind: ContextSpace`), mapped 1:1 to an NGSI-LD tenant on the broker data plane.
   - The canonical authoring surface for the owning project is `https://{host}/cs/{space}/`.
2. **Endpoints as Opaque Multi-Representation Views**:
   - External data sharing and public consumption are handled exclusively via **Endpoints** (`kind: Endpoint`) exposed at `https://{host}/api/endpoint/{endpointSlug}/`.
   - The `endpointSlug` is an opaque, high-entropy Base32 token (≥ 128 bits) preventing resource enumeration.
3. **Universal Representation Parity**:
   - Every Endpoint exposes a fixed child set (`ngsi-ld/v1/`, `mcp`, `file.{ext}`, `ogc/features/`, `sta/v1.1/`, `schema/`).
   - Every representation is evaluated against the exact same Policy decision at the PEP; representation translators convert query results without secondary access checks.
4. **Tenant Header Elimination**:
   - External clients NEVER transmit `NGSILD-Tenant`.
   - The Context Gateway strips incoming tenant headers, resolves `endpointSlug` to the underlying space via an in-memory ArcSwap table, and injects `NGSILD-Tenant: {space}` exclusively on the internal hop.

## 4. Consequences

### Positive

- **Zero Subdomain Sprawl**: Entire platform operates under a single domain with wildcard TLS certs eliminated.
- **Representation Parity**: Consumers access the same underlying digital twin entity graph as GeoJSON, OGC Features, SensorThings, or NGSI-LD without data divergence.
- **Safe Public Exposure**: Endpoints can be revoked or re-slugged instantaneously without altering internal Context Space data.

### Negative / Trade-offs

- The Context Gateway must perform runtime translation of NGSI-LD responses into OGC Features, CSV, and STA formats, requiring optimized serialization code in Rust.
- Entities lacking spatial geometry cannot be served via GeoJSON or OGC Features and return structured 400 ProblemDetails errors.

## 5. See Also

- Supersedes: CIVITAS ADR 020, ADR 022, ADR 039, ADR 040.
- Keeps and Extends: `docs/adr/adr013.qmd` (Context space addressing).
- Requirements: [EP-01…EP-28 (Endpoints)](../Requirements/endpoints.md), [SP-01…SP-21 (Space Surface)](../Requirements/space-surface.md).

## 6. Addendum: URN authority segment and access surface

The issuer segment of the entity URN is the Organization's **verified domain** (`urn:ngsi-ld:{Type}:{orgDomain}:{space}:{localId}`), replacing the free-form issuer code of legacy ADR 001; the gateway enforces all four segments on writes (Architecture/03, PF-41…PF-44). Every space and endpoint also exposes `access`, the caller's effective grants as AuthZEN JSON, ODRL 2.2 and a UCAST grant AST (Architecture/04 §1b, EP-55…EP-60), so consumers and agents learn what they may read, write or delete without probing.

## Related

- [EP-01…EP-28 (Endpoints)](../Requirements/endpoints.md) — referenced above.
- [SP-01…SP-21 (Space Surface)](../Requirements/space-surface.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
