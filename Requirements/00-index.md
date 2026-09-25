---
sidebar_position: 1
title: Requirements Architecture & Taxonomy
description: Normative requirements catalog map, conformance conventions, and consumer class definitions.
---

# Requirements Architecture & Taxonomy

The joinedcontext platform states its normative requirements in nineteen families, one file each. This page is the map: which family covers what, which IDs it holds, which architecture chapter owns it and which test family proves it. It also fixes the conformance keywords, the consumer-class tags and the terminology this specification uses in place of the legacy platform's.

## 1. Conformance and Keyword Semantics

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document and all sub-chapters are to be interpreted as described in BCP 14 [RFC 2119] [RFC 8174] when, and only when, they appear in all capitals, as used here.

Every requirement statement in this specification is uniquely identified by an alphanumeric code consisting of a family prefix, a hyphen, and a sequential number (for example, `PF-01`, `EP-12`).

## 2. Consumer Classes

Every platform capability MUST serve three distinct consumer classes without introducing bifurcated data pipelines or private backend channels:

- **`[H]` Human**: End-users, organizational operators, domain stewards, and system administrators interacting through accessible, localized browser interfaces (Portal UI). Operations are backed by self-describing forms, human-readable labels, and visual workflows with zero Git or YAML exposure in default paths.
- **`[P]` Program**: Traditional software services, client applications, batch workers, external IoT integrations, and automation scripts communicating over strictly defined, versioned APIs (REST, OpenAPI, ETSI GS CIM 009 NGSI-LD, OGC API Features, SensorThings API, WebSockets, MQTT).
- **`[A]` AI Agent**: Autonomous software agents interacting through the Model Context Protocol (MCP) or direct API endpoints with no prior out-of-band coordination. Agents require runtime semantic discovery via JSON-LD `@context`, pre-flight permission introspection, machine-readable schemas, structured error envelopes, and self-throttling rate-limit metadata.
- **`[S]` Security**: Security baseline and hardening controls governing infrastructure, admission policies, cryptographic primitives, and isolation barriers.

## 3. Requirement Families & Catalog Map

The ID range of each family is its lowest and highest live ID, not a count: a retired ID leaves a gap and is never reused. Whether a requirement is proven by a test is not in this table, because it changes with every commit; [compliance-matrix.md](compliance-matrix.md) carries it, generated from the tests that name each ID.

| Family Prefix | Family Name | Requirement Range | Specification File | Owning Architecture Chapter | Test Family |
|---|---|---|---|---|---|
| **PF** | Platform & Domain Invariants | PF-01…PF-89 | [platform.md](platform.md) | [Architecture/03-domain-model.md](../Architecture/03-domain-model.md) | [Testing/04-configuration-and-pipeline-tests.md](../Testing/04-configuration-and-pipeline-tests.md) |
| **MF** | Manifest Model, Import/Sync/Download | MF-01…MF-47 | [manifests.md](manifests.md) | [Architecture/06-configuration-as-code.md](../Architecture/06-configuration-as-code.md) | [Testing/04-configuration-and-pipeline-tests.md](../Testing/04-configuration-and-pipeline-tests.md) |
| **EP** | Endpoints & Representations | EP-01…EP-80 | [endpoints.md](endpoints.md) | [Architecture/04-context-spaces-and-endpoints.md](../Architecture/04-context-spaces-and-endpoints.md) | [Testing/02-conformance-tests.md](../Testing/02-conformance-tests.md) |
| **PL** | Pipeline Execution | PL-01…PL-57 | [pipelines.md](pipelines.md) | [Architecture/08-pipelines.md](../Architecture/08-pipelines.md) | [Testing/04-configuration-and-pipeline-tests.md](../Testing/04-configuration-and-pipeline-tests.md) |
| **AG** | Agent & MCP Governance | AG-01…AG-93 | [agents.md](agents.md) | [Architecture/07-agents-and-mcp.md](../Architecture/07-agents-and-mcp.md) | [Testing/06-security-tests.md](../Testing/06-security-tests.md) |
| **UI** | Portal & User Interface | UI-01…UI-86 | [portal-and-ui.md](portal-and-ui.md) | [Architecture/09-portal.md](../Architecture/09-portal.md) | [Testing/03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| **TS** | Testing & Quality Assurance | TS-01…TS-25 | [testing.md](testing.md) | [Architecture/01-overview.md](../Architecture/01-overview.md) | [Testing/00-strategy.md](../Testing/00-strategy.md) |
| **DM** | Data Models & LinkML Editor | DM-01…DM-60 | [data-models.md](data-models.md) | [Architecture/11-data-models.md](../Architecture/11-data-models.md) | [Testing/02-conformance-tests.md](../Testing/02-conformance-tests.md) |
| **MP** | Model Projections | MP-01…MP-03 | [model-projections.md](model-projections.md) | [Architecture/04-context-spaces-and-endpoints.md](../Architecture/04-context-spaces-and-endpoints.md) | [Testing/01-backend-tests.md](../Testing/01-backend-tests.md) |
| **SDK** | App SDK | SDK-01…SDK-30, SDK-35…SDK-37 | [app-sdk.md](app-sdk.md) | [Architecture/20-app-sdk.md](../Architecture/20-app-sdk.md) | [Testing/03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| **OPS** | Operations & Reliability | OPS-01…OPS-51 | [operations.md](operations.md) | [Architecture/13-security.md](../Architecture/13-security.md) | [Testing/05-deployment-and-performance-tests.md](../Testing/05-deployment-and-performance-tests.md) |
| **AP** | Apps on Demand | AP-01…AP-131 | [apps.md](apps.md) | [Architecture/16-apps-on-demand.md](../Architecture/16-apps-on-demand.md) | [Testing/03-frontend-and-e2e-tests.md](../Testing/03-frontend-and-e2e-tests.md) |
| **DS** | Data Space Connector | DS-01…DS-20 | [data-space.md](data-space.md) | [Architecture/18-data-space-connector.md](../Architecture/18-data-space-connector.md) | [Testing/02-conformance-tests.md](../Testing/02-conformance-tests.md) |
| **R** | Access Control Core | R1–R43 | [access-control.md](access-control.md) | [Architecture/05-context-gateway.md](../Architecture/05-context-gateway.md) | [Testing/01-backend-tests.md](../Testing/01-backend-tests.md) |
| **MIM** | Minimal Interoperability Mechanisms | MIM0–MIM10 | [access-control.md](access-control.md) | [Architecture/01-overview.md](../Architecture/01-overview.md) | [Testing/02-conformance-tests.md](../Testing/02-conformance-tests.md) |
| **GW** | Gateway Firewall | GW1–GW34 | [gateway-firewall.md](gateway-firewall.md) | [Architecture/05-context-gateway.md](../Architecture/05-context-gateway.md) | [Testing/01-backend-tests.md](../Testing/01-backend-tests.md) |
| **PW / I** | Policy Firewall Extensions & Identity | R44–R60, I1–I4 | [policy-firewall.md](policy-firewall.md) | [Architecture/05-context-gateway.md](../Architecture/05-context-gateway.md) | [Testing/01-backend-tests.md](../Testing/01-backend-tests.md) |
| **CC** | Configuration as Code | CC-01…CC-90 | [city-as-code.md](city-as-code.md) | [Architecture/06-configuration-as-code.md](../Architecture/06-configuration-as-code.md) | [Testing/04-configuration-and-pipeline-tests.md](../Testing/04-configuration-and-pipeline-tests.md) |
| **SP** | Space Surface | SP-01…SP-22 | [space-surface.md](space-surface.md) | [Architecture/04-context-spaces-and-endpoints.md](../Architecture/04-context-spaces-and-endpoints.md) | [Testing/02-conformance-tests.md](../Testing/02-conformance-tests.md) |

## 4. Terminology Delta & Vocabulary Mapping

| Legacy Term (CIVITAS/CORE v2 / Early Drafts) | Target Term (This Specification) | Scope and Semantic Delta |
|---|---|---|
| Tenant (Mandant) | **Organization** | Top-level administrative and organizational boundary owning users, groups, roles, and projects. |
| (Platform-level) Tenant ID | **Context Space (`ContextSpace`)** | The actual tenant on the NGSI-LD context broker; unit of data isolation. Never exposed as an HTTP header to clients. |
| DataPool / DataSpace | **Project** | Collaborative working domain owned by an Organization. Owns Context Spaces, Pipelines, Dashboards, and Blueprint instances. |
| DataSet | **Context Space + DataModel + Endpoint** | Decomposed concept: structural definition moves to `DataModel`, storage/state to `ContextSpace`, and consumption to `Endpoint`. |
| Connector / ETL job (the CIVITAS `DataSource`) | **Pipeline** | Unified declarative processing pipeline running Bento in resident streams or scheduled CronJob mode. The name is reused for something narrower: `kind: DataSource` is only the connection of one external feed and its credentials, which a Pipeline references (MF-35, PL-39). |
| Distribution | **Endpoint Representation** | Multi-format view (NGSI-LD, GeoJSON, OGC API, CSV, STA) exposed under an Endpoint. |
| DataStructure | **DataModel** | Data models authored in LinkML, compiling to versioned JSON Schema draft-07 and JSON-LD `@context`. |
| Application | **Addon** | External software components (for example Superset, Grafana, Agent Runner) deployed alongside core infrastructure. |
| City Repository | **Org Repository (`org-repo`)** | The single Git repository representing an Organization's declarative state. |
| User Application | **Portal** | The unified web interface consisting of Portal API (Rust) and Portal UI (React). |
| Evidencia / Razidlo | **Evidencia / Razidlo** (Kept) | Retained from ADR 001 for deterministic URN naming: `urn:ngsi-ld:{Type}:{orgDomain}:{space}:{localId}`. |

## Related

- [traceability.md](traceability.md) — end-to-end traceability matrix mapping requirement ranges to architecture and tests.
- [compliance-matrix.md](compliance-matrix.md) — every requirement with the named tests that prove it and the lane that runs them.
- [platform.md](platform.md) — fundamental platform and domain invariants.
- [access-control.md](access-control.md) — core access control and MIM interoperability requirements.
- [city-as-code.md](city-as-code.md) — declarative configuration plane requirements.
- [STYLE.md](../STYLE.md) — documentation style guidelines.
