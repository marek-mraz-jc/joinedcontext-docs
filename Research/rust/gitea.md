---
sidebar_position: 4
title: "Gitea for shako"
description: Research input for shako, the Rust Git forge that replaces Gitea 1.27.3; capability inventory, internals, extension model, security, tenancy, operations, test oracles, Argon pack plan and the MCP mapping, every claim with its source and a measured clone/push benchmark of the server-side Git libraries (T-6639).
---

# Gitea for shako

This page is the research input for shako (T-6634): one Rust Git forge for every organization of an installation, replacing Gitea. It lists what upstream does, what the platform uses today with file:line, how upstream works inside, what the Rust design keeps, changes or drops, which server-side Git library carries it (measured), and which upstream files feed the Argon generation. Readers: the worker who builds the shako pack, the reviewer of the generated code, the owner deciding the open questions in section 10.

## 1. Sources and pins

| Source | Pin | How read |
|---|---|---|
| Gitea upstream | tag `v1.27.3`, commit `146cc3eec57174711eac0e0a0c7b38670c6e3922` (2026-08-29), `https://github.com/go-gitea/gitea/tree/v1.27.3` | shallow clone, grep; cited as `gitea:<path>:<line>` |
| Gitea image on dev and prod | `docker.gitea.com/gitea:1.27.3-rootless@sha256:1c17ecae…45f2`, `gitea version 1.27.3 built with go1.26.7` | `deployment:components/gitea/images.yaml:2-14`; `docker exec … gitea --version` |
| Gitea chart | `gitea-charts/gitea` 12.7.0 | `deployment:components/gitea/charts.yaml:3-6` |
| Runner | Gitea runner v3.5.0, commit `699a97fc`, inside the app-builder image | `portal:builder/Dockerfile:42-47` |
| joinedcontext-portal | `d7f91eb28` (main, 2026-11-05) | grep; cited as `portal:<path>:<line>` |
| joinedcontext-deployment | `cee6ebcb9` (main) | cited as `deployment:<path>:<line>` |
| joinedcontext-platform | `e59ceb9f` (main) | cited as `platform:<path>:<line>` |
| gitoxide | `gix` 0.90.0 (2026-10-22), `gix-pack` 0.77.0, `gix-protocol` 0.68.0 | crates.io, built in `scripts/research/gitea-bench/rsbench` |
| libgit2 | `git2` 0.21.0, `libgit2-sys` 0.18.8+1.9.7 | same crate |
| C git | 2.47.3 (sandbox), the `git` inside the Gitea image for Gitea runs | `git --version` |

Size of upstream at the pin (commands run in the checkout): 488,312 lines of Go (`find . -name '*.go' | xargs wc -l`), 987 `*_test.go` files, 255 Go files in `tests/integration`, 26 Playwright specs in `tests/e2e`, 482 `operationId` in `templates/swagger/v1_json.tmpl`, 355 route registrations in `routers/api/v1/api.go`, about 639 in `routers/web/web.go`, 115 `db.RegisterModel` tables, 273 schema migrations (last #342, `gitea:models/migrations/migrations.go:422`).

## 2. Capability inventory

Legend: **Used** = the platform calls it today (file:line). **Need** = shako must have it for the platform. **No** = not needed, with the reason.

### 2.1 Git transport and storage

| Capability | Upstream | Status |
|---|---|---|
| Smart HTTP upload-pack (clone, fetch), protocol v0/v2 | `gitea:routers/web/githttp.go:11-27`, `gitea:routers/web/repo/githttp.go:370-455` | **Used**: `jcctl checkouts` and `jc-manifest` mirror every project repo with `git clone --mirror` (`platform:crates/jc-manifest/src/assemble.rs:796,872`; `platform:crates/jcctl/src/commands/checkouts.rs:1-40`); git-sync in the gateway (`deployment:components/context-gateway/values/gateway/base-values.yaml.gotmpl:193,202`); runners clone App repos |
| Smart HTTP receive-pack (push) | same | **Used**: the Portal pushes a bundle's refs in one receive-pack call (`portal:src/git/gitea.rs:1145,1172`, report parser `:294`) |
| `info/refs` advertisement | `gitea:routers/web/repo/githttp.go:455` | **Used**: the Portal probes external SyncSource remotes (`portal:src/sync/remote.rs:108`) |
| upload-archive, dumb HTTP objects | `gitea:routers/web/githttp.go:11-27` | **No**: no caller; dumb HTTP leaks object enumeration timing |
| SSH (built-in or OpenSSH `serv`) | `gitea:modules/ssh/ssh.go:29`, `gitea:cmd/serv.go:40` | **No**: off on every environment (`deployment:components/gitea/values/forge/base-values.yaml.gotmpl:178-179`); HTTPS with tokens covers every client |
| LFS (batch, upload, verify, locks) | `gitea:services/lfs/server.go:113,188,302,382`, `gitea:services/lfs/locks.go` | **Need** (T-6634 scope); not configured today (no `LFS` key in `deployment:components/gitea/values/forge/`) |
| Git bundle download `archive/{ref}.bundle` | API | **Used**: export and transfer (`portal:src/git/gitea.rs:2257`) |
| Zip and tar.gz archives | `gitea:routers/web/repo/repo.go`, `services/repository/archiver` | **Need**: UI download (T-6634) |
| Server-side gc | `cron.git_gc_repos` | **Used**: daily at midnight, autogc off (`deployment:…/forge/base-values.yaml.gotmpl:257-265`) |
| AGit flow (`refs/for/…` proc-receive) | `gitea:services/agit/agit.go` | **No**: the Portal opens PRs by API |

### 2.2 Repositories, permissions, review

| Capability | Upstream | Status |
|---|---|---|
| Repo create (auto_init or empty), get, delete, archive | `gitea:services/repository/` | **Used**: `portal:src/git/gitea.rs:1039,1047,1118,1597,1752` |
| Migrate (duplicate with history) | `gitea:services/migrations/` (github, gitlab, gitea, gogs, onedev, plain git …) | **Used** only for intra-forge duplication (`portal:src/git/gitea.rs:1081`; allow-list = the forge itself, `deployment:…/forge/base-values.yaml.gotmpl:218-226`). **Need**: plain-git import only; the 9 importers are **No** (SSRF surface, section 5.5) |
| Push mirrors (to GitHub) | `gitea:services/mirror/mirror_push.go` | **Used**: `portal:src/git/gitea.rs:1200,1216,1236,1244` |
| Pull mirrors | `gitea:services/mirror/mirror_pull.go` | **No**: SyncSource does pulls in the Portal |
| Orgs, teams, team repos, owner check | `gitea:models/organization/team.go:76-90`, `org.go:124,375` | **Used**: `portal:src/git/gitea.rs:1618-1731`; teams `{slug}-readers/-writers` (`portal:src/reconciler/project_teams.rs:1-23`). **Replaced** by jc-core RoleBinding/Group in shako (section 6) |
| Collaborators | `gitea:models/repo/collaboration.go:20-26` | **Used**: jc-gateway as read collaborator (`portal:src/git/gitea.rs:1763`). **Replaced** by a ServiceAccount RoleBinding |
| Branch protection (allowlists, approvals, status checks, signed commits, file patterns, admin override block) | `gitea:models/git/protected_branch.go:30-72` | **Used**: main protected, push/merge only jc-portal, no force push, `block_admin_merge_override` (`deployment:components/gitea/charts/bootstrap/templates/job.yaml:342-347`; `portal:src/git/gitea.rs:1779`). **Need** |
| Tag protection | `gitea:models/git/protected_tag.go:21-28` | **Need** (releases) |
| CODEOWNERS | `gitea:services/issue/pull.go:28`, parser `gitea:models/issues/pull.go:829,872` | **No** today; review routing is the Portal's change lanes. Keep the file format for a later reviewer suggestion |
| Contents API: read, write one, multi-file commit, delete | `gitea:services/repository/files/` | **Used**: `portal:src/git/gitea.rs:1918,1950,2052,2080`; agent-proxy door (`platform:crates/agent-proxy/src/routes/forge.rs:164`) |
| Trees, branches, commits, commit status, tags | API | **Used**: `portal:src/git/gitea.rs:1792,1810,1864,1877,1896,1908,2104,2268,2313` |
| Pull requests: list, create, get, files, reviews (read, post), close, update, merge | `gitea:services/pull/` | **Used**: `portal:src/git/gitea.rs:2174-2391` |
| Merge styles (merge, rebase, rebase-merge, squash, ff-only, manually-merged, rebase-update-only) | `gitea:models/repo/git.go:17-29`, `gitea:services/pull/merge_*.go` | **Need**: merge, squash, ff-only, update-by-merge (`portal:src/git/gitea.rs:2377,2391`); rebase styles later |
| Conflict check (`git merge-tree`, fallback 3-way in temp repo) | `gitea:services/pull/patch.go:56-67`, `merge_tree.go:21,53` | **Need**: gix `merge` feature does tree merges in memory |
| Issues, labels, milestones, projects/kanban, wiki, time tracking, reactions, stars, watches | `gitea:models/issues/`, `models/project/`, `services/wiki/` | **No**: issues and planning live outside the forge; a city's backlog is not in Git |
| Releases | `gitea:services/release/` | **No** today (tags suffice); later |
| Webhooks (11 types, 28 events) | `gitea:modules/webhook/type.go:11,120` | Portal route exists but nobody registers the hook and no secret is set, so it answers 503 and sync polls every 60 s (`portal:src/api/webhook.rs:129-161,184`; `portal:src/config.rs:90-98`). **Replaced**: shako emits in-process events to the one activity log; outbound webhooks of type `gitea` only |
| Notifications, mail | `gitea:services/mailer/mailer.go:48` | **No**: the platform notifies |
| Code and issue indexers (bleve, ES, meilisearch) | `gitea:modules/indexer/` | **No** at first; `git grep` equivalent per repo on demand |
| Admin pages (users, auths, queues, diagnosis) | `gitea:routers/web/admin/` | **No**: operations through the Portal and MCP |
| ActivityPub, nodeinfo | stub, returns NotImplemented (`gitea:routers/api/v1/api.go:1011-1013`) | **No** |

### 2.3 Packages, Actions, identity

| Capability | Upstream | Status |
|---|---|---|
| Container registry (OCI distribution: blob upload, cross-repo mount, manifests, tags; 24 h bearer JWT) | `gitea:routers/api/packages/api.go:557`, `container/container.go:244-748`, `gitea:services/packages/auth.go:31-37` | **Used**: the Portal pushes App images (`portal:src/git/gitea.rs:1507,1541,1573,1582`); clusters pull with `jc-registry-pull` (`deployment:…/bootstrap/templates/job.yaml:591-764`). **Need** |
| Generic packages | `gitea:routers/api/packages/generic/` | **Used**: App bundles (`portal:src/git/gitea.rs:1462,1484`; `portal:src/apps/fetch.rs:80`). **Need** |
| 22 other registry types (alpine, arch, cargo, chef, composer, conan, conda, cran, debian, goproxy, helm, maven, npm, nuget, pub, pypi, rpm, rubygems, swift, terraform, vagrant) | `gitea:routers/api/packages/api.go:119` | **No**: no caller; each parser is a CVE source (section 5.5) |
| Actions: runs, dispatch, queued jobs, artifacts, repo runner token | `gitea:models/actions/`, `gitea:services/actions/` | **Used**: `portal:src/git/gitea.rs:1283,1321,1337,1369,1384,1412`; build pods per queued job (`portal:src/apps/build_pods.rs:363`) |
| Runner protocol (connect-rpc `runner.v1`: Register, Declare, FetchTask, UpdateTask, UpdateLog; headers `x-runner-uuid`, `x-runner-token`) | `gitea:routers/api/actions/runner/runner.go:29,42,140,166,218,286`, `interceptor.go:25-38`; proto module `gitea.dev/actions-proto-go v0.6.0` (`gitea:go.mod:15`) | **Used**: `deployment:components/gitea-runner/values/runner/base-values.yaml.gotmpl:36-81`. **Need** (last run, section 10) |
| Actions secrets and variables | `gitea:models/secret/secret.go:39`, `models/actions/variable.go` | **Used**: lane-token CronJob writes `JC_LANE_TOKEN` (`deployment:components/gitea/charts/bootstrap/templates/lane-token.yaml:28-40,113-132`). **Need**, as secretRef |
| Reusable workflows, schedules | `gitea:services/actions/job_emitter.go:300` | **No** today |
| OAuth2/OIDC login (goth, auto-registration, account linking, group→team map) | `gitea:services/auth/source/oauth2/`, `gitea:routers/web/auth/oauth.go:143,356` | **Used**: Keycloak source, `groupTeamMap`, `adminGroup /forge-admins`, auto-register, linking auto (`deployment:…/forge/base-values.yaml.gotmpl:7-28,143-162,227-232`). **Replaced** by wardkeep OIDC + jc-auth decisions; no local users |
| LDAP, SMTP, PAM, SSPI sources, local passwords, 2FA, WebAuthn | `gitea:services/auth/source/{ldap,smtp,pam,sspi,db}` | **No**: wardkeep owns credentials and MFA |
| Gitea as OAuth2 provider | `gitea:routers/web/auth/oauth2_provider.go:94-685` | **No**: wardkeep is the only provider |
| Access tokens with scopes | `gitea:models/auth/access_token_scope.go:56-84` | **Used**: four machine tokens (`deployment:components/gitea/charts/bootstrap/values.yaml:43-65`). **Replaced** by ServiceAccount client tokens (audience `shako`) |

## 3. Internals

### 3.1 Request flow

1. `gitea:routers/init.go:177` mounts `/` (web), `/api/v1`, `/api/internal` (private), `/api/packages`, `/v2` (container), `/api/actions` and the artifact routes (`:183-207`).
2. Web chain (`gitea:routers/web/web.go:257-329`): static and avatars before any session, health, metrics, session (`MustInitSessioner`), `Contexter`, auth group (OAuth2 token, Basic, optional ReverseProxy, Session, optional SSPI, `:123-148`), `BlockExpensive`, `QoS`, routes.
3. API chain (`gitea:routers/api/v1/api.go:837-942`): CORS, `APIContexter`, deprecated-auth check, auth group (token, HTTP signature, Basic, optional ReverseProxy), `verifyAuthWithOptions`. No session auth on the API.
4. Git smart HTTP (`gitea:routers/web/repo/githttp.go`): `httpBase` (`:60`) resolves the repo, authenticates, checks the unit permission per service (`:69-72`), builds the pusher environment (`GITEA_REPO_ID`, `GITEA_PUSHER_ID` …, `gitea:modules/repository/env.go:19-30`); `serviceRPC` (`:370`) spawns `git upload-pack|receive-pack --stateless-rpc` from an allow-list (`:354-364`) and streams stdin/stdout (`:416-418`).
5. Hooks: every bare repo carries delegate hooks that exec `gitea hook --config=<ini> <name>` (`gitea:modules/gitrepo/hooks.go:18,81-117`); the hook process POSTs to `/api/internal/hook/{pre,post,proc}-receive` (`gitea:cmd/hook.go:33-92`, `gitea:routers/private/internal.go:79-81`), authenticated by the shared `InternalToken` in a header (`:32-34`). Branch protection is enforced in pre-receive (`gitea:routers/private/hook_pre_receive.go`).

A push therefore costs: one Go request, one `git receive-pack`, one `git index-pack`, one `gitea hook` process per hook stage with its own config load, and one internal HTTP call per stage. Measured: a 100 MB push takes 3.43 s through Gitea against 1.79 s through bare `git http-backend` (section 3.4).

### 3.2 Data model

- 115 tables (`db.RegisterModel` across `gitea:models/**`); the forge-relevant ones: `user` (users and orgs, `Type=UserTypeOrganization`, `gitea:models/user/user.go:54-57`), `repository` (`OwnerID`, `gitea:models/repo/repo.go:157`), `access` (precomputed, `gitea:models/perm/access/access.go`), `team`, `team_unit`, `team_repo`, `team_user`, `collaboration`, `protected_branch`, `protected_tag`, `pull_request`, `review`, `comment`, `commit_status`, `branch`, `webhook`, `hook_task`, `package*` (6), `action_*` (20), `secret`, `access_token`, `oauth2_*`, `external_login_user`.
- Scope columns: `OwnerID` in 35 model files, `RepoID` in 62, `OrgID` in 10; scope is global when both are 0. No `tenant` or `instance` column anywhere (`grep -rwi 'tenant\|tenant_id\|instance_id' models` is empty).
- Permission resolution: access modes None..Owner = 0..4 (`gitea:models/perm/access_mode.go:17-21`), 10 unit types (`gitea:models/unit/unit.go:24-35`), resolvers `GetDoerRepoPermission` (`gitea:models/perm/access/repo_permission.go:386`) and `GetActionsUserRepoPermission` (`:280`).

### 3.3 Background work, caching, scaling

- 16 named queues (webhook_sender, pr_patch_checker, push_update, mirror, actions_ready_job, repo-archive, code_indexer …; e.g. `gitea:services/webhook/deliver.go:321`, `gitea:services/pull/check.go:520`), default backend LevelDB (`gitea:modules/setting/queue.go:31`).
- 29 cron tasks (`gitea:services/cron/tasks_basic.go:169`, `tasks_extended.go:227`, `tasks_actions.go:14`).
- Cache memory/redis/memcache/twoqueue, session memory/file/redis/db…, global lock memory/redis, object storage local/minio/azure (`gitea:modules/setting/cache.go:53`, `session.go:45`, `modules/globallock/globallock.go:21`, `modules/storage/`). Dev runs the disk queue and cache and DB sessions (`deployment:…/forge/base-values.yaml.gotmpl:60-62,203-206`).
- HA needs shared POSIX storage for repositories, redis for queue/cache/session/lock, an external indexer and object storage, and identical `SECRET_KEY`/`InternalToken`; the cron runs in every replica. Upstream has no HA page in `docs/`. Dev runs one replica with `Recreate` on a 20 Gi RWO PVC (`deployment:…/forge/base-values.yaml.gotmpl:98-105`, `development-values.yaml.gotmpl:9-21`).

### 3.4 Server-side Git library: measured

Repository: 121 commits, 400 text files edited 20 at a time, 49 random 1.5 MB blobs; pack 100.13 MiB, 3,214 objects. Host: 16 vCPU, load average about 6 from other agents, 2026-11-07. Median of 3 runs, peak RSS from `wait4`. Harness: `scripts/research/gitea-bench/` (`bench.sh` rebuilds an equivalent repository from a synthetic word list; the measured one used words of `gitea:routers/web/web.go`).

| Step (server side) | Median s | Min s | Peak RSS MiB |
|---|---|---|---|
| Clone pack: `git rev-list --objects --all \| git pack-objects --stdout` | 0.45 | 0.44 | 104 |
| Clone pack: gix-pack 0.77 count + entries (delta copy) + write | 0.32 | 0.29 | 205 |
| Clone pack: libgit2 1.9.7 `PackBuilder` insert_walk + write_buf | 31.08 | 30.72 | 227 |
| Push index: `git index-pack` | 1.14 | 1.02 | — |
| Push index: gix `Bundle::write_to_directory` | 0.30 | 0.28 | — |
| Push index: libgit2 `Indexer` | 2.61 | 2.56 | — |
| `git index-pack` accepts the gix-written pack | 1.08 | — | — |
| gix in process, one thread: 1000 × (resolve HEAD, recursive tree walk, read one blob, walk 10 commits) | 0.16 total | 0.15 | 11 |

The push-index RSS column was a cumulative counter in the first harness, so it is left out; the `wait4` harness in the branch reports it per run.

| End to end over HTTP (git 2.47.3 client) | Median s | Min s |
|---|---|---|
| Push 100 MB to C git `http-backend` (CGI behind a Python server) | 1.79 | 1.70 |
| Push 100 MB to Gitea 1.27.3 (push-to-create, sqlite) | 3.43 | 3.23 |
| Clone 100 MB from `http-backend` | 1.60 | 1.54 |
| Clone 100 MB from Gitea 1.27.3 | 1.78 | 1.64 |
| Clone 100 MB `file://` with `--no-local` (no HTTP) | 1.55 | 1.52 |

The Gitea container's cgroup `memory.peak` after the Git runs was 367 MiB, page cache included.

API load, k6 at a constant 100 req/s for 60 s, five read routes the Portal calls most (repo, `contents/{path}`, `git/trees/{ref}?recursive=1` on 470 entries, `commits?limit=10`, `branches/{b}`): Gitea reached 90.2 req/s (5,452 requests, 0 failed), latency median 134 ms, p95 1.38 s, max 2.82 s, CPU 750 % on average (20 samples), RSS 249-284 MiB, cgroup peak 481 MiB. Most of that CPU is `git cat-file` and `git ls-tree` child processes per request.

Findings:

- **gix** has every server-side building block: pack generation with delta reuse and thin packs (`gix-pack` `data::output`, `allow_thin_pack`), pack indexing with thin-pack completion (`Bundle::write_to_directory`), ref transactions (`gix-ref`), revision walks, tree diff, in-memory tree merge (`merge` feature), archives (`worktree-archive`). It has no protocol server: `gix-protocol` 0.68 is "an abstraction over fetching a pack from the server" (`gix-protocol-0.68.0/src/lib.rs:1`). shako writes the upload-pack v2 (`ls-refs`, `fetch` with have/want negotiation, shallow, filter) and receive-pack (commands, report-status, push options) state machines, about 1.5-2.5k lines, tested against the git client.
- **libgit2** reuses no deltas in `PackBuilder` (31 s for a pack git writes in 0.45 s), has no server transport either, and brings a C dependency; rejected.
- **`git http-backend`** is the reference: correct by definition, fast, but a process per request, a C binary in the image and hooks as processes. Kept as the differential oracle (section 8), not as the runtime.
- The gix pack was 104,897,729 bytes, git's 104,897,738: the same objects, the same deltas copied.

## 4. Extension model

Upstream has no runtime plugin system (Go has none). What exists:

| Point | Upstream | Rust equivalent in shako |
|---|---|---|
| `custom/` templates and public assets overriding the built-in ones | `gitea:modules/setting/path.go:117,197`, `gitea:modules/templates/base.go:16`, `gitea:modules/public/public.go:26` | No server templates: the UI is the Portal's React shell with shared components; theming by the Portal's theme tokens |
| External renderers `[markup.<name>]` running a command per file; modes `no-sanitizer`/`iframe` disable the sanitizer | `gitea:modules/setting/markup.go:143,245-286`, `gitea:modules/markup/external/external.go:88-89,150` | WASM components on the platform wasm-host: `render(bytes, mime) -> html` with fuel, 64 MiB memory, no network or filesystem capability; output always through the one sanitizer; built-ins (Markdown, code highlight, CSV, GeoJSON, LinkML) behind Cargo features |
| Git hooks: delegate hooks plus per-repo `*.d` scripts (restricted again in 1.27.3) | `gitea:modules/gitrepo/hooks.go:110-117` | In-process hook trait (`PreReceive`, `PostReceive`) with built-ins: branch/tag protection, secret scan (the Portal's `secret_scan` rules), manifest validation via jc-manifest, size and path rules; optional WASM hook with read-only access to the pushed objects; no shell hooks at all |
| Webhooks (outbound), OAuth2, auth sources, Actions, package types | sections 2.2-2.3 | Activity-log events in process; outbound webhook of one type with HMAC; wardkeep for identity; Actions runner protocol; two package types |

Isolation rules for the WASM points: one instance per call, fuel and wall-clock limits, a capability list declared in the module manifest and approved through a Change, no host calls that reach another organization's data (the host passes only the objects of the repo being pushed or rendered).

## 5. Security

### 5.1 Login and token flows today

| Flow | Sequence | Source |
|---|---|---|
| Person in the browser | Portal link → `user/oauth2/keycloak?redirect_to=` → Keycloak realm `{slug}` → Gitea callback → goth OIDC validation → auto-register or auto-link → `groupTeamMap` puts the person into teams by `groups` claim → session cookie `i_like_gitea` (DB session, SameSite lax, Secure on https) | `portal:src/git/gitea.rs:866`; `deployment:…/forge/base-values.yaml.gotmpl:7-28,143-162,227-232`; `gitea:routers/web/auth/oauth.go:143,356`; `gitea:modules/setting/session.go:40,52-66` |
| Portal to API | `Authorization: token <jc-portal token>`; one token for every project | `portal:src/git/gitea.rs:757-835,900`; `deployment:components/gitea/charts/bootstrap/values.yaml:43-55` |
| Apps builds | jc-apps token; registry bearer from `/v2/token` with basic auth, 24 h JWT | `portal:src/git/gitea.rs:960,971,1507`; `gitea:services/packages/auth.go:31-37` |
| Agent runs | agent-proxy `/v1/forge/*`, limited to the run's one repo and app directory, forge token from file | `platform:crates/agent-proxy/src/routes/forge.rs:160-290` |
| Runner | registration token (org-scoped, from the bootstrap Job, or repo-scoped per build pod) → `Register` → `x-runner-uuid`/`x-runner-token` on each RPC; token stored as sha256 | `deployment:…/bootstrap/templates/job.yaml:755`; `portal:src/git/gitea.rs:1369`; `gitea:models/actions/runner.go:54` |
| Hook to server | `X-Gitea-Internal-Auth` shared token, constant-time compare, plain HTTP (upstream TODO) | `gitea:routers/private/internal.go:32-34` |

### 5.2 Weak points of today's setup

- Machine tokens are long-lived personal access tokens of local users (`jc-portal`, `jc-gateway`, `jc-apps`, `jc-registry-pull`, `jc-lane-secret`), rotated by the bootstrap Job; the platform rule is "no static keys between cluster services" (`/workspace/CLAUDE.md`, Non-negotiables).
- One Portal token can write every project repo; the per-project boundary is the Portal's code, not the forge (`portal:src/git/gitea.rs:977`).
- Permissions live twice: jc-core RoleBindings and Gitea teams synced by the reconciler and `groupTeamMap`; drift means a person keeps forge access after a RoleBinding is removed until the next login or reconcile (`portal:src/reconciler/project_teams.rs`).
- Secrets at rest: AES-CFB with `sha256(SECRET_KEY)` (`gitea:modules/secret/secret.go:20-33,58-61`, upstream "need to migrate" note); no authentication tag.

### 5.3 Rust design

- **Identity**: wardkeep OIDC only. Browser: Portal session (shako is a Portal module, same cookie, same CSRF rules). Git and API clients: wardkeep access tokens with audience `shako` (ServiceAccount client credentials for workloads; personal tokens via device or PKCE flow for `git` with a credential helper). No local users, no passwords, no PATs stored by shako.
- **Authorization**: every request asks `jc-auth::decide(subject, verb, resource)` with resource `(org, project, repo, ref?)`; verbs `read`, `propose` (push a non-protected branch, open a PR), `write`, `approve`, `admin`. Branch protection becomes a policy over refs evaluated in the receive-pack command phase, before any object is stored.
- **Secrets**: Actions secrets are `secretRef`s resolved at job dispatch from the secrets mount; nothing decryptable at rest in shako's tables.
- **Crypto**: rustls; tokens verified with wardkeep JWKS; HMAC-SHA256 with constant-time compare for outbound webhook signatures; runner tokens hashed with SHA-256 plus per-runner salt.
- **Input limits**: max push size per org (default 1 GiB), max object size (default 100 MiB, LFS above), max refs per push (1,000), pkt-line length checks, path rules (no `..`, no `.git` components, NFC/NFD and case-fold collisions refused per org setting), diff caps, request body caps per route, archive generation limited by a memory-weighted semaphore.
- **Code rules**: `forbid(unsafe_code)`, no subprocess on a request path (no `git` binary in the image), parameterized SQL, outbound allow-list with timeouts and size caps for push mirrors, `deny_unknown_fields` on every API body.

### 5.4 Upstream CVE classes and the answer

From the 99 SECURITY sections (304 entries) of `gitea:CHANGELOG.md` and `gitea:CHANGELOG-archived.md`. Classes, never recipes.

| Class | Example releases (fix) | shako answer |
|---|---|---|
| Token scope or public-only scope not enforced on a route | 1.27.3 packages (#39058), 1.27.0 (#37118), 1.26.2 raw/media (#37698) | One decision function per route generated from the operation registry; a route without a declared verb does not compile; a 401/403 test per route |
| Visibility leaks (hidden owners, revoked access) | 1.27.3 (#39012), 1.27.0 (#38390) | Forced RLS per organization; list and count queries run under the caller's decision; no precomputed `access` cache |
| Cross-repo object access (attachments, LFS without proof of possession) | 1.27.3 (#39077), 1.27.0 (#38389), 1.26.3 (#38050) | Objects addressed by `(repo_id, oid)` only; LFS upload requires the oid in the pushed tree or a verified batch; no global content-addressed lookup across repos |
| Actions fork-PR trust boundary | 1.27.3 (#39018), 1.27.0 (#38897) | No fork model; workflows run only from the protected default branch revision; secrets only for jobs on protected refs |
| Git hook privilege / RCE | 1.27.3 (#39016), 1.27.1 (CVE-2026-60004, KEV, `deployment:components/gitea/images.yaml:9`), 1.13.0 (#13058) | No shell hooks; hooks are compiled Rust or WASM without host capabilities |
| Git argument and ref injection | 1.17.3 (#21464), 1.10.0 (#7715) | No git subprocess; refs validated by `gix-validate` before use |
| SSRF in migrations, mirrors, webhooks (redirects, reserved ranges, unbounded bodies) | 1.27.3 (#39035, #39033), 1.27.0 (#38367, #38400), 1.26.3 (#38059) | Importers dropped except plain git; one outbound client with allow-list, no redirects, resolved-IP check, timeouts and size caps |
| Path traversal (restore, storage paths) | 1.27.0 (#38215), 1.16.5 (#19179) | Storage keys derived from ids, never from names; tree paths validated on push |
| Resource exhaustion in package parsers | 1.27.3 Swift/Maven/Alpine/Debian (#39032 …) | Only OCI and generic; manifest size cap, streaming digest checks |
| ReDoS (CODEOWNERS) | 1.26.3 (#38025) | Rust `regex` (linear time); no CODEOWNERS at first |
| OAuth2 provider flaws (PKCE, refresh replay, code reuse, introspection) | 1.26.2 (#37706), 1.25.5 (#36851), 1.27.0 (#38042) | shako is no provider |
| 2FA bypass on OAuth paths and API | 1.27.1 (#38606), 1.8.0 (#6674) | MFA belongs to wardkeep; shako trusts only wardkeep tokens |
| External-login linking (disabled users reactivated, stale links) | 1.26.4 (#38183), 1.26.3 (#38141) | No local accounts to link; subject = wardkeep `sub` |
| SSH LFS auth bypass | 1.26.3 (#38015) | No SSH |
| XSS in markup | 1.27.3 (#39054), 1.21.6 (#29336) | One sanitizer for every rendered output; renderers return HTML that is sanitized again; CSP with nonce from the Portal |
| Open redirect | 1.25.5 (#36716), 1.19.4 (#25143) | Redirect targets only relative paths of the Portal |
| Credentials at rest, cookie flags | 1.15.0 (#15547), 1.6.0 (#4706) | No stored credentials; Portal cookie rules |

## 6. Tenancy

| Question | Upstream Gitea | Platform today | shako |
|---|---|---|---|
| Unit of isolation | One instance = one database and one `ROOT_URL`; orgs are rows of `user`; no tenant or instance id (section 3.2) | One Gitea per installation; org `joinedcontext` holds the config repo, `joinedcontext-apps` the App repos; per-project repos and teams; no per-Organization Gitea org (`deployment:defaults/environment/global.yaml:45-53`; `portal:src/git/gitea.rs:977-983`; `deployment:.ci/example-deployments/environments/_layers/hosted/gitea.yaml.gotmpl`) | `instance_id` and `org_id` in every table, forced RLS on `org_id`, a database role per module without BYPASSRLS |
| Several forges per organization | Separate installations only | Not possible | `ForgeInstance` rows per organization (kind proposed below), each with its own domain, quotas, protection defaults and runner pool; repos belong to exactly one instance |
| Custom domain per organization or instance | One `ROOT_URL` per process | One host `{domain}/git` (`deployment:…/forge/base-values.yaml.gotmpl:166-181`) | Host header → instance lookup; per-instance TLS certificate by cert-manager HTTP-01 per hostname; clone URLs and UI links rendered with the instance host |
| Organization domain | none | `Organization.spec.domain` = `{orgDomain}`, `git_repository_url` (`platform:crates/jc-core/src/kinds/organization.rs:14-19,42-46`) | Default instance host `git.{orgDomain}`; repo path `/{project}/{repo}` |
| Identity | per-instance local users linked to OIDC | Keycloak realm per installation; `groupTeamMap` | wardkeep, several identity domains per organization allowed; subject = `(issuer, sub)` |
| Permission model | access modes × unit types, teams, collaborators | jc-core Role, RoleBinding, Group, Policy, DelegationPolicy, ServiceAccount, synced into teams | jc-auth decision only; no teams or collaborators tables; the RoleBinding is the only grant |
| Quotas | `LimitTotalOwnerSize` for packages only (`gitea:modules/setting/packages.go:20`) | none | per organization and per instance: repo count, storage bytes (Git + LFS + packages), push size, API requests per minute, concurrent clones, runner minutes |
| Storage layout | `{ROOT}/{owner}/{repo}.git` | PVC 20 Gi | object store or PVC keyed `{instance_id}/{repo_id}`; names never in paths |

Proposed jc-core kind (Decided, worker-t6639, owner may override): `ForgeInstance` in the organization registry, spec `{host, tls: {secretRef}, quotas, protection: {defaultBranch, requireChange}, runners: {pool}}`; a Project's `repository.name` resolves inside one instance (`platform:crates/jc-core/src/kinds/project.rs:48-62`).

Isolation tests (each a test in shako's suite, run per surface: smart HTTP, REST, UI loaders, MCP, registry, runner):

1. A token of org A gets 404 (never 403) for every repo, package, run and artifact of org B; the same for another instance of org A it has no binding in.
2. List and count endpoints of org A never include org B rows (`total` checked); search returns nothing across instances.
3. Timing: a missing repo and a forbidden repo answer within the same latency band (bounded test, p95 difference < 5 ms over 200 requests).
4. Registry: blob mount from a repo of org B is refused; manifest by digest of org B is 404.
5. Runner of instance X never receives a job of instance Y; a runner token is bound to one instance and one pool.
6. Host header of instance X with a repo path of instance Y is 404.
7. RLS: queries as the module role with `app.org_id` unset return zero rows.

## 7. Operations

| Area | Upstream | shako |
|---|---|---|
| Config as code | `app.ini` from chart values plus env `GITEA__section__KEY`; bootstrap Job of 1,254 lines creates orgs, repos, users, tokens and protections via API (`deployment:components/gitea/charts/bootstrap/templates/job.yaml`) | Instances, repos and protections are manifests in the organization registry reconciled by the Portal; no bootstrap Job; the config file lists only listen address, database URL from secretRef, storage root |
| Migrations | 273 xorm migrations, run at start | sqlx migrations, forward-only, with a rollback table as Antares does; data import from Gitea by a one-shot `shako import-gitea` (repos by git, PRs and reviews by API) |
| Backups | `gitea dump`; repositories on the PVC | Postgres via CNPG backups; Git objects in an object store with versioning, or a nightly `git bundle` per repo when on PVC |
| Upgrades | image bump; `Recreate` (RWO PVC) | rolling, stateless pods when objects live in the object store |
| Observability | `/metrics`, logs | OpenTelemetry traces and metrics with `org_id`, `instance_id`, `repo_id` at write time; activity events to the one log |
| Memory today | dev pod median 249 Mi, peak 306 Mi; request 320 Mi, limit 1 Gi (`/workspace/tasks/finished/T-4473-memory-efficiency-measured.md:50,88`; `deployment:components/gitea/values/forge/development-values.yaml.gotmpl:9-21`) | — |
| CPU at 100 req/s | 7.5 cores for 90 req/s of five read routes, p95 1.38 s (section 3.4) | in-process reads: 0.16 ms per composite read on one core (section 3.4) |

Budget for shako inside the 2 GB platform target (Decided, worker-t6639, owner may override): **128 MiB steady** (pack and object caches 64 MiB, HTTP and DB pools 32 MiB, rest 32 MiB), **0.5 core at 100 req/s** of the Portal's read mix, and a memory-weighted semaphore of **256 MiB** for clone pack generation and push indexing (gix-pack peaked at 205 MiB for a 100 MB full clone, so one large clone at a time per pod, small ones in parallel). Runners and build pods stay outside the budget, as today.

## 8. Test oracles

| Oracle | What it proves | How |
|---|---|---|
| C git client against shako | clone, fetch (v0 and v2), shallow, partial clone filter, push, force-push refusal, atomic push, push options, LFS | the git 2.47+ test scripts `t/t5551-http-fetch-smart.sh`, `t5541-http-push-smart.sh` and siblings pointed at shako via `GIT_TEST_HTTPD`-style wrappers; plus a scripted matrix in shako CI |
| Differential against `git http-backend` | byte-level ref advertisement and pack content equality (object sets) | same repository served by both; compare `ls-refs`, the object set of each fetch, report-status of each push |
| Differential against pinned Gitea 1.27.3 | the 53 Portal call rows answer the same JSON for the same repository | replay the Portal's calls (section 2) against both; diff after masking ids and times; image pinned as in section 1 |
| Portal contract | the Portal works unchanged on shako | `portal:src/git/gitea.rs` tests and `deployment:tests/fake_forge.py` (13 functions) as the compatibility contract; the Portal's forge-backed integration tests |
| Upstream integration tests as specification | merge, protection, review, packages, Actions behaviours | read `gitea:tests/integration/` (255 files) for the used rows, port the assertions, not the harness |
| OCI conformance | registry | `opencontainers/distribution-spec` conformance suite (push, pull, content discovery, management) |
| Runner protocol | build lane | Gitea runner v3.5.0 (the one in the builder image) registers, fetches a task, streams logs and uploads an artifact against shako |
| UI | browse, download, review, merge | Playwright journeys with 1440 and 400 px shots, as Portal pages |
| Isolation | section 6 tests | per surface, in CI |

100 % for a worker means: every row of section 2 marked Used or Need has a passing oracle test, the Portal's contract tests are green against shako, and the differential runs show no unexplained difference.

## 9. Argon pack plan

Token counts measured with repomix 1.18.1 (o200k) by `scripts/research/gitea-sources.sh` on the pinned checkout, `*_test.go` and `testdata` excluded:

| Part | Files | Bytes | Tokens |
|---|---|---|---|
| R1 git core: smart HTTP, private hook API, `cmd/hook.go`, `cmd/serv.go`, `modules/git`, `modules/gitrepo`, LFS, permissions, organizations, collaboration, repo model, branch and tag protection, units | 272 | 778,972 | 217,442 |
| R2 API and pulls: the API handlers of the Portal's routes, `services/repository/files`, `services/pull`, webhook delivery, the `modules/structs` types | 67 | 676,672 | 181,551 |
| R3 packages and Actions: container and generic registries, package auth and models, `routers/api/actions`, `models/actions`, `services/actions` | 77 | 674,865 | 175,797 |
| R4 UI and login: repo templates (home, view, blame, commits, diff, pulls, merge box), the matching web handlers, OAuth2 login source and linking | 64 | 361,285 | 97,982 |
| Ours, Portal: `src/git/gitea.rs`, `src/api/webhook.rs`, `src/apps/build_pods.rs`, `src/reconciler/project_teams.rs` | 4 | 171,032 | 40,434 |
| Ours, deployment: gitea and gitea-runner values, bootstrap Job, NetworkPolicies | 21 | 147,031 | 38,305 |
| Ours, platform: agent-proxy forge door, `jcctl checkouts`, Organization and Project kinds | 3 | 35,753 | 8,522 |

Generation split (one shared contract file `shako-contract.md`, about 15k tokens: this page's sections 2, 5.3, 6 and 11, the Portal call table, the jc-auth trait, the table list):

| Run | Inputs | Tokens in | Output |
|---|---|---|---|
| 1 Backend Git | contract + R1 + ours (87k) + the git protocol docs `gitea` does not carry (`Documentation/gitprotocol-v2.txt`, `gitprotocol-pack.txt`, `gitprotocol-http.txt` from git 2.47, about 25k) | about 345k | crates `shako-git` (upload-pack v2, receive-pack, hooks trait, LFS), `shako-store` (gix, object store), about 12-15k lines |
| 2 Backend API and registry | contract + R2 + R3 minus Actions (about 120k) + ours | about 360k | crates `shako-api` (53 Portal routes, PRs, merge, protection), `shako-registry` (OCI + generic), about 15-18k lines |
| 3 UI | contract + R4 + the Portal UI shared components and one existing page as style reference (about 60k) | about 175k | React pages in the Portal (`ui/src/modules/forge/`), about 8-10k lines |
| 4 Actions (last, if the owner keeps the runner protocol) | contract + Actions half of R3 (about 95k) + `actions-proto-go` v0.6.0 `.proto` files (about 5k) + `deployment:components/gitea-runner` + `portal:src/apps/build_pods.rs` | about 200k | crate `shako-actions` (runner.v1 connect-rpc, jobs, logs, artifacts), about 6-8k lines |

Every run stays under 500k tokens. Expected total about 45-50k lines with tests, matching the 50-70k estimate of T-6634 once the parity work lands.

## 10. Decisions and owner questions

Decided (worker-t6639, owner may override):

1. **gix as the Git engine**, own upload-pack v2 and receive-pack state machines; because it has delta-reusing pack generation (0.32 s vs git's 0.45 s) and the fastest indexing (0.30 s vs 1.14 s), runs in process (0.16 ms per composite read), and needs no C; options: libgit2 (rejected: 31 s pack generation, C, no server), `git http-backend` subprocess (kept as oracle; a process per request and shell hooks are the CVE class shako removes).
2. **No SSH**, HTTPS only; because no environment enables it today; option: add later behind a feature with keys bound to wardkeep subjects.
3. **No issues, wiki, projects, releases, 22 package types, importers, mail, indexers, OAuth2 provider, local accounts**; because nothing in the platform calls them and each is attack surface.
4. **Permissions only through jc-auth**; no teams or collaborators tables; because two permission stores drift (section 5.2).
5. **API compatibility**: shako serves the 53 Portal calls of section 2 with Gitea's paths and JSON shapes for the transition, under `/api/v1`; the Portal's `GiteaClient` stays until a native operation registry replaces it; option: change the Portal in the same batch (more risk at once).
6. **Webhook gap fixed by design**: in-process events replace the unregistered push webhook (section 2.2).
7. **`ForgeInstance` kind** and per-instance hosts (section 6).
8. **Budget** 128 MiB steady, 256 MiB clone semaphore (section 7).

Only the owner can answer:

1. Keep the Gitea runner protocol (run 4) or move App builds to an own runner and drop Actions from shako (T-6634 names this as the owner's call)?
2. Git objects in an object store (needs S3 credentials and money for a bucket) or on the node PVC as today?
3. Should a public repository be readable anonymously (clone and UI without sign-in), or does every read need a wardkeep token as every forge call does today?

## 11. MCP mapping

Rules from T-6640: one operation registry, the UI and MCP call the same operation, the same jc-auth decision, the same review lanes; read tools filter before paging and counting. Connector segments from `portal:src/connectors.rs:120-175` (`context`, `publish`, `apps`, `operate`, `access` …); a new segment `forge` is proposed (Decided, worker-t6639, owner may override) for repository work that is not App building.

| Tool | Input | Output | Permission (jc-auth verb on resource) | Segment |
|---|---|---|---|---|
| `jc_forge_repo_list` | `instance?`, `project?`, `q?`, `cursor` | repos with default branch, size, protection summary | `read` on each repo (filter before count) | forge |
| `jc_forge_repo_get` | `repo` | repo card, clone URLs, branches count | `read` repo | forge |
| `jc_forge_tree` | `repo`, `ref`, `path?`, `recursive?` | entries (path, kind, size, oid), capped at 2,000 | `read` repo | forge |
| `jc_forge_file_get` | `repo`, `ref`, `path` | content (text up to 256 KiB, else metadata and a download link) | `read` repo | forge |
| `jc_forge_commits` | `repo`, `ref`, `path?`, `cursor` | commits (sha, author, time, message head) | `read` repo | forge |
| `jc_forge_diff` | `repo`, `base`, `head`, `path?` | file list and unified diff, capped | `read` repo | forge |
| `jc_forge_change_propose` | `repo`, `branch`, `files[]` (put/delete), `message`, `title`, `body` | branch, commit, pull request | `propose` repo; secret scan and manifest checks run first | forge |
| `jc_forge_pr_list` / `jc_forge_pr_get` | `repo`, `state?` / `repo`, `number` | PRs with checks, reviews, mergeable | `read` repo | forge |
| `jc_forge_pr_review` | `repo`, `number`, `verdict`, `body` | review id | `approve` repo (proposer cannot approve own red-lane change) | forge |
| `jc_forge_pr_merge` | `repo`, `number`, `style` (merge, squash, ff-only) | merge commit | `write` on the target ref by protection policy | forge |
| `jc_forge_protection_get` / `_propose` | `repo`, `ref_pattern?` / `repo`, rule | rule / Change | `read` / `admin` repo, through a Change | forge |
| `jc_forge_archive_link` | `repo`, `ref`, `format` (zip, tar.gz, bundle) | short-lived signed URL | `read` repo | forge |
| `jc_forge_package_list` / `_get` | `instance`, `kind` (container, generic), `name?` | packages, tags, digests, sizes | `read` package | apps |
| `jc_forge_run_list` / `_get` | `repo` or `app`, `status?` | runs, jobs, durations | `read` repo | apps |
| `jc_forge_run_logs` | `run`, `job`, `since?`, `tail?` | log lines (redacted at write time) | `read` repo; resource subscription for a live tail | apps |
| `jc_forge_run_dispatch` | `repo`, `workflow`, `ref` | run id | `write` repo | apps |
| `jc_forge_activity` | `instance?`, `repo?`, `since` | push, merge, protection, token events with ids | `read` on each object (filtered before count) | operate |
| `jc_forge_quota` | `instance` | usage vs quota per dimension | `read` instance | operate |

Isolation tests for the tools: every tool called with org A's connector on org B's repo, package, run or instance returns the same "not found" text and timing band as a missing object; list tools report totals of org A only; `jc_forge_run_logs` subscriptions end when the binding is revoked; a DelegationPolicy without the `forge` segment hides all `forge` tools from `tools/list`.

## Related

- [Requirements of the next platform](../next-platform/05-requirements.md): the requirement ids a shako pack traces to.
- [Next platform architecture](../next-platform/02-architecture.md): the module layout, the one Postgres and the jc-auth crate this page assumes.
- [Identity and authorization](../next-platform/03-identity-and-authz.md): the decision model behind the verbs of sections 5.3 and 11.
- [Isolation threat model](../next-platform/04-isolation-threat-model.md): the threats the isolation tests of section 6 answer.
