---
sidebar_position: 55
title: "ADR-N-054: GitOps for dev with Argo CD Rendering the Helmfile Deployment"
---

# ADR-N-054: GitOps for dev with Argo CD Rendering the Helmfile Deployment

Date: 2026-10-18  
Status: Accepted  
Decision Makers: product owner (order of 2026-10-18 via the supervisor: "just do the auto deploy", "with argoCD and helmfile", "and make that production ready"); plugin design chosen by the supervisor, details recorded by worker-2 (T-4674), owner may override

This record replaces the hourly hand apply of `dev` with Argo CD pulling `main` of `joinedcontext-deployment`. Helmfile stays the one description of the deployment: Argo CD renders it through a Config Management Plugin, so nothing rendered is committed and `just dev-apply` keeps working as the recovery path.

## 1. Context

Measured on 2026-10-18 over 102 tasks: a change waited a median 29 minutes from push to merge, then a median 54 minutes until the deployer started `just dev-apply` (49 tasks), then an image build, the apply itself and `just dev-smoke`. The hand apply is the slowest step between a merge and a running change.

`just dev-apply` does four things: it refuses any cluster but `dev`, assembles `deployment/` from `defaults/deployment`, `.ci/example-deployments/helmfile.yaml` and the example environments, runs `helmfile -e dev sync --concurrency 4`, and waits for every rollout. Three properties of the helmfile deployment shape how Argo CD can take this over:

- **Helm `lookup`.** The secrets generator (`components/secrets`) reads a Secret that already exists and keeps its values, and the APISIX configuration chart keeps the standalone config the Portal composed. Argo CD renders with `helm template`, which has no cluster to look up, so both would render fresh values on every refresh.
- **One helmfile hook.** `components/prepare` creates the namespaces and annotates them for Linkerd on `prepare` of a `sync`. No other component carries a helmfile hook; charts carry Helm hooks, which Argo CD maps to its own.
- **Size.** `dev` renders 293 releases in 30 components. Rendering one release with `helmfile -l name=…` parses the whole state first, about 4 seconds, so an Application per release would spend about 25 minutes re-rendering after each commit with the plugin's parallelism of 1.

The node is a single `cpx42` at 89 % memory (12319 Mi, 2026-10-18T19:00Z), so Argo CD has to fit in 600 Mi of requests.

## 2. Decision

### 2.1 Argo CD, installed by helmfile

Argo CD v3.5.4 from the upstream chart `argo-cd` 10.10.2, images pinned by digest, in its own namespace `argocd`, as the component `gitops`. Helmfile installs it, and Argo CD never manages the `gitops` component itself, so the cluster can always be rebuilt from Git with `just dev-apply`. Dex, the ApplicationSet controller and HA are off; Redis keeps no volume; every pod carries requests and limits that sum to at most 600 Mi of requests.

### 2.2 The helmfile plugin

A Config Management Plugin sidecar in the repo server runs the stock `ghcr.io/helmfile/helmfile:v1.8.1` image, pinned by digest: the helmfile, helm 4.3.0, kubectl, sops and age versions CI runs. It runs `gitops/cmp/generate.sh` from the repository:

1. the assemble step of `just _dev-assemble`;
2. `helmfile -e <env> -l component=<component> template --skip-deps --include-crds`;
3. the data guard of §2.5 on the output.

The plugin reaches only chart repositories and GitHub. A test holds the plugin's output, joined over every component, equal to `helmfile -e dev template`.

### 2.3 One root Application, one Application per component

The root Application renders `gitops/chart` with two value files: `gitops/dev.yaml`, generated from `helmfile list` by `scripts/gitops-apps.py`, and `gitops/hold.yaml`. It holds:

- one AppProject `platform`;
- one Application per component with enabled releases, all components but `gitops`;
- the Application `smoke`, last.

Decided (worker-2, owner may override): an Application per component, not per release. 30 renders after a commit take about 3 minutes; 293 would take about 25. A component deploys into one namespace, which the generator checks. The component order of the environment's `components:` list becomes the sync wave, the order helmfile applies them in.

Each Application syncs with `automated: {selfHeal: true, prune: true}`, `ServerSideApply=true` and `CreateNamespace=true`. `managedNamespaceMetadata` carries the Linkerd annotations `prepare` used to write, so the `prepare` hook needs no replacement. Argo CD creates a missing namespace and never deletes one.

### 2.4 Image pins without a hand step

The workflow `pin-images.yml` in the deployment repository runs every ten minutes and on dispatch. For the platform, the Portal (with both app builders) and Antares it reads the head of `main`, and pins that commit's image digest when four things hold:

- the source repository's `ci` run on that commit is green;
- the image is published under the commit's tag;
- `cosign verify` accepts the signature of that repository's `image.yml` on `main`;
- the dev render passes.

It commits the pin to `main` with the workflow's own token. The repository is public, so Argo CD reads it without a key and the workflow needs no secret of its own.

Decided (worker-2, owner may override): this workflow instead of Argo CD Image Updater. Image Updater writes back only to Helm or Kustomize parameter files, never into the `images.yaml` files helmfile reads. It would also need a write key in the cluster, a second credential.

### 2.5 Argo CD never deletes data

The plugin marks every rendered object of a stateful kind with `argocd.argoproj.io/sync-options: Prune=false,Delete=false`: a PersistentVolumeClaim, a CNPG `Cluster`, a Secret, a Namespace or a CustomResourceDefinition. A test fails when one of them reaches Argo CD without the mark.

A Secret is rendered without a `lookup`, so its rendered data is never applied over the live data. Every Application ignores the `/data` and `/stringData` of Secrets, and the `data` of the ConfigMap `apisix-standalone-config`, with `RespectIgnoreDifferences=true`. Argo CD creates a missing Secret once and never rewrites a generated password or the routes the Portal composed. Rotation stays `scripts/rotate-secret.sh`.

### 2.6 Smoke as the gate

The `smoke` Application carries the revision it was rendered from, so each commit syncs it, and its PostSync Job:

1. waits until every Application of the project is Synced at that revision and Healthy, at most 15 minutes;
2. runs `scripts/smoke.sh` in the cluster.

A red smoke fails the sync. Rollback is never automatic. A failed sync or smoke is fixed forward on `main`, or by a `git revert` of the offending pin commit. Only an Argo CD administrator may roll back to an earlier revision, from the UI.

### 2.7 The hold switch

`gitops/hold.yaml` holds `hold: false`. Setting `hold: true` with a `reason` adds a `deny` sync window over every Application of the project. Automatic syncs stop, and a manual sync is still allowed for the deployer, for a Postgres or Keycloak maintenance. It replaces the "@integrator hold" note.

### 2.8 Access

The UI is `argocd.{domain}`, with an HTTP-01 certificate per hostname and no wildcard. Login goes through the Keycloak client `argocd` only (OIDC, PKCE). A member of the Keycloak group `platform-admins` (in the `groups` claim) gets `role:admin`, and every other login reads. The owner names the members. Anonymous access is off. The local `admin` account is disabled and its initial secret deleted once a Keycloak login syncs. The only API token belongs to the notification hook.

### 2.9 Watching it

Argo CD's metrics go to the platform's Prometheus. An alert fires when an Application stays OutOfSync or Degraded for more than 15 minutes, or a sync fails. The notifications controller opens a GitHub issue in the deployment repository on a failed sync or a degraded Application, once the owner stores its token (owner action, T-4674). `scripts/gitops-status.sh` prints each Application's sync and health status, revision and last sync time for the deployer's hourly round.

## 3. Alternatives

- **Rendering helmfile in CI into a rendered branch.** Argo CD would read plain manifests. Rejected: a second, generated copy of the deployment in Git, and a CI lane between every merge and the cluster.
- **Rewriting the deployment as Helm Applications.** Rejected: it would replace the helmfile layout OPS-01 requires and lose the environment values helmfile assembles.
- **Flux with a helmfile controller.** No maintained controller renders helmfile. Rejected.
- **An Application per release.** Rejected by its render time (§1).
- **Argo CD Image Updater.** Rejected in §2.4.

## 4. Consequences

- The deployment gains the `gitops` component (Argo CD, its NetworkPolicies, the root Application), `gitops/chart`, `gitops/cmp/generate.sh`, `gitops/dev.yaml`, `gitops/hold.yaml`, `scripts/gitops-apps.py`, `scripts/gitops-status.sh` and `.github/workflows/pin-images.yml`.
- `dev` follows `main` within minutes of a merge, and a platform change within the image build plus one pin run. The deployer watches Argo CD and the smoke instead of applying by hand.
- `just dev-apply` remains the bootstrap and the recovery path. Run while Argo CD is up, it converges to the same objects.
- A component whose releases span two namespaces needs splitting before it can join; the generator refuses it.
- A Secret's new key reaches the cluster only when the Secret is created, not when it changes; that is the price of §2.5, and the rotation script covers it.

## Related

- [Requirements/operations.md](../Requirements/operations.md) — OPS-54…OPS-58 state this decision as requirements.
- [Deployment/15-gitops.md](../Deployment/15-gitops.md) — the flow, rollback, the hold switch, credentials and sizing.
- [Deployment/06-updating.md](../Deployment/06-updating.md) — the component order the sync waves follow.
- [Deployment/14-production-smartcity.md](../Deployment/14-production-smartcity.md) — production keeps the hand promotion until it copies this pattern.
