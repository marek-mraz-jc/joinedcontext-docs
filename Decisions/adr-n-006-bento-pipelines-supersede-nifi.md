---
sidebar_position: 7
title: "ADR-N-006: Bento Pipelines Superseding Apache NiFi"
---

# ADR-N-006: Bento Pipelines Superseding Apache NiFi

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

## 1. Context

CIVITAS ADR 038 selected Apache NiFi as the pipeline engine over Redpanda Connect based on three arguments: built-in Role-Based Access Control (RBAC), a drag-and-drop web UI, and built-in multi-tenancy.

In practice, Apache NiFi introduced catastrophic operational overhead:

1. **Extreme Resource Baseline**: A minimal 2-node NiFi cluster required 4–8 GB RAM idle, making small tenant hosting prohibitively expensive.
2. **Poor GitOps Alignment**: NiFi flows are serialized as complex, position-heavy JSON flows that produce unreadable Git diffs and merge conflicts.
3. **No Container Isolation**: All NiFi process groups share a single JVM heap; script processors (`ExecuteScript`) can access shared memory of co-located pipelines.

Furthermore, Redpanda Connect was relicensed under the commercial Redpanda Community License. However, WarpStream forked the pre-acquisition codebase as **Bento** (`warpstreamlabs/bento`) under the permissive **MIT License**.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Model-driven data flow | **Full** | Pipeline YAML configs derived from Git repository manifests. |
| Distributed architecture with unified UX | **Full** | Pipelines run in isolated project runner pods; managed via Portal UI. |
| Modular design | **Full** | Native Bento engine; interchangeable pipeline definitions. |
| Integrability via defined interfaces | **Full** | Native support for MQTT, Kafka, HTTP, SQL, S3, WebSockets. |
| Open source as default | **Full** | Bento is 100% open source under the MIT License. |
| Cloud-native architecture | **Full** | Lightweight Go binary (15–30 MB RAM per idle stream), containerized execution. |
| Standard solutions before custom code | **Full** | Utilizes Bento streams mode, eliminating custom supervisor logic. |
| Self-contained deployment | **Full** | Runs as standard Kubernetes Deployments and CronJobs. |
| Technological consistency | **Full** | Standardizes pipeline configurations on YAML + Bloblang. |
| Multi-tenancy | **Full** | Per-project runner deployment isolation eliminates JVM memory sharing. |
| Security by design | **Full** | OS-level container isolation; secret references resolved at runtime. |

## 3. Decision

1. **Reverse CIVITAS ADR 038**: Apache NiFi is eliminated from the platform core.
2. **Adopt Bento (`warpstreamlabs/bento`, MIT)**:
   - Bento is adopted as the platform's standard pipeline engine.
   - `redpanda-data/connect` is explicitly disqualified due to commercial licensing restrictions (stack verdict S5).
3. **Dual Execution Classes**:
   - **Resident Pipelines**: Streaming inputs (MQTT, Kafka, WebSockets) execute in Bento **Streams Mode** (`bento streams`) within dedicated per-project `PipelineRunner` deployments.
   - **Scheduled Pipelines**: Batch loads (SQL dumps, daily CSV imports) execute as standard Kubernetes `CronJob` pods running `bento -c bento.yaml` to completion (scale-to-zero).
4. **Resolution of Legacy NiFi Arguments**:
   - *RBAC*: Governed by Project permissions in Git and Keycloak, rather than in-engine user tables.
   - *UI*: Managed via the Portal UI flow gallery and generated forms.
   - *Multi-tenancy*: Enforced via distinct Kubernetes Pods and NetworkPolicies per Project.
   - *Supervisor*: Bento's built-in streams mode hot-reloads streams from a mounted directory, eliminating the need for a custom supervisor.

## 4. Consequences

### Positive

- **Massive Resource Reduction**: Memory per pipeline dropped from ~500 MB (NiFi share) to 15–30 MB (Bento stream).
- **Native GitOps**: Bento YAML configs are clean, human-readable, and produce clear diffs during code review.
- **True Process Isolation**: A memory leak or crash in Project A's pipeline cannot destabilize Project B's pipelines.

### Negative / Trade-offs

- Complex visual canvas editing of deep transformation graphs is replaced by Bloblang mappings and standard blueprint forms.

## 5. Addendum: derived pipelines and compute steps

Pipelines also compute from entities already in a Context Space and write the result back, to the same or another space (PL-31…PL-38). Bento stays the engine; the compute step is one of `bloblang`, `mapping` (LinkML-Map), `wasm` (Rust compiled to `wasm32-wasip1`, run by Bento's `wasm` processor, no I/O, pinned by digest) or `container` (a CI-built image run as a Job for heavy or library-bound work). A separate workflow engine (Argo, Airflow, Temporal) was considered and rejected: the four kinds cover the cases seen so far with no new control plane, and every step still writes through the Endpoint and its Policy. Revisit if multi-step DAGs with human tasks appear. Provenance is `derivedFrom` + `computedBy` on the output; the reconciler blocks self-triggering feedback loops (PL-37).

## 6. See Also

- Supersedes: CIVITAS ADR 037, ADR 038.
- Requirements: [PL-01…PL-38 (Pipelines)](../Requirements/pipelines.md).
- Research: [city-as-code-stack.md](../Research/city-as-code-stack.md).

## Related

- [PL-01…PL-38 (Pipelines)](../Requirements/pipelines.md) — referenced above.
- [city-as-code-stack.md](../Research/city-as-code-stack.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
