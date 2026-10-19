---
sidebar_position: 15
title: "Production Instance smartcity"
description: "The production installation at smartcity.joinedcontext.com: its cluster, hostnames, what it carries, backups, restore, patching and the hold rules."
---

# Production Instance smartcity

`smartcity.joinedcontext.com` is the first production installation of the platform. It runs the same components and the same seeds as the `dev` instance, rendered for its own domain, on a cluster of its own. This page records what differs from `dev` and how an operator keeps it running. Installing any other instance follows [02-installation.md](02-installation.md); this page only names the choices made for this one.

## 1. Cluster

- **Node:** one Hetzner `cpx52` in `nbg1` (12 vCPU, 24 GB, 480 GB disk), created by the kube-hetzner kit at v3.2.1 with k3s `v1.35.9+k3s1` (T-4677).
- **Add-ons from the kit:** Traefik (the ingress class), cert-manager, Kyverno, Linkerd. SELinux is enforcing on the MicroOS node.
- **Secrets at rest:** etcd encrypts Secrets with `aescbc`. The key in use is `key2`, rotated on 2026-10-18 before any Secret of the platform existed (T-4678).
- **Access:** the API and SSH answer only to the operator's addresses (firewall). The kubeconfig and the break-glass SSH key live outside every repository. The terraform state holds private keys, so it lives in its own directory with mode 700, never in Git.
- **No high availability.** One node has no quorum. The environment runs the production profile with single-node overrides: one PostgreSQL instance, no required pod anti-affinity, single replicas where the profile asks for more. Backups (section 4) are the recovery path, not a standby.

## 2. Hostnames

Every name is a subdomain of `smartcity.joinedcontext.com`. A records for the apex and the wildcard point at the node. Each hostname gets its own certificate by HTTP-01, never a wildcard certificate.

| Host | Serves |
|---|---|
| `smartcity.joinedcontext.com` | the Portal, the public API pages, `/docs` |
| `portal.` | the Portal's own host |
| `idm.` | Keycloak, the realm of this instance |
| `api.` | public data, NGSI-LD, OGC, OData and MCP |
| `opendata.` | the CKAN open-data catalogue |
| `data.` | answers 301 to `opendata.` with the same path (T-4679) |
| `assistant.` | the public assistant channel |
| `tiles.` | the background map |
| `viz.` | the chart renderer |
| `*.apps.` | one host per published App |

Certificates came from `letsencrypt-staging` for the first apply and come from `letsencrypt-prod` since every staging certificate was Ready (2026-10-18). `dev` and this instance share the registered domain `joinedcontext.com`, so they share the Let's Encrypt limits: issue production certificates once, never in a retry loop.

## 3. What it carries

- **Same as `dev`:** every organization, project, Context Space, DataModel, Endpoint, Policy, Pipeline with its DataSource, App, visualization, AssistantDeployment, KnowledgeSource, MCP server, the branding, the texts and the CKAN catalogue with its datasets. They come from the same seed files under `components/*/seed/`. Current state fills from the same public sources within one pipeline cycle; the HSL vehicles stay at the owner's five lines.
- **History starts at the first write.** No history is copied from `dev`.
- **Never on this instance:**
  - demo users with known passwords. The owner's account, from `global.initialUserEmail`, is the only account at start;
  - the eval and conformance copies of assistants and Keycloak clients, and the `eval-uploads` knowledge source;
  - any Secret of `dev`. Every Secret is generated in this cluster or supplied by the operator through `secretRef`. The sops files of this instance use their own age key;
  - the model key, unless the owner says yes to it. Without one, the assistants deploy with `model` unset and say so.
- The render guards of the production profile refuse a render that breaks one of these rules (T-1720, T-1721, T-4678). `scripts/parity.py` compares the instance with `dev` and lists every difference by name.

## 4. Backups

- **PostgreSQL, target:** CloudNativePG writes a base backup every day and archives the WAL continuously to a Hetzner Object Storage bucket, through the Secret `postgres-backup-s3`. It keeps 30 days. Off until the owner supplies the bucket keys.
- **PostgreSQL, until then:** the CronJob `postgres-cluster-local-backup` writes a `pg_dumpall` of the platform cluster every night at 02:30 UTC onto a volume of the node and keeps 7 days (`postgres.databases.localBackup`). It covers a dropped table or a broken migration. It does not cover the loss of the node: **the instance has no off-site backup yet.**
- **Restore from a dump:** copy the newest `*.sql.gz` out of the volume and feed it to `psql` as the cluster's superuser against `postgres-cluster-rw`; the dump drops and recreates every object it carries.
- **Configuration:** the forge repositories are the source of truth for every object the Portal manages. Back them up as [07-backup-restore.md](07-backup-restore.md) section 3 describes.

## 5. Restore runbook

1. Create a throwaway namespace and a CloudNativePG `Cluster` that bootstraps by `recovery` from the bucket, with the same `postgres-backup-s3` credentials.
2. Wait for the cluster to be Ready, then count rows of the Portal's, Keycloak's and the broker's main tables in both clusters and record the counts.
3. For a real recovery, run the same `Cluster` under the platform's name after `just prod-apply` has recreated the namespaces, then sync again.
4. Delete the throwaway namespace after the counts are recorded.

The restore is tested once before user data arrives, and then once a month, as [07-backup-restore.md](07-backup-restore.md) describes for every instance.

## 6. Applying changes

- `just prod-apply` and `just prod-smoke` from `joinedcontext-deployment`, with the production kubeconfig named per command. The recipe `_prod-guard` compares the kube context's server with the node address `prod_node_ip` of the justfile and refuses any other cluster, `dev` included.
- **Images:** only digests that passed `dev-smoke`, signed, never a tag alone.
- **Smoke:** `just prod-smoke` runs `scripts/smoke.sh` against the instance without the endpoint write round trip, because the instance carries no conformance account. For the same reason the ETSI smoke `tests/etsi/smoke.robot` runs on `dev` only; the full ETSI TTF suite never runs against a live instance.
- **Argo CD** of this cluster (`argocd.smartcity.joinedcontext.com`, Keycloak login) follows the deployment repository's `release` branch, never `main`. It reads the public repository without a key. `just prod-apply` installs it and stays for disaster recovery.
- **Promotion:** after a green `just dev-apply` and `just dev-smoke`, `just dev-green <sha>` moves the `dev-green` branch to that commit. `just promote <sha>` refuses any commit outside `dev-green`, moves `release` forward to it and tags it `prod-<UTC>`; Argo CD syncs it within minutes.
- **Rollback:** `just rollback prod-<UTC>` commits that tag's tree on top of `release`. No branch is ever force-pushed; Argo CD's own rollback is for an admin in the UI.
- **Hold:** `gitops/hold-smartcity.yaml` with `hold: true` stops the automatic syncs of this instance only; `gitops/hold.yaml` holds every instance. A manual sync stays open to the operator. The first adoption runs under the hold until every Application shows an empty diff.

## 7. Patching and hold rules

- **Patch window:** the node does not upgrade itself (one node, no quorum). Once a week, in a window announced in `AI_shared_folder.md`, the operator runs `transactional-update up`, reboots, and bumps k3s to the newest patch release of its minor that is at least 7 days old.
- **Hold rules:**
  - no destroy and no PVC deletion without the owner's word;
  - no terraform run without the current Hetzner token, and none while the state disagrees with the node's encryption key;
  - no `dev` secret, fixture or account copied over;
  - a red `prod-smoke` stops the next promotion until it is fixed.

## 8. The BBSK demo beside the platform

The demo the owner sends to the Banská Bystrica self-governing region (T-4687) runs on this cluster at `https://bbsk.smartcity.joinedcontext.com`, and as a preview on `dev` at `https://bbsk-demo.apps.dev.joinedcontext.com`. It is outside the platform's deployment:

- **Its own unit:** `demos/bbsk/` in the deployment repository, a helmfile of its own with the environments `dev` and `smartcity`, namespace `demo-bbsk`. `just demo-bbsk-apply <env>` installs or updates it and `just demo-bbsk-destroy <env>` removes its releases, volumes and namespace; both refuse a cluster that is not the environment's own, through `_dev-guard` and `_prod-guard`. The platform's `helmfile -e smartcity` renders none of its objects, and its Argo CD Applications do not list it.
- **The page (T-4740):** the host serves a static landing page in the look of `www.bbsk.sk`, rebuilt in our own CSS with no file, font, logo or coat of arms of theirs: the six question cards, how it works, the MCP connector `https://api.{domain}/api/mcp/d/bbsk-demo` with client steps, privacy and limits, in Slovak at `/` and English at `/en/`. The demo assistant is docked on the right by the catalogue theme's own dock scripts. The pinned unprivileged nginx serves it with `script-src 'self'`, one `frame-src` (`https://assistant.{domain}`), `frame-ancestors 'none'`, no cookie and no form. Datasets are linked on the platform's catalogue `opendata.{domain}`.
- **What it runs behind the page:** a CKAN catalogue of the platform's chart and pinned images, its own Postgres (the platform's pinned cluster image, one instance, no CNPG) and the Secrets it generates on the first install. It holds no platform secret and reaches no platform database.
- **Only BB and BBSK:** the catalogue harvests the two organizations' sources (the national catalogue for the city, the ArcGIS Hub for the region) with the publish gate's hidden list for their packages, both read from the platform's catalogue values. Its assistant is the AssistantDeployment `bbsk/bbsk-demo` (publicId `bbsk-demo`), which reads the two bodies' public sources and Endpoints with read-only tools and nothing else.
- **DEMO everywhere:** the branding block's `ribbon` and `noindex` ([12-branding-and-naming.md](12-branding-and-naming.md)), `DEMO` in the site title, the footer and the assistant's greeting, and `X-Robots-Tag: noindex, nofollow` on every answer of its edge.
- **Edge:** a Traefik Ingress with one certificate by HTTP-01 for its one host and the platform's TLS policy, not an APISIX route, so removing the demo touches no platform route. NetworkPolicies close the namespace to everything but the ingress controller (to the page, and to the catalogue until it is removed), DNS, public `443` for the harvests and the Kubernetes API for the API token Job.

## Related

- [Installation Guide](02-installation.md): the procedure every instance follows.
- [Backup, Disaster Recovery & Restore](07-backup-restore.md): the backup and restore machinery this page configures.
- [Security Hardening & Phase-1 Baseline](08-security-hardening.md): the controls that apply here unchanged.
- [Branding and Naming](12-branding-and-naming.md): what the domain and the instance slug change.
