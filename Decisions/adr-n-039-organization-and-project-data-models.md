---
sidebar_position: 40
title: "ADR-N-039: Data Models at Organization and Project Level, Shared Upwards Only by an Administrator"
---

# ADR-N-039: Data Models at Organization and Project Level, Shared Upwards Only by an Administrator

Date: 2026-09-25  
Status: Accepted  
Decision Makers: product owner (decision of 2026-09-25, T-2878)

## 1. Context

Every `DataModel` today belongs to one Context Space of one project (DM-01, DM-61, ADR-N-033). A space may `import` another published model at a pinned version, and `GET /api/v1/organization/datamodels` lists every model the caller may read (DM-63). The organization itself holds no model. So a city that wants one "Air quality" model for every department copies it into each project, and the copies drift.

The owner's direction of 2026-09-25 sets three rules:

1. Data models exist at the organization level and at the project level. An organization model is usable by every project of the organization. A project model belongs to its project alone. The Data models page shows both, apart.
2. A project may propose sharing its model with the organization. The promotion is a Change that an organization administrator approves (red lane, PF-58). Until then the model stays in the project, and nothing lands in the organization catalogue by a project's own decision.
3. A whole project exported and imported elsewhere (MF-45, MF-46, PF-89, T-2647) keeps working: the export carries every model the project uses, and an import never dangles on a model the destination lacks and never overwrites an organization model.

### 1.1 What CIVITAS Core does

The legacy reference in this checkout (`civitas-core-docs_v2/Architecture/`) places everything inside one Tenant: "Organizational entity owning DataPools, DataSets, and users" (`domain_model.md`), and "What happens in one tenant does **not** affect any other" (`Architecture_General/Authorization_Data_Model.md`). A `DataStructure` has scopes "tenant, dataStructure" only, so a schema is tenant-wide, with no pool or project level beneath it. The Data Architect defines "commonly used data models". Creating and updating a structure is open to the Data Owner, the Data Steward and the Data Architect, and RELEASE to the Data Owner and the Data Gatekeeper. The docs name no approval workflow, no version pinning ("processed and versioned through model management", `Modelcentric_Dataflow.md`, with no rule on what a dataset consumes), and no export or move between installations.

| From CIVITAS Core | Here |
|---|---|
| The model is the unit a dataset is typed by (model-centric dataflow) | **Adopted.** A space's one model is its type system (DM-61). |
| Models sit at the tenant level, curated by a data architect | **Adopted** as the organization level, curated by an organization administrator. |
| Release is a separate right held by an owner or gatekeeper | **Adopted** as `approve` on `DataModel` at organization scope, and made a workflow: a red-lane Change with a named approver (PF-58). |
| No level below the tenant | **Different.** A project owns models of its own. That lets a department model without asking, and asking is only needed to share. |
| Versioning is claimed, not tied to consumption | **Different.** A consumer pins a major (DM-22). An organization model never changes under a project that uses it. |
| No export or move | **Different.** A project bundle carries the models it uses (MF-49, MF-50). |

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | LinkML `imports`, the existing `DataModel` kind, the Change and its lanes, the git-native bundle. No new kind. |
| Technological consistency | **Full** | One model format and one manifest kind at both levels. A promotion is an ordinary Change against the organization repository. |
| Security by design | **Full** | Only an organization-scope `approve` publishes a model for everyone. An agent or a bearer caller never approves (PF-58). A bundle carries schema files only. |
| Modular design | **Full** | Levels, promotion, and export/import are separate follow-up tasks with their own tests. |
| Multi-tenancy | **Full** | An organization model is read across the organization's projects and never across organizations. An import never writes into the destination's organization repository. |

## 3. Decision

### 3.1 Two levels, one kind

- **Organization model.** Kept in the organization repository at `datamodels/{name}/{name}.yaml` with its source `{name}.linkml.yaml` beside it. `kind: DataModel` without `metadata.namespace` and without `spec.contextSpaceRef`. Every person holding any binding in the organization reads it, because a schema carries no data. It changes only through Changes to the organization repository, in the red lane.
- **Project model.** Every space model (DM-61) is a project model. A project may also keep a model that no single space owns at `projects/{p}/datamodels/{name}/`. This is `kind: DataModel` with `metadata.namespace` and no `spec.contextSpaceRef`, and it is what an import lands a carried model as (§3.4). Only the project's readers see it.
- **Use.** A space still has exactly one model (DM-61). That model uses a shared one by `import` at a pinned major: an organization model or a project model of its own project, never another project's. The Portal resolves the import from the repository at that version and hands Model Tools the imported source beside the model, because Model Tools reads no platform state (Architecture/11 §6.5). An organization model that a space imports cannot be deleted. The refusal names the importers, and `retired` (DM-26) is the way out.
- **Page and pickers.** The Data models page shows "Organization models" and "This project's models" as two sections. Every model picker (ADR-N-033) shows the level of each entry. `GET /api/v1/organization/datamodels` gains `level`.

### 3.2 Promotion is a red-lane Change an organization administrator approves

A person with `propose` on `DataModel` in a project may propose sharing a published model with the organization. The Change copies the model at its current version into `datamodels/{name}/` of the organization repository. The LinkML source is kept byte for byte, every `class_uri` and `slot_uri` included, so entities typed by it keep their meaning. The copy records `spec.origin` (`project`, `space`, `name`, `version`, `commit`).

- The Change is in the red lane. Only a person whose binding at **organization** scope grants `approve` on `DataModel` approves it, with the typed name (CC-19). An approval by a project-scope approver is refused `403`. An agent run, MCP or a bearer caller may propose and never approve (PF-58, AG-11).
- The PF-58 self-approval applies unchanged: an organization administrator who promotes their own model approves it at propose, with the name typed.
- A name taken by an organization model of another origin is refused `409` naming it. A promotion from the same origin proposes that organization model's next version, and a breaking change makes it a new major (DM-22).
- Until the Change merges, the model stays in the project and nothing else moves.

### 3.3 After promotion, the organization edits and projects consume versions

An organization model is edited only at the organization level, by Changes to the organization repository. Projects consume a pinned major and move to a new one by editing their own model's `import`, which is a project Change. After the promotion merges, the promoting space keeps its model unchanged. The Portal offers the project a Change that swaps the space model's own classes for an import of the organization model at the promoted version, the same class names and IRIs, so no entity id changes. Nothing rewrites a project on its own.

### 3.4 Export carries the models, import lands them without overwriting

- **Export (MF-49).** The project bundle of MF-45 adds a copy of every organization model that a space of the project imports, at the pinned version. The `kind: Bundle` index lists each copy with its name, version, the SHA-256 of its LinkML source and its origin (organization and name). The bundle holds schema files only: no secret, no credential and no entity data.
- **Import (MF-50).** For each carried model, the destination either:
  - maps it onto an organization model of the same name whose published version of that major has a byte-identical source, and the space's import stays as it is; or
  - lands it as a project model at `projects/{slug}/datamodels/{name}/`, with `spec.origin` kept, and rewrites the spaces' imports to it in the same import Change.

  The import preview shows which of the two happens to each model before the person proposes. An import never writes into the destination's organization repository and never replaces an organization model. A carried model that is neither mapped nor landed refuses the import, naming the model.

## 4. Alternatives Considered

- **One organization-wide catalogue, no project models.** Every department would wait on an administrator to model anything. The owner kept the project level.
- **A project shares its model by itself (green or yellow lane).** Then the organization catalogue would stop being curated, and one project's edit would change every consumer. The owner ruled that an administrator approves it.
- **Organization models edited in their project of origin.** One project would own a schema that every project depends on. The organization owns the promoted copy instead, and the origin is recorded, not linked.
- **An export that references organization models by name only.** An import into another organization or instance would dangle. The bundle carries copies.
- **An import that writes the carried models into the destination's organization catalogue.** That would bypass §3.2. A project import stays a project Change.

## 5. Consequences

- DM-74…DM-78 and MF-49…MF-50 are new. DM-63's list gains `level`, and DM-01 gains the two new paths (T-2886).
- Work, filed against this ADR:
  - T-2886: the two levels in `jc-core` and the loaders, plus import resolution.
  - T-2883: the Data models page sections, the pickers' level, and `level` in DM-63.
  - T-2884: promotion as a red-lane Change with organization-scope approval.
  - T-2885: export and import of the models a project uses, plus the round-trip test.
- The round-trip live check runs after T-2885, in the integrator's hourly journey on dev: a project that uses one organization model and one project model is exported, imported under a new slug and works.

## Related

- [ADR-N-033](adr-n-033-one-data-model-per-space.md): one model per space, pickers everywhere.
- [ADR-N-029](adr-n-029-one-repository-per-project.md): the organization repository and one repository per project.
- [Requirements/data-models](../Requirements/data-models.md): DM-74…DM-78.
- [Requirements/manifests](../Requirements/manifests.md): MF-49…MF-50.
- [Architecture/11-data-models](../Architecture/11-data-models.md): `kind: DataModel`, Model Tools.
