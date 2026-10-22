---
sidebar_position: 59
title: "ADR-N-058: Several Organizations in One Installation"
---

# ADR-N-058: Several Organizations in One Installation

Date: 2026-10-22  
Status: Accepted  
Decision Makers: product owner (2026-10-22: Mesto Žilina "correctly create a new organization", <https://opendata.zilina.sk/sk/>); recorded by worker-t5238 (T-5238), owner may override

This record amends PF-01 and PF-02 ([Requirements/platform.md](../Requirements/platform.md)) and the Instance and Organization entries of [03-domain-model](../Architecture/03-domain-model.md).

## 1. Context

PF-01 makes an installation host exactly one Organization; a second organization is a second installation. The code follows it: jc-core places the one `Organization` at `org.yaml`, and the Portal reconciler and its Gitea client read that file as the organization. Every demo project (zilina, banskabystrica, bbsk, praha, slovensko, sharing) names `organizationRef: hel`, the City of Helsinki.

The owner wants the City of Žilina as an organization of its own on the same installation: its own administrators, its own Keycloak group subtree, its own CKAN organisation and its publisher in the catalogue. A second installation for one city costs a second node, realm and forge, and a city's open-data desk does not run a cluster.

PF-108 already lets one Organization host several publishers through `Project.spec.domain`. That field describes who publishes and grants nothing, so it cannot give Žilina administrators who hold no rights in Helsinki.

## 2. Decision

### 2.1 Files

An installation holds one or more Organizations, each at `organizations/{name}.yaml` of the organization repository. The legacy `org.yaml` still loads as one Organization; `jcctl validate` warns that it belongs at `organizations/{name}.yaml`, and the Portal reads both. Moving the file is one red-lane Change and changes nothing else.

### 2.2 The installation Organization

Exactly one Organization is the installation's. It owns what one installation has once: the configuration repository, the gateway's `{orgDomain}`, `JC_ORG_DOMAIN` for minting (PF-44), the brokers, environments, platform settings and organization-scoped kinds other than bindings and groups. With one Organization it is that one. With several, exactly one sets `spec.installation: true`, the legacy `org.yaml` counts as setting it, and a repository with none or two is refused naming the files.

Minting stays over the installation Organization's domain for every project. A project moved to another Organization keeps its ids, so the move duplicates no entity and loses no history, the same reasoning as PF-108.

### 2.3 Projects

`Project.spec.organizationRef` names the Organization that owns the project. `jcctl validate` and the Portal's verdict refuse a Project, file or registry entry, whose `organizationRef` names no Organization of the repository, naming `spec.organizationRef`. A project of an Organization other than the installation's publishes under that Organization: its `spec.domain`, when set, is that Organization's `spec.domain` or a subdomain of it, and anything else is refused naming `spec.domain`. Projects of the installation Organization keep PF-108's freedom to name another publisher.

An Organization may name its catalogue publisher, `spec.catalog` (the shape of `Project.spec.catalog`, EP-127). A project without a `spec.catalog` of its own takes its Organization's.

### 2.4 Rights end at the Organization

A `RoleBinding` with `spec.scope.organization: {name}` grants on that Organization's own settings and on the projects whose `organizationRef` is `{name}`, never on another Organization's. An org admin of `hel` therefore holds nothing in a project of `zilina`: proposing, approving and reading its private parts answer 403, as for anyone without a binding there. No seeded role, group or Policy spans two Organizations; reaching into a second one takes an explicit binding scoped to it.

The installation Organization's administrators also hold the installation-wide kinds of § 2.2 and propose or approve a new `Organization` manifest. Creating an Organization grants them nothing inside it: the same Change carries a `RoleBinding` that makes the named first administrator `org-admin` of the new Organization (PF-03).

A person sees an Organization when they hold a binding in it or in one of its projects, or when its project visibility (PF-61) reaches them.

### 2.5 Keycloak

Each Organization has its own group subtree `/{organization}` in the one realm, with the groups of that Organization under it. keycloak-config-cli creates and updates the subtree from the deployment's realm import; no group is made by hand. The realm, clients and audiences stay one per installation (PF-01 keeps the single realm).

### 2.6 CKAN

Each Organization is a CKAN organisation named `{name}` and titled from `metadata.title`. A dataset goes to the CKAN organisation of its project's Organization.

### 2.7 Portal

The top bar has an organization switcher when a person sees more than one Organization. It lists those Organizations by title and keeps the choice in the URL query `?org={name}`; the project list, the Administration page (UI-75) and the catalogue lists show the chosen Organization's. A person who sees one Organization gets no switcher.

## 3. Consequences

- PF-01 now reads "one or more Organizations"; PF-121…PF-124 carry § 2.1 to § 2.7.
- jc-core places `Organization` at `organizations/{name}.yaml` and adds `spec.installation` and `spec.catalog`; `jcctl validate` gains the checks of § 2.2 and § 2.3.
- The Portal reconciler, its Gitea client and the authorization of organization-scoped bindings follow § 2.1 and § 2.4. The deployment seed moves `hel` to `organizations/hel.yaml`, adds `organizations/zilina.yaml` and moves the project `zilina` to it, with its Keycloak subtree and CKAN organisation.
- The other demo projects stay under `hel`; moving one is its own decision.

## 4. Options considered

- **A second installation for Žilina.** PF-01 as written. Refused: a second node, realm and forge for one city, and the owner asked for an organization on this one.
- **Keep one Organization and give Žilina a project-scoped admin role.** Refused: a Helsinki org admin would keep every right in Žilina, and Žilina would have no organization settings, Keycloak subtree or CKAN organisation of its own.
- **Several Organizations, each its own repository and `{orgDomain}`.** Refused for now: every gateway route, overlay and minted id would become per organization, and moving a project would change its ids.
- **Several Organizations in one repository with one installation Organization** (chosen): the smallest change that gives each Organization its own rights, people and publisher while ids, routes and the repository stay as they are.

## Related

- [ADR-N-035](adr-n-035-organization-policies-and-limits.md) — organization policies and limits, per Organization.
- [ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md) — identity is (space, URN); nothing derives an organization from an id.
- [03-domain-model](../Architecture/03-domain-model.md) — Instance and Organization.
- [Requirements/platform.md](../Requirements/platform.md) — PF-01, PF-02, PF-121…PF-124.
