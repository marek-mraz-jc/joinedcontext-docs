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

ADR-N-026, written the same morning, put the build in a Kubernetes `Job` the Portal reconciler starts, uploading to the artifact store's `apps/` prefix, and rejected "Gitea Actions with an `act_runner` in the cluster" as a long-lived privileged daemon that runs whatever workflow a repository wrote. T-2592 built that Job. The owner has decided the other way, so this ADR replaces N-026's orchestration and storage and keeps what N-026 decided about the builder image, the build that installs nothing, the three shapes, functions and publication.

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

1. **The build is the repository's Gitea Actions workflow.** Every application repository carries `.gitea/workflows/build.yml` from the template (SDK-19), written by the Portal in every run's first commit beside `README.md` (AP-76). On a push to the default branch, which is the merge of AP-77 and AP-85, it links the image's installed dependencies (installing nothing, AP-82), runs the interface and function tests, builds (for `build: {}` it only computes `integrity.json`), bundles `functions.js`, produces the SBOM (AP-11), and publishes the bundle as a generic package. Its last step proposes `status.build {digest, commit, sdkVersion, builtAt}` through the Portal API as the build lane's `ServiceAccount`, whose token is an Actions organization secret minted by the forge bootstrap and put in the environment of that step only, never of a step that runs application code (AP-73, AP-80). The reconciler starts nothing. **Rebuild** in the Portal is a `workflow_dispatch` of that workflow on the default branch, through the Gitea API.
2. **The workflow file is the Portal's, not the run's.** The model writes the application, not its build: a run commit that adds, changes or deletes anything under `.gitea/` is refused, and a run commits only to its own branch (AP-76). A workflow therefore runs only in the version a reviewer merged, and it names `on: push` to the default branch and `workflow_dispatch` only.
3. **One runner component on the builder image.** `gitea-runner` is `act_runner` in host mode, running on the builder image of AP-82 (Node 22 and the template's dependencies installed once against the Portal release's SDK), with the label `node-22`. There is no Docker socket, no Docker-in-Docker and no privileged pod: the restricted Pod Security Standard, no Kubernetes token, egress to the forge and the Portal API only, a work directory wiped after every job, and the registration token from the gitea bootstrap Job as a Secret. The replica count is the only concurrency setting.
4. **The package registry is where builds live.** The workflow uploads `bundle.tar.gz` and `sbom.cdx.json` as the generic package `app-{name}`, version `{commit}`, of the organization, with the workflow's own job token. `status.build.digest` is the SHA-256 of `bundle.tar.gz`. The artifact store's `apps/` prefix holds no application builds; the store keeps its other consumers (Architecture/17 §2).
5. **The host fetches what the manifest names.** The static host downloads `app-{name}@{status.build.commit}` read-only with the Portal's forge token, checks the digest before anything is served, and keeps the build under `{apps_dir}/{name}/{digest}/`. A package that is missing or does not match leaves the previous build serving and the App's `Ready` condition red (AP-72).
6. **The catalog reads the runs.** An App is `building` while its latest run is in progress, `build failed` with a link to the run's log in the forge, carrying the forge's sign-in with the run as its return address (PF-81), and `served <commit>` once the host serves that build (AP-86).
7. **One place for a person.** The App page links the repository, the latest workflow run and the package; a person with forge read access (PF-79) opens all three.
8. **A `fullstack` application builds on the same forge into its container registry** (amended 2026-09-22, T-2615, on the owner's order to run applications "with rust and frontend" on `dev`). "Fullstack applications" below says how.
9. **What stays from ADR-N-026.** Its decisions 3 (the build installs nothing), 5 (three shapes of a `static` app), 6 (functions on `jc-functions`) and 7 (publication merges, then builds) stand unchanged. Its decisions 1, 2, 4 and 8 (the Job, the store upload, the Job's walls and where the catalog reads the state) are replaced by §3.1 to §3.6 above.

### Fullstack applications

A `fullstack` App (a Rust axum backend with its React interface embedded in the binary) is built by the same kind of workflow, published into the organization's **container** registry, and run by the reconciler as one pod.

1. **The workflow.** The repository carries `.gitea/workflows/build.yml` from the fullstack template, under the same rules as §3.2 (AP-100), and runs two jobs (AP-105):
   - `build`, on a runner labelled `rust-1.90`, builds the interface, runs `cargo test --offline --locked`, and builds the binary with `cargo build --release --offline --locked --target x86_64-unknown-linux-musl`, so it runs on an empty base. It then assembles the image with `crane append --oci-empty-base`: one layer holding the binary at `/app` and nothing else, no daemon, no privilege and no user namespace. It uploads the image tarball, its manifest digest (`crane digest --tarball`) and the SBOM as the run's Actions artifact with the job token.
   - `propose`, a separate job that runs no application code (§5), proposes `status.build {digest, commit, builtAt, run}`. For a `fullstack` App `digest` is the image's manifest digest, `sha256:…`.
2. **The Rust crates are baked, not vendored.** The `rust-1.90` runner image carries the Rust toolchain, the musl target, `crane`, and a Cargo registry cache holding every crate the Portal release's `Cargo.lock` names. The fullstack template's lockfile and the reference applications' lockfiles are cut from that lock. A repository whose `Cargo.lock` names a crate the store does not hold fails with Cargo's own offline error, so the build reaches no registry (AP-82). Trade-off: a `vendor/` directory would keep the runner image small, but it adds a few hundred megabytes of third-party source to every application repository and to every generated run's first commit. The baked store costs that once, in one image the release already signs.
3. **The Portal publishes the image.** The integrator's decision on the publishing credential (T-2609, 2026-09-22) applies unchanged: no write credential reaches the runner. The Portal downloads the run's artifact with its forge token and checks the tarball's manifest digest against `status.build.digest`. It then pushes the image to `{forge}/joinedcontext/app-{name}:{commit}` with its own token and refuses the proposal if the registry answers another digest (AP-104, AP-107).
4. **Its own runner.** The `rust-1.90` jobs run on a second instance of the `gitea-runner` component, with the same walls as §3.3 and AP-81, the `rust-1.90` builder image (AP-106), and a job memory limit sized for a release link (4 GiB on `dev`). The Node runner keeps its small limit. Replicas stay one each on the single node.
5. **The pod.** The reconciler composes the image reference `{registry}/joinedcontext/app-{name}@{digest}` from its own setting and `status.build.digest`. The manifest never names a registry. It renders the Deployment with `command: ["/app"]`, `runAsNonRoot` with a numeric user, the restricted Pod Security Standard, port 8080, and `imagePullSecrets` naming the Secret the deployment creates in the apps namespace: a `dockerconfigjson` holding a forge token that can read packages and nothing else. The NetworkPolicy admits the APISIX pods of the namespace the installation runs APISIX in, a setting, where `reconciler.rs` wrote the literal `apisix` (AP-108).
6. **Roles reach the backend by asking the Portal.** The edge hands the backend `X-Access-Token`. The backend calls `GET /api/v1/projects/{project}/apps/{name}/me` with that token as `Authorization: Bearer` and receives the same `{id, name, email, roles}` the static host writes into `#jc-config` (AP-92, AP-95, AP-109). The roles are computed in one place. A header set by the edge was rejected because APISIX would need the manifest's `spec.access` and a plugin to compute it, and a header a client can also send has to be stripped on every route. `visibility: roles` stays refused on a `fullstack` App (AP-94): the edge sends its requests to the pod without passing the static host. The backend answers a person with no role from `/me`, and the data grants follow the endpoint roles either way.
7. **The reference applications become seeds.** `hsl-transport` and `air-quality` move to their own repositories, `helsinki_hsl-transport` and `helsinki_air-quality`, in the shape of T-2599's seeds. Their manifests in the configuration repository name `spec.source.git`, and the forge builds them like any other application (AP-110).

## 4. Alternatives Considered

- **Keep the Portal-started `Job` (ADR-N-026).** One fixed command and no repository-written workflow. The owner decided against it: the build, its log and its artifact belong in the forge where the source is, and a person reads them there.
- **Let the workflow file be the application's own.** The run could then rewrite its build, run it on a branch nobody reviewed, and reach the lane's secret. Refusing `.gitea/` in run commits keeps the Portal's promise that only reviewed code builds.
- **A runner per job, created and deleted each time.** The stronger wall, and the upgrade path once `act_runner` supports ephemeral registration on this Gitea version. Today it means a controller of our own.
- **Docker or Kubernetes mode for the runner.** Each needs a container runtime or an API token inside the runner pod, which is the privilege this decision avoids. Host mode on the builder image runs what a static application needs.
- **buildah or kaniko for the image (T-2615).** Rootless buildah needs a user namespace and the setuid `newuidmap`, which the restricted Pod Security Standard (`allowPrivilegeEscalation: false`) takes away. kaniko runs as root inside its container. A fullstack image holds one static binary and runs no `RUN` step, so a tool that only writes layers and manifests (`crane`) builds it with no privilege at all. The price: an application cannot install system packages into its image.
- **Keep the bundles in the artifact store.** A second store with a second write key, when the forge already has a registry the workflow's job token can write and the Portal's token can read.

## 5. Security Analysis

- **The lane's secret.** The Actions organization secret is the lane `ServiceAccount`'s token and nothing else: its one right is `propose` on `App`, constrained to `status.build` (AP-73). The Portal refuses a `status.build` whose commit is not on the default branch of the App's repository or whose package does not exist with that digest (AP-104), so a stolen token cannot point an App at something the workflow did not build.
- **Untrusted code on a shared runner (T-1707).** The application's install scripts, tests and build run in the runner. The walls: no Kubernetes token, egress to the forge and the Portal API only, the work directory wiped per job, a build that installs nothing and runs no package install script (AP-82), and a workflow file only a reviewer's merge can change (§3.2). What remains, and it is the largest risk this decision takes: in host mode a job's steps run as the runner's own user, so application code that reads outside its work directory can reach the runner's registration file, and with it pick up the next jobs of other repositories and their lane secret. Running the application's steps as a second unprivileged user with no read access to the runner's files narrows that; a runner per job is the upgrade path that closes it (T-1707).
- **Registry writes.** A package is written by the job token of the repository it belongs to and nothing else; the Portal reads packages with a read-only token.
- **Amended 2026-09-22 (T-2608), measured on Gitea 1.27.0 and gitea-runner 3.5.0.** Three findings change the walls above:
  - **The runner is now one per job.** It registers with `--ephemeral` before every job, so the registration file a job can read is spent by that job. The organization's registration token is read once from memory and deleted before the first job, and it reaches `register` on stdin. A job found it in no file, no environment and no command line.
  - **A step-scoped secret is no wall in host mode.** A process an application step leaves behind read `LANE_SECRET` from `/proc/<pid>/environ` of a later step of the same job. So the lane secret belongs to a separate job that runs no application code. The runner kills every process a job left behind before it registers for the next job, and a probe in that separate job found the earlier job's watcher gone.
  - **A job token cannot write a package on Gitea 1.27.0.** `services/context/package.go` `determineAccessMode` carries `// TODO: ActionUser permission check`, and an upload with the job token answers `401` from `reqPackageAccess`, whatever the workflow's `permissions:` say and even with the package linked to the repository. §3.4 therefore needs another publishing credential until the forge implements it. That choice is open (T-2609).
- **Images (amended 2026-09-22, T-2615).** A `fullstack` image is assembled with no daemon and no privilege, and it is pushed by the Portal alone, never by the runner (§3, "Fullstack applications"). A node pulls it by digest with a read-only token. An image the Portal did not push under the proposed digest never reaches a pod, because the reconciler composes the reference from `status.build.digest` and the Portal checked that digest on push. A `service` App has no build class yet.

## 6. What Changes

- **Requirements:** AP-72, AP-74 and AP-80…AP-83, AP-86 are amended, and AP-100…AP-104 are added, in [Requirements/apps.md](../Requirements/apps.md) §17.
- **Deployment (T-2608):** Actions and packages switched on in `components/gitea`, the `gitea-runner` component, the lane token as an Actions organization secret. The Job, its Role and its NetworkPolicy of T-2592 go.
- **Fullstack (T-2615 docs, T-2616, T-2617):** AP-105…AP-110 in [Requirements/apps.md](../Requirements/apps.md) §19. The fullstack template workflow, the `rust-1.90` runner, the Portal's image push, the pull secret, the APISIX namespace setting and `…/apps/{name}/me` are T-2616's. The two reference applications as seeds on `dev` are T-2617's.
- **Portal (T-2593, T-2609):** the template's and the first commit's `build.yml`, refusal of `.gitea/` in run commits, the host's package fetch, the catalog's run states, Rebuild as a dispatch, and the App page's three links.

## Related

- [ADR-N-026](adr-n-026-the-build-lane-runs-in-the-cluster.md) — the decision this one replaces in part.
- [Architecture/20-app-sdk §6.0](../Architecture/20-app-sdk.md#60-where-the-build-runs) — the build lane as it now runs.
- [Architecture/17-artifact-store §2](../Architecture/17-artifact-store.md#2-layout-and-ownership) — the store without application builds.
- [Requirements/apps §17](../Requirements/apps.md#17-the-build-lane-on-the-forge-and-the-three-shapes-of-a-static-application) — AP-80…AP-87, AP-100…AP-104.
