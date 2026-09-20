---
sidebar_position: 2
title: "Cluster Prerequisites & Sizing"
---

# Cluster Prerequisites & Sizing

Before deploying an instance of the platform, the target Kubernetes cluster and base infrastructure services must meet the requirements defined below.

## 1. Cluster Requirements

- **Kubernetes Version**: 1.28+ (up to 1.32), Linux x86_64 or arm64 nodes.
- **Container Network Interface (CNI)**: Calico, Cilium, or provider-native CNI with standard `NetworkPolicy` v1 enforcement.
- **Storage Class**:
  - `RWO` (ReadWriteOnce) persistent volume provisioner with SSD/NVMe backing (IOPS ≥ 3000 recommended for PostgreSQL and temporal storage).
  - Storage class names must be configured in `global.storage.storageClass.rwo`.
- **Ingress Controller**: Traefik, ingress-nginx, or Envoy Ingress supporting TLS termination and proxy headers.
- **Certificate Management**: `cert-manager` v1.13+ configured with a valid `ClusterIssuer` (e.g., Let's Encrypt or in-cluster CA).

## 2. Network & DNS Requirements

A base domain (e.g., `example.joinedcontext.com`) must be delegated to the ingress controller. The following subdomains must resolve to the cluster ingress external IP:

| Subdomain | Target Service | Usage |
|---|---|---|
| `api.<domain>` | APISIX Data Plane | Public and external programmatic APIs, NGSI-LD, STA, OGC Features, MCP |
| `portal.<domain>` | Portal UI / API | Web administration, dashboarding, and interactive configuration |
| `idm.<domain>` | Keycloak | OIDC authentication, token issuance, and account console |
| — | Gitea Forge | Served under `https://<domain>/git/` on the primary host, not on a name of its own: one certificate and one DNS record fewer, and the edge route table already binds the forge to `{host}` ([10-edge-routing-apisix.md](10-edge-routing-apisix.md) §2). Git over SSH is off; clone over HTTPS. |

## 3. Component Resource Sizing

Resource profiles are managed via `global.profile`: `development` (single-replica, minimal limits) or `production` (multi-replica, strict PDBs, HPA, HA PostgreSQL).

### Sizing Specifications Table

| Component | Profile | Replicas | CPU Request / Limit | Memory Request / Limit | Storage (PVC) |
|---|---|---|---|---|---|
| **Antares Broker** | Dev<br/>Prod | 1<br/>3 | 250m / 1000m<br/>1000m / 4000m | 512Mi / 1Gi<br/>2Gi / 8Gi | N/A (Stateless engine)<br/>PostgreSQL backed |
| **Context Gateway** | Dev<br/>Prod | 1<br/>3 (HPA) | 200m / 500m<br/>500m / 2000m | 256Mi / 512Mi<br/>512Mi / 2Gi | N/A |
| **Portal API** | Dev<br/>Prod | 1<br/>2 | 100m / 500m<br/>250m / 1000m | 128Mi / 256Mi<br/>256Mi / 512Mi | N/A |
| **Portal UI** | Dev<br/>Prod | 1<br/>2 | 50m / 200m<br/>100m / 500m | 64Mi / 128Mi<br/>128Mi / 256Mi | N/A |
| **APISIX Standalone** | Dev<br/>Prod | 1<br/>3 (HPA) | 200m / 1000m<br/>500m / 2000m | 256Mi / 512Mi<br/>512Mi / 1Gi | ConfigMap mounted |
| **jcctl Daemon** | Dev<br/>Prod | 1<br/>1 | 100m / 500m<br/>200m / 1000m | 128Mi / 256Mi<br/>256Mi / 1Gi | 10Gi (Repo workdir) |
| **Gitea Core** | Dev<br/>Prod | 1<br/>1 (HA failover)| 200m / 1000m<br/>500m / 2000m | 512Mi / 1Gi<br/>1Gi / 4Gi | 20Gi (Git Repositories) |
| **Keycloak IAM** | Dev<br/>Prod | 1<br/>2 | 500m / 1000m<br/>1000m / 2000m | 1Gi / 1.5Gi<br/>1.5Gi / 3Gi | N/A (DB backed) |
| **PostgreSQL (CNPG)**| Dev<br/>Prod | 1<br/>3 (HA) | 500m / 1000m<br/>1000m / 4000m | 1Gi / 2Gi<br/>4Gi / 16Gi | 20Gi (Dev)<br/>100Gi+ (Prod SSD) |
| **Bento Runner** | Per Project| 1–5 (HPA) | 100m / 500m<br/>200m / 1000m | 128Mi / 512Mi<br/>256Mi / 1Gi | N/A |

### Cluster Infrastructure Presets

- **Development / Edge Cluster**: 1 Node, 4 CPU Cores, 16 GiB RAM, 50 GiB Storage.
- **Small City Cluster**: 3 Nodes, 8 CPU Cores & 32 GiB RAM per node, 250 GiB Storage.
- **Regional Federation Hub**: 5+ Nodes, 16 CPU Cores & 64 GiB RAM per node, dedicated NVMe storage pool.

## Related

- [00-intro](00-intro.md) — deployment chapter order.
- [01-runbooks](../Operations/01-runbooks.md) — what to do when it breaks.
- [13-security](../Architecture/13-security.md) — the security model being deployed.
