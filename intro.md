---
sidebar_position: 1
title: Platform Documentation
description: Architectural specifications, deployment topologies, and developer guidelines for the joinedcontext platform.
---

# Platform Documentation

The joinedcontext platform is a cloud-native, open-source data platform engineered for federated digital twins across municipalities, regions, utilities, and partner enterprises. One physical deployment (an Instance) serves one Organization, with its own Git repository, identity subtree, quotas, and projects; a second city runs a second instance, and the two share data through Endpoints under policy rather than through a shared deployment. This documentation provides comprehensive architecture blueprints, normative requirements, deployment guides, and developer workflows.

## 1. Target Audience

This documentation is written for:

- **Platform Architects and Security Engineers:** Designing context boundaries, trust fabrics, and policy firewalls.
- **Backend and Frontend Developers:** Building micro-services in Rust and user interfaces in React and TypeScript.
- **DevOps and Platform Operators:** Deploying and maintaining Kubernetes environments via Helmfile, GitOps, and Linkerd.
- **Autonomous Systems and Integration Engineers:** Developing AI agents and data pipelines using Model Context Protocol (MCP) and Bento.

## 2. Core Architectural Pillars

The platform is structured around seven non-negotiable architectural pillars:

| Pillar | Architectural Role | Key Implementation Reference |
|---|---|---|
| **1. Spec-Native CIM 009 Context Broker** | Spec-compliant ETSI GS CIM 009 context data plane using Antares in Rust (pluggable with Scorpio and Stellio). | [Architecture/01-overview.md](Architecture/01-overview.md), [ADR-N-008](Decisions/adr-n-008-antares-default-broker.md) |
| **2. Policy Firewall at the Trust Boundary** | Externalized PEP and in-process PDP enforcing granular, fail-closed access control, AST query rewriting, and tenant pinning. | [Architecture/05-context-gateway.md](Architecture/05-context-gateway.md), [Requirements/access-control.md](Requirements/access-control.md) |
| **3. Configuration as Code (CaC)** | Authoritative Git repository as single source of truth, converged idempotently via the `jcctl` reconciler across risk lanes. | [Architecture/06-configuration-as-code.md](Architecture/06-configuration-as-code.md), [Requirements/city-as-code.md](Requirements/city-as-code.md) |
| **4. Unified Space and Endpoint Model** | Tenancy encapsulated inside Context Spaces (`/cs/{space}`) and exposed externally via policy-narrowed Endpoints (`/api/endpoint/{slug}`). | [Architecture/04-context-spaces-and-endpoints.md](Architecture/04-context-spaces-and-endpoints.md), [Requirements/endpoints.md](Requirements/endpoints.md) |
| **5. AI Agents as First-Class Principals** | Autonomous agents governed by auditable identities, scoped grants, and Model Context Protocol (MCP) Streamable HTTP surfaces. | [Architecture/07-agents-and-mcp.md](Architecture/07-agents-and-mcp.md), [Requirements/agents.md](Requirements/agents.md) |
| **6. Apps on Demand** | Purpose-built applications generated from declarative `dataNeeds`, running under least-privilege endpoints. | [Architecture/16-apps-on-demand.md](Architecture/16-apps-on-demand.md), [Requirements/apps.md](Requirements/apps.md) |
| **7. Pure Rust and TypeScript Runtime** | High-performance, memory-safe backend services in Rust and modern web frontends in React 19 and Vite. | [Architecture/14-components.md](Architecture/14-components.md), [ADR-N-001](Decisions/adr-n-001-rust-typescript-stack.md) |

## 3. Documentation Structure & Map

The documentation is organized into modular functional areas:

| Section | Focus Area | Entry Point |
|---|---|---|
| **Architecture** | System architecture, domain models, gateway internals, pipelines, and security. | [Architecture/01-overview.md](Architecture/01-overview.md) |
| **Requirements** | Normative specifications covering platform invariants, access control, manifests, and pipelines. | [Requirements/00-index.md](Requirements/00-index.md) |
| **Architecture Decisions** | Formally accepted ADRs recording technology choices and supersessions. | [Decisions/00-register.md](Decisions/00-register.md) |
| **Deployment** | Helmfile components, cluster prerequisites, APISIX edge routing, and security baselines. | [Deployment/00-intro.md](Deployment/00-intro.md) |
| **Operations** | Incident response runbooks, capacity planning, and governance procedures. | [Operations/00-intro.md](Operations/00-intro.md) |
| **Development** | Rust backend guidelines, React frontend standards, manifest definitions, and blueprints. | [Development/00-intro.md](Development/00-intro.md) |
| **Testing** | Verification strategy, conformance test suites, property testing, and security scans. | [Testing/00-strategy.md](Testing/00-strategy.md) |
| **API Reference** | Portal REST API, Endpoint representations, and `jcctl` CLI contracts. | [API/00-intro.md](API/00-intro.md) |
| **User Guide** | Step-by-step operator workflows, data modeling, dashboards, and app management. | [User-Guide/00-intro.md](User-Guide/00-intro.md) |
| **Glossary** | Canonical terminology, definitions, and legacy mapping. | [Glossary.md](Glossary.md) |

## Related

- [Glossary.md](Glossary.md) — canonical terminology and legacy term mappings.
- [Architecture/01-overview.md](Architecture/01-overview.md) — high-level platform architecture and request flows.
- [Requirements/00-index.md](Requirements/00-index.md) — normative requirement catalog index and taxonomy.
- [Deployment/00-intro.md](Deployment/00-intro.md) — deployment architecture and operational baseline.
