---
sidebar_position: 9
title: "ADR-N-008: Antares as Default Context Broker"
---

# ADR-N-008: Antares as Default Context Broker

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

## 1. Context

CIVITAS/CORE v2 evaluated context broker technology for IoT and smart city data. Historical implementations frequently struggled with heavy JVM broker implementations (Scorpio, Stellio) that required significant heap memory (2–4 GB), exhibited slow boot times, and complicated edge deployments.

We require a high-performance, memory-efficient ETSI GS CIM 009 NGSI-LD context broker that can run in resource-constrained organisational environments, edge nodes, and centralized clusters while maintaining 100% compliance with the NGSI-LD specification.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Model-driven data flow | **Full** | Fully standard ETSI GS CIM 009 NGSI-LD data model. |
| Distributed architecture with unified UX | **Full** | Native support for Context Source Registrations and federation (R32–R39). |
| Modular design | **Full** | Broker is completely decoupled and policy-free (CC-01). |
| Integrability via defined interfaces | **Full** | Standard NGSI-LD v1.6+ HTTP REST and WebSocket bindings. |
| Open source as default | **Full** | 100% open source under Apache 2.0. |
| Cloud-native architecture | **Full** | Sub-50 MB RAM idle footprint; boots in <100 ms. |
| Standard solutions before custom code | **Full** | Strictly implements ETSI specification; zero proprietary extensions. |
| Self-contained deployment | **Full** | Runs against standard PostgreSQL with PostGIS/TimescaleDB. |
| Technological consistency | **Full** | Standardizes core high-throughput components on Rust. |
| Multi-tenancy | **Full** | Native shared-schema multi-tenancy backed by PostgreSQL Row-Level Security (RLS). |
| Security by design | **Full** | Memory-safe language; RLS provides hard cryptographic/database boundary (GW23). |

## 3. Decision

1. **Antares as Default Broker**:
   - The platform adopts **Antares** (Rust) as its primary, default NGSI-LD context broker.
   - Built on Rust, Tokio, and SQLx, running against PostgreSQL with PostGIS and TimescaleDB.
   - Provides native shared-schema multi-tenancy utilizing PostgreSQL Row-Level Security (`tenant_id`), targeting 10,000+ tenants with zero schema migration overhead.
2. **Vanilla ETSI Compliance (CC-01)**:
   - The broker remains strictly policy-free and vanilla. It contains no custom authentication plugins, no GitOps knowledge, and no proprietary API extensions.
   - The platform's security firewall lives entirely in front of the broker in the Context Gateway (PEP/PDP).
3. **Scorpio and Stellio as Supported Alternatives**:
   - To preserve absolute vendor independence, **Scorpio** and **Stellio** remain officially supported drop-in alternative brokers.
   - Because all platform logic speaks standard CIM 009 operations, an operator may replace Antares with Scorpio or Stellio simply by changing the Helmfile chart definition without rewriting any configuration manifests (CC-01, CC-50).

## 4. Consequences

### Positive

- **Ultra-Low Memory Footprint**: Broker idle footprint drops from ~2.5 GB (JVM brokers) to ~35 MB, allowing full deployments on organisational edge gateways.
- **Massive Tenancy Scale**: Shared-schema RLS avoids the PostgreSQL catalog exhaustion associated with schema-per-tenant architectures when managing thousands of context spaces.
- **Shared Codebase**: The Context Gateway links directly against Antares's `antares-ql` crate, ensuring 100% identical query parsing (R56).

### Negative / Trade-offs

- As a newer broker implementation, Antares's community is smaller than FIWARE Orion-LD, mitigated by adhering strictly to the ETSI test suite (TS-05).

## 5. See Also

- Requirements: [CC-01 (Vanilla Broker)](../Requirements/city-as-code.md), [GW23 (Antares RLS)](../Requirements/gateway-firewall.md), [TS-05 (Conformance)](../Requirements/testing.md).

## Related

- [CC-01 (Vanilla Broker)](../Requirements/city-as-code.md) — referenced above.
- [GW23 (Antares RLS)](../Requirements/gateway-firewall.md) — referenced above.
- [TS-05 (Conformance)](../Requirements/testing.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
