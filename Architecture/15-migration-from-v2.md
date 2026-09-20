---
sidebar_position: 15
title: Migration Guide from CIVITAS/CORE v2
description: Structural migration roadmap, component transitions, execution sequence, and data conversion rules from CIVITAS/CORE v2.
---

# Migration Guide from CIVITAS/CORE v2

This document provides a systematic migration roadmap for transitioning existing CIVITAS/CORE v2 deployments to the next-generation joinedcontext architecture. It specifies component transitions, data migration rules, and documentation reference mappings.

## 1. Component Transition Mapping

The table below documents the disposition of each legacy component, identifying whether it is kept, replaced, or dropped, along with the governing Architecture Decision Record.

| Legacy Component (v2) | Disposition | Replacement Component | Governing ADR | Architectural Rationale |
|---|---|---|---|---|
| **`portal-backend`** (Spring Boot) | Replaced | **Portal API** (Rust / Axum) | [ADR-N-001](../Decisions/adr-n-001-rust-typescript-stack.md) | Reduces memory footprint from ~1.5 GB to ~35 MB; instant cold start; eliminates Spring overhead. |
| **`portal-frontend`** (Next.js) | Replaced | **Portal UI** (React 19 / Vite) | [ADR-N-001](../Decisions/adr-n-001-rust-typescript-stack.md) | Eliminates BFF proxy layers; compiles types directly from backend OpenAPI contracts. |
| **`config-adapters`** (Java) | Replaced | **`jcctl` Reconciler** (Rust) | [ADR-N-005](../Decisions/adr-n-005-reconciler-jcctl-in-rust.md) | Replaces runtime Kafka configuration events with declarative GitOps reconciliation. |
| **Apache Kafka & Strimzi** | Dropped | **Gitea Git Repository** | [ADR-N-004](../Decisions/adr-n-004-configuration-as-code-and-gitea.md) | Eliminates Kafka cluster, Zookeeper/KRaft, and outbox/saga compensation cascades. |
| **Apache NiFi** | Replaced | **Bento Pipelines** (Go) | [ADR-N-006](../Decisions/adr-n-006-bento-pipelines-supersede-nifi.md) | Stream memory dropped by 85%; pipeline logic versioned directly as text manifests. |
| **`authz-adapter` & OPA sidecar**| Replaced | **Context Gateway** (Rust PEP/PDP) | [ADR-N-003](../Decisions/adr-n-003-context-gateway-in-rust.md) | In-process AST query rewriting eliminates the multi-hop decision latency bottleneck. |
| **APISIX etcd Cluster** | Replaced | **APISIX Standalone File Mode** | [ADR-N-007](../Decisions/adr-n-007-apisix-standalone-no-etcd.md) | Operates from static ConfigMap (`apisix.yaml`); eliminates mutable Admin API. |
| **EMF / Ecore Modeling** | Replaced | **LinkML Data Models** | [ADR-N-010](../Decisions/adr-n-010-linkml-data-models.md) | Single YAML truth compiling to JSON Schema draft-07 and JSON-LD `@context`. |
| **Stellio / Scorpio** | Replaced | **Antares Broker** (Rust) | [ADR-N-008](../Decisions/adr-n-008-antares-default-broker.md) | Ultra-low memory footprint; shared-schema RLS; Stellio and Scorpio remain supported alternatives. |
| **FROST-Server** | Converted to Addon | **Endpoint STA Representation** | [ADR-N-002](../Decisions/adr-n-002-context-space-and-endpoint-model.md) | Core provides SensorThings API v1.1 natively over NGSI-LD; FROST retained as addon. |
| **GeoServer Cloud** | Converted to Addon | **Endpoint OGC Representation** | [ADR-N-002](../Decisions/adr-n-002-context-space-and-endpoint-model.md) | Core serves OGC API Features natively; GeoServer moved to optional addon. |
| **Apache Superset** | Converted to Addon | **Portal Dashboards** | [ADR-N-011](../Decisions/adr-n-011-maplibre-deckgl-dashboards.md) | Embedded MapLibre/deck.gl visualizer in Portal; Superset retained as addon. |
| **HashiCorp Vault** | Replaced | **SOPS+age / OpenBao** | [ADR-N-012](../Decisions/adr-n-012-secrets-sops-openbao.md) | Replaces BSL-licensed Vault with 100% open-source secret engines (MPL 2.0). |
| **CloudNativePG Operator** | Kept | **CloudNativePG Operator** | ADR 004 | Retained as authoritative PostgreSQL cluster operator across all profiles. |
| **Linkerd Service Mesh** | Kept | **Linkerd Service Mesh** | ADR 024 | Mandatory `cluster-authenticated` mTLS retained across all instance namespaces. |
| **Keycloak IAM** | Kept with Change | **Keycloak IAM** | ADR 007 | Retained for OIDC and OID4VCI; token introspection replaced by JWKS verification inside the Portal and the Context Gateway. |

## 2. Migration Execution Sequence

The platform migration executes in six ordered phases:

1. **Deploy Shared Operators:** Deploy CloudNativePG and Kyverno operators via `deployment/helmfile-operators.yaml`.
2. **Bootstrap Identity & Git Forge:** Deploy Keycloak and Gitea in the instance namespace; import legacy Keycloak realms and configure OIDC clients.
3. **Transform Metadata to Manifests:** Export relational DataPools, DataSets, and DataStructures from the legacy `portal` database and compile them into `projects/`, `datamodels/`, and `endpoints/` YAML manifests.
4. **Initialize Org Repository:** Commit generated manifests into the authoritative Gitea repository and execute initial reconciliation via `jcctl apply`.
5. **Migrate Context & Telemetry Data:** Export entities from the legacy context broker and FROST server, rewrite identifiers to conform to ADR 001 URN standards, and import into Antares Context Spaces.
6. **Switch Ingress & Decommission:** Deploy standalone APISIX routing configurations, verify representation parity on all Endpoints, reroute public DNS, and decommission legacy JVM workloads.

## 3. Data Migration Rules

### URN Modernization Rule

Legacy URNs conforming to the historical 4-segment format `{Typ}:{Razidlo}:{Evidencia}:{Meno}` must be converted to the authoritative URN scheme:

```text
urn:ngsi-ld:{Type}:{orgDomain}:{space}:{localId}
```

1. `{Type}` is validated against the imported LinkML schema name.
2. `{orgDomain}` is mapped to the Organization's verified domain (e.g. `banskabystrica.sk`), replacing arbitrary legacy issuer codes.
3. `{space}` is mapped to the target Context Space name (the legacy `Evidencia` identifier).
4. `{localId}` carries the entity identifier. Plain UUIDs are preserved within `{localId}`.

### FROST SensorThings Mapping Rule

Sensor observations residing in legacy FROST-Server databases are migrated to standard NGSI-LD entities:

- STA `Thing` maps to an NGSI-LD entity of type `Device` or `Sensor`.
- STA `Datastream` properties map to NGSI-LD Property attributes.
- STA `Observations` map to temporal Property instances with `observedAt` timestamps.
- Legacy clients query these observations via the Endpoint's `/sta/v1.1/` representation without requiring a separate FROST instance.

## 4. Documentation Reference Mapping

| Legacy Documentation Location (`civitas-core-docs_v2`) | New Documentation Location (`docs_new`) | Scope of Change |
|---|---|---|
| `Architecture/Architecture_General/` | [Architecture/01-overview.md](01-overview.md) & [02-principles.md](02-principles.md) | Rewritten to reflect Rust and NGSI-LD architecture. |
| `Architecture/domain_model.md` | [Architecture/03-domain-model.md](03-domain-model.md) | Replaced DataPool and DataSet model with Context Spaces and Endpoints. |
| `Architecture/MessageBus/` | [Architecture/08-pipelines.md](08-pipelines.md) | Kafka, Saga, and Outbox sections deprecated and replaced by Bento. |
| `Architecture/Model_Management/` | [Architecture/11-data-models.md](11-data-models.md) | Replaced EMF/Ecore models with LinkML. |
| `Architecture/Pipeline_Engine/` | [Architecture/08-pipelines.md](08-pipelines.md) | Replaced Apache NiFi evaluation with Bento streams mode. |
| `Development/Portal_Backend/` | [Architecture/09-portal.md](09-portal.md) | Removed Spring Boot documentation; replaced with Rust Axum specs. |
| `Development/Portal_Frontend/` | [Architecture/09-portal.md](09-portal.md) | Updated Next.js docs to Vite, React 19, and RJSF draft-07. |
| `User-and-admin-guide/` | [User-Guide/00-intro.md](../User-Guide/00-intro.md) | Workflows updated for Blueprint flow gallery and Gitea approvals. |

## Related

- [01-overview.md](01-overview.md) — high-level platform architecture overview.
- [03-domain-model.md](03-domain-model.md) — domain model taxonomy and URN syntax rules.
- [04-context-spaces-and-endpoints.md](04-context-spaces-and-endpoints.md) — Context Space and Endpoint surfaces.
- [06-configuration-as-code.md](06-configuration-as-code.md) — Configuration as Code and reconciler engine.
- [../Decisions/00-register.md](../Decisions/00-register.md) — Architecture Decision Register detailing all supersessions.
