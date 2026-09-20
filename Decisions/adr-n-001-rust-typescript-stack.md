---
sidebar_position: 2
title: "ADR-N-001: Standardize Core Stack on Rust and React/TypeScript"
---

# ADR-N-001: Standardize Core Stack on Rust and React/TypeScript

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

## 1. Context

CIVITAS/CORE v2 implemented custom backend services (Portal Backend, AuthZ Adapter, Model Management, Configuration Adapters) in Java using Spring Boot. This architecture incurred significant operational trade-offs:

1. **High Memory Overhead**: JVM processes required a baseline footprint of 4–8 GB RAM before processing workload traffic, conflicting with organisational edge deployments and small-tenant hosting.
2. **Maintenance Drag**: Managing multiple Java services, Jackson object mappers, JPA entity graphs, and Kafka consumer threads created extensive boilerplate and frequent serialization drift.
3. **Frontend Contract Drift**: The Next.js BFF architecture maintained duplicated type declarations and proxy layers between browser components and backend controllers.

We require a lean, memory-efficient, cloud-native technology foundation with compile-time type safety across the entire API boundary.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Model-driven data flow | **Full** | OpenAPI schemas derived directly from Rust code (`utoipa`); TypeScript clients compiled directly from schema. |
| Distributed architecture with unified UX | **Full** | Single unified Portal SPA interface backed by lightweight APIs. |
| Modular design | **Full** | Clear separation between Portal API (Axum) and Portal UI (React 19). |
| Integrability via defined interfaces | **Full** | OpenAPI v3.1 contracts published natively by all endpoints. |
| Open source as default | **Full** | Built on 100% permissive open-source libraries (Rust, React, MIT/Apache). |
| Cloud-native architecture | **Full** | Sub-millisecond cold starts, minimal container images (<25 MB Alpine/distroless), predictable memory consumption. |
| Standard solutions before custom code | **Full** | Off-the-shelf libraries (`sqlx`, `axum`, `rjsf`, `ag-grid`) replace custom enterprise frameworks. |
| Self-contained deployment | **Full** | Minimal static binaries run in standard containers without JVM dependencies. |
| Technological consistency | **Full** | All custom backend code standardized on Rust; frontend on TypeScript. |
| Multi-tenancy | **Full** | PostgreSQL row-level security and tenant-scoped connection pools. |
| Security by design | **Full** | Memory safety without garbage collection pauses; strong compile-time nullability. |

## 3. Decision

1. **Eliminate All Custom Java Code**: The custom Spring Boot services (`portal-backend`, `authz-adapter`, `config-adapters`) are completely removed.
2. **Backend Standardized on Rust**:
   - **Framework**: `axum` running on `tokio` and `tower`.
   - **Database Access**: `sqlx` providing compile-time checked SQL queries against PostgreSQL.
   - **API Contracts**: `utoipa` generating OpenAPI v3.1 schemas directly from Rust data structures.
3. **Frontend Standardized on React/TypeScript**:
   - **Build & Runtime**: Vite + React 19 + TypeScript (strict mode).
   - **Routing & State**: TanStack Router and TanStack Query.
   - **Forms**: Dynamic rendering via `react-jsonschema-form` (RJSF) on JSON Schema draft-07.
   - **Data Grids & Maps**: AG Grid Community and MapLibre GL JS / deck.gl.
   - **Client Generation**: `openapi-typescript` compiling TypeScript API clients directly from the Portal API's OpenAPI specification.
4. **Keycloak Retained as Standard Component**: Keycloak is retained as the identity provider (OIDC/OID4VCI). It is operated as a pre-packaged, containerized off-the-shelf component, not custom-maintained project code.

## 4. Consequences

### Positive

- **Dramatically Reduced Footprint**: Portal API container runs in ~20–40 MB RAM (down from ~1.5 GB for Spring Boot).
- **Zero API Contract Drift**: TypeScript frontend types are generated mechanically during the CI build; mismatched parameters result in compile errors.
- **Instant Cold Starts**: Container startup time reduced from 30+ seconds to sub-second.

### Negative / Trade-offs

- Team members accustomed to Java/Spring Boot must be proficient in Rust idioms (ownership, lifetimes, async Tokio runtime).
- Compile times for Rust crates during CI are longer than TypeScript, mitigated by sccache and cargo-chef layer caching.

## 5. Alternatives

- **Continue with Spring Boot**: Rejected due to high idle memory consumption and operational complexity.
- **Go Backend**: Considered, but rejected due to lack of zero-cost abstractions, weaker compile-time type safety compared to Rust, and lack of native AST integration with the `antares-ql` parsing crate.

## 6. See Also

- Supersedes: CIVITAS ADR 002, ADR 009, ADR 016.
- [PF-01…PF-28 (Platform Invariants)](../Requirements/platform.md)

## Related

- [PF-01…PF-28 (Platform Invariants)](../Requirements/platform.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
