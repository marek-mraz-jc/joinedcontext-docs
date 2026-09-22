---
sidebar_position: 29
title: "ADR-N-028: Applications Build on the Forge: Gitea Actions, Its Package Registry and One Runner on the Builder Image"
---

# ADR-N-028: Applications Build on the Forge: Gitea Actions, Its Package Registry and One Runner on the Builder Image

Date: 2026-09-22  
Status: Accepted  
Decision Makers: product owner (decision of 2026-09-22, T-2607)

## 1. Context

The owner's decision (2026-09-22): "I think applications should be on gitea and build images and everything should be there". The forge is the application factory: source, build, artifacts and images live in Gitea, and the Portal orchestrates nothing it does not have to.

ADR-N-026, written the same morning, put the build in a Kubernetes `Job` the Portal reconciler starts, uploading to the artifact store's `apps/` prefix, and rejected "Gitea Actions with an `act_runner` in the cluster" as a long-lived privileged daemon that runs whatever workflow a repository wrote. T-2592 built that Job. The owner has decided the other way, so this ADR replaces N-026's orchestration and storage and keeps what N-026 decided about the builder image, the offline install, the three shapes, functions and publication.

What `dev` runs today (2026-09-22 05:10Z): Gitea `1.27.0-rootless` (chart 12.7.0) with `[actions] ENABLED=false`; the package API answers `403`, the registry being off; `/api/v1/orgs/joinedcontext/actions/runners` answers `200` with no runner. Nothing runs Actions.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | Gitea Actions, the Gitea package registry and `act_runner` are the forge's own features; the Portal stops owning a build scheduler. |
| Technological consistency | **Full** | One forge for source, build, logs and artifacts; the workflow syntax is the GitHub Actions dialect a developer already reads. |
| Security by design | **Partial** | The runner executes the workflow a repository carries, so the workflow file becomes Portal-owned and the runner is walled (§3.2, §5). The residual risk of untrusted build code on a shared runner is named, not hidden. |
| Modular design | **Full** | Build, store and serve meet at one contract, `App.status.build`, as before; the host only fetches a package by name and digest. |
| Multi-tenancy | **Full** | One package per App in the organization's registry, written by that repository's job token only. |

## 3. Decision

1. **The build is the repository's Gitea Actions workflow.** Every application repository carries `.gitea/workflows/build.yml` from the template (SDK-19), written by the Portal in every run's first commit beside `README.md` (AP-76). On a push to the default branch, which is the merge of AP-77 and AP-85, it installs offline, runs the interface and function tests, builds (for `build: {}` it only computes `integrity.json`), bundles `functions.js`, produces the SBOM (AP-11), and publishes the bundle as a generic package. It then proposes `status.build {digest, commit, sdkVersion, builtAt}` through the Portal API as the build lane's `ServiceAccount`, whose token is an Actions organization secret minted by the forge bootstrap (AP-73). The reconciler starts nothing. **Rebuild** in the Portal is a `workflow_dispatch` of that workflow on the default branch, through the Gitea API.
2. **The workflow file is the Portal's, not the run's.** The model writes the application, not its build: a run commit that adds, changes or deletes anything under `.gitea/` is refused, and a run commits only to its own branch (AP-76). A workflow therefore runs only in the version a reviewer merged, and it names `on: push` to the default branch and `workflow_dispatch` only.
3. **One runner component on the builder image.** `gitea-runner` is `act_runner` in host mode, running on the builder image of AP-82 (Node 22, the pnpm store and the SDK tarball of the Portal release baked in), with the label `node-22`. There is no Docker socket, no Docker-in-Docker and no privileged pod: the restricted Pod Security Standard, no Kubernetes token, egress to the forge and the Portal API only, a work directory wiped after every job, and the registration token from the gitea bootstrap Job as a Secret. The replica count is the only concurrency setting.
4. **The package registry is where builds live.** The workflow uploads `bundle.tar.gz` and `sbom.cdx.json` as the generic package `app-{name}`, version `{commit}`, of the organization, with the workflow's own job token. `status.build.digest` is the SHA-256 of `bundle.tar.gz`. The artifact store's `apps/` prefix holds no application builds; the store keeps its other consumers (Architecture/17 §2).
5. **The host fetches what the manifest names.** The static host downloads `app-{name}@{status.build.commit}` read-only with the Portal's forge token, checks the digest before anything is served, and keeps the build under `{apps_dir}/{name}/{digest}/`. A package that is missing or does not match leaves the previous build serving and the App's `Ready` condition red (AP-72).
6. **The catalog reads the runs.** An App is `building` while its latest run is in progress, `build failed` with a link to the run's log in the forge, carrying the forge's sign-in with the run as its return address (PF-81), and `served <commit>` once the host serves that build (AP-86).
7. **One place for a person.** The App page links the repository, the latest workflow run and the package; a person with forge read access (PF-79) opens all three.
8. **What stays from ADR-N-026.** Its decisions 3 (the offline install), 5 (three shapes of a `static` app), 6 (functions on `jc-functions`) and 7 (publication merges, then builds) stand unchanged. Its decisions 1, 2, 4 and 8 (the Job, the store upload, the Job's walls and where the catalog reads the state) are replaced by §3.1 to §3.6 above.

## 4. Alternatives Considered

- **Keep the Portal-started `Job` (ADR-N-026).** One fixed command and no repository-written workflow. The owner decided against it: the build, its log and its artifact belong in the forge where the source is, and a person reads them there.
- **Let the workflow file be the application's own.** The run could then rewrite its build, run it on a branch nobody reviewed, and reach the lane's secret. Refusing `.gitea/` in run commits keeps the Portal's promise that only reviewed code builds.
- **A runner per job, created and deleted each time.** The stronger wall, and the upgrade path once `act_runner` supports ephemeral registration on this Gitea version. Today it means a controller of our own.
- **Docker or Kubernetes mode for the runner.** Each needs a container runtime or an API token inside the runner pod, which is the privilege this decision avoids. Host mode on the builder image runs what a static application needs.
- **Keep the bundles in the artifact store.** A second store with a second write key, when the forge already has a registry the workflow's job token can write and the Portal's token can read.

## 5. Security Analysis

- **The lane's secret.** The Actions organization secret is the lane `ServiceAccount`'s token and nothing else: its one right is `propose` on `App`, constrained to `status.build` (AP-73). The Portal refuses a `status.build` whose commit is not on the default branch of the App's repository or whose package does not exist with that digest (AP-104), so a stolen token cannot point an App at something the workflow did not build.
- **Untrusted code on a shared runner (T-1707).** The application's install scripts, tests and build run in the runner. The walls: no Kubernetes token, egress to the forge and the Portal API only, the work directory wiped per job, the offline install that reaches no package registry (AP-82), and a workflow file only a reviewer's merge can change (§3.2). What remains: a job of one application runs on the same runner process as the next one's, so a build that escapes its work directory could read what the next job writes during its run. A runner per job is the upgrade path.
- **Registry writes.** A package is written by the job token of the repository it belongs to and nothing else; the Portal reads packages with a read-only token.
- **Images.** A `fullstack` or `service` App's image would be pushed to Gitea's container registry the same way. That needs a rootless builder step (buildah or kaniko) in the workflow and is out of scope until those classes are decided.

## 6. What Changes

- **Requirements:** AP-72, AP-74 and AP-80…AP-83, AP-86 are amended, and AP-100…AP-104 are added, in [Requirements/apps.md](../Requirements/apps.md) §17.
- **Deployment (T-2608):** Actions and packages switched on in `components/gitea`, the `gitea-runner` component, the lane token as an Actions organization secret. The Job, its Role and its NetworkPolicy of T-2592 go.
- **Portal (T-2593, T-2609):** the template's and the first commit's `build.yml`, refusal of `.gitea/` in run commits, the host's package fetch, the catalog's run states, Rebuild as a dispatch, and the App page's three links.

## Related

- [ADR-N-026](adr-n-026-the-build-lane-runs-in-the-cluster.md) — the decision this one replaces in part.
- [Architecture/20-app-sdk §6.0](../Architecture/20-app-sdk.md#60-where-the-build-runs) — the build lane as it now runs.
- [Architecture/17-artifact-store §2](../Architecture/17-artifact-store.md#2-layout-and-ownership) — the store without application builds.
- [Requirements/apps §17](../Requirements/apps.md#17-the-build-lane-on-the-forge-and-the-three-shapes-of-a-static-application) — AP-80…AP-87, AP-100…AP-104.
