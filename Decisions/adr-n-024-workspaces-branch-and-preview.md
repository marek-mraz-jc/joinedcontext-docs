---
sidebar_position: 25
title: "ADR-N-024: Workspaces: Copy, Change, Test and Bring Back, Renamed at Render and Never at Rest"
---

# ADR-N-024: Workspaces: Copy, Change, Test and Bring Back, Renamed at Render and Never at Rest

Date: 2026-09-18  
Status: Accepted  
Amended by: ADR-N-029: a project workspace is a branch of the project repository, an organization workspace a branch of the organization repository  
Decision Makers: product owner

## 1. Context

The owner's question (2026-09-18): make every pipeline, endpoint and project easy to duplicate and still deployable. Three scenarios. An agent copies a whole project, changes and tests a few things, and deploys them back to the main project. An employee copies a project, a space, a model or a pipeline, works on the copy, and pushes it to the main project. A copy is one action with no hand-editing. A better design is welcome even when it means a rewrite.

How configuration as code works today, from the code on `main`:

- Every resource is one manifest in the organization repository. A write goes through `propose_with_identity` (`joinedcontext-portal/src/api/mutate.rs`), which validates, diffs against the mirror, classifies a lane, commits to **a branch of its own** (`branch_name` builds `portal/{op}-{kind}-{name}-{hash}`) and opens a pull request that the Portal shows as a Change. One open Change per resource: `open_change_on` refuses a second.
- Names are the identity. `metadata.name` is unique per kind per project namespace; references between manifests are names (`contextSpaceRef`, `projectionRef`, `dataModelRef`, …). Three things are unique beyond the project: the project name, the **Context Space name** (unique in the organization because it is the `{space}` segment of every entity URN, PF-44, PF-76) and the **Endpoint slug** (minted per environment, EP-75).
- Environment-specific values are **rendered at load, never stored**: `kind: Environment` overlays (CC-73), `{orgDomain}` replaced by the loader (`jcctl/src/loader.rs`, `ORG_DOMAIN_PLACEHOLDER`), slugs minted per environment (CC-74). One repository renders every environment.
- The import door (`src/api/import.rs`) copies across projects and instances: `ConflictPolicy` fail, skip, replace, rename; `rewrite_reference` and `rewrite_space` rewrite names inside the bundle; slugs are minted again. Export strips status and secrets. `SyncSource` repeats an import on a schedule.
- Drafts (`src/ops/drafts.rs`) hold one unsaved manifest per (project, kind, name) with its Verdict. A proposal needs a fresh green Verdict whose `inputDigest` matches the manifest (PF-57).

What this cannot do today: hold **several related edits together**, run them **somewhere safe**, and bring them back as **one reviewed Change**. A Change is one resource on one branch. The import door copies, and nothing brings a copy back.

## 2. What a Stored Copy Costs

The first design pass (DeepSeek, kept in the scratchpad) proposed the obvious: copy the manifests into a sibling project with a suffix on every name, record a rename map in a new `kind: Workspace`, and bring changes back with a three-way merge that reverses the map. It reuses the import door and is cheap to start. It fails on exactly the cases that matter:

| Case | What happens with a stored, renamed copy |
|---|---|
| A resource is **added** in the copy | It has no origin name. The reverse map has to invent one and may collide. |
| A resource is **renamed** in the copy or in the origin meanwhile | The map points at a name that no longer exists on one side. |
| A reference is typed by hand in the copy (YAML view, agent) | It names the copy's resource. The reverse rewrite must find every reference in every kind, including ones inside Bloblang, SQL and dashboard JSON, where `rewrite_reference` cannot see them. |
| The origin moves while the copy is open | The merge is ours, not Git's: a second merge engine to write, test and keep correct for every kind and every list type. |
| The reviewer | Reads a diff that was produced by un-renaming. What they approve is not what ran. |
| The Verdict | Was taken for the renamed manifest. After un-renaming the `inputDigest` differs, so every check has to run again or the gate is weakened. |
| Expiry | The copy is manifests in Git. Deleting a namespace does not delete them, and the reconciler brings the copy back. |

Every row has the same root: **the copy is renamed at rest, so the platform must reverse the rename to bring it back.**

## 3. Decision

**A workspace is a branch of the organization repository plus a preview of that branch. Manifests in a workspace keep their real names. The preview is renamed when it is rendered, the way `{orgDomain}` and slugs already are.**

1. **Workspace = long-lived Change branch.** `jc_workspace_open` creates the branch `workspace/{name}` from `main` at revision R and records it (owner, base revision, scope: a project, a space subtree or a list of resources, TTL). Every write made "in the workspace" is the same `propose_with_identity`, committing to that branch instead of opening a one-resource branch. Today's Change becomes the special case: a workspace with one edit that is proposed at once.
2. **Nothing is renamed in Git.** The pipeline `bikes-ingest` is `bikes-ingest` in the workspace. References, Bloblang, SQL and dashboard JSON stay untouched, because nothing moved.
3. **Preview = one more rendered environment.** The loader already merges an `Environment` overlay before validation. A preview overlay adds one thing: a **render prefix** `ws-{name}-` applied by the loader to the three organization-unique identities (project namespace, Context Space name and therefore the `{space}` URN segment, Kubernetes and Keycloak object names derived from them), with slugs minted for the preview as for any environment. The preview's spaces are separate spaces with separate data. It cannot write into the origin because its space names are different names.
4. **A preview is paused and sampled by default.** Pipelines render with `spec.enabled: false` semantics (PL-40) unless the person starts one. Data for a test comes from the existing pipeline test (sample in, capture out, nothing written) or, when a person asks, from a bounded replay of the origin's entities into the preview space, read with the person's own grants. One preview runs on `dev` at a time per workspace, within the project's quota.
5. **Bring back = the pull request of that branch.** Git computes base, ours and theirs. The forge's three-way merge is the merge engine. A conflict is a Git conflict on one manifest file, shown per field by the existing plan diff (`plan::diff`), resolved by the person in the workspace (never "theirs wins" silently), and the merged result is validated again. The Change is one, its lane is `riskiest` over every file (the function T-1224 added), approval is unchanged: PF-50, PF-58, an agent never approves.
6. **The Verdict stays honest.** Names did not change, so the manifest that was checked is byte for byte the manifest that is proposed, and the `inputDigest` holds. After a merge with `main` the digests of touched files change and the check runs again, which is the gate doing its job.
7. **Duplicate is a different, small thing.** "Make another pipeline like this one" is not a workspace. It is **Save as**: the existing form opened on the existing manifest with a new name (and, for a space, the import door's `rename`, which already rewrites references inside the bundle). It lands as an ordinary Change. No origin is recorded because nothing comes back.
8. **Across instances and projects** stays the import door: export a bundle, import it with `rename`. A workspace may be exported like any revision.

The same three operations serve all three scenarios. The agent's scenario: `jc_workspace_open` for project `helsinki`, edits through the registry with the workspace named in the call, `jc_workspace_preview`, the existing checks, `jc_workspace_propose`. The agent acts with the rights of the person who started it (AG-70), never approves (AG-11), and its workspace carries a TTL.

## 4. Names Carry No Prefix

Should an endpoint be named with a prefix, `organization-project-endpoint`, so it can be copied
across projects and organizations? **No.** A prefix inside `metadata.name` is a rename at rest
under another name: the copy in project B would either keep A's prefix (a lie) or be renamed (and
every reference with it). The platform already has the three identities a copy needs, and none of
them is in the name:

| Question | Answered by | Example |
|---|---|---|
| Which resource is this, inside its project? | `metadata.name`, unique per kind per project | `bikes-public` |
| Which project and organization? | where the manifest lives: `metadata.namespace` and the repository path `projects/{project}/…`, and `{orgDomain}` rendered from the Environment (CC-73, CC-74) | `projects/helsinki/spaces/helsinki/endpoints/bikes-public.yaml` |
| How does anyone outside the project reach it? | the **slug**: opaque, minted per environment, never derived from a name (EP-02, EP-75). Cross-project use already goes by it: `SharedSpaceReferenceSpec` holds `endpoint_slug` and a local `alias` | `/api/endpoint/k7m2qz4tv6xh3n5jb2ryd3wcfa` |

So `bikes-public` can exist in ten projects and two organizations at once, a copy keeps its name,
and its address is minted where it lands. On screen and in logs the qualified form
`{orgDomain}/{project}/{name}` is a display string built from those three, never stored.

Two things do break when one endpoint is copied to another project, and neither is the name:

1. **Its space.** `spec.contextSpaceRef` names a space of the source project. The copy needs one of:
   the space copied with it (a space subtree), an existing space of the target chosen by the
   person, or, when the intent is to *use* the source's data rather than duplicate it, no copy at
   all but a `SharedSpaceReference` to the source endpoint's slug. The copy dialog must ask which.
2. **The one prefix the platform does store.** A Context Space name is unique in the organization
   because it is the `{space}` segment of every entity URN, and PF-76 proposes `{project}-{name}`
   by default. A space `helsinki-bikes` copied into project `espoo` keeps a name that says
   `helsinki`, in the manifest and in every entity id. The owner decided it in section 10, question 6.

## 5. Alternatives Considered

| | A. **Branch + rendered preview** (chosen) | B. Sibling project, rename map, own three-way merge | C. Forge fork + SyncSource | D. Bundles + "promote" | E. Overlays (store only differences) | F. Stable ids, names as labels |
|---|---|---|---|---|---|---|
| Rename at rest | none | every name | none | every name | none | none |
| Merge engine | Git's | ours, per kind | Git's | none (overwrite) | ours | ours, simpler |
| Added, deleted, renamed resources | fall out of Git | special cases | fall out of Git | lost | hard | fine |
| Reviewer sees | what ran | an un-renamed reconstruction | what ran | a bundle | an overlay | what ran |
| Verdict survives bring-back | yes | no | yes | no | no | yes |
| Expiry | delete a branch | a Change that deletes manifests | delete a repository | nothing to expire | delete a file | as A |
| New code | loader render prefix, branch-targeted propose, workspace registry, preview lifecycle | copy, rename map, reverse map, typed merge, conflict UI | fork management, tokens per fork | small | new format, new reconciler path | every kind, every reference, the mirror, every repository migrated |
| Deletes | the one-resource branch naming as a special path | nothing | nothing | nothing | nothing | the name-based model |

B is where the first pass landed and is rejected for the reasons in section 2. C costs a repository and forge credentials per workspace for the same result as a branch. D has no merge. E makes every reader resolve overlays forever. **F is the honest rewrite**: stable ids would make renames free. It is rejected because A removes the need: when nothing is renamed at rest, names are already stable. F stays the answer if the owner later wants resources to be renamed in place without breaking references; A does not block it.

## 6. What Changes in the Code

- `jcctl/src/loader.rs`: a render prefix beside `{orgDomain}`. One function, applied to namespace, Context Space names and URN `{space}` segments, tested so a rendered preview never contains an unprefixed organization-unique name. **This is the only place a rename exists.**
- `joinedcontext-portal/src/api/mutate.rs`: `propose_with_identity` takes an optional workspace. With one, it commits to `workspace/{name}` and returns the workspace's state instead of a new pull request. `open_change_on` learns that a resource edited in a workspace is "open" there.
- `src/sync/mirror.rs`: the mirror is per revision already in spirit (it mirrors `main`). A workspace reads its own branch overlaid on `main`, so lists, forms and dry runs inside a workspace see the workspace's manifests.
- A small workspace registry (Postgres table beside drafts, not a new kind in Git: a workspace describes a branch and should not live on it): name, owner, base revision, scope, TTL, preview state.
- Reconciler: a preview is a second render of another branch with a prefix, applied into namespaces labelled for the existing sandbox reaper (CC-67), which already deletes them at TTL. Deleting the branch is the rest of the cleanup. On `dev` nothing of a preview runs as its own workload while its pipelines are paused, so the shared gateway serves the prefixed render and no namespace is created (Architecture/06 §7.2, 2026-09-18).
- Drafts: a draft belongs to a workspace (or to none). This removes today's ambiguity between a draft and an open Change on the same resource.
- Deleted: nothing at first. After parity tests, the one-resource branch path in `mutate.rs` becomes "open a workspace, commit, propose" and the special case goes.

## 7. User Experience

Plain words, no Git vocabulary on screen.

1. **Work on a copy** on a project, a space or any resource row. One dialog: a name for the work ("Bike stations cleanup"), what it covers (preselected from where the person clicked), how long to keep it. Nothing else to fill in.
2. **A workspace bar** across the top while inside it: "You are working on a copy of Helsinki, started 18 Sep. 3 changes. Nothing here is live." with **Try it**, **Compare**, **Bring back**, **Leave**. Every page below is the normal page, showing the workspace's state. Forms, Check and the assistant work as always.
3. **Try it** starts the preview and shows its addresses (the preview's endpoint links), what is running, what is paused, and a **Stop** button. A failed preview says which resource failed and links to it.
4. **Compare** is the existing plan diff for every changed resource, grouped by kind, with added and removed resources listed first.
5. **Bring back** shows that list again with the lane, who can approve, and any resource that changed in the main project meanwhile. A conflict opens that resource's form with both values per field and the person picks or types. Then one Change, the normal approval page, and the approver sees one more line: "From the copy *Bike stations cleanup* by Jana, tried on 18 Sep, all checks green."
6. **Save as** on every resource form and row: the form, prefilled, new name required.
7. **The assistant**: "Copy the Helsinki project, switch the bike pipeline to the new feed, test it, bring it back" opens a workspace, edits, runs the pipeline test and the preview, reports what it saw, and stops at **Bring back** for the person.
8. States: empty workspace ("Nothing changed yet"), expired ("This copy was removed on … ; its changes were never brought back"), no permission (the control is disabled with the reason, the same everywhere), someone else's workspace (read only).

## 8. Security Analysis

| Threat | Control |
|---|---|
| A copy reads data the person may not read | A workspace reads manifests with the person's `read` grants. A replay into a preview reads through the origin's Endpoint with the person's token, so its Policy decides. |
| Rights gained through a copy | A workspace grants nothing: the same `permissions::for_request` and `within_own_rights` run on every write into it. RoleBindings and Policies in a preview render into the prefixed namespace only. Bring-back of a grant is a red-lane file like any other. |
| A preview writes into the origin's space | Impossible by name: preview spaces carry the render prefix, and the loader test forbids an unprefixed organization-unique name in a preview render. |
| A secret travels | Manifests hold `secretRef` only (MF-24 runs on every workspace write). A preview resolves a `secretRef` only when the person may use it in the origin project, and only for a pipeline the person started. |
| Bring-back hides a change from the approver | The Change is the branch's pull request: the approver sees every file Git sees. The lane is `riskiest` over all of them. No reconstruction step exists. |
| Approving your own copy | Unchanged: PF-58. An agent never approves (AG-11), whoever opened the workspace. |
| A stale green Verdict | `inputDigest` is over the real manifest. Any merge that touches a file invalidates its Verdict. |
| Node exhaustion | One preview per workspace, paused pipelines, the project's quota counts a preview, TTL on every agent workspace, the reaper removes namespaces, branch deletion removes the rest. |
| A confusing branch name or workspace name | DNS-1123, the same `validate_meta` rule. |

## 9. Requirements

The decision lands as requirements, each in its family:

- [Requirements/city-as-code.md](../Requirements/city-as-code.md) — CC-76…CC-81: the workspace, names kept at rest, the rendered preview, one Change to bring it back, conflicts resolved by a person, expiry.
- [Requirements/platform.md](../Requirements/platform.md) — PF-82, PF-83: every write into a workspace passes the same checks; a preview never writes into a main space and runs paused.
- [Requirements/agents.md](../Requirements/agents.md) — AG-82: an agent works in a workspace for a change of more than one resource and never brings it back or approves it.
- [Requirements/portal-and-ui.md](../Requirements/portal-and-ui.md) — UI-61…UI-63: Work on a copy and Save as, the workspace bar, Bring back, and the approver's line.

## 10. Owner Decisions

The owner answered each question on 2026-09-18. The bar the owner set: *"when you copy an organisation it should just work, when you copy an endpoint it should just work."*

| Question | Decision |
|---|---|
| 1. Previews on `dev`, one 16 GB node | **Limited**: at most one running preview per workspace and two on the node, pipelines paused. |
| 2. Real data in a preview | **Opt-in, bounded copy** through the origin's Endpoint with the person's own rights, for example 1 000 entities per type. |
| 3. Where the workspace registry lives | **A database table** beside drafts, not a `kind: Workspace` manifest on `main`. |
| 4. Order | **Workspaces first** (open, edit, compare, bring back), previews second. |
| 5. Stable ids (option F) | **Not now**; option A does not block it. |
| 6. Context Space identity across projects | The rule stays: a space name is unique in the organization and part of every entity id. **The prefix is added by the platform from the project, never written into a name.** |

## 11. "It Just Works", Checked Against the Manifests on Dev

The rule is: **a manifest says only what is local to it; everything that depends on where it
lives is rendered from where it lives.** Read against `components/context-gateway/seed/helsinki`
(87 manifests), most of the platform already obeys it and four places do not.

| What | Today | Copy-safe? |
|---|---|---|
| Pipeline, DataSource, Policy, Role, RoleBinding, Dashboard, ServiceAccount names | local (`citybikes-gbfs`, `public-bikes`, `stewards`) | yes |
| References between them (`contextSpaceRef`, `dataSourceRef`, `policyRef`, `endpointRef`, `serviceAccountRef`) | bare names, resolved inside the project | yes |
| Keycloak client of a ServiceAccount | rendered `{project}-{name}` | yes |
| Organization domain in entity ids | injected: `let domain = env("JC_ORG_DOMAIN")` | yes |
| Endpoint address | slug, minted where it lands | yes |
| Endpoint names | local by rule, but written with the project by habit (`helsinki-bikes`) | works; the copy in `espoo` is still called `helsinki-bikes` |
| **Space segment of entity ids inside mappings** | a string literal in every Bento file: `"urn:ngsi-ld:%v:%v:%v:%v".format("BikeHireDockingStation", $domain, "helsinki", …)` | **no**: a copied pipeline mints ids of the origin's space |
| **Context Space names** | prefix written in (`helsinki-hub`, `helsinki-kpi`) and referenced by that name | **no**: the one rename a project copy needs |
| **`did:web` of the organization in Policies** | a literal, `assigner: did:web:hel.fi`, written by the endpoint form (`assigner: \`did:web:${orgDomain}\``), the share tool and the KPI tool | **no** for an organization copy; CC-74 already forbids a domain literal and the loader already detects one (`literal_domains`) |
| **SharedSpaceReference** | `endpointSlug` of the source; the import door re-mints the endpoint's slug and does not touch the reference | **no**: after copying an organization, or two projects together, the reference points at a slug that does not exist there |

What can never be copied, and must be reported instead of failing later: secret values behind
`secretRef`, people (`user: demo.steward@hel.fi` in RoleBindings and Policies), hosts and
certificates (the Environment overlay), feed credentials. A copy ends with a list: "3 secrets to
provide, 4 people to map, 1 host to set", each linking to where.

## Related

- [ADR-N-004](adr-n-004-configuration-as-code-and-gitea.md) — configuration as code in Gitea.
- [ADR-N-021](adr-n-021-one-operation-registry-behind-ui-api-assistant-and-mcp.md) — one operation registry behind every door.
- [Architecture/06-configuration-as-code.md](../Architecture/06-configuration-as-code.md) — §7, workspaces and previews.
- [Requirements/city-as-code.md](../Requirements/city-as-code.md) — CC-34, CC-63, CC-67, CC-73, CC-74, CC-76…CC-81.
