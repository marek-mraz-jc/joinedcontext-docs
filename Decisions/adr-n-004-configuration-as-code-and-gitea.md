---
sidebar_position: 5
title: "ADR-N-004: Configuration-as-Code Configuration Plane with Gitea"
---

# ADR-N-004: Configuration-as-Code Configuration Plane with Gitea

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

## 1. Context

CIVITAS/CORE v2 propagated platform configuration (users, roles, datasets, apisix routes, geoserver layers) using an asynchronous event-driven architecture over an Apache Kafka message bus using CloudEvents (ADR 013, ADR 021). Multi-service provisioning workflows were orchestrated via an asynchronous Saga engine backed by transactional outbox tables (ADR 030, ADR 031).

This approach proved fragile in production:

1. **Eventual Inconsistency and Deadlocks**: Compensation cascades in distributed sagas failed on partial network outages, leaving dangling external resources in APISIX or Keycloak.
2. **Infrastructure Weight**: Running Strimzi Kafka, Zookeeper/KRaft, and multiple config-adapter JVM services required extensive cluster RAM and maintenance.
3. **No Audit Trail**: Kafka topics with retention windows did not provide an immutable, human-reviewable historical audit of who changed what, when, and who approved it.

We evaluated declarative Configuration-as-Code approaches (Approach A through G in `configuration-plane-approaches.md`).

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Model-driven data flow | **Full** | The Git repository is the authoritative source of truth for platform model structure. |
| Distributed architecture with unified UX | **Full** | Users interact with blueprints via Portal forms; changes commit to Git transparently. |
| Modular design | **Full** | Configuration plane is decoupled from runtime broker operations. |
| Integrability via defined interfaces | **Full** | Standard Git protocols, OpenAPI webhooks, and JSON Schema. |
| Open source as default | **Full** | Gitea is 100% open-source (MIT). |
| Cloud-native architecture | **Full** | Reconciler runs as Kubernetes jobs or lightweight daemon; zero Kafka dependency. |
| Standard solutions before custom code | **Full** | Leverages standard Git semantics (commits, branches, pull requests, CODEOWNERS). |
| Self-contained deployment | **Full** | Gitea deployed in-cluster via Helm; easily backed up or replaced. |
| Technological consistency | **Full** | Eliminates Java config adapters; standardizes reconciler on Rust. |
| Multi-tenancy | **Full** | Organizations map 1:1 to Gitea organizations and protected repositories. |
| Security by design | **Full** | All configuration changes attributable, peer-reviewed, and cryptographically signed. |

## 3. Decision

1. **Adopt Approach A (Pure Configuration-as-Code)**:
   - Eliminate Kafka, Zookeeper, CloudEvents config adapters, transactional outbox tables, and distributed sagas.
   - The Git repository ("org repository") is the **single source of truth** for all platform configuration (CC-02).
   - The reconciler (`jcctl`) is the **only component** authorized to write configuration to the broker, gateway, Keycloak, or pipeline runners (CC-03).
2. **In-Cluster Forge: Gitea**:
   - Gitea is deployed as the in-cluster Git forge.
   - GitLab CE was evaluated and **disqualified**: GitLab Free paywalls required merge approvals and file-specific code owners behind Premium/Ultimate licenses (stack verdict S2).
   - In Gitea, domain ownership is governed by `CODEOWNERS` and protected branches (CC-41). Interim code-owner validation is enforced via CI status checks until Gitea 28 ships native code-owner blocking.
3. **Interaction Lanes**:
   - Configuration changes adhere to risk-classed lanes (CC-63): Green (auto-approved self-service), Yellow (single domain approver), and Red (full multi-party review).

## 4. Consequences

### Positive

- **Immense Operational Simplification**: Eliminating Kafka, Zookeeper, and 5+ Java adapter pods saves >6 GB RAM per deployment.
- **Immutable Audit Trail**: Git history natively records the author, approver commit hash, and timestamp for every single platform setting (CC-44).
- **Disaster Recovery by Replay**: Complete cluster disaster recovery is achieved simply by pointing `jcctl` at the repository and running `apply` (CC-50).

### Negative / Trade-offs

- Changes made by users in the Portal UI have a bounded latency of several seconds while the commit, CI checks, and webhook-triggered reconcile execute.
- In-cluster Gitea storage and PostgreSQL metadata must be included in backup schedules.

## 5. See Also

- Supersedes: CIVITAS ADR 013, ADR 021, ADR 026, ADR 030, ADR 031, ADR 036, ADR 041, ADR 042, ADR 043.
- Requirements: [CC-01…CC-70 (Configuration-as-Code)](../Requirements/city-as-code.md), [PF-01…PF-28 (Platform)](../Requirements/platform.md).
- Research: [configuration-plane-approaches.md](../Research/configuration-plane-approaches.md), [city-as-code-stack.md](../Research/city-as-code-stack.md).

## 6. Addendum, resource model

Manifests use the Kubernetes resource model (`apiVersion`, `kind`, `metadata`, `spec`, server-side `status`) and a kubectl-shaped resource API, so download, import and continuous sync (`SyncSource`) are first-class UI operations with CLI/MCP parity ([MF-01…MF-34](../Requirements/manifests.md)). This is the *shape* of Kubernetes objects only: they live in Git and are applied over plain NGSI-LD and pipeline APIs; CRDs and an in-cluster operator (approach B in [configuration-plane-approaches](../Research/configuration-plane-approaches.md)) remain rejected because they would tie the configuration plane to a cluster and to CRD schema evolution.

## Related

- [CC-01…CC-70 (Configuration-as-Code)](../Requirements/city-as-code.md) — referenced above.
- [PF-01…PF-28 (Platform)](../Requirements/platform.md) — referenced above.
- [configuration-plane-approaches.md](../Research/configuration-plane-approaches.md) — referenced above.
- [city-as-code-stack.md](../Research/city-as-code-stack.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
