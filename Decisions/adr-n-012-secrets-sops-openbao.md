---
sidebar_position: 13
title: "ADR-N-012: Secrets Management via SOPS and OpenBao"
---

# ADR-N-012: Secrets Management via SOPS and OpenBao

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

## 1. Context

CIVITAS ADR 027 established HashiCorp Vault for external pipeline credentials, while ADR 028 introduced interim AES-256-GCM encryption in the PostgreSQL database.

In August 2023, HashiCorp transitioned Vault from the open-source MPL 2.0 license to the Business Source License (BSL 1.1). BSL is not an open-source license recognized by the Open Source Initiative (OSI) and creates legal and procurement liabilities for public sector organisational data platforms adhering to the "Public Money – Public Code" principle.

Furthermore, deploying a full Vault cluster for small, single-city installations introduces unnecessary operational complexity. We need a dual-tier secrets strategy adhering strictly to open-source licenses.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Model-driven data flow | **Full** | Manifests declare named secret references (`secretRef`); values resolved at apply. |
| Distributed architecture with unified UX | **Full** | Transparent to users; Portal handles secret entry into secure backends. |
| Modular design | **Full** | Decoupled secrets engine; pluggable between SOPS and OpenBao. |
| Integrability via defined interfaces | **Full** | Standard Kubernetes Secret injection and REST/Vault APIs. |
| Open source as default | **Full** | OpenBao (MPL 2.0) and SOPS (Apache 2.0) are 100% open source. |
| Cloud-native architecture | **Full** | Integrates natively with Kubernetes ServiceAccount tokens. |
| Standard solutions before custom code | **Full** | OpenBao is the Linux Foundation fork of Vault; SOPS is CNCF ecosystem standard. |
| Self-contained deployment | **Full** | SOPS requires zero running pods; OpenBao deploys cleanly in-cluster. |
| Technological consistency | **Full** | Secrets never committed in plaintext in Git (CC-06). |
| Multi-tenancy | **Full** | Path-scoped access control per project and pipeline runner. |
| Security by design | **Full** | Encryption at rest, short-lived tokens, zero plaintext leaks in logs. |

## 3. Decision

1. **Reject HashiCorp Vault (BSL)**:
   - HashiCorp Vault is disqualified due to its non-OSI BSL license (stack verdict S6).
   - Database-level encryption (ADR 028) is eliminated.
2. **Adopt OpenBao as Enterprise Secrets Backend**:
   - For regional, multi-cluster, or high-security deployments, **OpenBao** (Linux Foundation, MPL 2.0) is adopted as the enterprise secret store.
   - OpenBao maintains full API compatibility with Vault, supporting Kubernetes auth methods and KV-v2 secret engines.
3. **Adopt SOPS + age for Lightweight Single-City Deployments**:
   - For single-instance, lightweight organisational installations, **SOPS** with `age` encryption keys is adopted.
   - Encrypted files (`secrets.enc.yaml`) are stored in the repository; the reconciler decrypts them in memory at apply time using the cluster's private age key.
4. **External Secrets Pattern (CC-06, PL-14)**:
   - Manifests in Git store **named references only** (`secretRef: parking-mqtt-creds`).
   - The Portal UI writes secret values directly to OpenBao or encrypts via SOPS; plaintext secrets never enter Git commits, merge request diffs, or CI logs.
   - The reconciler resolves secret references during wave apply and injects them into pipeline runner environments.

## 4. Consequences

### Positive

- **100% Open-Source Compliance**: Eliminates all BSL licensing liabilities for organisational procurement.
- **Operational Scalability**: Small cities use lightweight SOPS (zero pods); regional platforms use OpenBao.
- **Zero Plaintext in Git**: Full adherence to CC-06 and TR-03187 security standards.

### Negative / Trade-offs

- Operators using OpenBao must manage unsealing, snapshot backups, and transit keys.

## 5. See Also

- Supersedes: CIVITAS ADR 027, ADR 028.
- Requirements: [CC-06 (Secrets Invariant)](../Requirements/city-as-code.md), [PL-14…PL-17 (Pipeline Secrets)](../Requirements/pipelines.md).
- Research: [city-as-code-stack.md](../Research/city-as-code-stack.md) (Seam S6).

## Related

- [CC-06 (Secrets Invariant)](../Requirements/city-as-code.md) — referenced above.
- [PL-14…PL-17 (Pipeline Secrets)](../Requirements/pipelines.md) — referenced above.
- [city-as-code-stack.md](../Research/city-as-code-stack.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
