---
sidebar_position: 63
title: "ADR-N-062: Branch Previews on the dev Node"
---

# ADR-N-062: Branch Previews on the dev Node

Date: 2026-10-25  
Status: Proposed  
Decision Makers: product owner (2026-10-24: "if different branches can be deployed, just improve that"); drafted by worker-t5546 (T-5546), owner may override

This record decides what a preview of a code branch runs on the `dev` node, what it is isolated by and how many fit. [Deployment/17](../Deployment/17-branch-previews.md) carries the numbers and the namespace manifests; T-5547 builds the branch images and T-5548 the recipe and the isolation suite.

## 1. Context

The platform previews configuration, not code. A workspace preview ([ADR-N-024](adr-n-024-workspaces-branch-and-preview.md)) renders a configuration branch inside the shared Portal and gateway, runs no workload and is capped at 2 on the node (`joinedcontext-portal` `src/ops/previews.rs`, `MAX_ON_NODE = 2`). A change to the Portal, gateway or broker code is seen running only after it is merged and the hourly apply reaches dev. The prod path is T-0051's release gate (`v*` tag, render diff, approval on the `production` environment); a staging cluster stays unfunded (owner 2026-09-14, 2026-10-06).

The node has no room for much. dev is one `cpx42` with 13,805 Mi allocatable; at 2026-10-24T19:37Z it used 12,990 Mi (94 %), and T-5113 found it cannot reach 20 % headroom from values ([Operations/02](../Operations/02-capacity-and-scaling.md) section 4).

## 2. Options

| Option | Memory per preview | Isolation | Verdict |
|---|---|---|---|
| A. A full second instance per branch (`deployLayer: instance`) | about what dev uses, 8-12 GiB | own namespace, but 46 fixed-name cluster-scoped objects of `.ci/golden/dev.txt` collide unless split by layer, which dev does not run | refused: does not fit on any node the owner runs |
| B. The changed service only, in dev's namespace, beside dev's own | one pod | none: shares dev's Secrets, database and network | refused: a branch would read dev data |
| C. The changed services plus what they cannot start without, in `pv-{slug}`, each against its own database, Keycloak clients in a realm `preview` and a fixture forge organization | 0.75-2.15 GiB at most | namespace, NetworkPolicy, `pg_hba`, realm, signed images | **chosen** |
| D. C, but its Keycloak clients in dev's realm | same as C | dev's gateway refuses by audience only, and dev people sign in to branch code | refused for the realm part: issuer and audience together are stronger than audience alone |
| E. A fixed pool of two preview hosts whose certificates outlive the branches | same as C | same as C | not now: saves certificates, but a Certificate's Secret cannot cross from a long-lived namespace to `pv-{slug}`; reconsider if the 10-a-week cap binds |

## 3. Decision

1. **The unit.** A preview runs the services its branch changed, one replica each, in `pv-{slug}`: the Portal (with its UI bundle), the gateway, or both; the broker only when its repository changed. A service the changed one cannot start without runs from dev's pinned, signed digest inside the same namespace. Nothing in the preview calls dev's gateway, broker or Portal.
2. **Its own state.** A database `pv_{slug}` in the shared CNPG cluster under its own role, with no grant elsewhere and a `pg_hba` line refusing `pv_*` roles on every other database; clients `pv-{slug}-*` in one realm `preview` with fixture people only; a Gitea organization `pv-{slug}` loaded from a committed fixture; Secrets created in its namespace. No dev data and no dev secret enter a preview.
3. **The budget.** Requests start at dev's, limits lower (Deployment/17 section 2). Today no preview fits: the recipe refuses above 90 % node memory, and dev is at 94 %. After T-4936 one Portal preview fits at its at-rest size, as an owner exception to the 80 % line. A `cpx52` takes 4 Portal or 2 Portal-and-gateway previews, a `cpx62` (estimate) 12 or 6, a tainted `cpx32` agent node (estimate) 5 or 2. Whatever the node, at most 2 branch previews run at once. Buying a node is the owner's decision; this record orders none and recommends the tainted agent node if one is bought, because previews on it never take memory from dev's pods.
4. **The host.** `preview-{slug}.dev.joinedcontext.com`, a Traefik Ingress in the preview's namespace, one HTTP-01 certificate per host from `letsencrypt-prod`, no wildcard and no DNS API. At most 10 preview certificates per 7 days, from the 50 that dev and prod share on `joinedcontext.com`.
5. **The lifetime.** Label `sandbox.joinedcontext.com/lifecycle: preview`, annotation `sandbox.joinedcontext.com/ttl: 48h`; the sandbox reaper deletes the namespace (14-day ceiling, OPS-44, PF-19), and the recipe removes the database, role, clients and forge organization by name. The reaper is deployed on dev before the first preview.
6. **The relation.** Workspace previews stay as ADR-N-024 has them. Branch previews never touch prod and never promote: their `pv-` image tags are never pinned (T-5547), their forge organization is a fixture, and T-0051 stays the only path to prod. A staging cluster remains the owner's call.

## 4. Security

The isolation suite of T-5548 checks five properties from inside a preview namespace: no TCP to dev's gateway, broker, Portal or the internet; the `pv_{slug}` role cannot connect to a dev database; dev's gateway and Portal answer 401 to a preview client's token (wrong issuer, wrong audience); no preview pod references a dev Secret; the quota refuses a 2 GiB pod. Admission checks a sixth: a preview runs only images CI built and signed from its branch, or dev's pinned digests, under the unchanged image-signature policy.

What stays open: dev's databases grant `CONNECT` to `PUBLIC`, as Postgres does by default. The `pg_hba` refusal closes that for preview roles; revoking `CONNECT` from `PUBLIC` on every dev database would close it for every role and is left to its own change, because each dev service's role then needs an explicit grant.

## 5. Consequences

- dev gains the sandbox reaper, a realm `preview`, a `pg_hba` block and ingress halves on Keycloak, Postgres and Gitea for `pv-*` namespaces (T-5548).
- `image.yml` in the portal and platform repositories gains a branch build with `pv-` tags and a 14-day registry clean-up (T-5547).
- No preview runs until node memory is below 90 %, which today means after T-4936 or a node the owner buys.

## Related

- [Deployment/17](../Deployment/17-branch-previews.md): the numbers, the namespace manifests and the isolation checks.
- [ADR-N-024](adr-n-024-workspaces-branch-and-preview.md): workspace previews, unchanged.
- [ADR-N-056](adr-n-056-gitops-argo-cd-helmfile.md): how dev follows `main`, which previews never enter.
- [Operations/02](../Operations/02-capacity-and-scaling.md): the node's memory and the add-a-node rules.
- [Requirements/operations.md](../Requirements/operations.md): OPS-44; [Requirements/platform.md](../Requirements/platform.md): PF-19, PF-83.
