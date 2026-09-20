---
sidebar_position: 2
title: Architecture Principles
description: Fourteen foundational architecture principles governing system design, technology choices, and platform invariants.
---

# Architecture Principles

The design, implementation, and evolution of the joinedcontext platform are governed by fourteen fundamental architecture principles. Every structural modification, component integration, and pull request must adhere to these rules.

## 1. Model-Driven Data Flow

The platform structures data ingestion, processing, and exposure according to explicit, versioned schemas authored in LinkML, compiling them into JSON Schema draft-07 and JSON-LD contexts that runtime services interpret and enforce directly. Implemented in [11-data-models.md](11-data-models.md) and requirement family [DM](../Requirements/data-models.md).

## 2. Distributed Architecture with a Unified User Experience

The platform consists of decoupled micro-services and federated digital twins operating across different infrastructure boundaries, while presenting a unified, coherent portal interface and consistent REST and MCP APIs to operators, analysts, and public users. Implemented in [01-overview.md](01-overview.md), [09-portal.md](09-portal.md), and requirement family [UI](../Requirements/portal-and-ui.md).

## 3. Modular Design

Platform layers are strictly modular, with core components delivering the minimal capability set required to operate an ETSI-compliant digital twin, while specialized domains such as business intelligence and legacy GIS are isolated in pluggable addons that can be added or replaced without modifying the core platform. Implemented in [14-components.md](14-components.md) and requirement family [PF](../Requirements/platform.md).

## 4. Integrability via Well-Defined Interfaces

Every external and inter-service interface is exposed through open, standardized protocols including ETSI GS CIM 009 NGSI-LD, OGC API Features, OpenAPI 3.1, and Model Context Protocol, with proprietary or vendor-locked communication mechanisms strictly prohibited across trust boundaries. Implemented in [04-context-spaces-and-endpoints.md](04-context-spaces-and-endpoints.md) and requirement family [EP](../Requirements/endpoints.md).

## 5. Open Source by Default

The platform is developed, documented, and released under the European Union Public Licence 1.2, the reciprocal licence the European Commission publishes for public-sector software; every workspace declares it (`license = "EUPL-1.2"` in `joinedcontext-platform/Cargo.toml` and `joinedcontext-portal/Cargo.toml`, `joinedcontext-deployment/LICENSE`, and the Antares broker). Deployment manifests, container recipes, tooling, and test suites are public, and no capability is behind a closed-source or commercial-only gate. Implemented in [14-components.md](14-components.md) and requirement family [PF](../Requirements/platform.md).

## 6. Cloud-Native Architecture

Components run as horizontally scalable, non-root, containerized workloads in Kubernetes or lightweight edge container environments adhering to 12-Factor principles, supporting automated lifecycle probes, graceful termination, and declarative resource limits. Implemented in [13-security.md](13-security.md) and requirement family [OPS](../Requirements/operations.md).

## 7. Standard Solutions Before Custom Development

Off-the-shelf open-source products are utilized wherever they satisfy requirements, permitting bespoke development only when existing solutions fail to meet architectural criteria, security mandates, or resource targets. Implemented in [14-components.md](14-components.md) and requirement family [PF](../Requirements/platform.md).

## 8. Self-Contained Deployment

The entire platform core must be fully operable within a single standard Kubernetes cluster without requiring external commercial cloud services, SaaS dependencies, or mandatory central platform registries, while allowing auxiliary systems to integrate cleanly with enterprise infrastructure. Implemented in [13-security.md](13-security.md) and requirement family [OPS](../Requirements/operations.md).

## 9. Technological Consistency to Ensure Maintainability

Technology fragmentation is avoided by standardizing custom software on Rust for performance-critical backend services, gateways, and reconcilers, and React with TypeScript for user interfaces and browser tools, unified by consistent linting and build tooling. Implemented in [14-components.md](14-components.md), [ADR-N-001](../Decisions/adr-n-001-rust-typescript-stack.md), and requirement family [TS](../Requirements/testing.md).

## 10. Multi-Tenancy

Multi-tenancy is enforced at administrative, logical, and data layers through Organizations, Projects, Context Spaces mapped to broker tenants, and PostgreSQL Row-Level Security (RLS) guaranteeing data partition isolation inside shared storage backends. Implemented in [03-domain-model.md](03-domain-model.md) and requirement family [PF](../Requirements/platform.md).

## 11. Security and Privacy by Design

Security is a continuous default: mutual TLS between workloads, carried by the Linkerd proxy and made mandatory by a Kyverno policy that refuses any Pod without the sidecar in a namespace annotated `linkerd.io/inject=enabled` (a workload opts out only explicitly, and the opt-out is itself policed); least-privilege execution tokens; strict separation between the policy control plane and data payloads; and fail-closed evaluation on every authorization and routing decision. Implemented in [05-context-gateway.md](05-context-gateway.md), [13-security.md](13-security.md), and requirement families [R](../Requirements/access-control.md) and [GW](../Requirements/gateway-firewall.md).

## 12. Configuration as Code First

All declarative platform configuration, including Organizations, Projects, Context Spaces, routing rules, access policies, data models, subscriptions, and pipelines, is authored, reviewed, versioned, and stored in Git as the authoritative source of truth. One elected Portal replica converges it to the live services in process, and it carries `jcctl` as a library, so the reconciler and the command line read a manifest the same way and nothing else writes to a live service. Implemented in [06-configuration-as-code.md](06-configuration-as-code.md) and requirement family [CC](../Requirements/city-as-code.md).

## 13. AI Agents as First-Class Principals

Autonomous AI agents authenticate via discrete cryptographic identities, operate under the same policy rules as human users, interact through standardized Model Context Protocol (MCP) interfaces, follow risk-based approval lanes, and isolate untrusted payloads to prevent indirect prompt-injection attacks. Implemented in [07-agents-and-mcp.md](07-agents-and-mcp.md) and requirement family [AG](../Requirements/agents.md).

## 14. One Data Path

All secondary representations and views such as GeoJSON, CSV, SensorThings API, and OGC API Features are derived directly as on-demand, deterministic projections of the spec-native NGSI-LD Context Data Plane under an identical policy firewall decision, eliminating separate databases or unmediated bypass routes. Implemented in [04-context-spaces-and-endpoints.md](04-context-spaces-and-endpoints.md) and requirement family [EP](../Requirements/endpoints.md).

## Related

- [01-overview.md](01-overview.md) — architectural overview and operational areas.
- [03-domain-model.md](03-domain-model.md) — domain model taxonomy and tenant hierarchy.
- [04-context-spaces-and-endpoints.md](04-context-spaces-and-endpoints.md) — multi-representation translation and endpoint model.
- [06-configuration-as-code.md](06-configuration-as-code.md) — Configuration as Code architecture and reconciler engine.
- [13-security.md](13-security.md) — trust zones and BSI TR-03187 security controls.
