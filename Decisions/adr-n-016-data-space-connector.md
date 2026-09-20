---
sidebar_position: 17
title: "ADR-N-016: Data Space Connector behind the Endpoint Layer"
---

# ADR-N-016: Data Space Connector behind the Endpoint Layer

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

## 1. Context

Organisations must share data with participants they have no prior relationship with (other twins, national platforms, companies) under negotiated, machine-readable contracts, and must consume such data themselves. The legacy platform planned an IDSA-style connector with its own data path. joinedcontext already has one enforcement point (the Context Gateway) and one sharing primitive (the Endpoint) with a DCAT-AP record and an ODRL-capable access surface.

## 2. Decision

The data space connector is an addon **behind** the Endpoint layer. It implements the Dataspace Protocol and DCP, publishes Endpoints as catalog Datasets, negotiates ODRL agreements, compiles them into `Policy` entities through the existing mapper (ADR 003) via a reviewed Git change, and hands consumers agreement-bound tokens for the Endpoint. It never touches the broker. On the consumer side, agreements feed Context Source Registrations, mounted Shared Space References or Bento pipelines. No engine is chosen: the addon is post-MVP, and the engine is picked when a data-space partner appears, behind the same `DataSpaceParticipant` manifest (DS-06).

## 3. Alternatives considered

- **Connector with its own data plane** (EDC data-plane proxying the broker): a second PEP with a second policy language; rejected.
- **No connector, Endpoints only**: works inside a known circle, fails the "unknown participant" and legal-contract cases; rejected as sole option.
- **TMForum product catalog and marketplace stack**: heavy, Java, duplicates the DCAT-AP catalog the Endpoints already have; left out, can be added as an addon in front of the connector.

## 4. Consequences

- One policy model and one enforcement point remain; contracts only produce grants inside the existing ceiling (DS-03).
- The did:web identity of the Organization (PF-41) does double duty as URN authority and data space participant id.
- Nothing in the platform depends on a connector today: the addon ships no chart and no component until the engine is chosen (DS-06).

## Related

- [00-register](00-register.md) — all decisions and their status.
- [../Architecture/18-data-space-connector.md](../Architecture/18-data-space-connector.md) — the design this decision governs.
- [../Requirements/data-space.md](../Requirements/data-space.md) — DS-01…DS-20.
