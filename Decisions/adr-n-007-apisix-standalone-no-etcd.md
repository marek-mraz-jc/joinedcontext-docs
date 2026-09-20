---
sidebar_position: 8
title: "ADR-N-007: Apache APISIX in Declarative Standalone Mode"
---

# ADR-N-007: Apache APISIX in Declarative Standalone Mode

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

## 1. Context

CIVITAS/CORE v2 deployed Apache APISIX backed by an external clustered `etcd` datastore with custom RBAC authentication (ADR 014, `apisix-configuration.md`). Route configurations were provisioned dynamically at runtime via HTTP calls to the APISIX Admin API using generated admin API keys.

This introduced significant architectural liabilities:

1. **Operational Vulnerability**: The APISIX Admin API represented a high-value mutable attack surface. A compromised admin key allowed arbitrary route manipulation and backend exfiltration.
2. **Infrastructure Overhead**: Running an etcd cluster (1–3 pods) with persistent storage, volume claims, and authentication init jobs added operational fragility.
3. **Out-of-Band State Drift**: Routes pushed directly to the Admin API bypassed GitOps pipelines and were vulnerable to desynchronization upon etcd restarts.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Model-driven data flow | **Full** | `apisix.yaml` rendered deterministically from Git manifests by the reconciler. |
| Distributed architecture with unified UX | **Full** | Unifies ingress routing under declarative GitOps control. |
| Modular design | **Full** | Gateway operates as a stateless data plane. |
| Integrability via defined interfaces | **Full** | Standard Kubernetes ConfigMaps and standard HTTP reverse proxying. |
| Open source as default | **Full** | Apache APISIX is Apache 2.0. |
| Cloud-native architecture | **Full** | Stateless pods, sub-second boot, scales horizontally without etcd quorum. |
| Standard solutions before custom code | **Full** | Uses APISIX's built-in standalone YAML file mode. |
| Self-contained deployment | **Full** | Eliminates etcd StatefulSets, PVCs, and auth-init jobs. |
| Technological consistency | **Full** | All infrastructure routing managed as declarative manifests. |
| Multi-tenancy | **Full** | APISIX handles prefix routing; Context Gateway handles tenant isolation. |
| Security by design | **Full** | Mutable Admin API is physically disabled; zero route manipulation attack surface. |

## 3. Decision

1. **Operate APISIX in Standalone File Mode**:
   - APISIX is deployed with `deployment.role: data_plane` and `deployment.role_data_plane.config_provider: yaml`.
   - The entire routing configuration is mounted into `/usr/local/apisix/conf/apisix.yaml` via a Kubernetes ConfigMap.
2. **Eliminate etcd**:
   - Embedded and external `etcd` clusters are completely removed from the deployment stack (`etcd.enabled: false`).
3. **Physically Disable Admin API**:
   - In standalone file mode, APISIX does not start the Admin API, removing the network port and eliminating credential exposure risks.
4. **Declarative Rendering and Reloads**:
   - The `jcctl` reconciler renders `apisix.yaml` from committed platform manifests.
   - The ConfigMap is updated on merge, and APISIX reloads routing rules into worker memory within 1 second without dropping active connections.
   - The reconciler MUST append the mandatory `#END` marker to `apisix.yaml` per stack verdict S7.

## 4. Consequences

### Positive

- **Zero Mutable Admin Surface**: Routes cannot be injected or modified via HTTP; the data plane strictly reflects Git truth.
- **Resource Savings**: Deleting etcd saves 1–3 pods, PVCs, and ~500 MB memory.
- **Deterministic Routing**: Routing configuration is versioned, reviewed, and diffable in Git.

### Negative / Trade-offs

- Route reload latency is bounded by Kubernetes ConfigMap mount propagation and APISIX's 1-second file poll interval (CC-65).
- Reconciler bugs generating an invalid `apisix.yaml` or omitting `#END` could cause APISIX to reject the new configuration (mitigated by CI validation TS-18).

## 5. Addendum: Edge Baseline

The phase-1 deployment baseline operationalizes APISIX standalone file mode with the following concrete architectural decisions:

1. **Edge Ingress Topology:** The platform supports both two-tier ingress (shared ingress controller in front of APISIX ClusterIP) and single-tier direct edge (APISIX exposed via `Service` of type `LoadBalancer` terminating TLS directly via cert-manager). Single-tier direct edge is the primary architectural recommendation for dedicated deployments because it eliminates unnecessary proxy hops and simplifies Linkerd service mesh boundaries.
2. **Decommissioned Components:** The legacy `apisix-static-configuration` batch Job (`components/apisix/charts/configuration/templates/configuration.yaml`), the clustered etcd component (`components/etcd`), and the admin credentials Secret (`apisix-admin-credentials`) are permanently removed from the deployment tree.
3. **Elimination of Mutable Control Plane:** APISIX is deployed with `admin.enabled: false`. Port 9180 is physically closed, eliminating the risk of runtime route injection or credential compromise.
4. **Declarative Rendering via `jcctl`:** Route tables, upstreams, and plugin configurations are synthesized deterministically from committed `Endpoint` and `App` manifests. The generated `/usr/local/apisix/conf/apisix.yaml` is validated prior to ConfigMap commit and strictly terminates with the mandatory `#END` marker.
5. **Gateway Security Headers:** All route plugin configurations inject mandatory HTTP security headers (HSTS, CSP, X-Content-Type-Options, Cache-Control) via the `response-rewrite` plugin, closing legacy finding deployment#242.
6. **Detailed Specification:** See [Edge Routing & APISIX Standalone Specification](../Deployment/10-edge-routing-apisix.md) for complete route tables, plugin parameters, and failure recovery runbooks.

## 6. See Also

- Modifies: CIVITAS ADR 014.
- Requirements: [SP-21 (Provisioning)](../Requirements/space-surface.md), [OPS-01…OPS-03 (Deployment)](../Requirements/operations.md).
- Research: [city-as-code-stack.md](../Research/city-as-code-stack.md) (Seam S7).

## Related

- [Edge Routing & APISIX Standalone Specification](../Deployment/10-edge-routing-apisix.md) — referenced above.
- [SP-21 (Provisioning)](../Requirements/space-surface.md) — referenced above.
- [OPS-01…OPS-03 (Deployment)](../Requirements/operations.md) — referenced above.
- [city-as-code-stack.md](../Research/city-as-code-stack.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
