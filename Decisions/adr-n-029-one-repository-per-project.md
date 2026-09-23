---
sidebar_position: 30
title: "ADR-N-029: One Repository per Project, Assembled Through the Organization's Project Registry"
---

# ADR-N-029: One Repository per Project, Assembled Through the Organization's Project Registry

Date: 2026-09-22  
Status: Accepted  
Decision Makers: product owner (decision of 2026-09-22, T-2637, T-2638)

## 1. Context

The owner's direction (2026-09-22): "i think the projects should be in seperated git repositores", "it should be posible just to create a new project and implement the things and then data sources etc.... and then move the project to another digital twin", "i want versioning per project, with ENVs for example, that i can change when deploying somwhere else", "exporting the repo with the whole git structure", "admin give certian users access to this git repository and user should be able to use git commands with this project".

[ADR-N-004](adr-n-004-configuration-as-code-and-gitea.md) put an Organization's whole configuration into one Gitea repository, and PF-02 and CC-08 said so. That repository holds every project under `projects/{slug}/`. Two of the owner's asks cannot be met inside it:

- **Read access per project.** Git has no per-directory read control: a clone reads the whole repository and its history ([Research/city-as-code-prior-art §9.1](../Research/city-as-code-prior-art.md#91-repo-access-only-their-own-part)). A person who may clone "only this project" needs a repository that holds only this project.
- **A project that travels with its history.** Moving a project today is a YAML bundle and per-file checksums (MF-42). The owner wants the project's own Git history, tags and versions to go with it, which means a repository of its own.

The research named the answer in 2026: where read isolation is real, a domain gets its own repository, and the reconciler aggregates repositories through a declared fleet manifest (the Flux multi-repository and Argo ApplicationSet pattern).

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | Forge repositories, forge teams, forks, `git bundle` and tags are Git's and Gitea's own features; the platform adds a registry file and an assembly step. |
| Security by design | **Full** | Read access becomes a property of repository membership, which the forge enforces, instead of a promise the Portal keeps (PF-87). |
| Modular design | **Full** | A project is one repository, one registry entry and one set of teams; creating, copying and moving it are operations on those three. |
| Technological consistency | **Partial** | Every loader has to assemble N+1 checkouts into the tree the kinds address today (CC-86); the kinds and their paths inside a project stay the same. |
| Multi-tenancy | **Full** | A project member's forge token reaches that project's repository and nothing else, and the organization repository stays behind an organization binding. |

## 3. Decision

1. **Three kinds of repository.** An Organization has one *organization repository* and one *project repository* per Project; an application keeps a repository of its own (AP-72). The organization repository holds the organization-level kinds (`org.yaml`, `environments/`, `users/`, `blueprints/`, `agentprofiles/`, `portal/`, `policies/`) and the project registry. A project repository holds at its root what `projects/{slug}/` holds today (PF-85, CC-85).
2. **The project registry is the fleet manifest.** `projects/{slug}.yaml` in the organization repository, `kind: Project`, names the project's repository (a local forge repository, or an external git URL with a `secretRef`), the ref this deployment runs, and this deployment's parameter values. The registry slug renders `{project}`, not the repository name, so one repository can run under two slugs (PF-86). Adding, removing or repointing an entry is an organization change in the red lane.
3. **One render, assembled.** The reconciler, the gateway and the Portal fetch the organization checkout and every registered project checkout at its ref and assemble them into the virtual tree `projects/{slug}/…` the kinds address in layout 1. The kinds, their paths inside a project and every rule of the loader stay as they are; what was a directory walk becomes a walk over N+1 checkouts. Uniqueness across the organization (PF-44, endpoint slugs) is checked at assembly, and a project whose ref cannot be fetched renders at its last fetched ref and says so on its registry entry (CC-86).
4. **The layout is versioned.** Both repository kinds carry `.jc/layout`, one integer: 1 is today's single repository, 2 is this decision; an organization repository without the file is layout 1. A loader refuses a layout it does not know, and `jcctl migrate` is the only writer of a layout change (CC-85, MF-47).
5. **A project has a version and parameters.** `project.yaml` carries `spec.version` (semver) and `spec.parameters`, one declaration per knob a deployment sets (a subset of JSON Schema: `type`, `default`, `description`, `enum`, and the type `secret`). A manifest writes `{param:name}`, a mapping `env("JC_PARAM_<NAME>")`, beside `{orgDomain}` and `env("JC_ORG_DOMAIN")`. A release is the tag `v{version}`; the registry entry pins it and carries this deployment's values (CC-88).
6. **Membership is forge membership.** One Keycloak group per project maps, through the group→team mapping of PF-79, to the forge teams `{slug}-readers` (a binding with `read` on the project's kinds) and `{slug}-writers` (`propose` or more). Each team reaches its own project repository and no other. Git runs over HTTPS with the person's own forge credential, and the Portal never proxies it (PF-87).
7. **A Change targets one repository.** A project workspace is a branch of the project repository, an organization workspace a branch of the organization repository. An operation that touches both is two linked Changes; the organization one is red-lane and is applied first (CC-87).
8. **Lifecycle through the forge.** Creating a project creates the repository from the template and the registry entry in one operation, both or neither (PF-88). Deleting archives the repository and removes the entry (PF-77, PF-78). Duplicating is a fork or an import under a new slug with its own parameters (PF-89). Export is `git bundle` per repository with the head commit in the index; import creates the repositories, asks for the parameters and verifies each head (MF-45, MF-46).
9. **External projects.** A registry entry may name a git repository outside the forge: the platform mirrors it read-only at the pinned ref and refuses every edit through the Portal (CC-89). A `SyncSource` stays for subtrees such as model libraries and blueprint sets.

This supersedes the "one repository" half of ADR-N-004; its configuration plane (Git as the source of truth, CI gates, the reconciler) stands. It amends [ADR-N-024](adr-n-024-workspaces-branch-and-preview.md): a workspace is a branch of the project repository, not of the organization repository.

## 4. Alternatives Considered

- **Monorepo and sparse checkout.** A sparse or partial clone narrows what lands on disk, not what the server lets a person fetch; anyone who can clone the path can fetch the rest. It meets none of PF-87.
- **Monorepo and `SyncSource` mirrors.** One mirror repository per project, synced from the monorepo, gives read isolation for readers but two sources of truth for writers; every push to a mirror has to be carried back through an import and conflicts become the platform's.
- **Git submodules.** Submodules pin project repositories inside the organization repository, which is the registry with worse tools: every ref bump is a commit in the parent, the parameters have nowhere to live, and a clone of the parent without access to one submodule fails.

## 5. Security Analysis

- **The new read boundary (PF-87).** A project repository is readable by `{slug}-readers`, `{slug}-writers` and the forge organization's owners, and by nobody else. A forge credential of a project member reaches that project's repository and none other, and the organization repository is readable only with a binding at the organization. The seeded team `readers` of PF-79 moves from "every signed-in person" to "every person with an organization binding".
- **What the registry exposes.** A registry entry names a repository, a ref and parameter values; a parameter of type `secret` is a `secretRef` name, never a value (CC-88). Editing an entry repoints what a project runs, which is why it is red-lane.
- **Agents (AG-86).** An agent workspace clones the project repository with a credential scoped to that repository, issued by the credential proxy, and touches the organization repository only through an organization-level operation with its own Change. A project agent therefore cannot read another project's configuration or the organization's roles.
- **Pushes that skip review.** A writer can push a branch with git, as before; `main` is protected in every project repository and merging stays the Portal's approval (PF-80, PF-88).
- **Assembly is a gate.** Two projects that would claim one organization-unique name are refused at assembly, so a project repository cannot take over another project's endpoint slug or space segment (CC-86, PF-44).

## 6. What Changes

- **Requirements:** PF-85…PF-89, CC-85…CC-90, MF-45…MF-47 and AG-86, with PF-02 and CC-08 superseded and PF-79, CC-76, CC-83 and MF-42 amended ([T-2637](../Requirements/platform.md#project-repositories)).
- **Architecture:** [06 §1](../Architecture/06-configuration-as-code.md#1-repository-layout-cc-08-cc-85), §3, §6, §7 and §8; [03](../Architecture/03-domain-model.md#project); [12](../Architecture/12-identity-and-access.md); [07](../Architecture/07-agents-and-mcp.md) and [19](../Architecture/19-agent-runner.md).
- **Deployment and operations:** [Deployment/11](../Deployment/11-moving-a-project.md) (the git-native move), [Deployment/07](../Deployment/07-backup-restore.md) (N+1 repositories), [Operations/01](../Operations/01-runbooks.md) (the migration from layout 1).
- **Code:** jc-core (T-2639), `jcctl` (T-2640), the gateway's store (T-2641), the Portal (T-2642…T-2645), the deployment (T-2646).

## Related

- [ADR-N-004](adr-n-004-configuration-as-code-and-gitea.md) — the configuration plane whose "one repository" half this replaces.
- [ADR-N-024](adr-n-024-workspaces-branch-and-preview.md) — workspaces, now branches of the project repository.
- [Research/city-as-code-prior-art §9.1](../Research/city-as-code-prior-art.md#91-repo-access-only-their-own-part) — the fleet manifest this decision adopts.
- [Requirements/platform §Project repositories](../Requirements/platform.md#project-repositories) — PF-85…PF-89.
- [Requirements/city-as-code §15](../Requirements/city-as-code.md#15-repositories-per-project) — CC-85…CC-90.
