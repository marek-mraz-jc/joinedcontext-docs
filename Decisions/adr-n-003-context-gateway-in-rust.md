---
sidebar_position: 4
title: "ADR-N-003: Context Gateway in Rust with Embedded Policy Evaluation"
---

# ADR-N-003: Context Gateway in Rust with Embedded Policy Evaluation

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

## 1. Context

CIVITAS/CORE v2 implemented security enforcement by routing requests through Apache APISIX, which invoked an external Open Policy Agent (OPA) sidecar over HTTP via the `opa` plugin. OPA in turn queried an external Spring Boot AuthZ Adapter, which queried PostgreSQL tables (ADR 023).

This architecture had severe performance and correctness issues:

1. **Triple Network Hop Latency**: `APISIX → OPA → AuthZ Adapter → PostgreSQL` added 30–80 ms overhead to every API request.
2. **Inexpressible Query Rewriting**: APISIX's Lua plugin and OPA's compile API could not parse or manipulate NGSI-LD Query Language (QL) abstract syntax trees, preventing native `scopeQ` and `q` injection.
3. **Privilege Bleed**: Concatenating user queries with policy filters caused cross-product grant leakage (ADR 006).

We evaluated Pingora, Apache APISIX plugins, standalone OPA, and a dedicated Rust gateway.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Model-driven data flow | **Full** | Policy rules are evaluated directly against `Policy` entities (ADR 002). |
| Distributed architecture with unified UX | **Full** | Gateway operates as a single ingress enforcement point. |
| Modular design | **Full** | Gateway can run embedded within Antares or as a standalone proxy. |
| Integrability via defined interfaces | **Full** | Transparent to standard NGSI-LD clients (R15). |
| Open source as default | **Full** | Permissive Rust crate ecosystem. |
| Cloud-native architecture | **Full** | Stateless, horizontally scalable, sub-millisecond overhead. |
| Standard solutions before custom code | **Partial** | Custom gateway required because no existing proxy parses NGSI-LD QL ASTs. |
| Self-contained deployment | **Full** | Operates without external OPA sidecars or database adapters. |
| Technological consistency | **Full** | Standardizes on Rust, sharing `antares-ql` crate with the broker. |
| Multi-tenancy | **Full** | Enforces tenant pinning and RLS propagation (GW20, GW23). |
| Security by design | **Full** | Fail-closed default, property-tested AST rewriter, zero bypass paths. |

## 3. Decision

1. **Develop Context Gateway in Rust**:
   - Built with `axum`, `hyper`, and `tower`.
   - Operates as the Policy Enforcement Point (PEP) and Representation Translator.
   - May be compiled directly into Antares (embedded mode) or run standalone in front of any compliant broker (standalone mode).
2. **One Grammar Everywhere (`antares-ql`)**:
   - The gateway parses incoming `q`, `scopeQ`, and `geoQ` parameters using the context broker's own `antares-ql` parser compiled as a shared Rust library (R56).
   - AST rewriting folds scope grants into anchored regex on `scope` and intersects query constraints per GW10–GW12.
3. **Native Rust Policy Decision Point (PDP)**:
   - External OPA sidecars and Java AuthZ adapters are eliminated from the data path.
   - The gateway evaluates policy rules natively in Rust against pre-compiled in-memory `Policy` entity data synchronized from the broker's policy space.
4. **Reject Pingora & APISIX Lua Plugins**:
   - Cloudflare Pingora was evaluated and rejected: Pingora is a byte/stream proxy optimized for HTTP/1-2 caching, lacking deep JSON-LD document manipulation primitives.
   - APISIX Lua plugins were rejected due to LuaJIT memory limits and inability to maintain shared memory AST trees without cross-process serialization bottlenecks.

## 4. Consequences

### Positive

- **Microsecond Policy Evaluation**: In-memory Rust evaluation eliminates the 3-hop HTTP round-trip; p99 gateway overhead drops to ≤ 5 ms under load.
- **Guaranteed Soundness**: AST rewriting uses the identical grammar as the broker, eliminating parsing divergence vulnerabilities.
- **Fail-Secure Architecture**: If policy caches are uninitialized or corrupted, the gateway denies all traffic (GW5).

### Negative / Trade-offs

- The team maintains the Context Gateway codebase in Rust rather than configuring off-the-shelf APISIX plugins.
- Property-based testing (`proptest`) becomes a mandatory CI gate to prevent rewriter regressions (TS-02).

## 5. See Also

- Supersedes: CIVITAS ADR 023, ADR 029, ADR 044.
- Requirements: [R1…R15 (Access Control)](../Requirements/access-control.md), [GW1…GW30 (Gateway Firewall)](../Requirements/gateway-firewall.md), [R44…R60 (Policy Firewall)](../Requirements/policy-firewall.md).

## Related

- [R1…R15 (Access Control)](../Requirements/access-control.md) — referenced above.
- [GW1…GW30 (Gateway Firewall)](../Requirements/gateway-firewall.md) — referenced above.
- [R44…R60 (Policy Firewall)](../Requirements/policy-firewall.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
