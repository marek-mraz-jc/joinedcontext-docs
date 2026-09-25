---
sidebar_position: 2
title: "Cluster Prerequisites & Sizing"
---

# Cluster Prerequisites & Sizing

What the target cluster must provide before [02-installation.md](02-installation.md), and how much of it each component asks for. Every number below is read from `joinedcontext-deployment`; the file it comes from is named beside it, so an operator can change it rather than guess.

## 1. Cluster Requirements

- **Kubernetes**: 1.28 or newer, Linux x86_64 or arm64 nodes. The reference cluster is single-node k3s pinned to channel `v1.33` (`hetzner-kit/kube.tf`).
- **Container Network Interface**: any CNI enforcing `NetworkPolicy` v1 (Calico, Cilium, or a provider-native one). The platform ships policies for every component and expects them to be enforced, not merely accepted.
- **Ingress controller**: one that terminates TLS and forwards proxy headers. Set its class in `global.ingress.ingressClass`. The shipped default is `nginx` (`defaults/environment/global.yaml`) and the reference cluster overrides it to `traefik`, because k3s ships Traefik: an installation whose cluster has a different controller must override this or the Ingress objects bind to nothing.
- **Certificate management**: `cert-manager` with a working `ClusterIssuer`, named in `global.ingress.clusterIssuer`. The reference cluster uses `letsencrypt-prod`, installed by kube-hetzner.
- **Storage**: a ReadWriteOnce provisioner. `global.storage.storageClass.rwo` is empty by default, which takes the cluster's default class; the reference cluster sets `local-path`. PostgreSQL and the artifact store are the volumes that matter, so SSD or NVMe backing is what the database wants. ReadWriteMany is not used by any component.
- **Service mesh**: Linkerd, injected by the `prepare` component, which also annotates every platform namespace `config.linkerd.io/default-inbound-policy: cluster-authenticated`. See [00-intro.md](00-intro.md) §2.

## 2. Network & DNS Requirements

One base domain is delegated to the ingress controller (`global.domain`). The edge puts most surfaces on the apex host and gives three names their own subdomain, taken from the `subDomain` key of each component's `apisix-routes.yaml`.

| Host | Target | Usage |
|---|---|---|
| `<domain>` | APISIX data plane | The programmatic surfaces: `/api/endpoint/*` (NGSI-LD, STA, OGC Features, MCP, per Endpoint), `/cs/*`, the forge under `/git/*`, and `/apps/{name}/*` only as a `308` to the App's host |
| `{name}.apps.<domain>` | APISIX, one host per published App | The App, its endpoint calls and its functions ([ADR-N-037](../Decisions/adr-n-037-an-origin-per-app.md)); covered by the `*.<domain>` record, one HTTP-01 certificate per App, no wildcard certificate |
| `portal.<domain>` | Portal | The API, the UI and the Portal's MCP door ([ADR-N-019](../Decisions/adr-n-019-login-at-the-edge-apisix-openid-connect.md)) |
| `idm.<domain>` | Keycloak | OIDC authentication, token issuance, account console |
| `data.<domain>` | CKAN | The open-data catalogue, when the `ckan` component is deployed |

There is no `api.<domain>`: the data-plane surfaces live on the apex. Gitea has no host of its own either, so the installation needs one certificate and one DNS record fewer; Git over SSH is off and clones go over HTTPS ([10-edge-routing-apisix.md](10-edge-routing-apisix.md) §2).

## 3. Component Resource Sizing

`global.profile` selects one of two value sets in every component: `development` (one replica, small limits) or `production` (more replicas, PodDisruptionBudgets, autoscaling where a component declares it). The numbers below are the `requests` and `limits` of `components/<component>/values/<release>/<profile>-values.yaml.gotmpl`.

| Component | Profile | Replicas | CPU request / limit | Memory request / limit | Storage |
|---|---|---|---|---|---|
| **Antares broker** | dev<br/>prod | 1<br/>1 | 100m / 1<br/>200m / 2 | 128Mi / 1Gi<br/>256Mi / 1Gi | none; state is in PostgreSQL |
| **Context Gateway** | dev<br/>prod | 1<br/>2, HPA to 5 at 70% CPU | 100m / 1<br/>500m / 2 | 128Mi / 512Mi<br/>512Mi / 2Gi | none |
| **Portal** (API, UI and reconciler) | dev<br/>prod | 1<br/>2, PDB minAvailable 1 | 100m / 1<br/>200m / 2 | 128Mi / 512Mi<br/>256Mi / 1Gi | none |
| **APISIX standalone** | dev<br/>prod | 1<br/>2, HPA to 10 at 80% CPU and memory | 100m / 500m<br/>500m / 2000m | 256Mi / 512Mi<br/>512Mi / 2Gi | rendered `apisix.yaml` from a file mount |
| **Gitea** | dev<br/>prod | 1<br/>1 | 200m / 1<br/>500m / 2 | 512Mi / 1Gi<br/>1Gi / 4Gi | 20Gi |
| **Keycloak** | dev<br/>prod | 1<br/>1 | 500m / 1000m<br/>2000m / 4000m | 1024Mi / 2048Mi<br/>4096Mi / 8192Mi | none; state is in PostgreSQL |
| **PostgreSQL instance (CNPG)** | dev<br/>prod | 1<br/>1 | 100m / 500m<br/>2 / 2 | 512Mi / 1Gi<br/>8Gi / 8Gi | 1Gi<br/>50Gi |
| **CNPG operator** | dev<br/>prod | 1<br/>2 | 100m / —<br/>200m / — | 200Mi / —<br/>400Mi / — | none |
| **Bento pipeline runner** | dev and prod | 1 | 100m / 1000m | 256Mi / 1024Mi | none |
| **Agent runner proxy** | dev<br/>prod | 1<br/>2 | 50m / 500m<br/>100m / 1 | 64Mi / 256Mi<br/>128Mi / 512Mi | none |
| **CKAN** | dev<br/>prod | 1<br/>1 | 200m / 2<br/>500m / 4 | 512Mi / 2Gi<br/>1Gi / 4Gi | PostgreSQL backed |

Two numbers to expect rather than be surprised by: the broker's development memory limit is 1Gi, not 512Mi, because a Load pipeline upserting four thousand vehicles per poll was OOM-killed at 512Mi seconds after each restart; and the production PostgreSQL instance requests and limits the same 2 CPU and 8Gi, which is what a database wants instead of a burstable limit.

### Cluster Infrastructure Presets

- **Development, and the reference cluster**: one node, 8 vCPU, 16 GiB RAM, node-local storage (a Hetzner `cpx42`). This runs the whole platform, the demo pipelines included.
- **Small city**: three nodes, 8 vCPU and 32 GiB RAM each, 250 GiB of network storage.
- **Regional federation hub**: five or more nodes, 16 vCPU and 64 GiB RAM each, a dedicated NVMe pool for the database.

## Related

- [00-intro](00-intro.md) — the chapter order and what each component is.
- [02-installation](02-installation.md) — the procedure these prerequisites are for.
- [03-configuration](03-configuration.md) — where `global.*` is read from and how to override it.
- [10-edge-routing-apisix](10-edge-routing-apisix.md) — the route table behind the host list above.
- [01-runbooks](../Operations/01-runbooks.md) — what to do when it breaks.
